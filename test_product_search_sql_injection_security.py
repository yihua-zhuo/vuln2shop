import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app import create_app


class ProductSearchSqlInjectionSecurityTest(unittest.TestCase):
    def test_search_input_cannot_expand_product_results(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / 'shop.db'
            application = create_app({
                'TESTING': True,
                'SECRET_KEY': 'security-test-only',
                'DATABASE': str(database_path),
            })
            product_marker = 'Security catalogue sentinel'
            with closing(sqlite3.connect(database_path)) as database:
                database.execute(
                    'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                    (product_marker, 'ordinary-coffee-marker', 100),
                )
                database.commit()

            client = application.test_client()
            ordinary_response = client.get('/', query_string={'q': 'ordinary-coffee-marker'})
            missing_response = client.get('/', query_string={'q': 'missing'})
            self.assertEqual(
                (ordinary_response.status_code, missing_response.status_code),
                (200, 200),
                'Ordinary product searches must succeed without authentication',
            )
            self.assertIn(product_marker, ordinary_response.get_data(as_text=True))
            self.assertNotIn(product_marker, missing_response.get_data(as_text=True))

            response = client.get('/', query_string={'q': "missing' OR 1=1 -- "})
            self.assertIn(
                response.status_code,
                (200, 400, 422),
                'Search must safely handle or reject SQL-like input, not fail internally',
            )
            self.assertNotIn(
                product_marker,
                response.get_data(as_text=True),
                'Search text must not alter the SQL predicate to reveal nonmatching products',
            )


if __name__ == '__main__':
    unittest.main()
