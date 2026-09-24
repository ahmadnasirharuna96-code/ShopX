from django.contrib import admin
from .models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "phone_number", "city", "state", "is_active", "created_at")
    list_filter = ("is_active", "state", "city")
    search_fields = ("name", "phone_number", "owner__username")
