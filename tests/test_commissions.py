from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from accounts.models import User
from businesses.models import Business
from catalog.models import Category, Product
from commissions.models import CommissionLedger, CommissionWallet, PaystackPayment
from commissions.services import CommissionService, PaystackService
from customers.models import Customer
from orders.models import Order, OrderItem, OrderStatus


class CommissionFeatureTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="commission_owner", password="pass123", role="BUSINESS_OWNER")
        self.business = Business.objects.create(
            owner=self.owner,
            name="Commission Shop",
            phone_number="08012345678",
            address="Main Street",
            city="Lagos",
            state="Lagos",
        )
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            business=self.business,
            category=self.category,
            name="Laptop",
            description="Test product",
            price=Decimal("50000.00"),
        )
        self.customer = Customer.objects.create(phone_number="08055555555", name="Jane Customer")
        self.order = Order.objects.create(
            order_number="SX-1001",
            customer=self.customer,
            business=self.business,
            status=OrderStatus.DELIVERED,
            total_amount=Decimal("100000.00"),
            customer_confirmed=True,
            business_confirmed=True,
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=2,
            subtotal=Decimal("100000.00"),
        )

    def test_commission_calculates_one_percent_of_product_value(self):
        commission = CommissionService.calculate_commission_for_order(self.order)
        self.assertEqual(commission, Decimal("1000.00"))

    def test_commission_finalization_deducts_wallet_and_tracks_outstanding(self):
        wallet = CommissionWallet.objects.create(business=self.business, balance=Decimal("500.00"), outstanding_balance=Decimal("0.00"))

        entry = CommissionService.finalize_commission_for_order(self.order)

        wallet.refresh_from_db()
        self.assertEqual(entry.amount, Decimal("1000.00"))
        self.assertEqual(wallet.balance, Decimal("0.00"))
        self.assertEqual(wallet.outstanding_balance, Decimal("500.00"))
        self.assertEqual(
            CommissionLedger.objects.filter(business=self.business, transaction_type=CommissionLedger.TransactionType.COMMISSION_CHARGE).count(),
            1,
        )

    def test_duplicate_delivered_order_does_not_double_charge(self):
        CommissionService.finalize_commission_for_order(self.order)
        first_count = CommissionLedger.objects.filter(
            business=self.business,
            transaction_type=CommissionLedger.TransactionType.COMMISSION_CHARGE,
        ).count()

        CommissionService.finalize_commission_for_order(self.order)

        second_count = CommissionLedger.objects.filter(
            business=self.business,
            transaction_type=CommissionLedger.TransactionType.COMMISSION_CHARGE,
        ).count()
        self.assertEqual(first_count, second_count)
        self.assertEqual(second_count, 1)

    @patch("commissions.services.requests.post")
    @patch.object(settings, "PAYSTACK_SECRET_KEY", "test-secret-key")
    def test_paystack_initialize_success_creates_payment_record(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            "status": True,
            "data": {
                "reference": "paystack-ref-001",
                "authorization_url": "https://checkout.paystack.com/paystack-ref-001",
            },
        }

        payment = PaystackService.initialize_transaction(
            business=self.business,
            amount=Decimal("2500.00"),
            purpose=PaystackPayment.Purpose.WALLET_TOPUP,
        )

        self.assertEqual(payment.business, self.business)
        self.assertEqual(payment.status, PaystackPayment.Status.PENDING)
        self.assertTrue(payment.internal_reference)
        mock_post.assert_called_once()

    @patch("commissions.services.requests.get")
    @patch.object(settings, "PAYSTACK_SECRET_KEY", "test-secret-key")
    def test_paystack_duplicate_verification_is_idempotent(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {
            "status": True,
            "data": {
                "status": "success",
                "reference": "ref-dup-001",
                "amount": 50000,
                "currency": "NGN",
            },
        }

        payment = PaystackPayment.objects.create(
            business=self.business,
            purpose=PaystackPayment.Purpose.WALLET_TOPUP,
            amount=Decimal("500.00"),
            internal_reference="ref-dup-001",
            paystack_reference="ref-dup-001",
            status=PaystackPayment.Status.PENDING,
        )

        first = PaystackService.process_verified_payment("ref-dup-001", expected_amount=Decimal("500.00"), expected_business=self.business)
        second = PaystackService.process_verified_payment("ref-dup-001", expected_amount=Decimal("500.00"), expected_business=self.business)

        self.assertEqual(first.status, PaystackPayment.Status.VERIFIED)
        self.assertEqual(second.status, PaystackPayment.Status.VERIFIED)
        self.assertEqual(CommissionWallet.objects.get(business=self.business).balance, Decimal("500.00"))
