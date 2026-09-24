from django.db import models
from common.models import TimeStampedModel
from common.utils import normalize_phone_number


class Customer(TimeStampedModel):
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=150, blank=True, default="Valued Customer")

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.phone_number:
            self.phone_number = normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)

    def get_default_address(self):
        return self.addresses.filter(is_default=True).first() or self.addresses.first()

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class Address(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="addresses",
        db_index=True
    )
    area = models.CharField(max_length=150)
    street = models.CharField(max_length=255, blank=True, default="")
    house_number = models.CharField(max_length=50, blank=True, default="")
    landmark = models.CharField(max_length=255, blank=True, default="")
    delivery_note = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, default="Local")
    state = models.CharField(max_length=100, default="State")
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ["-is_default", "-created_at"]

    def save(self, *args, **kwargs):
        if self.is_default and self.customer_id:
            Address.objects.filter(customer_id=self.customer_id, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def full_address_single_line(self) -> str:
        parts = []
        if self.house_number:
            parts.append(f"No. {self.house_number}")
        if self.street:
            parts.append(self.street)
        if self.area:
            parts.append(self.area)
        if self.landmark:
            parts.append(f"Near {self.landmark}")
        if self.city:
            parts.append(self.city)
        return ", ".join(parts) if parts else "No address provided"

    def __str__(self):
        return f"{self.customer.phone_number}: {self.full_address_single_line()}"
