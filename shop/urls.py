from django.urls import path
from .views import (
    shop_home_view,
    product_detail_view,
    cart_view,
    cart_add_view,
    cart_update_view,
    cart_remove_view,
    checkout_view,
    order_confirmation_view,
    my_orders_view,
    customer_login_view,
    customer_register_view,
)

urlpatterns = [
    path("", shop_home_view, name="shop-home"),
    path("product/<int:pk>/", product_detail_view, name="shop-product-detail"),
    path("cart/", cart_view, name="shop-cart"),
    path("cart/add/<int:product_id>/", cart_add_view, name="cart-add"),
    path("cart/update/<int:product_id>/", cart_update_view, name="cart-update"),
    path("cart/remove/<int:product_id>/", cart_remove_view, name="cart-remove"),
    path("checkout/", checkout_view, name="shop-checkout"),
    path("order/<str:order_number>/confirmation/", order_confirmation_view, name="shop-order-confirmation"),
    path("orders/", my_orders_view, name="shop-my-orders"),
    path("login/", customer_login_view, name="customer-login"),
    path("register/", customer_register_view, name="customer-register"),
]
