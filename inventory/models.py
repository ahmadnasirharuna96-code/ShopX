from django.db import models
from django.db.models import Q, F
from catalog.models import Product

# Detect whether the installed Django version supports CheckConstraint(..., condition=...)
# Do this at module import time and expose `__SUPPORTS_CHECK_CONSTRAINT_CHECK__` for
# use inside the model Meta class. Keep `Q` and `F` at module scope so Django does
# not treat them as invalid Meta attributes.
__SUPPORTS_CHECK_CONSTRAINT_CHECK__ = False
try:
    _ = models.CheckConstraint(condition=Q(quantity__gte=F("reserved_quantity")), name="__test__")
    __SUPPORTS_CHECK_CONSTRAINT_CHECK__ = True
except TypeError:
    __SUPPORTS_CHECK_CONSTRAINT_CHECK__ = False
except Exception:
    __SUPPORTS_CHECK_CONSTRAINT_CHECK__ = False


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
        # Only add database-level CheckConstraints when supported by the
        # installed Django version. Use the module-level detection flag and
        # module-scoped `Q`/`F` imports so Django does not interpret them as
        # invalid Meta attributes.
        constraints = []
        if __SUPPORTS_CHECK_CONSTRAINT_CHECK__:
            constraints = [
                models.CheckConstraint(
                    condition=Q(quantity__gte=F("reserved_quantity")),
                    name="quantity_gte_reserved"
                ),
                models.CheckConstraint(
                    condition=Q(reserved_quantity__gte=0),
                    name="reserved_quantity_non_negative"
                ),
                models.CheckConstraint(
                    condition=Q(quantity__gte=0),
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
