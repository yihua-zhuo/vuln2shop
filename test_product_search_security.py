import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class ProductSearchSecurityTest(unittest.TestCase):
    def test_search_cannot_return_nonmatching_products(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        database_path = Path(temporary_directory.name) / 'shop.db'
        application = create_app({
            'TESTING': True,
            'SECRET_KEY': 'product-search-test-only',
            'DATABASE': str(database_path),
        })
        product_names = ('SearchAlphaMarker', 'SearchBetaMarker')
        with sqlite3.connect(database_path) as database:
            database.execute('DELETE FROM products')
            database.executemany(
                'INSERT INTO products (id, name, description, price_cents) '
                'VALUES (?, ?, ?, ?)',
                [(101, product_names[0], 'First fixture product', 100),
                 (102, product_names[1], 'Second fixture product', 200)],
            )

        client = application.test_client()
        ordinary_response = client.get('/', query_string={'q': product_names[0]})
        self.assertEqual(ordinary_response.status_code, 200)
        self.assertIn(product_names[0], ordinary_response.get_data(as_text=True))
        self.assertNotIn(product_names[1], ordinary_response.get_data(as_text=True))

        response = client.get('/', query_string={'q': "' OR '"})
        self.assertTrue(
            response.status_code == 200 or 400 <= response.status_code < 500,
            'Search syntax must be handled as literal text or explicitly rejected',
        )
        response_text = response.get_data(as_text=True)
        self.assertFalse(
            any(product_name in response_text for product_name in product_names),
            'Search syntax must not expose nonmatching products',
        )


if __name__ == '__main__':
    unittest.main()
