"""Search text must not change the database query's meaning."""

from app import create_app


def test_anonymous_search_cannot_return_unrelated_products(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "shop.db"),
        "SECRET_KEY": "search-regression-test-only",
    })
    client = app.test_client()
    product = "复古相机"
    marker = "no-match-xyz"

    # Establish that ordinary search works and the marker matches nothing.
    matching = client.get("/", query_string={"q": product})
    assert matching.status_code == 200
    assert product in matching.get_data(as_text=True)
    missing = client.get("/", query_string={"q": marker})
    assert missing.status_code == 200
    assert product not in missing.get_data(as_text=True)

    # A benign true condition must remain search text, not become SQL logic.
    response = client.get("/", query_string={"q": marker + "' OR 1=1 -- "})
    assert response.status_code in (200, 400, 422)
    assert product not in response.get_data(as_text=True), (
        "SQL-like search input disclosed a product unrelated to the search"
    )
