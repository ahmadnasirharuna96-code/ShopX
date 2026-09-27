import logging
from typing import Optional

from django.utils import timezone

from common.utils import normalize_phone_number
from notifications.africastalking_sms import AfricaTalkingSMSService
from notifications.models import (
    SMSNotification,
    SMSNotificationStatus,
    SMSNotificationType,
)

logger = logging.getLogger(__name__)


def _product_summary(order) -> str:
    item = order.items.first()
    if item and getattr(item, "product_name", None):
        return f"{item.product_name} x{item.quantity}"
    return "your item"


def _format_ngn(value) -> str:
    return f"NGN {float(value):,.0f}"


def order_created_message(order) -> str:
    summary = _product_summary(order)
    return (
        f"KasuwanciX: Order #{order.order_number} received. {summary}. "
        f"Total: {_format_ngn(order.total_amount)}. Payment: {order.get_payment_method_display()}. "
        "Your order is awaiting business confirmation."
    )


def business_new_order_message(order) -> str:
    summary = _product_summary(order)
    customer_name = getattr(order.customer, "name", "Customer") or "Customer"
    return (
        f"KasuwanciX: New Order #{order.order_number}. Customer: {customer_name}. "
        f"Product: {summary}. Total: {_format_ngn(order.total_amount)}. Please review and accept/reject this order."
    )


def order_accepted_message(order) -> str:
    return (
        f"KasuwanciX: Your Order #{order.order_number} has been accepted by the business. "
        f"Status: Confirmed. Payment: {order.get_payment_method_display()}."
    )


def order_rejected_message(order, reason: str = "") -> str:
    suffix = f" Reason: {reason[:80]}." if reason else ""
    return (
        f"KasuwanciX: Your Order #{order.order_number} was rejected by the business."
        f" Please try another seller.{suffix}"
    )


def order_ready_message(order) -> str:
    return f"KasuwanciX: Order #{order.order_number} is ready for delivery."


def order_out_for_delivery_message(order) -> str:
    return f"KasuwanciX: Order #{order.order_number} is now out for delivery."


def order_delivered_message(order) -> str:
    return (
        f"KasuwanciX: Order #{order.order_number} has been delivered successfully. "
        "Thank you for using KasuwanciX."
    )


def order_cancelled_message(order) -> str:
    return f"KasuwanciX: Order #{order.order_number} has been cancelled by the customer."


def business_order_status_message(order, status_label: str) -> str:
    return (
        f"KasuwanciX: Order #{order.order_number} status update: {status_label}. "
        f"Customer: {getattr(order.customer, 'name', 'Customer') or 'Customer'}."
    )


def _retrieve_or_create_notification(order, recipient: str, notification_type: str, message: str):
    normalized_recipient = normalize_phone_number(recipient or "")
    if not normalized_recipient:
        logger.warning("SMS notification skipped due to missing recipient for %s.", notification_type)
        return None

    record, created = SMSNotification.objects.get_or_create(
        order=order,
        notification_type=notification_type,
        recipient=normalized_recipient,
        defaults={
            "message": message,
            "provider": "africastalking",
            "status": SMSNotificationStatus.PENDING,
        },
    )
    if not created:
        if record.message != message:
            record.message = message
            record.save(update_fields=["message", "updated_at"])
        return record
    return record


def _parse_provider_message_id(response) -> str:
    if not isinstance(response, dict):
        return ""
    recipients = response.get("SMSMessageData", {}).get("Recipients") or []
    if not recipients:
        return ""
    first = recipients[0]
    if isinstance(first, dict):
        return str(first.get("messageId") or "")
    return ""


def send_sms(phone_number: str, message: str) -> bool:
    """Sends a single SMS using Africa's Talking while logging failures and avoiding crashes."""
    normalized_phone = normalize_phone_number(phone_number or "")
    if not normalized_phone or not message or not message.strip():
        logger.warning("send_sms called with empty phone_number or message.")
        return False

    try:
        response = AfricaTalkingSMSService.send_sms(normalized_phone, message)
        logger.info("Africa's Talking SMS accepted for %s: %s", normalized_phone, response)
        return True
    except Exception as exc:  # pragma: no cover - defensive logger path
        logger.error("Africa's Talking SMS failed for %s: %s", normalized_phone, exc, exc_info=True)
        return False


