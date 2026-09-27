from decimal import Decimal

from django.conf import settings
from django.db import models

from businesses.models import Business
from common.models import TimeStampedModel
from orders.models import Order


class CommissionWallet(TimeStampedModel):
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name="commission_wallet")
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    outstanding_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business.name} wallet: {self.balance}"

    def add_funds(self, amount: Decimal):
        if amount <= 0:
            raise ValueError("Top-up amount must be greater than zero.")
        self.balance = self.balance + amount
        self.save(update_fields=["balance", "updated_at"])
        return self.balance

    def deduct(self, amount: Decimal):
        if amount <= 0:
            raise ValueError("Deduction must be greater than zero.")
        if amount > self.balance:
            deduction = self.balance
            self.balance = Decimal("0.00")
            self.outstanding_balance = self.outstanding_balance + (amount - deduction)
            self.save(update_fields=["balance", "outstanding_balance", "updated_at"])
            return deduction, amount - deduction
        self.balance = self.balance - amount
        self.save(update_fields=["balance", "updated_at"])
        return amount, Decimal("0.00")


class CommissionLedger(TimeStampedModel):
    class TransactionType(models.TextChoices):
        WALLET_TOPUP = "WALLET_TOPUP", "Wallet Top-up"
        COMMISSION_CHARGE = "COMMISSION_CHARGE", "Commission Charge"
        COMMISSION_WALLET_DEDUCTION = "COMMISSION_WALLET_DEDUCTION", "Commission Wallet Deduction"
        COMMISSION_PAYMENT = "COMMISSION_PAYMENT", "Commission Payment"
        COMMISSION_REVERSAL = "COMMISSION_REVERSAL", "Commission Reversal"
        REFUND = "REFUND", "Refund"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        POSTED = "POSTED", "Posted"
        REVERSED = "REVERSED", "Reversed"
        FAILED = "FAILED", "Failed"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="commission_ledger")
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL, related_name="commission_ledger")
    transaction_type = models.CharField(max_length=40, choices=TransactionType.choices, db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    balance_after = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    outstanding_after = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    reference = models.CharField(max_length=120, unique=True, db_index=True, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.POSTED, db_index=True)
    description = models.TextField(blank=True, default="")
    metadata = models.JSONField(blank=True, default=dict)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business.name} {self.transaction_type}: {self.amount}"


class PaystackPayment(TimeStampedModel):
    class Purpose(models.TextChoices):
        WALLET_TOPUP = "WALLET_TOPUP", "Wallet Top-up"
        COMMISSION_PAYMENT = "COMMISSION_PAYMENT", "Commission Payment"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Successful"
        FAILED = "FAILED", "Failed"
        VERIFIED = "VERIFIED", "Verified"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="paystack_payments")
    purpose = models.CharField(max_length=30, choices=Purpose.choices, default=Purpose.WALLET_TOPUP, db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="NGN")
    internal_reference = models.CharField(max_length=120, unique=True, db_index=True)
    paystack_reference = models.CharField(max_length=200, blank=True, default="")
    authorization_url = models.URLField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(blank=True, default=dict)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business.name} {self.purpose} {self.amount} ({self.status})"


class CommissionSettlement(TimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="commission_settlements")
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL, related_name="commission_settlements")
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    wallet_deduction = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    outstanding_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=[("POSTED", "Posted"), ("PARTIAL", "Partial"), ("OUTSTANDING", "Outstanding")], default="POSTED", db_index=True)
    metadata = models.JSONField(blank=True, default=dict)

    class Meta:
        ordering = ["-created_at"]

    @property
    def amount(self):
        return self.commission_amount

    def __str__(self):
        return f"Settlement for {self.business.name}: {self.commission_amount}"
