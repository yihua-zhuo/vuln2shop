import tempfile
import unittest
from pathlib import Path

from app import create_app


class ShopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = {'TESTING': True, 'SECRET_KEY': 'test-only',
                       'DATABASE': str(Path(self.tmp.name) / 'shop.db')}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def post(self, url, data=None):
        self.client.get('/')
        with self.client.session_transaction() as session:
            token = session['csrf']
        return self.client.post(url, data={**(data or {}), 'csrf': token}, follow_redirects=True)

    def account(self, name):
        self.post('/register', {'username': name, 'password': 'password123'})
        return self.post('/login', {'username': name, 'password': 'password123'})

    def test_shopping_and_account_isolation(self):
        self.assertEqual(self.account('alice').status_code, 200)
        response = self.post('/cart', {'product_id': '3', 'quantity': '2'})
        self.assertIn('¥49.00', response.text)
        response = self.post('/checkout')
        self.assertIn('订单 #1', response.text)
        self.assertIn('咖啡豆 500g × 2', response.text)
        self.assertIn('¥49.00', response.text)
        self.assertIn('购物车还是空的', self.client.get('/cart').text)
        self.post('/checkout')
        self.assertNotIn('订单 #2', self.client.get('/orders').text)
        self.post('/logout')
        self.account('bob')
        self.assertIn('暂无订单', self.client.get('/orders').text)
        self.post('/logout')
        self.client = create_app(self.config).test_client()
        self.post('/login', {'username': 'alice', 'password': 'password123'})
        self.assertIn('订单 #1', self.client.get('/orders').text)

    def test_validation(self):
        self.assertEqual(self.client.get('/cart').status_code, 302)
        self.assertEqual(self.client.post('/register').status_code, 400)
        self.account('alice')
        self.assertEqual(self.post('/cart', {'product_id': '1', 'quantity': '-1'}).status_code, 400)
        self.assertEqual(self.post('/cart', {'product_id': '999', 'quantity': '1'}).status_code, 404)
        self.post('/cart', {'product_id': '1', 'quantity': '1'})
        self.assertIn('购物车还是空的', self.post('/cart', {'product_id': '1', 'quantity': '0'}).text)
        self.assertIn('咖啡豆', self.client.get('/', query_string={'q': '咖啡'}).text)

    def test_search_sql_injection(self):
        self.assertIn('没有找到相关商品', self.client.get('/', query_string={'q': 'no-match-xyz'}).text)
        response = self.client.get('/', query_string={'q': "no-match-xyz' OR 1=1 -- "})
        self.assertEqual(response.status_code, 200)
        self.assertIn('复古相机', response.text)
        self.assertIn('机械键盘', response.text)

    def test_search_reflected_xss(self):
        payload = '<script>alert(1)</script>'
        response = self.client.get('/', query_string={'q': payload})
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'搜索关键词：{payload}', response.text)

    def test_order_idor(self):
        self.account('alice')
        self.post('/cart', {'product_id': '1', 'quantity': '2'})
        self.post('/checkout')
        self.post('/logout')
        self.assertEqual(self.client.get('/orders/1').status_code, 302)
        self.account('bob')
        self.assertIn('暂无订单', self.client.get('/orders').text)
        response = self.client.get('/orders/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('复古相机 × 2', response.text)
        self.assertIn('¥398.00', response.text)


if __name__ == '__main__':
    unittest.main()
