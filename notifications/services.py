import logging
from django.conf import settings
from common.utils import normalize_phone_number

logger = logging.getLogger(__name__)


def send_sms(phone_number: str, message: str) -> bool:
    """
    Sends an SMS notification using Africa's Talking service adapter.
    If credentials are missing or SMS service fails, logs warning and returns False.
    Does NOT raise unhandled exceptions or interrupt business transactions.
    """
    if not phone_number or not message:
        logger.warning("send_sms called with empty phone_number or message.")
        return False

    normalized_phone = normalize_phone_number(phone_number)
    username = getattr(settings, "AFRICASTALKING_USERNAME", "sandbox")
    api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")
    sender_id = getattr(settings, "AFRICASTALKING_SENDER_ID", None)

    # Mock mode if no valid API key or sandbox test setup
    if not api_key or api_key == "your_africastalking_api_key_here":
        logger.info(
            f"[SMS MOCK PROVIDER] To: {normalized_phone} | Sender: {sender_id or 'ShopX'} | Message: {message}"
        )
        return True

    try:
        import africastalking
        africastalking.initialize(username, api_key)
        sms = africastalking.SMS

        kwargs = {
            "message": message,
            "recipients": [normalized_phone]
        }
        if sender_id and sender_id.strip():
            kwargs["sender_id"] = sender_id.strip()

        response = sms.send(**kwargs)
        logger.info(f"Africa's Talking SMS response for {normalized_phone}: {response}")
        return True

    except Exception as e:
        logger.error(f"Africa's Talking SMS failed for {normalized_phone}: {e}", exc_info=True)
        return False


def notify_business_new_order(order):
    """
    Sends notification to business owner when a new USSD order is placed.
    """
    phone = order.business.phone_number
    msg = (
        f"[ShopX Alert] New order #{order.order_number} received! "
        f"Amount: N{order.total_amount}. Log into dashboard to confirm/reject."
    )
    send_sms(phone, msg)


def notify_customer_order_status(order, status_detail: str):
    """
    Sends notification to customer on order state update.
    """
    phone = order.customer.phone_number
    msg = f"[ShopX] Order #{order.order_number}: {status_detail}"
    send_sms(phone, msg)
