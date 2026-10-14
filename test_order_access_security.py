"""Regression coverage for ownership checks on order details."""
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest

from app import create_app


class FormToken(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = ''

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if tag == 'input' and fields.get('name') == 'csrf':
            self.token = fields.get('value', '')


class OrderAccessSecurityTest(unittest.TestCase):
    def post_form(self, client, path, data=None, form_path=None):
        form = client.get(form_path or path)
        parser = FormToken()
        parser.feed(form.get_data(as_text=True))
        return client.post(path, data={**(data or {}), 'csrf': parser.token},
                           follow_redirects=True)

    def make_order(self, client, username, product_id):
        credentials = {'username': username, 'password': 'password123'}
        self.post_form(client, '/register', credentials)
        self.post_form(client, '/login', credentials)
        self.post_form(client, '/cart', {'product_id': product_id, 'quantity': '1'})
        self.post_form(client, '/checkout', form_path='/cart')

    def test_shopper_cannot_read_another_shoppers_order(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'security-test-only',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            owner, other = app.test_client(), app.test_client()
            self.make_order(owner, 'owner', '1')
            self.make_order(other, 'other', '3')

            owned = owner.get('/orders/1')
            self.assertEqual(owned.status_code, 200)
            self.assertIn('复古相机', owned.get_data(as_text=True))
            own_control = other.get('/orders/2')
            self.assertEqual(own_control.status_code, 200)
            self.assertIn('咖啡豆', own_control.get_data(as_text=True))

            response = other.get('/orders/1', follow_redirects=True)
            # A denial, a redirect, or a filtered page may all be secure.
            # None may disclose the foreign order, including in an error page.
            body = response.get_data(as_text=True)
            self.assertTrue(
                response.status_code in (200, 401, 403, 404)
                and all(private not in body for private in
                        ('复古相机', '订单 #1', '¥199.00')),
                'Another shopper could read the private order details',
            )


if __name__ == '__main__':
    unittest.main()
