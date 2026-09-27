from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from businesses.models import Business
from catalog.models import Category, Product
from customers.models import Address, Customer
from inventory.models import Inventory
from notifications.models import SMSNotification
from notifications.services import (
    send_order_created_notifications,
    send_order_accepted_notification,
    send_order_rejected_notification,
    send_order_ready_notification,
    send_order_out_for_delivery_notification,
    send_order_delivered_notification,
    notify_business_new_order,
    send_sms,
)
from orders.models import OrderStatus
from orders.services import accept_order, create_order, reject_order, update_order_status

User = get_user_model()


class SMSNotificationServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="sms_owner", password="password", role="BUSINESS_OWNER")
        self.business = Business.objects.create(
            owner=self.owner,
            name="SMS Shop",
            phone_number="08011112222",
            address="Main St",
            city="Abuja",
            state="FCT",
        )
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(business=self.business, category=self.category, name="Samsung A15", price=250000.00)
        Inventory.objects.create(product=self.product, quantity=5, reserved_quantity=0)
        self.customer = Customer.objects.create(phone_number="08099990000", name="Ahmad")
        self.address = Address.objects.create(customer=self.customer, area="Wuse", city="Abuja", state="FCT")

    @patch("notifications.africastalking_sms.AfricaTalkingSMSService.send_sms")
    def test_send_sms_successful_api_call(self, mock_send_sms):
        mock_send_sms.return_value = {"status": "success", "SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "abc-123"}]}}

        result = send_sms("08012345678", "KasuwanciX: test")

        self.assertTrue(result)
        self.assertTrue(mock_send_sms.called)

    def test_send_sms_invalid_phone_number(self):
        self.assertFalse(send_sms("", "KasuwanciX: test"))
        self.assertFalse(send_sms("invalid", "KasuwanciX: test"))

    @patch("notifications.africastalking_sms.AfricaTalkingSMSService.send_sms")
    def test_order_created_triggers_customer_and_business_sms(self, mock_send_sms):
        mock_send_sms.return_value = {"status": "success", "SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "msg-1"}]}}

        order = create_order(self.customer, self.business, self.product, 1, self.address)
        notifications = SMSNotification.objects.filter(order=order)

        self.assertGreaterEqual(notifications.count(), 2)
        self.assertTrue(any(n.notification_type == "ORDER_CREATED" for n in notifications))
        self.assertTrue(any(n.notification_type == "BUSINESS_NEW_ORDER" for n in notifications))

    @patch("notifications.africastalking_sms.AfricaTalkingSMSService.send_sms")
    def test_send_order_accepted_notification_customer_only(self, mock_send_sms):
        mock_send_sms.return_value = {"status": "success", "SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "msg-2"}]}}
        order = create_order(self.customer, self.business, self.product, 1, self.address)

        accept_order(order, self.owner)
        notification = SMSNotification.objects.filter(order=order, notification_type="ORDER_ACCEPTED").first()

        self.assertIsNotNone(notification)
        self.assertIn("accepted", notification.message.lower())

    @patch("notifications.africastalking_sms.AfricaTalkingSMSService.send_sms")
    def test_duplicate_event_is_not_logged_twice(self, mock_send_sms):
        mock_send_sms.return_value = {"status": "success", "SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "msg-3"}]}}
        order = create_order(self.customer, self.business, self.product, 1, self.address)

        send_order_created_notifications(order)
        send_order_created_notifications(order)

        self.assertEqual(SMSNotification.objects.filter(order=order, notification_type="ORDER_CREATED").count(), 1)

    @patch("notifications.africastalking_sms.AfricaTalkingSMSService.send_sms")
    def test_order_ready_and_delivery_notifications_are_sent(self, mock_send_sms):
        mock_send_sms.return_value = {"status": "success", "SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "msg-4"}]}}
        order = create_order(self.customer, self.business, self.product, 1, self.address)

        send_order_ready_notification(order)
        send_order_out_for_delivery_notification(order)
        send_order_delivered_notification(order)

        self.assertTrue(SMSNotification.objects.filter(order=order, notification_type="ORDER_READY").exists())
        self.assertTrue(SMSNotification.objects.filter(order=order, notification_type="OUT_FOR_DELIVERY").exists())
        self.assertTrue(SMSNotification.objects.filter(order=order, notification_type="ORDER_DELIVERED").exists())

    @patch("notifications.africastalking_sms.AfricaTalkingSMSService.send_sms")
    def test_order_rejected_notification_is_sent_to_customer(self, mock_send_sms):
        mock_send_sms.return_value = {"status": "success", "SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "msg-5"}]}}
        order = create_order(self.customer, self.business, self.product, 1, self.address)

        reject_order(order, self.owner, reason="Out of stock")
        notification = SMSNotification.objects.filter(order=order, notification_type="ORDER_REJECTED").first()

        self.assertIsNotNone(notification)
        self.assertIn("rejected", notification.message.lower())

    @patch("notifications.africastalking_sms.AfricaTalkingSMSService.send_sms")
    def test_business_receives_order_status_updates(self, mock_send_sms):
        mock_send_sms.return_value = {"status": "success", "SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "msg-6"}]}}
        order = create_order(self.customer, self.business, self.product, 1, self.address)
        accept_order(order, self.owner)
        update_order_status(order, OrderStatus.PREPARING, self.owner)
        update_order_status(order, OrderStatus.READY_FOR_DELIVERY, self.owner)
        update_order_status(order, OrderStatus.OUT_FOR_DELIVERY, self.owner)

        self.assertTrue(SMSNotification.objects.filter(order=order, notification_type="OUT_FOR_DELIVERY").exists())

    @patch("notifications.africastalking_sms.AfricaTalkingSMSService.send_sms")
    def test_business_new_order_notification_uses_business_phone(self, mock_send_sms):
        mock_send_sms.return_value = {"status": "success", "SMSMessageData": {"Recipients": [{"status": "Success", "messageId": "msg-7"}]}}
        order = create_order(self.customer, self.business, self.product, 1, self.address)

        notify_business_new_order(order)

        self.assertTrue(SMSNotification.objects.filter(order=order, notification_type="BUSINESS_NEW_ORDER", recipient="+2348011112222").exists())
