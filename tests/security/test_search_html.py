from html.parser import HTMLParser

from app import create_app


class ElementParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def test_search_query_cannot_create_html_elements(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "search-regression-test",
        "DATABASE": str(tmp_path / "shop.db"),
    })
    with app.test_client() as client:
        baseline = client.get("/", query_string={"q": "search-marker"})
        response = client.get("/", query_string={"q": "<b>search-marker</b>"})

    assert baseline.status_code == 200
    # Rejecting markup is also secure; server errors are not a successful fix.
    assert response.status_code in (200, 400, 422)
    baseline_html = ElementParser()
    baseline_html.feed(baseline.get_data(as_text=True))
    search_html = ElementParser()
    search_html.feed(response.get_data(as_text=True))
    assert search_html.tags.count("b") <= baseline_html.tags.count("b"), (
        "The search query created an HTML element instead of remaining inert text"
    )
