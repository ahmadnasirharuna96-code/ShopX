from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from businesses.models import Business
from catalog.models import Category, Product
from inventory.models import Inventory
from orders.models import Order
from ussd.services import USSDService

User = get_user_model()


class USSDIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username="shop_owner", password="password", role="BUSINESS_OWNER")
        self.business = Business.objects.create(owner=self.owner, name="Mega Store", phone_number="08022223333", address="Main St", city="Abuja", state="FCT")
        self.category = Category.objects.create(name="Phones", slug="phones")
        self.product = Product.objects.create(business=self.business, category=self.category, name="Smartphone X", price=50000.00)
        self.inventory = Inventory.objects.create(product=self.product, quantity=10, reserved_quantity=0)

    def test_ussd_initial_menu_response(self):
        url = reverse("ussd-callback")
        data = {
            "sessionId": "ATSession123",
            "serviceCode": "*384*1#",
            "phoneNumber": "+2348011112222",
            "text": ""
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.decode("utf-8").startswith("CON Welcome to ShopX"))

    def test_ussd_category_and_business_selection_flow(self):
        session_id = "SESS999"
        phone = "+2348099887766"

        # 1. Start -> Main Menu
        res1 = USSDService.handle_request(session_id, phone, "")
        self.assertTrue(res1.startswith("CON Welcome to ShopX"))

        # 2. Select Option 1 (Browse Shops) -> Shows Category List
        res2 = USSDService.handle_request(session_id, phone, "1")
        self.assertTrue(res2.startswith("CON Select category:"))
        self.assertIn("Phones", res2)

        # 3. Select Category 1 (Phones) -> Shows Shop List
        res3 = USSDService.handle_request(session_id, phone, "1*1")
        self.assertTrue(res3.startswith("CON Select shop:"))
        self.assertIn("Mega Store", res3)

        # 4. Select Shop 1 -> Shows Product List
        res4 = USSDService.handle_request(session_id, phone, "1*1*1")
        self.assertTrue(res4.startswith("CON Select product:"))
        self.assertIn("Smartphone X", res4)

        # 5. Select Product 1 -> Shows Product Details & Stock Status
        res5 = USSDService.handle_request(session_id, phone, "1*1*1*1")
        self.assertTrue(res5.startswith("CON Smartphone X"))
        self.assertIn("IN STOCK", res5)

    def test_ussd_full_checkout_places_order(self):
        session_id = "SESS_FULL"
        phone = "+2348012345678"

        # Step inputs: 1 (Browse), 1 (Phones), 1 (Mega Store), 1 (Smartphone X), 1 (Buy), 1 (Qty=1), John (Name), Wuse 2 (Area), Street 5 (Street), Landmark (Landmark), 1 (Confirm)
        text_seq = "1*1*1*1*1*1*John Doe*Wuse 2*Street 5*Near Bank*1"
        inputs = text_seq.split("*")

        res = None
        for i in range(len(inputs) + 1):
            sub_text = "*".join(inputs[:i])
            res = USSDService.handle_request(session_id, phone, sub_text)

        self.assertTrue(res.startswith("END Thank you! Your order"))
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.customer.phone_number, "+2348012345678")
        self.assertEqual(order.items.first().product_name, "Smartphone X")
