from django.db import models

from common.models import TimeStampedModel
from orders.models import Order


class SMSNotificationType(models.TextChoices):
    ORDER_CREATED = "ORDER_CREATED", "Order Created"
    BUSINESS_NEW_ORDER = "BUSINESS_NEW_ORDER", "Business New Order"
    ORDER_ACCEPTED = "ORDER_ACCEPTED", "Order Accepted"
    ORDER_REJECTED = "ORDER_REJECTED", "Order Rejected"
    CUSTOMER_CONFIRMED = "CUSTOMER_CONFIRMED", "Customer Confirmed"
    ORDER_READY = "ORDER_READY", "Order Ready"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
    ORDER_DELIVERED = "ORDER_DELIVERED", "Order Delivered"
    ORDER_CANCELLED = "ORDER_CANCELLED", "Order Cancelled"
    ORDER_STATUS_UPDATE = "ORDER_STATUS_UPDATE", "Order Status Update"


class SMSNotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    DELIVERED = "DELIVERED", "Delivered"


class SMSNotification(TimeStampedModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="sms_notifications",
        null=True,
        blank=True,
        db_index=True,
    )
    recipient = models.CharField(max_length=30, db_index=True)
    notification_type = models.CharField(
        max_length=30,
        choices=SMSNotificationType.choices,
        default=SMSNotificationType.ORDER_STATUS_UPDATE,
        db_index=True,
    )
    message = models.TextField()
    provider = models.CharField(max_length=40, default="africastalking", db_index=True)
    provider_message_id = models.CharField(max_length=200, blank=True, default="")
    provider_response = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=SMSNotificationStatus.choices,
        default=SMSNotificationStatus.PENDING,
        db_index=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "notification_type", "recipient"],
                name="unique_order_sms_notification",
            )
        ]

    def __str__(self):
        return f"{self.notification_type} -> {self.recipient} ({self.status})"
