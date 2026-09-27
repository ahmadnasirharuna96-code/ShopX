import logging
from decimal import Decimal
from uuid import uuid4

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from businesses.models import Business
from commissions.models import CommissionLedger, CommissionSettlement, CommissionWallet, PaystackPayment
from orders.models import Order, OrderStatus

logger = logging.getLogger(__name__)
COMMISSION_RATE = Decimal("0.01")


class CommissionService:
    @staticmethod
    def calculate_commission_for_order(order: Order) -> Decimal:
        product_value = Decimal("0.00")
        for item in order.items.all():
            product_value += item.subtotal or Decimal("0.00")
        return (product_value * COMMISSION_RATE).quantize(Decimal("0.01"))

    @staticmethod
    def get_or_create_wallet(business: Business) -> CommissionWallet:
        wallet, _ = CommissionWallet.objects.get_or_create(business=business)
        return wallet

    @staticmethod
    def finalize_commission_for_order(order: Order):
        if order.status != OrderStatus.DELIVERED:
            return None

        existing = CommissionSettlement.objects.filter(order=order).first()
        if existing:
            return existing

        commission_amount = CommissionService.calculate_commission_for_order(order)
        wallet = CommissionService.get_or_create_wallet(order.business)
        wallet_before = wallet.balance
        outstanding = Decimal("0.00")

        with transaction.atomic():
            existing_in_txn = CommissionSettlement.objects.filter(order=order).first()
            if existing_in_txn:
                return existing_in_txn

            amount_used = min(commission_amount, wallet.balance)
            wallet.balance = wallet.balance - amount_used
            outstanding = commission_amount - amount_used
            wallet.outstanding_balance = outstanding
            wallet.save(update_fields=["balance", "outstanding_balance", "updated_at"])

            settlement = CommissionSettlement.objects.create(
                business=order.business,
                order=order,
                commission_amount=commission_amount,
                wallet_deduction=amount_used,
                outstanding_amount=outstanding,
                status="OUTSTANDING" if outstanding > 0 else "POSTED",
                metadata={"wallet_before": str(wallet_before), "wallet_after": str(wallet.balance)},
            )

            CommissionLedger.objects.create(
                business=order.business,
                order=order,
                transaction_type=CommissionLedger.TransactionType.COMMISSION_CHARGE,
                amount=commission_amount,
                balance_after=wallet.balance,
                outstanding_after=outstanding,
                reference=f"COMMISSION-{order.order_number}",
                status=CommissionLedger.Status.POSTED,
                description=f"Commission due for order {order.order_number}",
            )

            if amount_used > 0:
                CommissionLedger.objects.create(
                    business=order.business,
                    order=order,
                    transaction_type=CommissionLedger.TransactionType.COMMISSION_WALLET_DEDUCTION,
                    amount=amount_used,
                    balance_after=wallet.balance,
                    outstanding_after=outstanding,
                    reference=f"WALLET-{order.order_number}",
                    status=CommissionLedger.Status.POSTED,
                    description=f"Deducted {amount_used} from wallet for order {order.order_number}",
                )

        return settlement

    @staticmethod
    def apply_wallet_topup(business: Business, amount: Decimal, reference: str, description: str = ""):
        wallet = CommissionService.get_or_create_wallet(business)
        with transaction.atomic():
            wallet.balance += amount
            wallet.save(update_fields=["balance", "updated_at"])
        CommissionLedger.objects.create(
            business=business,
            transaction_type=CommissionLedger.TransactionType.WALLET_TOPUP,
            amount=amount,
            balance_after=wallet.balance,
            outstanding_after=wallet.outstanding_balance,
            reference=reference,
            status=CommissionLedger.Status.POSTED,
            description=description or "Merchant wallet top-up",
        )
        return wallet

    @staticmethod
    def settle_outstanding_commission(business: Business, amount: Decimal, reference: str, description: str = ""):
        wallet = CommissionService.get_or_create_wallet(business)
        with transaction.atomic():
            if amount > wallet.outstanding_balance:
                amount = wallet.outstanding_balance
            wallet.outstanding_balance = wallet.outstanding_balance - amount
            wallet.save(update_fields=["outstanding_balance", "updated_at"])
        CommissionLedger.objects.create(
            business=business,
            transaction_type=CommissionLedger.TransactionType.COMMISSION_PAYMENT,
            amount=amount,
            balance_after=wallet.balance,
            outstanding_after=wallet.outstanding_balance,
            reference=reference,
            status=CommissionLedger.Status.POSTED,
            description=description or "Outstanding commission settled",
        )
        return wallet


