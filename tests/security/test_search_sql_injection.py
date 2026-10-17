import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchSqlInjectionSecurityTest(unittest.TestCase):
    def test_search_quotes_cannot_select_nonmatching_products(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'shop.db'
            application = create_app({
                'TESTING': True,
                'PROPAGATE_EXCEPTIONS': False,
                'SECRET_KEY': 'search-security-test-only',
                'DATABASE': str(database),
            })
            single_quote_marker = 'single-quote-only-product-marker'
            double_quote_marker = 'double-quote-product-marker'
            with sqlite3.connect(database) as connection:
                connection.executemany(
                    'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                    [
                        ("Single'quote notebook", single_quote_marker, 100),
                        ("Double''quote notebook", double_quote_marker, 100),
                    ],
                )

            client = application.test_client()
            ordinary = client.get('/', query_string={'q': 'notebook'})
            self.assertEqual(ordinary.status_code, 200)
            self.assertTrue(
                all(marker in ordinary.text for marker in (
                    single_quote_marker, double_quote_marker,
                )),
                'Ordinary search must find both seeded notebooks',
            )

            quoted = client.get('/', query_string={'q': "''"})
            self.assertIn(
                quoted.status_code, (200, 400, 422),
                'Quoted search must be handled safely or explicitly rejected',
            )
            self.assertNotIn(
                single_quote_marker, quoted.text,
                'Search interpreted doubled apostrophes as SQL syntax and returned a nonmatching product',
            )
            if quoted.status_code == 200:
                self.assertIn(
                    double_quote_marker, quoted.text,
                    'Accepted search must find the product containing the literal search text',
                )


if __name__ == '__main__':
    unittest.main()
