"""Product searches must not treat user input as SQL syntax."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app import create_app


class ProductSearchSQLInjectionTest(unittest.TestCase):
    def test_search_cannot_return_an_unrelated_product(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = str(Path(temporary_directory) / "shop.db")
            application = create_app({
                "TESTING": True,
                "SECRET_KEY": "search-security-test-only",
                "DATABASE": database,
            })
            product_name = "SearchControlProductMarker"
            with closing(sqlite3.connect(database)) as connection:
                with connection:
                    connection.execute(
                        "INSERT INTO products (name, description, price_cents) "
                        "VALUES (?, ?, ?)",
                        (product_name, "A harmless regression test product.", 100),
                    )

            client = application.test_client()

            # The full product name is not in the request, so reflected search
            # text alone cannot satisfy this positive control.
            matching = client.get("/", query_string={"q": "SearchControl"})
            self.assertEqual(matching.status_code, 200)
            self.assertIn(product_name, matching.get_data(as_text=True))

            missing_term = "no-match-xyz"
            missing = client.get("/", query_string={"q": missing_term})
            self.assertEqual(missing.status_code, 200)
            self.assertNotIn(product_name, missing.get_data(as_text=True))

            # A benign true predicate in an isolated database is sufficient;
            # no private tables or credentials need to be queried.
            response = client.get(
                "/", query_string={"q": missing_term + "' OR 1=1 -- "}
            )
            self.assertTrue(
                response.status_code == 200 or 400 <= response.status_code < 500,
                "The search should treat the input as text or reject it cleanly.",
            )
            self.assertNotIn(
                product_name,
                response.get_data(as_text=True),
                "Search input changed the query and exposed an unrelated product.",
            )


if __name__ == "__main__":
    unittest.main()