class PaystackService:
    @staticmethod
    def get_headers():
        secret = getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""
        return {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}

    @staticmethod
    def initialize_transaction(business: Business, amount: Decimal, purpose: str, metadata=None):
        secret = getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""
        if not secret:
            raise ValueError("PAYSTACK_SECRET_KEY is not configured.")

        reference = f"{purpose}-{business.pk}-{uuid4().hex[:12]}"
        payload = {
            "email": getattr(business.owner, "email", "merchant@shopx.local") or "merchant@shopx.local",
            "amount": int((Decimal(str(amount)) * Decimal("100")).quantize(Decimal("1"))),
            "currency": "NGN",
            "reference": reference,
            "metadata": metadata or {"business_id": business.pk, "purpose": purpose},
        }

        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers=PaystackService.get_headers(),
            json=payload,
            timeout=15,
        )

        if not response.ok:
            raise ValueError("Paystack initialization failed.")

        payload_data = response.json()
        if not payload_data.get("status"):
            raise ValueError("Paystack initialization response was unsuccessful.")

        data = payload_data.get("data", {})
        payment = PaystackPayment.objects.create(
            business=business,
            purpose=purpose,
            amount=Decimal(str(amount)),
            internal_reference=reference,
            paystack_reference=data.get("reference", reference),
            authorization_url=data.get("authorization_url", ""),
            status=PaystackPayment.Status.PENDING,
            metadata={"business_id": business.pk, "purpose": purpose},
        )
        return payment

    @staticmethod
    def verify_transaction(reference: str):
        secret = getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""
        if not secret:
            raise ValueError("PAYSTACK_SECRET_KEY is not configured.")

        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=PaystackService.get_headers(),
            timeout=15,
        )
        if not response.ok:
            raise ValueError("Paystack verification failed.")

        payload = response.json()
        if not payload.get("status"):
            raise ValueError("Paystack verification returned unsuccessful.")

        data = payload.get("data", {})
        return data

    @staticmethod
    def process_verified_payment(reference: str, expected_amount: Decimal | None = None, expected_business: Business | None = None):
        payment = PaystackPayment.objects.filter(paystack_reference=reference).first()
        if payment is None:
            payment = PaystackPayment.objects.filter(internal_reference=reference).first()
        if payment is None:
            raise ValueError("No matching Paystack payment record was found.")

        if payment.status == PaystackPayment.Status.VERIFIED:
            return payment

        data = PaystackService.verify_transaction(reference)
        if data.get("status") != "success":
            payment.status = PaystackPayment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            raise ValueError("Paystack transaction was not successful.")

        gateway_amount = Decimal(str((int(data.get("amount", 0)) / 100)))
        if expected_amount is not None and gateway_amount != expected_amount:
            raise ValueError("Paystack amount does not match the expected merchant amount.")

        if expected_business is not None and payment.business_id != expected_business.pk:
            raise ValueError("Paystack payment does not belong to this business.")

        payment.paystack_reference = data.get("reference", payment.paystack_reference or reference)
        payment.status = PaystackPayment.Status.VERIFIED
        payment.verified_at = timezone.now()
        payment.save(update_fields=["paystack_reference", "status", "verified_at", "updated_at"])

        if payment.purpose == PaystackPayment.Purpose.WALLET_TOPUP:
            CommissionService.apply_wallet_topup(payment.business, payment.amount, payment.paystack_reference or payment.internal_reference, "Wallet top-up via Paystack")
        elif payment.purpose == PaystackPayment.Purpose.COMMISSION_PAYMENT:
            CommissionService.settle_outstanding_commission(payment.business, payment.amount, payment.paystack_reference or payment.internal_reference, "Outstanding commission payment via Paystack")

        return payment
