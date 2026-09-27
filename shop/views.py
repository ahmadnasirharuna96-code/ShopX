from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from accounts.forms import CustomerCreationForm
from django.db import transaction
from django.db.models import Q

from catalog.models import Product, Category
from businesses.models import Business
from customers.models import Customer, Address
from customers.services import get_or_create_customer_by_phone, create_customer_address
from orders.models import Order, OrderStatus
from orders.services import create_order
from accounts.models import User, UserRole

from .cart import SessionCart


def shop_home_view(request):
    """
    Customer Web App Home / Storefront page.
    Allows searching, category filtering, and product browsing without requiring login.
    """
    categories = Category.objects.filter(is_active=True).order_by("name")
    products_qs = Product.objects.filter(is_active=True, business__is_active=True).select_related("business", "category", "inventory")

    search_query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()

    if search_query:
        products_qs = products_qs.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query) | Q(business__name__icontains=search_query)
        )

    if category_slug:
        products_qs = products_qs.filter(category__slug=category_slug)

    cart = SessionCart(request)

    context = {
        "categories": categories,
        "products": products_qs,
        "search_query": search_query,
        "selected_category": category_slug,
        "cart_count": len(cart),
    }
    return render(request, "shop/home.html", context)


def product_detail_view(request, pk):
    """
    Detailed product page showing large image, description, seller info, stock status, quantity input.
    """
    product = get_object_or_404(Product.objects.select_related("business", "category", "inventory"), pk=pk, is_active=True)
    cart = SessionCart(request)

    context = {
        "product": product,
        "cart_count": len(cart),
    }
    return render(request, "shop/product_detail.html", context)


def cart_view(request):
    """
    Shopping cart page showing items, quantities, subtotal, and total amount.
    """
    cart = SessionCart(request)
    context = {
        "cart_items": cart.get_items(),
        "total_amount": cart.get_total_amount(),
        "cart_count": len(cart),
    }
    return render(request, "shop/cart.html", context)


