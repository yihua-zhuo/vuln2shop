"""Regression coverage for unauthenticated product-search SQL injection."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app import create_app


class ProductSearchSecurityTest(unittest.TestCase):
    def test_search_punctuation_cannot_return_an_unmatched_product(self):
        marker = "PublicSearchRegressionMarker"
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "shop.db"
            application = create_app({
                "TESTING": True,
                "SECRET_KEY": "search-regression-test-only",
                "DATABASE": str(database),
            })
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)",
                    (marker, "A harmless public product for the search test.", 100),
                )
                connection.commit()

            client = application.test_client()
            matching = client.get("/", query_string={"q": "PublicSearch"})
            self.assertEqual(matching.status_code, 200)
            self.assertIn(marker, matching.get_data(as_text=True))

            missing = client.get("/", query_string={"q": "no-such-product"})
            self.assertEqual(missing.status_code, 200)
            self.assertNotIn(marker, missing.get_data(as_text=True))

            # Neither product field contains this literal text. Interpolating it
            # into SQL instead ends the LIKE string and comments out the filter.
            response = client.get(
                "/", query_string={"q": "'--"}, follow_redirects=True,
            )
            self.assertLess(response.status_code, 500,
                            "Search punctuation must not cause a server error.")
            self.assertNotIn(
                marker,
                response.get_data(as_text=True),
                "Search punctuation must not return an unrelated public product; "
                "the input must be treated as search text or rejected.",
            )


if __name__ == "__main__":
    unittest.main()
