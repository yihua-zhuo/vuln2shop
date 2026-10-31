import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchSecurityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        config = {'TESTING': True, 'SECRET_KEY': 'test-only',
                  'DATABASE': str(Path(self.tmp.name) / 'shop.db')}
        self.app = create_app(config)
        self.client = self.app.test_client()

    def test_anonymous_search_does_not_disclose_user_rows(self):
        marker = 'private-user-marker'
        self.client.get('/')
        with self.client.session_transaction() as session:
            token = session['csrf']
        response = self.client.post('/register', data={
            'username': marker, 'password': 'password123', 'csrf': token,
        }, follow_redirects=True)
        self.assertIn('注册成功', response.text)

        self.client = self.app.test_client()
        response = self.client.get('/', query_string={'q': '咖啡'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('咖啡豆 500g', response.text)

        response = self.client.get('/', query_string={
            'q': "' UNION SELECT id,username,'',0 FROM users--",
        })
        self.assertLess(response.status_code, 500)
        self.assertNotIn(marker, response.text,
                         'Anonymous product search must not disclose user rows')


if __name__ == '__main__':
    unittest.main()