def cart_add_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = SessionCart(request)
    quantity = int(request.POST.get("quantity", 1))

    # Validate against available inventory
    inv = getattr(product, "inventory", None)
    available = inv.available_quantity if inv else 0

    if available < quantity:
        messages.error(request, f"Only {available} unit(s) available for {product.name}.")
    else:
        cart.add(product=product, quantity=quantity)
        messages.success(request, f"Added {quantity}x '{product.name}' to your cart.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "shop-cart"
    return redirect(next_url)


def cart_update_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = SessionCart(request)
    quantity = int(request.POST.get("quantity", 1))

    inv = getattr(product, "inventory", None)
    available = inv.available_quantity if inv else 0

    if quantity > available:
        messages.error(request, f"Only {available} unit(s) available for {product.name}.")
    else:
        cart.update(product=product, quantity=quantity)
        messages.success(request, f"Updated quantity for '{product.name}'.")

    return redirect("shop-cart")


def cart_remove_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = SessionCart(request)
    cart.remove(product)
    messages.info(request, f"Removed '{product.name}' from your cart.")
    return redirect("shop-cart")


def checkout_view(request):
    """
    Checkout Page.
    Supports Guest checkout and Logged-in checkout without forcing registration.
    """
    cart = SessionCart(request)
    cart_items = cart.get_items()

    if not cart_items:
        messages.info(request, "Your shopping cart is empty.")
        return redirect("shop-home")

    # Prefill customer data if user is logged in
    customer_profile = None
    default_address = None
    if request.user.is_authenticated:
        customer_profile = getattr(request.user, "customer_profile", None)
        if customer_profile:
            default_address = customer_profile.get_default_address()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        area = request.POST.get("area", "").strip()
        street = request.POST.get("street", "").strip()
        house_number = request.POST.get("house_number", "").strip()
        landmark = request.POST.get("landmark", "").strip()
        city = request.POST.get("city", "Local").strip()
        state = request.POST.get("state", "State").strip()

        if not name or not phone or not area:
            messages.error(request, "Please fill in your Name, Phone Number, and Delivery Area.")
            return render(request, "shop/checkout.html", {
                "cart_items": cart_items,
                "total_amount": cart.get_total_amount(),
                "cart_count": len(cart),
                "customer_profile": customer_profile,
                "default_address": default_address,
            })

        try:
            with transaction.atomic():
                # Get or create customer record
                customer, _ = get_or_create_customer_by_phone(phone, name)
                if email:
                    customer.email = email
                
                # Link user if logged in
                if request.user.is_authenticated and not customer.user:
                    customer.user = request.user
                customer.save()

                # Create address
                address = create_customer_address(
                    customer=customer,
                    area=area,
                    street=street,
                    house_number=house_number,
                    landmark=landmark,
                    city=city,
                    state=state,
                    is_default=True
                )

                created_orders = []
                # Group cart items by business since an order belongs to a business
                items_by_business = {}
                for item in cart_items:
                    biz_id = item["product"].business_id
                    if biz_id not in items_by_business:
                        items_by_business[biz_id] = []
                    items_by_business[biz_id].append(item)

                # Create an order per business
                for biz_id, b_items in items_by_business.items():
                    business = b_items[0]["product"].business
                    for b_item in b_items:
                        order = create_order(
                            customer=customer,
                            business=business,
                            product=b_item["product"],
                            quantity=b_item["quantity"],
                            address=address
                        )
                        created_orders.append(order)

                # Clear cart upon success
                cart.clear()
                
                first_order_number = created_orders[0].order_number
                messages.success(request, "Your order has been placed successfully!")
                return redirect("shop-order-confirmation", order_number=first_order_number)

        except Exception as e:
            messages.error(request, f"Checkout failed: {str(e)}")

    context = {
        "cart_items": cart_items,
        "total_amount": cart.get_total_amount(),
        "cart_count": len(cart),
        "customer_profile": customer_profile,
        "default_address": default_address,
    }
    return render(request, "shop/checkout.html", context)


def order_confirmation_view(request, order_number):
    """
    Post-checkout Order Confirmation Page.
    """
    order = get_object_or_404(Order.objects.select_related("customer", "business", "address").prefetch_related("items"), order_number=order_number)
    cart = SessionCart(request)

    context = {
        "order": order,
        "cart_count": len(cart),
    }
    return render(request, "shop/order_confirmation.html", context)


def my_orders_view(request):
    """
    Order history page for registered customers.
    If unauthenticated, displays non-blocking prompt: 'Create an account or login to use this feature.'
    """
    cart = SessionCart(request)

    if not request.user.is_authenticated:
        return render(request, "shop/my_orders.html", {
            "is_guest": True,
            "cart_count": len(cart),
        })

    customer = getattr(request.user, "customer_profile", None)
    orders = []
    if customer:
        orders = Order.objects.filter(customer=customer).select_related("business").prefetch_related("items")
    elif request.user.phone_number:
        c = Customer.objects.filter(phone_number=request.user.phone_number).first()
        if c:
            orders = Order.objects.filter(customer=c).select_related("business").prefetch_related("items")

    context = {
        "is_guest": False,
        "orders": orders,
        "cart_count": len(cart),
    }
    return render(request, "shop/my_orders.html", context)


def customer_login_view(request):
    """
    Customer Login View.
    """
    if request.user.is_authenticated:
        return redirect("shop-home")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get("next") or "shop-home"
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, "shop/customer_login.html", {"form": form})


def customer_register_view(request):
    """
    Customer Registration View.
    """
    if request.user.is_authenticated:
        return redirect("shop-home")

    if request.method == "POST":
        form = CustomerCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = UserRole.CUSTOMER
            user.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("shop-home")
    else:
        form = CustomerCreationForm()

    return render(request, "shop/customer_register.html", {"form": form})
