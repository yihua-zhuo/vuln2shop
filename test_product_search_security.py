"""Product searches must treat SQL-looking input as data or reject it."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app import create_app


class ProductSearchSecurityTest(unittest.TestCase):
    def test_search_cannot_change_predicates_or_add_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'shop.db')
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-regression-test-only',
                'DATABASE': database,
            })
            product_marker = 'catalog-security-fixture'
            with closing(sqlite3.connect(database)) as db:
                with db:
                    db.execute(
                        'INSERT INTO products (name, description, price_cents) '
                        'VALUES (?, ?, ?)',
                        ('Regression sample product', product_marker, 100),
                    )

            # Use an anonymous client and confirm ordinary search still works.
            client = app.test_client()
            response = client.get('/', query_string={'q': 'Regression sample'})
            self.assertEqual(response.status_code, 200)
            self.assertIn(product_marker, response.get_data(as_text=True))
            response = client.get('/', query_string={'q': 'zz'})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(product_marker, response.get_data(as_text=True))

            probes = (
                ("zz' OR 1 --", product_marker),
                # Constants only: no user records or other tables are read.
                # Concatenation keeps the marker out of the echoed search term.
                ("zz' UNION SELECT 0,'union-'||'probe','',0 --", 'union-probe'),
            )
            for query, forbidden_marker in probes:
                with self.subTest(query=query):
                    response = client.get('/', query_string={'q': query})
                    self.assertIn(response.status_code, (200, 400, 403, 422))
                    self.assertNotIn(
                        forbidden_marker,
                        response.get_data(as_text=True),
                        'Search input must not expose an unrelated product or '
                        'create a result row by executing SQL.',
                    )


if __name__ == '__main__':
    unittest.main()
