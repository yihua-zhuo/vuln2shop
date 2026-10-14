import re
import tempfile
import unittest
from pathlib import Path

from app import create_app


class OrderAccessSecurityTest(unittest.TestCase):
    def test_other_shopper_cannot_read_order(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'order-security-test',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            owner = app.test_client()
            other = app.test_client()

            def post(client, path, data=None):
                page = client.get('/login')
                token = re.search(r'name="csrf" value="([^"]+)"', page.text)
                self.assertIsNotNone(token, 'Public forms must supply a CSRF token')
                return client.post(path, data={
                    **(data or {}), 'csrf': token.group(1),
                }, follow_redirects=True)

            for client, name in ((owner, 'owner'), (other, 'other')):
                credentials = {'username': name, 'password': 'password123'}
                post(client, '/register', credentials)
                response = post(client, '/login', credentials)
                self.assertIn(name, response.text)
                self.assertIn('/logout', response.text)

            post(owner, '/cart', {'product_id': '1', 'quantity': '2'})
            post(owner, '/checkout')
            detail = owner.get('/orders/1')
            self.assertEqual(detail.status_code, 200)
            self.assertIn('复古相机 × 2', detail.text)
            self.assertIn('订单 #1', detail.text)
            self.assertNotIn('订单 #1', other.get('/orders').text)

            response = other.get('/orders/1', follow_redirects=True)
            self.assertLess(response.status_code, 500, 'Access refusal must not crash')
            self.assertFalse(
                '复古相机 × 2' in response.text or '订单 #1' in response.text,
                'Another shopper can read the owner\'s order details',
            )
