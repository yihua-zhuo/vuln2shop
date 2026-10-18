import tempfile
import unittest
from pathlib import Path

from app import create_app


class OrderDetailSecurityTest(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'order-security-test-only',
            'DATABASE': str(Path(temporary_directory.name) / 'shop.db'),
        })

    def post(self, client, path, data=None):
        client.get('/')
        with client.session_transaction() as session:
            csrf = session['csrf']
        return client.post(
            path, data={**(data or {}), 'csrf': csrf}, follow_redirects=True,
        )

    def register_and_login(self, client, username):
        credentials = {'username': username, 'password': 'password123'}
        self.post(client, '/register', credentials)
        self.post(client, '/login', credentials)

    def test_order_details_are_private_to_the_owner(self):
        owner = self.app.test_client()
        self.register_and_login(owner, 'owner')
        self.post(owner, '/cart', {'product_id': '1', 'quantity': '1'})
        self.post(owner, '/checkout')

        own_order = owner.get('/orders/1')
        self.assertEqual(own_order.status_code, 200)
        self.assertIn('复古相机 × 1', own_order.get_data(as_text=True))

        other_shopper = self.app.test_client()
        self.register_and_login(other_shopper, 'other-shopper')
        self.assertEqual(
            other_shopper.get('/orders').status_code, 200,
            'The requesting shopper must be authenticated',
        )

        response = other_shopper.get('/orders/1', follow_redirects=True)
        self.assertIn(response.status_code, (200, 403, 404))
        body = response.get_data(as_text=True)
        leaked_details = [
            detail for detail in ('复古相机', '¥199.00') if detail in body
        ]
        self.assertFalse(
            leaked_details,
            "Another shopper's order details must not be disclosed",
        )


if __name__ == '__main__':
    unittest.main()
