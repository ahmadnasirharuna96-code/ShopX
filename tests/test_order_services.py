from django.test import TestCase
from django.contrib.auth import get_user_model
from businesses.models import Business
from catalog.models import Category, Product
from inventory.models import Inventory
from customers.models import Customer, Address
from orders.models import Order, OrderStatus, PaymentStatus
from orders.services import (
    create_order,
    accept_order,
    reject_order,
    update_order_status,
    release_expired_reservations,
)
from common.exceptions import InvalidOrderStateTransition, UnauthorizedBusinessAccess

User = get_user_model()


class OrderServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner1", password="password", role="BUSINESS_OWNER")
        self.other_owner = User.objects.create_user(username="owner2", password="password", role="BUSINESS_OWNER")
        
        self.business = Business.objects.create(owner=self.owner, name="Shop 1", phone_number="08011112222", address="A", city="B", state="C")
        self.category = Category.objects.create(name="Cat 1")
        self.product = Product.objects.create(business=self.business, category=self.category, name="Laptop", price=200000.00)
        self.inventory = Inventory.objects.create(product=self.product, quantity=5, reserved_quantity=0)
        
        self.customer = Customer.objects.create(phone_number="08099990000", name="Jane Doe")
        self.address = Address.objects.create(customer=self.customer, area="Wuse 2")

    def test_create_order_reserves_stock_and_snapshots_price(self):
        order = create_order(
            customer=self.customer,
            business=self.business,
            product=self.product,
            quantity=2,
            address=self.address
        )
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.total_amount, 400000.00)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 2)
        
        item = order.items.first()
        self.assertEqual(item.product_name, "Laptop")
        self.assertEqual(item.unit_price, 200000.00)

    def test_price_change_does_not_affect_existing_order_snapshot(self):
        order = create_order(self.customer, self.business, self.product, 1, self.address)
        
        # Price change
        self.product.price = 300000.00
        self.product.save()

        item = order.items.first()
        self.assertEqual(item.unit_price, 200000.00)
        self.assertEqual(order.total_amount, 200000.00)

    def test_accept_order_by_owner(self):
        order = create_order(self.customer, self.business, self.product, 1, self.address)
        accept_order(order, self.owner)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.BUSINESS_CONFIRMED)
        self.assertTrue(order.business_confirmed)

    def test_unauthorized_business_cannot_accept_order(self):
        order = create_order(self.customer, self.business, self.product, 1, self.address)
        with self.assertRaises(UnauthorizedBusinessAccess):
            accept_order(order, self.other_owner)

    def test_reject_order_releases_stock(self):
        order = create_order(self.customer, self.business, self.product, 2, self.address)
        reject_order(order, self.owner)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.REJECTED)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 0)

    def test_order_fulfillment_lifecycle_to_delivery_and_paid(self):
        order = create_order(self.customer, self.business, self.product, 1, self.address)
        accept_order(order, self.owner)
        update_order_status(order, OrderStatus.PREPARING, self.owner)
        update_order_status(order, OrderStatus.READY_FOR_DELIVERY, self.owner)
        update_order_status(order, OrderStatus.OUT_FOR_DELIVERY, self.owner)
        update_order_status(order, OrderStatus.DELIVERED, self.owner)

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.DELIVERED)
        self.assertEqual(order.payment_status, PaymentStatus.PAID)

        # Inventory committed
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 4)
        self.assertEqual(self.inventory.reserved_quantity, 0)

    def test_invalid_order_state_transition(self):
        order = create_order(self.customer, self.business, self.product, 1, self.address)
        with self.assertRaises(InvalidOrderStateTransition):
            update_order_status(order, OrderStatus.DELIVERED, self.owner)
