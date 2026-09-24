from django.db import models
from catalog.models import Product


class Inventory(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory",
        primary_key=True
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Inventories"
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=models.F("reserved_quantity")),
                name="quantity_gte_reserved"
            ),
            models.CheckConstraint(
                check=models.Q(reserved_quantity__gte=0),
                name="reserved_quantity_non_negative"
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name="quantity_non_negative"
            )
        ]

    @property
    def available_quantity(self) -> int:
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self) -> bool:
        return self.available_quantity <= self.low_stock_threshold and self.available_quantity > 0

    @property
    def is_out_of_stock(self) -> bool:
        return self.available_quantity <= 0

    def __str__(self):
        return f"Inventory for {self.product.name}: Total={self.quantity}, Reserved={self.reserved_quantity}, Available={self.available_quantity}"
