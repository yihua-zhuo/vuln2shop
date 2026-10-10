"""Regression coverage for unauthenticated product-search SQL injection."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app import create_app


class ProductSearchSecurityTest(unittest.TestCase):
    def test_search_text_cannot_expose_an_unrelated_product(self):
        product_marker = "search-fixture-product-marker"
        with tempfile.TemporaryDirectory(prefix="search-security-") as directory:
            database = Path(directory) / "shop.db"
            app = create_app({
                "TESTING": True,
                "SECRET_KEY": "search-security-test-only",
                "DATABASE": str(database),
            })
            with closing(sqlite3.connect(database)) as db:
                db.execute(
                    "INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)",
                    (product_marker, "Temporary search fixture.", 100),
                )
                db.commit()

            client = app.test_client()

            # A partial search must show the complete marker from the product row,
            # so merely reflecting the search text cannot satisfy this control.
            matching = client.get("/", query_string={"q": "search-fixture"})
            self.assertEqual(matching.status_code, 200)
            self.assertIn(product_marker, matching.get_data(as_text=True))

            missing = client.get("/", query_string={"q": "no-such-product"})
            self.assertEqual(missing.status_code, 200)
            self.assertNotIn(product_marker, missing.get_data(as_text=True))

            # This minimal quote/comment input turns the vulnerable LIKE clause
            # into a match-all query. It reads only this temporary test database.
            response = client.get("/", query_string={"q": "'--"})
            self.assertTrue(
                response.status_code == 200 or 400 <= response.status_code < 500,
                "Search must handle the text normally or explicitly reject it.",
            )
            self.assertNotIn(
                product_marker,
                response.get_data(as_text=True),
                "Search text changed the query and exposed an unrelated product.",
            )


if __name__ == "__main__":
    unittest.main()
