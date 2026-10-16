import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app import create_app


class SearchSqlInjectionSecurityTest(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        database_path = Path(temporary_directory.name) / 'shop.db'
        application = create_app({
            'TESTING': True,
            'SECRET_KEY': 'security-test-only',
            'DATABASE': str(database_path),
        })
        self.client = application.test_client()
        with closing(sqlite3.connect(database_path)) as database:
            database.executemany(
                'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                [
                    ('search-marker-x', 'First security fixture.', 100),
                    ('search-marker-y', 'Second security fixture.', 100),
                ],
            )
            database.commit()

    def test_search_cannot_interpret_a_literal_quote_as_sql(self):
        ordinary_response = self.client.get('/', query_string={'q': 'search-marker-x'})
        self.assertEqual(ordinary_response.status_code, 200)
        self.assertIn('search-marker-x', ordinary_response.get_data(as_text=True))
        self.assertNotIn('search-marker-y', ordinary_response.get_data(as_text=True))

        response = self.client.get('/', query_string={'q': "x'--"})
        self.assertIn(response.status_code, (200, 400, 403, 422))
        self.assertNotIn(
            'search-marker-x',
            response.get_data(as_text=True),
            'Search input must be treated as data, not SQL',
        )


if __name__ == '__main__':
    unittest.main()
