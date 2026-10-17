import tempfile
import unittest
from pathlib import Path

from app import create_app


class OrderAuthorizationSecurityTest(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.application = create_app({
            'TESTING': True,
            'SECRET_KEY': 'order-authorization-test-only',
            'DATABASE': str(Path(temporary_directory.name) / 'shop.db'),
        })

    def post(self, client, path, data=None):
        client.get('/')
        with client.session_transaction() as session:
            csrf_token = session['csrf']
        response = client.post(
            path,
            data={**(data or {}), 'csrf': csrf_token},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200, 'Shopper setup must succeed')
        return response

    def sign_in(self, client, username):
        credentials = {'username': username, 'password': 'password123'}
        self.post(client, '/register', credentials)
        response = self.post(client, '/login', credentials)
        self.assertIn(username, response.get_data(as_text=True))

    def test_shopper_cannot_read_another_shoppers_order(self):
        owner = self.application.test_client()
        self.sign_in(owner, 'order-owner')
        self.post(owner, '/cart', {'product_id': '1', 'quantity': '1'})
        self.post(owner, '/checkout')

        owner_response = owner.get('/orders/1')
        self.assertEqual(owner_response.status_code, 200)
        private_details = ('复古相机 × 1', '¥199.00')
        for detail in private_details:
            self.assertIn(detail, owner_response.get_data(as_text=True))

        other_shopper = self.application.test_client()
        self.sign_in(other_shopper, 'other-shopper')
        response = other_shopper.get('/orders/1')

        self.assertLess(response.status_code, 500, 'Access denial must not crash')
        self.assertFalse(
            any(detail in response.get_data(as_text=True) for detail in private_details),
            'Another shopper must not receive the owner\'s order details',
        )


if __name__ == '__main__':
    unittest.main()
