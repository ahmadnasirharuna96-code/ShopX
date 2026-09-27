from django.contrib import admin

from .models import CallLog, Conversation, Message, SupportTicket


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("customer", "business", "order", "status", "updated_at")
    list_filter = ("status", "business")
    search_fields = ("customer__phone_number", "business__name", "order__order_number")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "message_type", "is_read", "created_at")
    list_filter = ("sender", "message_type", "is_read")


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "customer", "business", "category", "status", "created_at")
    list_filter = ("status", "category")
    search_fields = ("ticket_number", "customer__phone_number", "business__name")


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ("customer", "business", "order", "call_direction", "status", "provider", "created_at")
    list_filter = ("call_direction", "status", "provider")
    search_fields = ("provider_call_id", "customer__phone_number", "business__name")