def _send_notification(order, recipient: str, notification_type: str, message: str, *, provider: str = "africastalking") -> bool:
    normalized_recipient = normalize_phone_number(recipient or "")
    if not normalized_recipient:
        logger.warning("Skipping SMS %s for order #%s due to missing recipient.", notification_type, getattr(order, "order_number", "unknown"))
        return False

    record = _retrieve_or_create_notification(order, normalized_recipient, notification_type, message)
    if record is None:
        return False

    try:
        response = AfricaTalkingSMSService.send_sms(normalized_recipient, message)
        provider_message_id = _parse_provider_message_id(response)
        record.provider_response = response if isinstance(response, dict) else {"response": str(response)}
        record.provider_message_id = provider_message_id
        record.status = SMSNotificationStatus.SENT
        record.sent_at = timezone.now()
        record.error_message = ""
        record.save(update_fields=["provider_response", "provider_message_id", "status", "sent_at", "error_message", "updated_at"])
        logger.info("SMS sent to %s (%s): %s", normalized_recipient, notification_type, message)
        return True
    except Exception as exc:
        record.status = SMSNotificationStatus.FAILED
        record.error_message = str(exc)
        record.save(update_fields=["status", "error_message", "updated_at"])
        logger.error("SMS failed for %s (%s): %s", normalized_recipient, notification_type, exc, exc_info=True)
        return False


def send_order_created_notifications(order):
    customer_message = order_created_message(order)
    business_message = business_new_order_message(order)
    customer_sent = _send_notification(order, order.customer.phone_number, SMSNotificationType.ORDER_CREATED, customer_message)
    business_sent = _send_notification(order, order.business.phone_number, SMSNotificationType.BUSINESS_NEW_ORDER, business_message)
    return customer_sent or business_sent


def send_order_accepted_notification(order):
    return _send_notification(order, order.customer.phone_number, SMSNotificationType.ORDER_ACCEPTED, order_accepted_message(order))


def send_order_rejected_notification(order, reason: str = ""):
    return _send_notification(order, order.customer.phone_number, SMSNotificationType.ORDER_REJECTED, order_rejected_message(order, reason))


def send_order_ready_notification(order):
    return _send_notification(order, order.customer.phone_number, SMSNotificationType.ORDER_READY, order_ready_message(order))


def send_order_out_for_delivery_notification(order):
    return _send_notification(order, order.customer.phone_number, SMSNotificationType.OUT_FOR_DELIVERY, order_out_for_delivery_message(order))


def send_order_delivered_notification(order):
    return _send_notification(order, order.customer.phone_number, SMSNotificationType.ORDER_DELIVERED, order_delivered_message(order))


def send_order_cancelled_notification(order):
    return _send_notification(order, order.customer.phone_number, SMSNotificationType.ORDER_CANCELLED, order_cancelled_message(order))


def notify_business_new_order(order):
    return _send_notification(order, order.business.phone_number, SMSNotificationType.BUSINESS_NEW_ORDER, business_new_order_message(order))


def notify_customer_order_status(order, status_detail: str):
    return _send_notification(order, order.customer.phone_number, SMSNotificationType.ORDER_STATUS_UPDATE, f"KasuwanciX: Order #{order.order_number}: {status_detail}")


def send_business_order_alert(order, message: str):
    return _send_notification(order, order.business.phone_number, SMSNotificationType.ORDER_STATUS_UPDATE, message)


def send_customer_order_confirmation(order):
    return _send_notification(order, order.customer.phone_number, SMSNotificationType.CUSTOMER_CONFIRMED, f"KasuwanciX: Order #{order.order_number} confirmed by you. Your order is now being prepared.")
