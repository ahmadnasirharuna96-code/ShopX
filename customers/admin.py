from django.contrib import admin
from .models import Customer, Address


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "created_at")
    search_fields = ("name", "phone_number")
    inlines = [AddressInline]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "area", "street", "city", "is_default")
    search_fields = ("customer__phone_number", "area", "street")
