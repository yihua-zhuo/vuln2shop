import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchSqlInjectionSecurityTest(unittest.TestCase):
    def test_search_cannot_return_nonmatching_products_through_sql_syntax(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / 'shop.db'
            application = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-regression-test-only',
                'DATABASE': str(database_path),
            })
            product_marker = 'SearchSentinel'
            with sqlite3.connect(database_path) as database:
                database.execute(
                    'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                    (product_marker, 'Harmless regression fixture.', 100),
                )

            client = application.test_client()
            ordinary_response = client.get('/', query_string={'q': product_marker})
            missing_response = client.get('/', query_string={'q': 'absent'})

            self.assertEqual(
                (ordinary_response.status_code, missing_response.status_code),
                (200, 200),
                'Ordinary unauthenticated searches must remain available',
            )
            self.assertIn(product_marker, ordinary_response.get_data(as_text=True))
            self.assertNotIn(product_marker, missing_response.get_data(as_text=True))

            injection_response = client.get(
                '/', query_string={'q': "absent' OR 1=1 -- "},
            )
            self.assertTrue(
                injection_response.status_code == 200
                or 400 <= injection_response.status_code < 500,
                'Search must treat SQL syntax as data or reject it without a server error',
            )
            self.assertNotIn(
                product_marker,
                injection_response.get_data(as_text=True),
                'SQL syntax in a search term must not expose a nonmatching product',
            )
