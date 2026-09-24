from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.db import transaction

from .forms import BusinessRegistrationForm
from businesses.models import Business
from businesses.forms import BusinessProfileForm


class ShopXLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("dashboard-overview")


class ShopXLogoutView(LogoutView):
    next_page = reverse_lazy("login")


def register_business_view(request):
    if request.user.is_authenticated and hasattr(request.user, "owned_business"):
        return redirect("dashboard-overview")

    if request.method == "POST":
        if request.user.is_authenticated:
            # User is logged in but doesn't have a business yet
            form = BusinessProfileForm(request.POST) if 'business_name' in request.POST else BusinessRegistrationForm(request.POST)
            # If submitted with registration form or profile form
            b_name = request.POST.get("business_name") or request.POST.get("name")
            b_phone = request.POST.get("business_phone") or request.POST.get("phone_number")
            b_address = request.POST.get("business_address") or request.POST.get("address")
            city = request.POST.get("city", "Abuja")
            state = request.POST.get("state", "FCT")

            if b_name and b_phone and b_address:
                Business.objects.create(
                    owner=request.user,
                    name=b_name,
                    phone_number=b_phone,
                    address=b_address,
                    city=city,
                    state=state,
                )
                return redirect("dashboard-overview")
        
        form = BusinessRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.role = "BUSINESS_OWNER"
                user.save()

                Business.objects.create(
                    owner=user,
                    name=form.cleaned_data["business_name"],
                    phone_number=form.cleaned_data["business_phone"],
                    address=form.cleaned_data["business_address"],
                    city=form.cleaned_data["city"],
                    state=form.cleaned_data["state"],
                )
                login(request, user)
                return redirect("dashboard-overview")
    else:
        form = BusinessRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})
