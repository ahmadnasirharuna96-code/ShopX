from django.db import models

from accounts.models import User
from businesses.models import Business
from common.models import TimeStampedModel
from customers.models import Customer
from orders.models import Order


class ConversationStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"


class MessageType(models.TextChoices):
    TEXT = "TEXT", "Text"
    SYSTEM = "SYSTEM", "System"
    COMPLAINT = "COMPLAINT", "Complaint"


class Conversation(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="support_conversations")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="support_conversations")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="support_conversations")
    status = models.CharField(max_length=20, choices=ConversationStatus.choices, default=ConversationStatus.OPEN, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["customer", "business", "order"], name="unique_support_conversation")
        ]

    def __str__(self):
        return f"{self.customer.name} <> {self.business.name} - Order #{self.order.order_number}"

    @property
    def latest_message(self):
        return self.messages.order_by("-created_at").first()

    def add_message(self, sender, message_type, content):
        return Message.objects.create(
            conversation=self,
            sender=sender,
            message_type=message_type,
            content=content,
        )


class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=50, db_index=True)
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.TEXT, db_index=True)
    content = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.content[:40]}"


class SupportTicketCategory(models.TextChoices):
    ORDER_PROBLEM = "ORDER_PROBLEM", "Order Problem"
    PRODUCT_PROBLEM = "PRODUCT_PROBLEM", "Product Problem"
    DELIVERY_PROBLEM = "DELIVERY_PROBLEM", "Delivery Problem"
    BUSINESS_COMPLAINT = "BUSINESS_COMPLAINT", "Business Complaint"
    OTHER = "OTHER", "Other"
    PLATFORM_ISSUE = "PLATFORM_ISSUE", "Platform Issue"


class SupportTicketStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"
    ESCALATED = "ESCALATED", "Escalated"


class TicketPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class SupportTicket(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="support_tickets")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="support_tickets", null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="support_tickets")
    ticket_number = models.CharField(max_length=30, unique=True, db_index=True)
    category = models.CharField(max_length=30, choices=SupportTicketCategory.choices, default=SupportTicketCategory.OTHER)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=TicketPriority.choices, default=TicketPriority.MEDIUM)
    status = models.CharField(max_length=20, choices=SupportTicketStatus.choices, default=SupportTicketStatus.OPEN, db_index=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_support_tickets")
    resolution = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket_number} - {self.get_category_display()}"


class CallDirection(models.TextChoices):
    OUTBOUND = "OUTBOUND", "Outbound"
    INBOUND = "INBOUND", "Inbound"


class CallStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    RINGING = "RINGING", "Ringing"
    ANSWERED = "ANSWERED", "Answered"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    NO_ANSWER = "NO_ANSWER", "No Answer"


class CallLog(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="voice_calls")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="voice_calls")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="voice_calls")
    call_direction = models.CharField(max_length=20, choices=CallDirection.choices, default=CallDirection.OUTBOUND, db_index=True)
    provider = models.CharField(max_length=40, default="africastalking", db_index=True)
    provider_call_id = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=20, choices=CallStatus.choices, default=CallStatus.QUEUED, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.phone_number} -> {self.business.name} ({self.status})"
