import logging
from django.db import transaction
from django.utils import timezone
from .models import Inventory
from catalog.models import Product
from common.exceptions import InsufficientStockException

logger = logging.getLogger(__name__)


def reserve_inventory(product: Product, quantity: int) -> Inventory:
    """
    Atomically reserves inventory for a product using select_for_update().
    Prevents race conditions and overselling.
    """
    if quantity <= 0:
        raise ValueError("Quantity to reserve must be greater than zero.")

    with transaction.atomic():
        # Row-level locking to prevent concurrent overselling
        inventory = Inventory.objects.select_for_update().get(product=product)

        available = inventory.quantity - inventory.reserved_quantity
        if available < quantity:
            logger.warning(
                f"Stock reservation failed for product {product.id} ({product.name}). "
                f"Requested: {quantity}, Available: {available}"
            )
            raise InsufficientStockException(
                f"Insufficient stock available for {product.name}. Requested {quantity}, available {available}."
            )

        inventory.reserved_quantity += quantity
        inventory.save(update_fields=["reserved_quantity", "updated_at"])
        logger.info(
            f"Successfully reserved {quantity} unit(s) of product {product.id}. "
            f"New reserved_quantity: {inventory.reserved_quantity}"
        )
        return inventory


def release_inventory(product: Product, quantity: int) -> Inventory:
    """
    Releases reserved stock back to available pool.
    Called when an order is rejected or cancelled.
    """
    if quantity <= 0:
        return None

    with transaction.atomic():
        inventory = Inventory.objects.select_for_update().get(product=product)
        inventory.reserved_quantity = max(0, inventory.reserved_quantity - quantity)
        inventory.save(update_fields=["reserved_quantity", "updated_at"])
        logger.info(
            f"Released {quantity} unit(s) for product {product.id}. "
            f"Current reserved_quantity: {inventory.reserved_quantity}"
        )
        return inventory


def commit_inventory_deduction(product: Product, quantity: int) -> Inventory:
    """
    Deducts both total physical quantity and reserved quantity upon final order fulfillment/delivery.
    """
    if quantity <= 0:
        return None

    with transaction.atomic():
        inventory = Inventory.objects.select_for_update().get(product=product)
        inventory.quantity = max(0, inventory.quantity - quantity)
        inventory.reserved_quantity = max(0, inventory.reserved_quantity - quantity)
        inventory.save(update_fields=["quantity", "reserved_quantity", "updated_at"])
        logger.info(
            f"Committed deduction of {quantity} unit(s) for product {product.id}. "
            f"Physical quantity remaining: {inventory.quantity}"
        )
        return inventory


def adjust_stock(product: Product, new_quantity: int, low_stock_threshold: int = None) -> Inventory:
    """
    Allows merchant to adjust total stock quantity safely without violating existing reservations.
    """
    with transaction.atomic():
        inventory = Inventory.objects.select_for_update().get(product=product)

        if new_quantity < inventory.reserved_quantity:
            raise ValueError(
                f"Cannot decrease stock to {new_quantity} because {inventory.reserved_quantity} units are currently reserved for pending orders."
            )

        inventory.quantity = new_quantity
        if low_stock_threshold is not None:
            inventory.low_stock_threshold = low_stock_threshold

        inventory.save()
        return inventory
