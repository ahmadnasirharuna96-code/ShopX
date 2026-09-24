import logging
from orders.models import Order, OrderStatus
from orders.services import update_order_status

logger = logging.getLogger(__name__)


class DeliveryService:
    """
    Delivery lifecycle management service abstraction.
    Extensible for future third-party logistics APIs.
    """

    @staticmethod
    def mark_preparing(order: Order, user) -> Order:
        return update_order_status(order, OrderStatus.PREPARING, user)

    @staticmethod
    def mark_ready_for_delivery(order: Order, user) -> Order:
        return update_order_status(order, OrderStatus.READY_FOR_DELIVERY, user)

    @staticmethod
    def mark_out_for_delivery(order: Order, user) -> Order:
        return update_order_status(order, OrderStatus.OUT_FOR_DELIVERY, user)

    @staticmethod
    def mark_delivered(order: Order, user) -> Order:
        """
        Marks order as DELIVERED and triggers payment completion (PAID) and permanent stock deduction.
        """
        return update_order_status(order, OrderStatus.DELIVERED, user)
