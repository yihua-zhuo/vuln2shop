import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchSqlSecurityTest(unittest.TestCase):
    def test_search_input_cannot_change_product_selection(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / 'shop.db'
            application = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test-only',
                'DATABASE': str(database_path),
            })
            product_name = 'fixture-only-needle'
            with sqlite3.connect(database_path) as database:
                database.execute(
                    'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                    (product_name, 'Isolated search fixture', 100),
                )

            client = application.test_client()
            ordinary_response = client.get('/', query_string={'q': 'needle'})
            self.assertEqual(ordinary_response.status_code, 200)
            self.assertIn(product_name, ordinary_response.get_data(as_text=True))

            response = client.get('/', query_string={'q': "needle' --"})
            self.assertLess(
                response.status_code, 500,
                'Search must safely handle or reject quote/comment input',
            )
            self.assertNotIn(
                product_name, response.get_data(as_text=True),
                'Search input changed SQL selection and exposed a nonmatching product',
            )


if __name__ == '__main__':
    unittest.main()
