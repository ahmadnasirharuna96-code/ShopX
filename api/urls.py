from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BusinessViewSet,
    CategoryViewSet,
    ProductViewSet,
    InventoryViewSet,
    CustomerViewSet,
    OrderViewSet,
)

router = DefaultRouter()
router.register(r"businesses", BusinessViewSet, basename="api-business")
router.register(r"categories", CategoryViewSet, basename="api-category")
router.register(r"products", ProductViewSet, basename="api-product")
router.register(r"inventory", InventoryViewSet, basename="api-inventory")
router.register(r"customers", CustomerViewSet, basename="api-customer")
router.register(r"orders", OrderViewSet, basename="api-order")

urlpatterns = [
    path("", include(router.urls)),
]
