"""Order details must remain private to the shopper who placed the order."""

from html.parser import HTMLParser
import re

from app import create_app


class _Page(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.csrf = None
        self.order_urls = []
        self.text = []
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "csrf":
            self.csrf = attrs.get("value")
        if tag == "a" and re.fullmatch(r"/orders/\d+", attrs.get("href") or ""):
            self.order_urls.append(attrs["href"])

    def handle_data(self, data):
        self.text.append(data)

    @property
    def visible_text(self):
        return " ".join(" ".join(self.text).split())


def _post_form(client, form_url, action_url, data=None):
    form = client.get(form_url)
    assert form.status_code == 200, "The setup form must be available"
    page = _Page(form.get_data(as_text=True))
    assert page.csrf, "The setup form must provide a CSRF token"
    response = client.post(
        action_url,
        data={**(data or {}), "csrf": page.csrf},
        follow_redirects=True,
    )
    assert response.status_code == 200, "The normal shopping flow must succeed"
    return response


def _register_and_login(client, username):
    credentials = {"username": username, "password": "test-password"}
    _post_form(client, "/register", "/register", credentials)
    _post_form(client, "/login", "/login", credentials)
    assert client.get("/orders").status_code == 200, "The shopper must be logged in"


def test_another_shopper_cannot_read_order_details(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "order-access-test-only",
        "DATABASE": str(tmp_path / "shop.db"),
    })
    owner = app.test_client()
    other_shopper = app.test_client()

    _register_and_login(owner, "order-owner")
    _post_form(owner, "/cart", "/cart", {"product_id": "1", "quantity": "1"})
    receipt = _post_form(owner, "/cart", "/checkout")
    order_urls = _Page(receipt.get_data(as_text=True)).order_urls
    assert len(order_urls) == 1, "Checkout must create one order with a detail link"
    order_url = order_urls[0]

    owner_response = owner.get(order_url)
    assert owner_response.status_code == 200, "The owner must retain order access"
    private_details = ("复古相机 × 1", "合计 ¥199.00")
    owner_text = _Page(owner_response.get_data(as_text=True)).visible_text
    for detail in private_details:
        assert detail in owner_text, "The owner's order must contain the purchased item"

    _register_and_login(other_shopper, "other-shopper")
    own_orders = other_shopper.get("/orders")
    assert "暂无订单" in own_orders.get_data(as_text=True), "The other shopper has no orders"

    response = other_shopper.get(order_url, follow_redirects=True)
    # Accept denial, redirects, or a filtered page, but never a crash or leaked details.
    for page_response in (*response.history, response):
        assert 200 <= page_response.status_code < 500, "Access control must not crash"
        text = _Page(page_response.get_data(as_text=True)).visible_text
        for detail in private_details:
            assert detail not in text, (
                "An authenticated shopper received another shopper's order details: "
                f"{detail!r}"
            )
