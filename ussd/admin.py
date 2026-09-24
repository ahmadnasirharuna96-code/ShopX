from django.contrib import admin
from .models import USSDSession


@admin.register(USSDSession)
class USSDSessionAdmin(admin.ModelAdmin):
    list_display = ("session_id", "phone_number", "current_state", "updated_at", "expires_at")
    list_filter = ("current_state",)
    search_fields = ("session_id", "phone_number")
