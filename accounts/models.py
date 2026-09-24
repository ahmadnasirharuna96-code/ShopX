from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    BUSINESS_OWNER = "BUSINESS_OWNER", "Business Owner"
    BUSINESS_STAFF = "BUSINESS_STAFF", "Business Staff"


class User(AbstractUser):
    """
    Custom User model for ShopX.
    Supports authenticated platform roles (ADMIN, BUSINESS_OWNER, BUSINESS_STAFF).
    """
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.BUSINESS_OWNER,
        help_text="Role of the authenticated platform user."
    )
    phone_number = models.CharField(max_length=20, blank=True, default="")

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN or self.is_superuser

    @property
    def is_business_owner(self) -> bool:
        return self.role == UserRole.BUSINESS_OWNER

    @property
    def is_business_user(self) -> bool:
        return self.role in (UserRole.BUSINESS_OWNER, UserRole.BUSINESS_STAFF) or self.is_admin

    def get_business(self):
        """
        Returns the business associated with this user.
        """
        if hasattr(self, 'owned_business'):
            return self.owned_business
        return getattr(self, 'staff_business', None)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
