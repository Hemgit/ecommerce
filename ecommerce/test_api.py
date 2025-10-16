import unittest
from app import app, db, Product, User
from flask import json

class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.drop_all()  # Ensure clean DB before each test
            db.create_all()
            # Create admin user
            admin = User(username='admin', password='adminpass')
            db.session.add(admin)
            db.session.commit()
            self.admin_id = admin.id
            # Create sample product
            product = Product(name='Sample', price=10.0, inventory=5, category='Test', image_url='')
            db.session.add(product)
            db.session.commit()
            self.product_id = product.id

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    def test_get_products(self):
        response = self.app.get('/api/products')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('products', data)

    def test_get_product(self):
        response = self.app.get(f'/api/products/{self.product_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], self.product_id)

    def test_add_product_admin(self):
        # Simulate admin login
        with self.app.session_transaction() as sess:
            sess['user_id'] = self.admin_id
        response = self.app.post('/api/products', json={
            'name': 'New Product',
            'price': 20.0,
            'inventory': 10,
            'category': 'Test',
            'image_url': ''
        })
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('id', data)

    def test_add_product_non_admin(self):
        response = self.app.post('/api/products', json={
            'name': 'New Product',
            'price': 20.0,
            'inventory': 10,
            'category': 'Test',
            'image_url': ''
        })
        self.assertEqual(response.status_code, 403)

    def test_update_product(self):
        with self.app.session_transaction() as sess:
            sess['user_id'] = self.admin_id
        response = self.app.put(f'/api/products/{self.product_id}', json={
            'name': 'Updated',
            'price': 15.0
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Product updated')

    def test_delete_product(self):
        with self.app.session_transaction() as sess:
            sess['user_id'] = self.admin_id
        response = self.app.delete(f'/api/products/{self.product_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Product deleted')

if __name__ == '__main__':
    unittest.main()
