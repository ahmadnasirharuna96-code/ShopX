from django.urls import path

from .views import (
    commission_dashboard_view,
    commission_history_view,
    wallet_topup_view,
    paystack_verify_view,
)

urlpatterns = [
    path("dashboard/", commission_dashboard_view, name="commission-dashboard"),
    path("history/", commission_history_view, name="commission-history"),
    path("wallet/topup/", wallet_topup_view, name="commission-wallet-topup"),
    path("paystack/verify/", paystack_verify_view, name="commission-paystack-verify"),
]
