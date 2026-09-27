from django.urls import path

from .views import (
    business_support_chat_view,
    business_support_index_view,
    customer_support_chat_view,
    support_ticket_create_view,
)

urlpatterns = [
    path("orders/<str:order_number>/chat/", customer_support_chat_view, name="customer-order-support"),
    path("orders/<str:order_number>/ticket/", support_ticket_create_view, name="customer-support-ticket"),
    path("dashboard/", business_support_index_view, name="dashboard-support"),
    path("dashboard/conversation/<int:pk>/", business_support_chat_view, name="dashboard-support-chat"),
]
