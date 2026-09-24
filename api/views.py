from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from businesses.models import Business
from catalog.models import Category, Product
from inventory.models import Inventory
from customers.models import Customer
from orders.models import Order
from orders.services import accept_order, reject_order, update_order_status
from .serializers import (
    BusinessSerializer,
    CategorySerializer,
    ProductSerializer,
    InventorySerializer,
    CustomerSerializer,
    OrderSerializer,
)


class BusinessViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Business.objects.filter(is_active=True)
    serializer_class = BusinessSerializer
    permission_classes = [permissions.AllowAny]


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True)
        # Business isolation for authenticated users
        if self.request.user.is_authenticated and hasattr(self.request.user, "owned_business"):
            return Product.objects.filter(business=self.request.user.owned_business)
        return qs


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "owned_business"):
            return Inventory.objects.filter(product__business=self.request.user.owned_business)
        return Inventory.objects.none()


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "owned_business"):
            # Customers who have placed orders with this merchant's business
            biz = self.request.user.owned_business
            return Customer.objects.filter(orders__business=biz).distinct()
        return Customer.objects.none()


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "owned_business"):
            return Order.objects.filter(business=self.request.user.owned_business).prefetch_related("items")
        return Order.objects.none()

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        order = self.get_object()
        updated_order = accept_order(order, request.user)
        return Response(OrderSerializer(updated_order).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        order = self.get_object()
        updated_order = reject_order(order, request.user)
        return Response(OrderSerializer(updated_order).data)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get("status")
        updated_order = update_order_status(order, new_status, request.user)
        return Response(OrderSerializer(updated_order).data)
