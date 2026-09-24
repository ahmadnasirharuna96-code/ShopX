from django.contrib import admin
from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "reserved_quantity", "available_quantity", "low_stock_threshold", "updated_at")
    search_fields = ("product__name", "product__business__name")
