import sqlite3
import tempfile
import unittest
from html import unescape
from pathlib import Path

from app import create_app


class ProductSearchSqlInjectionTest(unittest.TestCase):
    def test_search_keeps_apostrophes_as_literal_data(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'shop.db'
            application = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test-only',
                'DATABASE': str(database),
            })
            marker = 'QUOTE_BOUNDARY_MARKER'
            with sqlite3.connect(database) as connection:
                connection.execute(
                    'INSERT INTO products (id, name, description, price_cents) '
                    'VALUES (?, ?, ?, ?)',
                    (101, f"{marker}'s notebook", "Writer's notebook", 100),
                )

            client = application.test_client()
            ordinary_response = client.get('/', query_string={'q': marker})
            self.assertEqual(ordinary_response.status_code, 200)
            self.assertIn(
                f"{marker}'s notebook",
                unescape(ordinary_response.get_data(as_text=True)),
            )

            response = client.get('/', query_string={'q': "''"})
            self.assertIn(
                response.status_code,
                (200, 400, 422),
                'Search must handle quote characters normally or reject them safely',
            )
            self.assertNotIn(
                marker,
                response.get_data(as_text=True),
                'Search returned a product that does not contain the literal search term',
            )


if __name__ == '__main__':
    unittest.main()
