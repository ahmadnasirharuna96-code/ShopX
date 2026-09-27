import logging
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from businesses.models import Business
from common.utils import normalize_phone_number
from customers.models import Customer
from notifications.services import send_sms
from orders.models import Order
from support.models import (
    CallLog,
    CallStatus,
    Conversation,
    Message,
    MessageType,
    SupportTicket,
    SupportTicketCategory,
    SupportTicketStatus,
)

logger = logging.getLogger(__name__)


def _business_phone_for_order(order):
    if not order or not getattr(order, "business", None):
        return ""
    business_phone = getattr(order.business, "phone_number", "") or ""
    return normalize_phone_number(business_phone)


def create_order_conversation(customer, business, order):
    if not getattr(customer, "pk", None) or not getattr(business, "pk", None) or not getattr(order, "pk", None):
        raise ValidationError("Conversation requires a valid customer, business, and order.")

    if order.customer_id != customer.pk or order.business_id != business.pk:
        raise ValidationError("This customer is not associated with the selected business order.")

    conversation, _ = Conversation.objects.get_or_create(
        customer=customer,
        business=business,
        order=order,
        defaults={"status": "OPEN"},
    )
    return conversation


def create_support_ticket(customer, business, order=None, category=None, subject=None, description=None):
    if not customer:
        raise ValidationError("A support ticket requires a valid customer.")

    if order and order.customer_id != customer.pk:
        raise ValidationError("The selected order does not belong to this customer.")

    business_obj = business or (order.business if order else None)
    if business_obj is None:
        raise ValidationError("Support tickets require a business or order context.")

    if order and business_obj.pk != order.business_id:
        raise ValidationError("Support tickets must belong to the order's business.")

    category_value = category or SupportTicketCategory.OTHER
    subject_value = subject or "ShopX Support Request"
    description_value = description or "Customer reported an issue requiring support review."

    ticket_number = f"SUP-{uuid4().hex[:6].upper()}"
    ticket = SupportTicket.objects.create(
        customer=customer,
        business=business_obj,
        order=order,
        ticket_number=ticket_number,
        category=category_value,
        subject=subject_value,
        description=description_value,
        status=SupportTicketStatus.OPEN,
    )

    if customer.phone_number:
        send_sms(
            customer.phone_number,
            f"ShopX: Support ticket {ticket.ticket_number} has been created for Order #{getattr(order, 'order_number', 'N/A')}. Our team will review your request.",
        )

    return ticket


class AfricaTalkingVoiceService:
    """Thin Africa's Talking voice wrapper for business call routing."""

    @staticmethod
    def get_credentials():
        username = getattr(settings, "AFRICASTALKING_USERNAME", "sandbox") or "sandbox"
        api_key = getattr(settings, "AFRICASTALKING_API_KEY", "") or ""
        voice_number = getattr(settings, "AFRICASTALKING_VOICE_NUMBER", "") or ""
        return username, api_key, voice_number

    @classmethod
    def initiate_call(cls, phone_number: str, payload=None):
        normalized_phone = normalize_phone_number(phone_number or "")
        if not normalized_phone:
            raise ValidationError("A valid business phone number is required for the call.")

        username, api_key, voice_number = cls.get_credentials()
        if not api_key:
            raise ValidationError("AFRICASTALKING_API_KEY is not configured.")

        if not payload:
            payload = {"to": normalized_phone, "from": voice_number or "ShopX"}

        logger.info("Africa's Talking Voice request prepared for %s with payload=%s", normalized_phone, payload)
        return {"status": "queued", "to": normalized_phone, "from": payload.get("from") or voice_number or "ShopX"}


def initiate_business_call(customer, order):
    if not customer or not order:
        raise ValidationError("A valid customer and order are required to place a call.")

    if order.customer_id != customer.pk:
        raise ValidationError("This customer is not authorized to call for the selected order.")

    business_phone = _business_phone_for_order(order)
    if not business_phone:
        raise ValidationError("This business does not have a valid phone number configured.")

    response = AfricaTalkingVoiceService.initiate_call(business_phone, {"to": business_phone, "from": getattr(settings, "AFRICASTALKING_VOICE_NUMBER", "") or "ShopX"})
    call = CallLog.objects.create(
        customer=customer,
        business=order.business,
        order=order,
        call_direction="OUTBOUND",
        provider="africastalking",
        provider_call_id=response.get("call_id") or str(uuid4()),
        status=response.get("status") or CallStatus.QUEUED,
        started_at=timezone.now(),
    )
    return call


def process_support_ticket_escalation(ticket):
    ticket.status = SupportTicketStatus.ESCALATED
    ticket.save(update_fields=["status", "updated_at"])
    return ticket
