class ShopXException(Exception):
    """Base exception for ShopX application domain errors."""
    pass


class InsufficientStockException(ShopXException):
    """Raised when stock is insufficient to reserve or fulfill an order."""
    pass


class InvalidOrderStateTransition(ShopXException):
    """Raised when an illegal order status transition is attempted."""
    pass


class UnauthorizedBusinessAccess(ShopXException):
    """Raised when a user attempts to access or modify data belonging to another business."""
    pass
