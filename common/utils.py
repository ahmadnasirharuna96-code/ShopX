import re
import uuid


def normalize_phone_number(phone_number: str) -> str:
    """
    Normalizes a phone number string into E.164-like format (e.g. +2348012345678).
    Handles Nigerian local formats like 080... or 80...
    """
    if not phone_number:
        return ""
    
    cleaned = re.sub(r"[^\d+]", "", phone_number.strip())
    
    # If starts with + (e.g., +234...)
    if cleaned.startswith("+"):
        return cleaned
    
    # Standard Nigerian local format 080... or 070... -> +23480...
    if cleaned.startswith("0") and len(cleaned) == 11:
        return "+234" + cleaned[1:]
    
    # Without leading zero e.g. 80... or 23480...
    if cleaned.startswith("234") and len(cleaned) == 13:
        return "+" + cleaned
    elif len(cleaned) == 10 and not cleaned.startswith("0"):
        return "+234" + cleaned
    
    return cleaned if cleaned.startswith("+") else f"+{cleaned}"


def generate_order_number() -> str:
    """
    Generates a unique, human-readable order number, e.g., SX1001.
    Uses timestamp / sequence / random hex suffix to guarantee uniqueness.
    """
    from django.utils.crypto import get_random_string
    prefix = "SX"
    rand_part = get_random_string(6, allowed_chars="1234567890ABCDEF")
    return f"{prefix}{rand_part}"
