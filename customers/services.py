from typing import Tuple
from common.utils import normalize_phone_number
from .models import Customer, Address


def get_or_create_customer_by_phone(phone_number: str, name: str = None) -> Tuple[Customer, bool]:
    """
    Retrieves or creates a Customer by phone number.
    Ensures phone number normalization.
    """
    norm_phone = normalize_phone_number(phone_number)
    customer, created = Customer.objects.get_or_create(
        phone_number=norm_phone,
        defaults={"name": name.strip() if name else "Valued Customer"}
    )
    if not created and name and customer.name == "Valued Customer":
        customer.name = name.strip()
        customer.save(update_fields=["name", "updated_at"])
    return customer, created


def create_customer_address(
    customer: Customer,
    area: str,
    street: str = "",
    house_number: str = "",
    landmark: str = "",
    delivery_note: str = "",
    city: str = "Local City",
    state: str = "State",
    is_default: bool = True
) -> Address:
    """
    Creates a new delivery address for a customer.
    """
    address = Address.objects.create(
        customer=customer,
        area=area.strip(),
        street=street.strip(),
        house_number=house_number.strip(),
        landmark=landmark.strip(),
        delivery_note=delivery_note.strip(),
        city=city.strip(),
        state=state.strip(),
        is_default=is_default
    )
    return address
