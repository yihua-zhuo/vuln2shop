"""Public search must treat SQL-looking text as data or reject it."""

import sqlite3

from app import create_app


def test_public_search_cannot_turn_a_no_match_into_a_match(tmp_path):
    database = tmp_path / "shop.db"
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "search-regression-only",
        "DATABASE": str(database),
    })
    marker = "search_security_canary"
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM products")
        connection.execute(
            "INSERT INTO products (id, name, description, price_cents) "
            "VALUES (?, ?, ?, ?)",
            (1, marker, "Synthetic test product", 100),
        )

    # A fresh client has no authenticated account.
    client = app.test_client()
    ordinary = client.get("/", query_string={"q": "canary"})
    assert ordinary.status_code == 200 and marker in ordinary.get_data(as_text=True), (
        "Ordinary search must find the synthetic product"
    )
    missing = client.get("/", query_string={"q": "no-match"})
    assert missing.status_code == 200 and marker not in missing.get_data(as_text=True), (
        "A nonmatching ordinary search must not return the synthetic product"
    )

    response = client.get("/", query_string={"q": "no-match' OR 1=1 -- "})
    assert response.status_code in (200, 400, 422), (
        "SQL-looking search text must be handled normally or explicitly rejected"
    )
    assert marker not in response.get_data(as_text=True), (
        "SQL search syntax exposed a product that does not match the search text"
    )
