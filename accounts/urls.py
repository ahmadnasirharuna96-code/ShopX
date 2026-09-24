from django.urls import path
from .views import ShopXLoginView, ShopXLogoutView, register_business_view

urlpatterns = [
    path("login/", ShopXLoginView.as_view(), name="login"),
    path("logout/", ShopXLogoutView.as_view(), name="logout"),
    path("register/", register_business_view, name="register"),
]
