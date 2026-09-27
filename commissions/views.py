from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from businesses.models import Business
from commissions.models import CommissionLedger, CommissionSettlement, CommissionWallet, PaystackPayment
from commissions.services import CommissionService, PaystackService


def get_merchant_business(user):
    if not user.is_authenticated:
        return None
    return getattr(user, "owned_business", None)


@login_required
def commission_dashboard_view(request):
    business = get_merchant_business(request.user)
    if not business:
        messages.error(request, "Please set up your business profile first.")
        return redirect("register")

    wallet, _ = CommissionWallet.objects.get_or_create(business=business)
    settlements = CommissionSettlement.objects.filter(business=business)
    total_sales = sum((s.commission_amount for s in settlements), Decimal("0.00"))
    paid_commission = sum((ledger.amount for ledger in CommissionLedger.objects.filter(business=business, transaction_type=CommissionLedger.TransactionType.COMMISSION_PAYMENT)), Decimal("0.00"))
    outstanding = wallet.outstanding_balance
    context = {
        "business": business,
        "wallet": wallet,
        "total_sales": total_sales,
        "completed_orders": settlements.count(),
        "shopx_commission": total_sales,
        "paid_commission": paid_commission,
        "outstanding_commission": outstanding,
        "wallet_balance": wallet.balance,
    }
    return render(request, "dashboard/commission_dashboard.html", context)


@login_required
def commission_history_view(request):
    business = get_merchant_business(request.user)
    if not business:
        return redirect("dashboard-overview")

    settlements = CommissionSettlement.objects.filter(business=business).select_related("order")
    ledgers = CommissionLedger.objects.filter(business=business).order_by("-created_at")
    return render(request, "dashboard/commission_history.html", {"business": business, "settlements": settlements, "ledgers": ledgers})


@login_required
@require_http_methods(["GET", "POST"])
def wallet_topup_view(request):
    business = get_merchant_business(request.user)
    if not business:
        return redirect("dashboard-overview")

    if request.method == "POST":
        amount = request.POST.get("amount")
        try:
            amount_value = Decimal(str(amount))
        except Exception:
            messages.error(request, "Please provide a valid amount.")
            return redirect("commission-dashboard")
        if amount_value <= 0:
            messages.error(request, "Top-up amount must be greater than zero.")
            return redirect("commission-dashboard")

        payment = PaystackService.initialize_transaction(
            business=business,
            amount=amount_value,
            purpose=PaystackPayment.Purpose.WALLET_TOPUP,
            metadata={"business_id": business.pk, "purpose": PaystackPayment.Purpose.WALLET_TOPUP},
        )
        return redirect(payment.authorization_url or "commission-dashboard")

    return render(request, "dashboard/wallet_topup.html", {"business": business})


@login_required
@require_http_methods(["GET"])
def paystack_verify_view(request):
    reference = request.GET.get("reference")
    if not reference:
        messages.error(request, "Invalid Paystack payment reference.")
        return redirect("commission-dashboard")

    try:
        data = PaystackService.verify_transaction(reference)
    except Exception as exc:
        messages.error(request, str(exc))
        return redirect("commission-dashboard")

    if data.get("status") != "success":
        messages.error(request, "Paystack payment could not be verified.")
        return redirect("commission-dashboard")

    payment = PaystackPayment.objects.filter(paystack_reference=reference).first()
    if payment is None:
        messages.error(request, "No matching merchant payment record was found.")
        return redirect("commission-dashboard")
    if payment.status == PaystackPayment.Status.VERIFIED:
        messages.info(request, "This Paystack payment has already been processed.")
        return redirect("commission-dashboard")

    payment.status = PaystackPayment.Status.VERIFIED
    payment.verified_at = payment.created_at
    payment.save(update_fields=["status", "verified_at", "updated_at"])

    if payment.purpose == PaystackPayment.Purpose.WALLET_TOPUP:
        CommissionService.apply_wallet_topup(payment.business, payment.amount, payment.paystack_reference or payment.internal_reference, "Wallet top-up via Paystack")
    elif payment.purpose == PaystackPayment.Purpose.COMMISSION_PAYMENT:
        CommissionService.settle_outstanding_commission(payment.business, payment.amount, payment.paystack_reference or payment.internal_reference, "Outstanding commission payment via Paystack")

    messages.success(request, "Payment verified successfully.")
    return redirect("commission-dashboard")
