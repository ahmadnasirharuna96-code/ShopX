from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction

from accounts.permissions import BusinessUserRequiredMixin
from catalog.models import Product, Category
from catalog.forms import ProductForm
from inventory.models import Inventory
from inventory.services import adjust_stock
from inventory.forms import StockAdjustmentForm
from orders.models import Order, OrderStatus
from orders.services import accept_order, reject_order, update_order_status
from .models import Business
from .forms import BusinessProfileForm


def get_merchant_business(user):
    if not user.is_authenticated:
        return None
    return getattr(user, "owned_business", None)


@login_required
def dashboard_overview_view(request):
    business = get_merchant_business(request.user)
    if not business:
        messages.error(request, "Please set up your business profile first.")
        return redirect("register")

    products_qs = Product.objects.filter(business=business)
    orders_qs = Order.objects.filter(business=business)

    total_products = products_qs.count()
    pending_orders_count = orders_qs.filter(status=OrderStatus.PENDING).count()
    confirmed_orders_count = orders_qs.filter(
        status__in=[OrderStatus.BUSINESS_CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY_FOR_DELIVERY, OrderStatus.OUT_FOR_DELIVERY]
    ).count()

    low_stock_products = [
        p for p in products_qs.select_related("inventory")
        if hasattr(p, "inventory") and p.inventory.is_low_stock
    ]
    low_stock_count = len(low_stock_products)

    recent_orders = orders_qs.select_related("customer", "address").prefetch_related("items")[:10]

    context = {
        "business": business,
        "total_products": total_products,
        "pending_orders_count": pending_orders_count,
        "confirmed_orders_count": confirmed_orders_count,
        "low_stock_count": low_stock_count,
        "recent_orders": recent_orders,
    }
    return render(request, "dashboard/index.html", context)


@login_required
def products_list_view(request):
    business = get_merchant_business(request.user)
    products = Product.objects.filter(business=business).select_related("category", "inventory")
    return render(request, "dashboard/products.html", {"business": business, "products": products})


@login_required
def product_create_view(request):
    business = get_merchant_business(request.user)
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                product = form.save(commit=False)
                product.business = business
                product.save()

                initial_stock = form.cleaned_data.get("initial_stock", 10)
                low_stock = form.cleaned_data.get("low_stock_threshold", 5)
                Inventory.objects.create(
                    product=product,
                    quantity=initial_stock,
                    reserved_quantity=0,
                    low_stock_threshold=low_stock
                )
            messages.success(request, f"Product '{product.name}' created successfully.")
            return redirect("dashboard-products")
    else:
        form = ProductForm()

    return render(request, "dashboard/product_form.html", {"form": form, "title": "Add New Product"})


@login_required
def product_edit_view(request, pk):
    business = get_merchant_business(request.user)
    product = get_object_or_404(Product, pk=pk, business=business)
    inventory = getattr(product, "inventory", None)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            if inventory:
                low_stock = form.cleaned_data.get("low_stock_threshold")
                if low_stock:
                    inventory.low_stock_threshold = low_stock
                    inventory.save()
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect("dashboard-products")
    else:
        initial = {}
        if inventory:
            initial["low_stock_threshold"] = inventory.low_stock_threshold
            initial["initial_stock"] = inventory.quantity
        form = ProductForm(instance=product, initial=initial)

    return render(request, "dashboard/product_form.html", {"form": form, "product": product, "title": "Edit Product"})


@login_required
def inventory_list_view(request):
    business = get_merchant_business(request.user)
    products = Product.objects.filter(business=business).select_related("inventory", "category")
    return render(request, "dashboard/inventory.html", {"business": business, "products": products})


@login_required
def stock_adjust_view(request, pk):
    business = get_merchant_business(request.user)
    product = get_object_or_404(Product, pk=pk, business=business)
    inventory = get_object_or_404(Inventory, product=product)

    if request.method == "POST":
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                adjust_stock(
                    product=product,
                    new_quantity=form.cleaned_data["quantity"],
                    low_stock_threshold=form.cleaned_data["low_stock_threshold"]
                )
                messages.success(request, f"Stock for '{product.name}' updated successfully.")
                return redirect("dashboard-inventory")
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = StockAdjustmentForm(initial={
            "quantity": inventory.quantity,
            "low_stock_threshold": inventory.low_stock_threshold
        })

    return render(request, "dashboard/stock_adjust.html", {"form": form, "product": product, "inventory": inventory})


@login_required
def orders_list_view(request):
    business = get_merchant_business(request.user)
    status_filter = request.GET.get("status", "")
    orders = Order.objects.filter(business=business).select_related("customer", "address").prefetch_related("items")

    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        "business": business,
        "orders": orders,
        "status_filter": status_filter,
        "OrderStatus": OrderStatus,
    }
    return render(request, "dashboard/orders.html", context)


@login_required
@require_POST
def order_accept_view(request, pk):
    business = get_merchant_business(request.user)
    order = get_object_or_404(Order, pk=pk, business=business)
    try:
        accept_order(order, request.user)
        messages.success(request, f"Order #{order.order_number} confirmed.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("dashboard-orders")


@login_required
@require_POST
def order_reject_view(request, pk):
    business = get_merchant_business(request.user)
    order = get_object_or_404(Order, pk=pk, business=business)
    try:
        reject_order(order, request.user)
        messages.info(request, f"Order #{order.order_number} rejected.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("dashboard-orders")


@login_required
@require_POST
def order_status_update_view(request, pk):
    business = get_merchant_business(request.user)
    order = get_object_or_404(Order, pk=pk, business=business)
    new_status = request.POST.get("status")
    try:
        update_order_status(order, new_status, request.user)
        messages.success(request, f"Order #{order.order_number} updated to {new_status}.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("dashboard-orders")


@login_required
def business_profile_view(request):
    business = get_merchant_business(request.user)
    if request.method == "POST":
        form = BusinessProfileForm(request.POST, instance=business)
        if form.is_valid():
            form.save()
            messages.success(request, "Business profile updated successfully.")
            return redirect("dashboard-profile")
    else:
        form = BusinessProfileForm(instance=business)

    return render(request, "dashboard/profile.html", {"form": form, "business": business})
