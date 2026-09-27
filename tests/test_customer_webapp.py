from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from catalog.models import Product, Category
from businesses.models import Business
from accounts.models import User
from inventory.models import Inventory
from customers.models import Customer
import io
from PIL import Image


def make_test_image(filename='test.png'):
    f = io.BytesIO()
    Image.new('RGB', (100, 100), color=(73, 109, 137)).save(f, 'PNG')
    f.seek(0)
    return SimpleUploadedFile(filename, f.read(), content_type='image/png')


class CustomerWebAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='merchant', password='password123')
        self.business = Business.objects.create(owner=self.user, name='Test Shop', phone_number='08012345678', address='Market', city='Abuja', state='FCT')
        self.cat = Category.objects.create(name='Fruits')

    def test_mandatory_image_rejected(self):
        # Attempt to create a product via ProductForm without image (simulate view POST)
        url = reverse('product-create')
        self.client.login(username='merchant', password='password123')
        response = self.client.post(url, {
            'name': 'No Image Product',
            'category': self.cat.id,
            'price': '100.00',
            'description': 'A product without image',
            'initial_stock': 10,
            'low_stock_threshold': 2,
        })
        self.assertContains(response, 'Product image is required.', status_code=200)

    def test_valid_product_image_upload(self):
        url = reverse('product-create')
        self.client.login(username='merchant', password='password123')
        img = make_test_image()
        response = self.client.post(url, {
            'name': 'Has Image',
            'category': self.cat.id,
            'price': '250.00',
            'description': 'A product with image',
            'initial_stock': 5,
            'low_stock_threshold': 1,
            'image': img,
        }, format='multipart')
        # After successful creation, redirect to dashboard-products
        self.assertEqual(response.status_code, 302)

    def test_guest_browsing_and_cart_and_checkout(self):
        # Create product with inventory
        product = Product.objects.create(business=self.business, category=self.cat, name='Apple', price=50.00)
        Inventory.objects.create(product=product, quantity=20, reserved_quantity=0, low_stock_threshold=2)

        # Home page
        resp = self.client.get(reverse('shop-home'))
        self.assertEqual(resp.status_code, 200)

        # Add to cart
        add_url = reverse('cart-add', args=[product.id])
        resp = self.client.post(add_url, {'quantity': 2}, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Checkout as guest
        resp = self.client.get(reverse('shop-checkout'))
        self.assertEqual(resp.status_code, 200)

        post_data = {
            'name': 'Guest User',
            'phone': '08098765432',
            'area': 'Garki',
            'street': 'Main St',
            'house_number': '12',
            'city': 'Abuja',
            'state': 'FCT'
        }
        resp = self.client.post(reverse('shop-checkout'), post_data, follow=True)
        # Expect redirect to order confirmation
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Order Confirmation', status_code=200)

    def test_customer_orders_view_requires_auth(self):
        resp = self.client.get(reverse('shop-my-orders'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Create an account or login', status_code=200)

    def test_stock_validation(self):
        product = Product.objects.create(business=self.business, category=self.cat, name='Banana', price=30.00)
        Inventory.objects.create(product=product, quantity=2, reserved_quantity=0, low_stock_threshold=1)

        add_url = reverse('cart-add', args=[product.id])
        # attempt to add 5 items
        resp = self.client.post(add_url, {'quantity': 5}, follow=True)
        # Should show error message about available quantity or similar
        self.assertEqual(resp.status_code, 200)
