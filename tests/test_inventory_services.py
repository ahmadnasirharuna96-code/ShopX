from django.test import TestCase
from django.contrib.auth import get_user_model
from businesses.models import Business
from catalog.models import Category, Product
from inventory.models import Inventory
from inventory.services import (
    reserve_inventory,
    release_inventory,
    commit_inventory_deduction,
    adjust_stock,
)
from common.exceptions import InsufficientStockException

User = get_user_model()


class InventoryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="password", role="BUSINESS_OWNER")
        self.business = Business.objects.create(owner=self.user, name="Biz", phone_number="08011111111", address="A", city="B", state="C")
        self.category = Category.objects.create(name="Gadgets")
        self.product = Product.objects.create(business=self.business, category=self.category, name="Gadget A", price=1000.00)
        self.inventory = Inventory.objects.create(product=self.product, quantity=10, reserved_quantity=0)

    def test_successful_inventory_reservation(self):
        reserve_inventory(self.product, 3)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 3)
        self.assertEqual(self.inventory.available_quantity, 7)

    def test_insufficient_stock_reservation_failure(self):
        with self.assertRaises(InsufficientStockException):
            reserve_inventory(self.product, 15)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 0)

    def test_release_inventory(self):
        reserve_inventory(self.product, 5)
        release_inventory(self.product, 5)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 0)
        self.assertEqual(self.inventory.available_quantity, 10)

    def test_commit_inventory_deduction_on_delivery(self):
        reserve_inventory(self.product, 4)
        commit_inventory_deduction(self.product, 4)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 6)
        self.assertEqual(self.inventory.reserved_quantity, 0)
        self.assertEqual(self.inventory.available_quantity, 6)

    def test_adjust_stock_prevents_setting_below_reserved(self):
        reserve_inventory(self.product, 5)
        with self.assertRaises(ValueError):
            adjust_stock(self.product, new_quantity=3)
