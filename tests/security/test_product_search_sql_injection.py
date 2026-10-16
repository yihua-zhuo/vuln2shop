import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class ProductSearchSQLInjectionSecurityTest(unittest.TestCase):
    def test_search_syntax_cannot_expose_unmatched_products(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'shop.db'
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'security-test-only',
                'DATABASE': str(database),
            })
            marker = 'catalog-security-marker'
            with sqlite3.connect(database) as connection:
                connection.execute(
                    'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                    (marker, 'Synthetic regression-test product', 100),
                )

            client = app.test_client()
            ordinary = client.get('/', query_string={'q': marker})
            self.assertEqual(ordinary.status_code, 200)
            self.assertIn(marker, ordinary.get_data(as_text=True))

            unmatched = client.get('/', query_string={'q': 'absent-search-term'})
            self.assertNotIn(marker, unmatched.get_data(as_text=True))

            response = client.get('/', query_string={'q': "'--"})
            self.assertIn(
                response.status_code, (200, 400, 422),
                'Search syntax must be handled as data or rejected cleanly',
            )
            self.assertNotIn(
                marker, response.get_data(as_text=True),
                'Search syntax exposed a product that does not match the search term',
            )
