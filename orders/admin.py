from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("subtotal",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "business", "customer", "total_amount",
        "status", "payment_status", "created_at"
    )
    list_filter = ("status", "payment_status", "business")
    search_fields = ("order_number", "customer__phone_number", "business__name")
    inlines = [OrderItemInline]
