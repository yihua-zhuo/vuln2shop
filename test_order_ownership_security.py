"""Regression coverage for customer order-detail authorization."""

import tempfile
import unittest
from pathlib import Path

from app import create_app


class OrderOwnershipSecurityTest(unittest.TestCase):
    def test_other_customer_cannot_read_order_detail(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'order-ownership-test',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            owner = app.test_client()
            other_customer = app.test_client()

            def post(client, path, data=None):
                client.get('/login')
                with client.session_transaction() as session:
                    csrf = session['csrf']
                response = client.post(
                    path, data={**(data or {}), 'csrf': csrf},
                    follow_redirects=True,
                )
                self.assertEqual(response.status_code, 200)
                return response

            for client, username in ((owner, 'alice'), (other_customer, 'bob')):
                credentials = {'username': username, 'password': 'password123'}
                post(client, '/register', credentials)
                post(client, '/login', credentials)

            post(owner, '/cart', {'product_id': '1', 'quantity': '1'})
            post(owner, '/checkout')

            own_order = owner.get('/orders/1')
            self.assertEqual(own_order.status_code, 200)
            self.assertIn('复古相机 × 1', own_order.get_data(as_text=True))

            # Establish that Bob is authenticated and the list already isolates him.
            other_list = other_customer.get('/orders')
            self.assertEqual(other_list.status_code, 200)
            self.assertNotIn('订单 #1', other_list.get_data(as_text=True))

            # Accept a denial, a safe redirect, or an empty/redacted response.
            response = other_customer.get('/orders/1', follow_redirects=True)
            body = response.get_data(as_text=True)
            self.assertFalse(
                any(value in body for value in ('复古相机 × 1', '订单 #1')),
                'Another customer can read private order details',
            )
            self.assertLess(response.status_code, 500, 'Access denial must not crash')
