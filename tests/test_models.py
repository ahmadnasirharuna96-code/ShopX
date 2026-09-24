from django.test import TestCase
from django.contrib.auth import get_user_model
from businesses.models import Business
from catalog.models import Category, Product
from inventory.models import Inventory
from customers.models import Customer, Address
from common.utils import normalize_phone_number, generate_order_number

User = get_user_model()


class ModelUnitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_owner", password="password", role="BUSINESS_OWNER")
        self.business = Business.objects.create(
            owner=self.user,
            name="Test Electronics",
            phone_number="08012345678",
            address="123 Test Street",
            city="Lagos",
            state="Lagos"
        )
        self.category = Category.objects.create(name="Tech")

    def test_business_and_user_creation(self):
        self.assertEqual(self.business.owner, self.user)
        self.assertTrue(self.user.is_business_user)

    def test_phone_normalization(self):
        phone1 = normalize_phone_number("08012345678")
        self.assertEqual(phone1, "+2348012345678")

    def test_product_and_inventory_available_stock(self):
        product = Product.objects.create(
            business=self.business,
            category=self.category,
            name="Test Phone",
            price=50000.00
        )
        inv = Inventory.objects.create(product=product, quantity=10, reserved_quantity=3)
        self.assertEqual(inv.available_quantity, 7)
        self.assertFalse(inv.is_out_of_stock)

    def test_customer_address_default_toggle(self):
        customer = Customer.objects.create(phone_number="08099998888", name="John Doe")
        addr1 = Address.objects.create(customer=customer, area="Wuse", is_default=True)
        addr2 = Address.objects.create(customer=customer, area="Garki", is_default=True)

        addr1.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)
