from django.db import models
from common.models import TimeStampedModel
from customers.models import Customer, Address
from businesses.models import Business
from catalog.models import Product


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Business Confirmation"
    BUSINESS_CONFIRMED = "BUSINESS_CONFIRMED", "Confirmed by Business"
    PREPARING = "PREPARING", "Preparing Order"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY", "Ready for Delivery"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"
    REJECTED = "REJECTED", "Rejected by Business"


class PaymentMethod(models.TextChoices):
    PAY_ON_DELIVERY = "PAY_ON_DELIVERY", "Pay on Delivery"


class PaymentStatus(models.TextChoices):
    UNPAID = "UNPAID", "Unpaid"
    PAID = "PAID", "Paid"


class Order(TimeStampedModel):
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="orders",
        db_index=True
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="orders",
        db_index=True
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders"
    )
    status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.PAY_ON_DELIVERY
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    customer_confirmed = models.BooleanField(default=True)
    business_confirmed = models.BooleanField(default=False)
    reservation_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_number} ({self.get_status_display()}) - N{self.total_amount}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    product_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.subtotal:
            self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product_name} @ N{self.unit_price} (Subtotal: N{self.subtotal})"
