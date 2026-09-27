from decimal import Decimal
from catalog.models import Product


SESSION_CART_KEY = "shopx_cart"


class SessionCart:
    """
    Session-based shopping cart manager.
    Supports both guest and authenticated customers.
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(SESSION_CART_KEY)
        if not cart:
            cart = self.session[SESSION_CART_KEY] = {}
        self.cart = cart

    def add(self, product: Product, quantity: int = 1, override_quantity: bool = False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = 0

        if override_quantity:
            self.cart[product_id] = max(1, quantity)
        else:
            self.cart[product_id] += quantity

        self.save()

    def update(self, product: Product, quantity: int):
        product_id = str(product.id)
        if quantity > 0:
            self.cart[product_id] = quantity
        else:
            self.remove(product)
        self.save()

    def remove(self, product: Product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        # Reset the cart to an empty dict instead of deleting the key to avoid KeyError
        self.session[SESSION_CART_KEY] = {}
        self.save()

    def save(self):
        self.session.modified = True

    def get_items(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids, is_active=True).select_related("business", "category", "inventory")
        
        items = []
        for product in products:
            qty = self.cart.get(str(product.id), 0)
            subtotal = product.price * qty
            items.append({
                "product": product,
                "quantity": qty,
                "unit_price": product.price,
                "subtotal": subtotal,
            })
        return items

    def get_total_amount(self) -> Decimal:
        return sum(item["subtotal"] for item in self.get_items())

    def __len__(self) -> int:
        return sum(self.cart.values())
