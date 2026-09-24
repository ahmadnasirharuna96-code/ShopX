from rest_framework import permissions
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin


class IsBusinessUserPermission(permissions.BasePermission):
    """
    DRF permission to check if user is a business owner/staff or admin.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_business_user
        )


class BusinessUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Django view mixin to restrict access to authenticated business users.
    """
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_business_user
