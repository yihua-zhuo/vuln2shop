import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class ProductSearchSqlInjectionTest(unittest.TestCase):
    def test_search_text_cannot_change_the_product_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'shop.db')
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'security-test-only',
                'DATABASE': database,
            })
            marker = 'security-search-fixture-product'
            connection = sqlite3.connect(database)
            try:
                with connection:
                    connection.execute(
                        'INSERT INTO products (name, description, price_cents) '
                        'VALUES (?, ?, ?)',
                        (marker, 'Harmless regression fixture.', 100),
                    )
            finally:
                connection.close()

            client = app.test_client()

            # The full marker is not in the search term, so reflection of the
            # term cannot satisfy this control assertion.
            matching = client.get('/', query_string={'q': 'search-fixture'})
            self.assertEqual(matching.status_code, 200)
            self.assertIn(marker, matching.get_data(as_text=True))

            missing = client.get('/', query_string={'q': 'absent-search-term'})
            self.assertEqual(missing.status_code, 200)
            self.assertNotIn(marker, missing.get_data(as_text=True))

            # Neither fixture field contains this text. In an interpolated
            # SQLite query it joins two '%' strings, matching every product.
            response = client.get('/', query_string={'q': "'||'"})
            self.assertIn(
                response.status_code, (200, 400, 403, 422),
                'Search must handle the text normally or explicitly reject it.',
            )
            self.assertNotIn(
                marker, response.get_data(as_text=True),
                'Search text must not alter SQL and return a non-matching product.',
            )


if __name__ == '__main__':
    unittest.main()
