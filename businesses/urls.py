from django.urls import path
from .views import (
    dashboard_overview_view,
    products_list_view,
    product_create_view,
    product_edit_view,
    inventory_list_view,
    stock_adjust_view,
    orders_list_view,
    order_accept_view,
    order_reject_view,
    order_status_update_view,
    business_profile_view,
)

urlpatterns = [
    path("", dashboard_overview_view, name="dashboard-overview"),
    path("products/", products_list_view, name="dashboard-products"),
    path("products/create/", product_create_view, name="product-create"),
    path("products/<int:pk>/edit/", product_edit_view, name="product-edit"),
    path("inventory/", inventory_list_view, name="dashboard-inventory"),
    path("inventory/<int:pk>/adjust/", stock_adjust_view, name="stock-adjust"),
    path("orders/", orders_list_view, name="dashboard-orders"),
    path("orders/<int:pk>/accept/", order_accept_view, name="order-accept"),
    path("orders/<int:pk>/reject/", order_reject_view, name="order-reject"),
    path("orders/<int:pk>/status/", order_status_update_view, name="order-status-update"),
    path("profile/", business_profile_view, name="dashboard-profile"),
]
