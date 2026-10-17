"""Public product searches must treat SQL syntax as search text."""

from pathlib import Path
import sqlite3
import tempfile
import unittest

from app import create_app


class SearchSqlSecurityTest(unittest.TestCase):
    def test_search_cannot_bypass_product_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'shop.db'
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-sql-security-test',
                'DATABASE': str(database),
            })
            marker = 'search-security-marker'
            with sqlite3.connect(database) as connection:
                connection.execute(
                    'INSERT INTO products (name, description, price_cents) '
                    'VALUES (?, ?, ?)',
                    (marker, 'An ordinary test product', 100),
                )

            with app.test_client() as client:
                ordinary = client.get('/', query_string={'q': marker})
                self.assertEqual(ordinary.status_code, 200)
                self.assertIn(marker, ordinary.get_data(as_text=True))

                response = client.get('/', query_string={'q': "' --"})
                self.assertIn(response.status_code, (200, 400, 422))
                self.assertNotIn(
                    marker, response.get_data(as_text=True),
                    'Search SQL syntax bypassed the product filter',
                )


if __name__ == '__main__':
    unittest.main()
