from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from businesses.models import Business
from catalog.models import Category, Product
from orders.models import Order
from customers.models import Customer
from orders.services import create_order

User = get_user_model()


class BusinessDataIsolationTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Owner A & Business A
        self.owner_a = User.objects.create_user(username="owner_a", password="password123", role="BUSINESS_OWNER")
        self.biz_a = Business.objects.create(owner=self.owner_a, name="Store A", phone_number="0801111", address="A", city="A", state="A")
        self.cat = Category.objects.create(name="General")
        self.prod_a = Product.objects.create(business=self.biz_a, category=self.cat, name="Product A", price=100)
        from inventory.models import Inventory
        Inventory.objects.create(product=self.prod_a, quantity=10)

        # Owner B & Business B
        self.owner_b = User.objects.create_user(username="owner_b", password="password123", role="BUSINESS_OWNER")
        self.biz_b = Business.objects.create(owner=self.owner_b, name="Store B", phone_number="0802222", address="B", city="B", state="B")
        self.prod_b = Product.objects.create(business=self.biz_b, category=self.cat, name="Product B", price=200)
        Inventory.objects.create(product=self.prod_b, quantity=10)

        self.customer = Customer.objects.create(phone_number="0809999", name="Cust")
        self.order_a = create_order(self.customer, self.biz_a, self.prod_a, 1)

    def test_owner_a_cannot_see_business_b_products_in_dashboard(self):
        self.client.login(username="owner_a", password="password123")
        response = self.client.get(reverse("dashboard-products"))
        self.assertEqual(response.status_code, 200)
        products = response.context["products"]
        self.assertIn(self.prod_a, products)
        self.assertNotIn(self.prod_b, products)

    def test_owner_a_cannot_accept_business_b_orders(self):
        self.client.login(username="owner_a", password="password123")
        order_b = create_order(self.customer, self.biz_b, self.prod_b, 1)

        # POST accept to order_b as owner_a
        response = self.client.post(reverse("order-accept", kwargs={"pk": order_b.pk}))
        self.assertEqual(response.status_code, 404)  # 404 because get_object_or_404 filters by business
