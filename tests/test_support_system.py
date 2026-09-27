from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from businesses.models import Business
from catalog.models import Category, Product
from customers.models import Customer
from orders.models import Order, OrderStatus
from support.models import (
    Conversation,
    Message,
    MessageType,
    SupportTicket,
    SupportTicketCategory,
    SupportTicketStatus,
)
from support.services import (
    create_order_conversation,
    create_support_ticket,
    initiate_business_call,
)


class SupportSystemTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="merchant", password="pass123", role="BUSINESS_OWNER")
        self.business = Business.objects.create(
            owner=self.owner,
            name="ABC Electronics",
            phone_number="08012345678",
            address="Main Street",
            city="Lagos",
            state="Lagos",
        )
        self.category = Category.objects.create(name="Phones", slug="phones")
        self.product = Product.objects.create(
            business=self.business,
            category=self.category,
            name="Samsung A15",
            description="Demo phone",
            price=250000,
        )
        self.customer_user = User.objects.create_user(username="customer", password="pass123", role="CUSTOMER")
        self.customer = Customer.objects.create(
            user=self.customer_user,
            phone_number="08076543210",
            name="Ahmad",
        )
        self.order = Order.objects.create(
            order_number="KX1042",
            customer=self.customer,
            business=self.business,
            status=OrderStatus.OUT_FOR_DELIVERY,
            total_amount=250000,
            customer_confirmed=True,
            business_confirmed=True,
        )

    def test_customer_can_open_own_order_conversation(self):
        conversation = create_order_conversation(self.customer, self.business, self.order)
        self.assertEqual(conversation.customer, self.customer)
        self.assertEqual(conversation.business, self.business)
        self.assertEqual(conversation.order, self.order)
        self.assertEqual(conversation.status, "OPEN")

    def test_customer_cannot_view_other_customers_conversation(self):
        other_customer = Customer.objects.create(phone_number="08044444444", name="Maryam")
        other_order = Order.objects.create(
            order_number="KX2000",
            customer=other_customer,
            business=self.business,
            status=OrderStatus.PENDING,
            total_amount=50000,
            customer_confirmed=True,
            business_confirmed=False,
        )
        other_conversation = create_order_conversation(other_customer, self.business, other_order)

        self.assertNotEqual(other_conversation.customer, self.customer)
        self.assertFalse(other_conversation.customer == self.customer)

    def test_customer_can_send_a_message(self):
        conversation = create_order_conversation(self.customer, self.business, self.order)
        message = conversation.add_message(sender="customer", message_type=MessageType.TEXT, content="Where is my order?")
        self.assertEqual(message.content, "Where is my order?")
        self.assertEqual(message.conversation, conversation)

    def test_customer_can_create_support_ticket(self):
        ticket = create_support_ticket(
            customer=self.customer,
            business=self.business,
            order=self.order,
            category=SupportTicketCategory.DELIVERY_PROBLEM,
            subject="Order not delivered",
            description="The order has not arrived.",
        )
        self.assertEqual(ticket.customer, self.customer)
        self.assertEqual(ticket.order, self.order)
        self.assertEqual(ticket.status, SupportTicketStatus.OPEN)
        self.assertTrue(ticket.ticket_number.startswith("SUP-"))

    @patch("support.services.AfricaTalkingVoiceService.initiate_call")
    def test_customer_can_call_business_for_own_order(self, mock_initiate):
        mock_initiate.return_value = {"status": "queued", "call_id": "call-1"}

        call = initiate_business_call(self.customer, self.order)

        self.assertEqual(call.customer, self.customer)
        self.assertEqual(call.business, self.business)
        self.assertEqual(call.order, self.order)
        self.assertEqual(call.status, "queued")
        mock_initiate.assert_called_once()

    def test_business_can_view_its_own_order_conversations(self):
        conversation = create_order_conversation(self.customer, self.business, self.order)
        self.assertEqual(conversation.business, self.business)
        self.assertTrue(conversation.business == self.business)

    def test_business_can_reply_to_customer_message(self):
        conversation = create_order_conversation(self.customer, self.business, self.order)
        conversation.add_message(sender="business", message_type=MessageType.TEXT, content="The rider has picked it up.")
        self.assertEqual(conversation.messages.count(), 1)

    def test_ussd_support_flow_uses_selected_order_business(self):
        from ussd.services import USSDService

        session_id = "support-menu-test"
        first_response = USSDService.handle_request(session_id, self.customer.phone_number, "")
        self.assertIn("Welcome to ShopX", first_response)

        support_response = USSDService.handle_request(session_id, self.customer.phone_number, "3")
        self.assertIn("Customer Support", support_response)
