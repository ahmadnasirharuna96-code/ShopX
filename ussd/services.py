import logging
from datetime import timedelta
from typing import Tuple
from django.utils import timezone

from common.utils import normalize_phone_number
from catalog.models import Category, Product
from businesses.models import Business
from customers.models import Customer, Address
from customers.services import get_or_create_customer_by_phone, create_customer_address
from orders.models import Order
from orders.services import create_order
from inventory.models import Inventory
from .models import USSDSession

logger = logging.getLogger(__name__)


class USSDService:
    """
    Africa's Talking USSD State Machine Service.
    Parses request inputs, manages session state, returns CON/END responses.
    """

    @classmethod
    def handle_request(cls, session_id: str, phone_number: str, text: str) -> str:
        norm_phone = normalize_phone_number(phone_number)
        
        # Retrieve or create session
        expires = timezone.now() + timedelta(minutes=5)
        session, _ = USSDSession.objects.get_or_create(
            session_id=session_id,
            defaults={"phone_number": norm_phone, "current_state": "START", "expires_at": expires}
        )

        # Africa's Talking provides user inputs concatenated by *
        inputs = text.split("*") if text else []
        latest_input = inputs[-1].strip() if inputs else ""

        # Session timeout check
        if session.expires_at and session.expires_at < timezone.now():
            session.current_state = "START"
            session.temp_data = {}
            session.save()

        session.expires_at = expires

        try:
            response_text, is_end = cls._dispatch_state(session, norm_phone, inputs, latest_input)
            if is_end:
                session.delete()
            else:
                session.save()
            
            prefix = "END " if is_end else "CON "
            return f"{prefix}{response_text}"

        except Exception as e:
            logger.error(f"USSD processing error for session {session_id}: {e}", exc_info=True)
            return "END Sorry, ShopX is temporarily unavailable. Please try again later."

    @classmethod
    def _dispatch_state(cls, session: USSDSession, phone_number: str, inputs: list, latest_input: str) -> Tuple[str, bool]:
        state = session.current_state

        # Initial launch
        if not inputs or not latest_input or state == "START":
            return cls._show_initial_menu(session)

        if state == "MAIN_MENU":
            if latest_input == "1":
                return cls._show_category_selection(session)
            elif latest_input == "2":
                return cls._show_my_orders(phone_number)
            elif latest_input == "3":
                return cls._show_help()
            else:
                return "Invalid option.\n1. Browse Shops\n2. My Orders\n3. Help", False

        elif state == "CATEGORY_SELECTION":
            return cls._handle_category_selection(session, latest_input)

        elif state == "BUSINESS_SELECTION":
            return cls._handle_business_selection(session, latest_input)

        elif state == "PRODUCT_SELECTION":
            return cls._handle_product_selection(session, latest_input)

        elif state == "PRODUCT_DETAIL":
            return cls._handle_product_detail(session, latest_input)

        elif state == "QUANTITY_INPUT":
            return cls._handle_quantity_input(session, phone_number, latest_input)

        elif state == "ADDRESS_SELECTION":
            return cls._handle_address_selection(session, latest_input)

        elif state == "NEW_ADDRESS_NAME":
            session.temp_data["name"] = latest_input
            session.current_state = "NEW_ADDRESS_AREA"
            return "Enter your area/neighborhood (e.g. Wuse 2):", False

        elif state == "NEW_ADDRESS_AREA":
            session.temp_data["area"] = latest_input
            session.current_state = "NEW_ADDRESS_STREET"
            return "Enter street & house number:", False

        elif state == "NEW_ADDRESS_STREET":
            session.temp_data["street"] = latest_input
            session.current_state = "NEW_ADDRESS_LANDMARK"
            return "Enter nearby landmark (or 0 to skip):", False

        elif state == "NEW_ADDRESS_LANDMARK":
            session.temp_data["landmark"] = "" if latest_input == "0" else latest_input
            return cls._show_order_summary(session)

        elif state == "ORDER_SUMMARY":
            return cls._handle_order_confirmation(session, phone_number, latest_input)

        # Fallback reset
        session.current_state = "START"
        return cls._show_initial_menu(session)

    @classmethod
    def _show_initial_menu(cls, session: USSDSession) -> Tuple[str, bool]:
        session.current_state = "MAIN_MENU"
        menu = (
            "Welcome to ShopX\n"
            "Local commerce, connected.\n\n"
            "1. Browse Shops\n"
            "2. My Orders\n"
            "3. Help"
        )
        return menu, False

    @classmethod
    def _show_help(cls) -> Tuple[str, bool]:
        help_msg = (
            "ShopX connects you directly to local businesses.\n"
            "Browse items, check real-time stock, and order with Pay on Delivery.\n"
            "Support: +23480000SHOPX"
        )
        return help_msg, True

    @classmethod
    def _show_my_orders(cls, phone_number: str) -> Tuple[str, bool]:
        customer = Customer.objects.filter(phone_number=phone_number).first()
        if not customer:
            return "You have no order history with ShopX.", True
        
        recent_orders = Order.objects.filter(customer=customer).order_by("-created_at")[:3]
        if not recent_orders.exists():
            return "You have no recent orders.", True

        lines = ["Recent ShopX Orders:"]
        for o in recent_orders:
            lines.append(f"#{o.order_number}: N{o.total_amount} ({o.get_status_display()})")
        return "\n".join(lines), True

    @classmethod
    def _show_category_selection(cls, session: USSDSession) -> Tuple[str, bool]:
        categories = list(Category.objects.filter(is_active=True).order_by("name")[:6])
        if not categories:
            return "No active product categories available currently.", True

        session.current_state = "CATEGORY_SELECTION"
        session.temp_data["categories"] = [c.id for c in categories]

        lines = ["Select category:"]
        for idx, cat in enumerate(categories, 1):
            lines.append(f"{idx}. {cat.name}")

        return "\n".join(lines), False

    @classmethod
    def _handle_category_selection(cls, session: USSDSession, input_val: str) -> Tuple[str, bool]:
        cat_ids = session.temp_data.get("categories", [])
        try:
            choice = int(input_val)
            if choice < 1 or choice > len(cat_ids):
                return "Invalid category choice. Please try again.", False
            
            selected_cat_id = cat_ids[choice - 1]
            session.category_id = selected_cat_id
            
            # Fetch businesses offering products in this category
            businesses = list(
                Business.objects.filter(
                    is_active=True,
                    products__category_id=selected_cat_id,
                    products__is_active=True
                ).distinct().order_by("name")[:6]
            )

            if not businesses:
                return "No active shops currently available in this category.", True

            session.temp_data["businesses"] = [b.id for b in businesses]
            session.current_state = "BUSINESS_SELECTION"

            lines = ["Select shop:"]
            for idx, b in enumerate(businesses, 1):
                lines.append(f"{idx}. {b.name}")

            return "\n".join(lines), False

        except ValueError:
            return "Invalid input. Please enter a number.", False

    @classmethod
    def _handle_business_selection(cls, session: USSDSession, input_val: str) -> Tuple[str, bool]:
        biz_ids = session.temp_data.get("businesses", [])
        try:
            choice = int(input_val)
            if choice < 1 or choice > len(biz_ids):
                return "Invalid shop choice. Please try again.", False

            selected_biz_id = biz_ids[choice - 1]
            session.business_id = selected_biz_id

            products = list(
                Product.objects.filter(
                    business_id=selected_biz_id,
                    category_id=session.category_id,
                    is_active=True
                ).order_by("name")[:6]
            )

            if not products:
                return "No products available in this shop.", True

            session.temp_data["products"] = [p.id for p in products]
            session.current_state = "PRODUCT_SELECTION"

            lines = ["Select product:"]
            for idx, p in enumerate(products, 1):
                lines.append(f"{idx}. {p.name} (N{p.price})")

            return "\n".join(lines), False

        except ValueError:
            return "Invalid input. Please enter a number.", False

    @classmethod
    def _handle_product_selection(cls, session: USSDSession, input_val: str) -> Tuple[str, bool]:
        prod_ids = session.temp_data.get("products", [])
        try:
            choice = int(input_val)
            if choice < 1 or choice > len(prod_ids):
                return "Invalid product choice. Please try again.", False

            selected_prod_id = prod_ids[choice - 1]
            session.product_id = selected_prod_id
            product = Product.objects.get(id=selected_prod_id)

            inv = getattr(product, "inventory", None)
            available = inv.available_quantity if inv else 0

            session.current_state = "PRODUCT_DETAIL"

            if available <= 0:
                msg = f"{product.name}\nPrice: N{product.price}\nStatus: OUT OF STOCK\n\n0. Back"
            elif inv and inv.is_low_stock:
                msg = f"{product.name}\nPrice: N{product.price}\nStatus: LOW STOCK ({available} left)\n\n1. Order Now\n2. Back"
            else:
                msg = f"{product.name}\nPrice: N{product.price}\nStatus: IN STOCK\n\n1. Order Now\n2. Back"

            return msg, False

        except (ValueError, Product.DoesNotExist):
            return "Invalid product selection.", False

    @classmethod
    def _handle_product_detail(cls, session: USSDSession, input_val: str) -> Tuple[str, bool]:
        if input_val == "1":
            session.current_state = "QUANTITY_INPUT"
            return "Enter quantity:", False
        elif input_val in ("2", "0"):
            return cls._show_category_selection(session)
        else:
            return "Invalid option.\n1. Order Now\n2. Back", False

    @classmethod
    def _handle_quantity_input(cls, session: USSDSession, phone_number: str, input_val: str) -> Tuple[str, bool]:
        try:
            qty = int(input_val)
            if qty <= 0:
                return "Quantity must be at least 1. Enter quantity:", False

            product = Product.objects.get(id=session.product_id)
            inv = getattr(product, "inventory", None)
            available = inv.available_quantity if inv else 0

            if qty > available:
                return f"Sorry, only {available} unit(s) available. Enter smaller quantity:", False

            session.quantity = qty
            customer = Customer.objects.filter(phone_number=phone_number).first()
            default_addr = customer.get_default_address() if customer else None

            if customer and default_addr:
                session.current_state = "ADDRESS_SELECTION"
                msg = (
                    f"Welcome back, {customer.name}!\n"
                    f"Use saved address?\n"
                    f"{default_addr.full_address_single_line()}\n\n"
                    f"1. Yes\n"
                    f"2. Change Address"
                )
                return msg, False
            else:
                session.current_state = "NEW_ADDRESS_NAME"
                return "Enter your full name:", False

        except (ValueError, Product.DoesNotExist):
            return "Invalid quantity number. Please enter digits:", False

    @classmethod
    def _handle_address_selection(cls, session: USSDSession, input_val: str) -> Tuple[str, bool]:
        if input_val == "1":
            return cls._show_order_summary(session)
        elif input_val == "2":
            session.current_state = "NEW_ADDRESS_NAME"
            return "Enter your full name:", False
        else:
            return "Invalid selection.\n1. Yes\n2. Change Address", False

    @classmethod
    def _show_order_summary(cls, session: USSDSession) -> Tuple[str, bool]:
        product = Product.objects.get(id=session.product_id)
        total = product.price * session.quantity
        session.current_state = "ORDER_SUMMARY"

        msg = (
            f"Order Summary:\n"
            f"Item: {session.quantity}x {product.name}\n"
            f"Total: N{total}\n"
            f"Payment: Pay on Delivery\n\n"
            f"1. Confirm Order\n"
            f"2. Cancel"
        )
        return msg, False

    @classmethod
    def _handle_order_confirmation(cls, session: USSDSession, phone_number: str, input_val: str) -> Tuple[str, bool]:
        if input_val != "1":
            return "Order cancelled. Thank you for using ShopX.", True

        product = Product.objects.get(id=session.product_id)
        business = Business.objects.get(id=session.business_id)

        # Get or create Customer
        cust_name = session.temp_data.get("name", "Valued Customer")
        customer, _ = get_or_create_customer_by_phone(phone_number, cust_name)

        # Get or create Address
        if "area" in session.temp_data:
            address = create_customer_address(
                customer=customer,
                area=session.temp_data.get("area", ""),
                street=session.temp_data.get("street", ""),
                landmark=session.temp_data.get("landmark", "")
            )
        else:
            address = customer.get_default_address()

        # Place order via Order Creation Service
        try:
            order = create_order(
                customer=customer,
                business=business,
                product=product,
                quantity=session.quantity,
                address=address
            )
            return (
                f"Thank you! Your order #{order.order_number} has been placed.\n"
                f"Total: N{order.total_amount} (Pay on Delivery).\n"
                f"The merchant will contact you shortly."
            ), True

        except Exception as e:
            logger.error(f"Order placement failed via USSD: {e}")
            return "Sorry, stock for this product changed or is unavailable. Please try again.", True
