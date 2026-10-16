import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchSqlInjectionSecurityTest(unittest.TestCase):
    def test_search_does_not_reinterpret_apostrophes_as_sql(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'shop.db'
            application = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test-only',
                'DATABASE': str(database),
            })
            marker = 'literal-quote-control'
            with sqlite3.connect(database) as connection:
                connection.execute(
                    'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                    (marker, "A single apostrophe: '", 100),
                )

            with application.test_client() as client:
                ordinary_response = client.get('/', query_string={'q': marker})
                self.assertEqual(ordinary_response.status_code, 200)
                self.assertIn(marker, ordinary_response.get_data(as_text=True))

                quote_response = client.get('/', query_string={'q': "''"})
                self.assertIn(quote_response.status_code, (200, 400, 422))
                self.assertNotIn(
                    marker,
                    quote_response.get_data(as_text=True),
                    'Search must not reinterpret doubled apostrophes as SQL quoting',
                )
