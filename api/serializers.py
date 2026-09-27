from rest_framework import serializers
from businesses.models import Business
from catalog.models import Category, Product
from inventory.models import Inventory
from customers.models import Customer, Address
from orders.models import Order, OrderItem
from rest_framework.exceptions import ValidationError


class BusinessSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Business
        fields = [
            "id", "owner_username", "name", "description",
            "phone_number", "address", "city", "state", "is_active",
            "created_at", "updated_at"
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "is_active", "created_at", "updated_at"]


class InventorySerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "product", "quantity", "reserved_quantity",
            "available_quantity", "low_stock_threshold",
            "is_low_stock", "is_out_of_stock", "updated_at"
        ]


class ProductSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    inventory = InventorySerializer(read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    image_url = serializers.CharField(source="image_url", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "business", "business_name", "category", "category_name",
            "name", "description", "price", "is_active", "inventory",
            "image", "image_url", "created_at", "updated_at"
        ]

    def validate(self, attrs):
        # Enforce product image for new products created via API when the
        # product instance does not already have an image.
        request = self.context.get("request")
        is_create = self.instance is None

        # If creating and no image provided in data/files, reject.
        if is_create:
            has_image_in_attrs = bool(attrs.get("image"))
            has_image_in_files = False
            if request is not None:
                has_image_in_files = bool(request.FILES.get("image"))

            if not (has_image_in_attrs or has_image_in_files):
                raise ValidationError({"image": "Product image is required."})

        return attrs


class AddressSerializer(serializers.ModelSerializer):
    full_address = serializers.CharField(source="full_address_single_line", read_only=True)

    class Meta:
        model = Address
        fields = [
            "id", "area", "street", "house_number", "landmark",
            "delivery_note", "city", "state", "is_default", "full_address"
        ]


class CustomerSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "phone_number", "name", "addresses", "created_at", "updated_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "unit_price", "quantity", "subtotal"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_phone = serializers.CharField(source="customer.phone_number", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer", "customer_phone", "customer_name",
            "business", "business_name", "address", "status", "status_display",
            "payment_method", "payment_status", "total_amount",
            "customer_confirmed", "business_confirmed", "reservation_expires_at",
            "items", "created_at", "updated_at"
        ]
