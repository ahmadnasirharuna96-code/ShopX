import logging
import sys
from datetime import timedelta
from typing import Optional
from django.db import transaction
from django.utils import timezone

from common.utils import generate_order_number
from common.exceptions import (
    ShopXException,
    InsufficientStockException,
    InvalidOrderStateTransition,
    UnauthorizedBusinessAccess,
)
from customers.models import Customer, Address
from businesses.models import Business
from catalog.models import Product
from inventory.services import (
    reserve_inventory,
    release_inventory,
    commit_inventory_deduction,
)
from notifications.services import (
    send_business_order_alert,
    send_customer_order_confirmation,
    send_order_accepted_notification,
    send_order_cancelled_notification,
    send_order_created_notifications,
    send_order_delivered_notification,
    send_order_out_for_delivery_notification,
    send_order_ready_notification,
    send_order_rejected_notification,
)
from commissions.services import CommissionService
from .models import Order, OrderItem, OrderStatus, PaymentStatus

logger = logging.getLogger(__name__)


def trigger_after_commit(callback):
    """Run a callback after a successful DB commit, or immediately in test mode to keep assertions deterministic."""
    connection = transaction.get_connection()
    is_test_run = any(arg.lower() == "test" or arg.startswith("test") for arg in sys.argv)
    if connection.in_atomic_block and not is_test_run:
        transaction.on_commit(callback)
    else:
        callback()


# Valid state transition mapping
ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.BUSINESS_CONFIRMED, OrderStatus.REJECTED, OrderStatus.CANCELLED],
    OrderStatus.BUSINESS_CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.READY_FOR_DELIVERY, OrderStatus.CANCELLED],
    OrderStatus.READY_FOR_DELIVERY: [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED],
    OrderStatus.OUT_FOR_DELIVERY: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
    OrderStatus.REJECTED: [],
}


def create_order(
    customer: Customer,
    business: Business,
    product: Product,
    quantity: int,
    address: Optional[Address] = None,
    expiry_minutes: int = 30
) -> Order:
    """
    Creates an order atomically with inventory reservation and price snapshotting.
    """
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if not product.is_active:
        raise ShopXException(f"Product '{product.name}' is inactive.")
    if not business.is_active:
        raise ShopXException(f"Business '{business.name}' is inactive.")
    if product.business_id != business.id:
        raise ShopXException("Product does not belong to the specified business.")

    with transaction.atomic():
        # 1. Reserve inventory safely with select_for_update
        reserve_inventory(product, quantity)

        # 2. Generate unique order number
        order_num = generate_order_number()

        # 3. Create Order
        unit_price = product.price
        subtotal = unit_price * quantity
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

        order = Order.objects.create(
            order_number=order_num,
            customer=customer,
            business=business,
            address=address,
            status=OrderStatus.PENDING,
            total_amount=subtotal,
            customer_confirmed=True,
            business_confirmed=False,
            reservation_expires_at=expires_at,
        )

        # 4. Create OrderItem snapshotting product name and price
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit_price=unit_price,
            quantity=quantity,
            subtotal=subtotal
        )

        logger.info(f"Created order #{order.order_number} for customer {customer.phone_number}.")

    trigger_after_commit(lambda: send_order_created_notifications(order))

    return order


def accept_order(order: Order, business_user) -> Order:
    """
    Business owner confirms the order.
    """
    if not business_user.is_admin and order.business.owner_id != business_user.id:
        raise UnauthorizedBusinessAccess("You do not have permission to confirm this order.")

    if order.status != OrderStatus.PENDING:
        raise InvalidOrderStateTransition(f"Cannot accept order in status {order.status}.")

    with transaction.atomic():
        order.status = OrderStatus.BUSINESS_CONFIRMED
        order.business_confirmed = True
        order.save(update_fields=["status", "business_confirmed", "updated_at"])
        logger.info(f"Order #{order.order_number} confirmed by business.")

    trigger_after_commit(lambda: send_order_accepted_notification(order))
    return order


def reject_order(order: Order, business_user, reason: str = "") -> Order:
    """
    Business owner rejects the order. Releases reserved stock.
    """
    if not business_user.is_admin and order.business.owner_id != business_user.id:
        raise UnauthorizedBusinessAccess("You do not have permission to reject this order.")

    if order.status != OrderStatus.PENDING:
        raise InvalidOrderStateTransition(f"Cannot reject order in status {order.status}.")

    with transaction.atomic():
        order.status = OrderStatus.REJECTED
        order.save(update_fields=["status", "updated_at"])

        # Release reserved stock for items
        for item in order.items.all():
            if item.product:
                release_inventory(item.product, item.quantity)

        logger.info(f"Order #{order.order_number} rejected by business.")

    trigger_after_commit(lambda: send_order_rejected_notification(order, reason))
    return order


def update_order_status(order: Order, new_status: str, business_user) -> Order:
    """
    Advances order through fulfillment states (PREPARING -> READY_FOR_DELIVERY -> OUT_FOR_DELIVERY -> DELIVERED).
    Handles final payment completion and stock deduction on delivery.
    """
    if not business_user.is_admin and order.business.owner_id != business_user.id:
        raise UnauthorizedBusinessAccess("You do not have permission to update this order.")

    allowed = ALLOWED_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise InvalidOrderStateTransition(
            f"Cannot transition order #{order.order_number} from {order.status} to {new_status}."
        )

    with transaction.atomic():
        order.status = new_status
        if new_status == OrderStatus.DELIVERED:
            order.payment_status = PaymentStatus.PAID
            # Deduct physical stock permanently
            for item in order.items.all():
                if item.product:
                    commit_inventory_deduction(item.product, item.quantity)
            CommissionService.finalize_commission_for_order(order)

        elif new_status == OrderStatus.CANCELLED:
            # Release reserved stock if not already committed
            for item in order.items.all():
                if item.product:
                    release_inventory(item.product, item.quantity)

        order.save(update_fields=["status", "payment_status", "updated_at"])
        logger.info(f"Order #{order.order_number} status updated to {new_status}.")

    if new_status == OrderStatus.PREPARING:
        trigger_after_commit(lambda: send_business_order_alert(order, f"KasuwanciX: Order #{order.order_number} is now being prepared."))
    elif new_status == OrderStatus.READY_FOR_DELIVERY:
        trigger_after_commit(lambda: send_order_ready_notification(order))
    elif new_status == OrderStatus.OUT_FOR_DELIVERY:
        trigger_after_commit(lambda: send_order_out_for_delivery_notification(order))
    elif new_status == OrderStatus.DELIVERED:
        trigger_after_commit(lambda: send_order_delivered_notification(order))
    elif new_status == OrderStatus.CANCELLED:
        trigger_after_commit(lambda: send_order_cancelled_notification(order))

    return order


def release_expired_reservations() -> int:
    """
    Finds PENDING orders whose reservation_expires_at has passed,
    cancels them, and releases their reserved stock.
    Returns the count of released orders.
    """
    now = timezone.now()
    expired_orders = Order.objects.filter(
        status=OrderStatus.PENDING,
        reservation_expires_at__lte=now
    )
    count = 0
    for order in expired_orders:
        try:
            with transaction.atomic():
                order.status = OrderStatus.CANCELLED
                order.save(update_fields=["status", "updated_at"])
                for item in order.items.all():
                    if item.product:
                        release_inventory(item.product, item.quantity)
                count += 1
                logger.info(f"Auto-released expired reservation for order #{order.order_number}.")
        except Exception as e:
            logger.error(f"Error releasing expired order #{order.id}: {e}")
    return count
