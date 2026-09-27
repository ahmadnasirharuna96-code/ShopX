import logging

from django.conf import settings

from common.utils import normalize_phone_number

logger = logging.getLogger(__name__)


class AfricaTalkingSMSService:
    """Thin wrapper around Africa's Talking SMS API with environment-based credentials."""

    @staticmethod
    def get_credentials():
        username = getattr(settings, "AFRICASTALKING_USERNAME", "sandbox").strip() or "sandbox"
        api_key = getattr(settings, "AFRICASTALKING_API_KEY", "").strip()
        sender_id = getattr(settings, "AFRICASTALKING_SENDER_ID", "").strip()
        return username, api_key, sender_id

    @classmethod
    def send_sms(cls, phone_number: str, message: str, sender_id: str = None):
        normalized_phone = normalize_phone_number(phone_number or "")
        if not normalized_phone:
            raise ValueError("A valid phone number is required for SMS delivery.")
        if not message or not message.strip():
            raise ValueError("An SMS message body is required.")

        username, api_key, default_sender_id = cls.get_credentials()
        if not api_key:
            raise ValueError("AFRICASTALKING_API_KEY is not configured.")

        try:
            import africastalking
        except ImportError as exc:
            raise RuntimeError("The africastalking Python SDK is not installed.") from exc

        africastalking.initialize(username, api_key)
        sms = africastalking.SMS

        payload = {
            "message": message,
            "recipients": [normalized_phone],
        }
        resolved_sender = (sender_id or default_sender_id or "").strip()
        if resolved_sender:
            payload["sender_id"] = resolved_sender

        return sms.send(**payload)
