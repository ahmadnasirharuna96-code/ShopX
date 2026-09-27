from django.contrib import admin

from .models import SMSNotification


@admin.register(SMSNotification)
class SMSNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "notification_type",
        "order",
        "status",
        "provider_message_id",
        "created_at",
        "sent_at",
    )
    list_filter = ("notification_type", "status", "provider")
    search_fields = ("recipient", "notification_type", "provider_message_id", "order__order_number")
    readonly_fields = ("created_at", "sent_at", "provider_message_id", "provider_response")
