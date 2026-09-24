from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from businesses.models import Business
from catalog.models import Category, Product
from inventory.models import Inventory

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds realistic demo data for ShopX platform."

    def handle(self, *args, **options):
        self.stdout.write("Seeding ShopX demo data...")

        with transaction.atomic():
            # Create Superuser / Admin
            admin_user, _ = User.objects.get_or_create(
                username="admin",
                defaults={
                    "email": "admin@shopx.local",
                    "role": "ADMIN",
                    "is_staff": True,
                    "is_superuser": True
                }
            )
            admin_user.set_password("Password123!")
            admin_user.save()

            # Categories
            cat_electronics, _ = Category.objects.get_or_create(name="Electronics", slug="electronics")
            cat_fashion, _ = Category.objects.get_or_create(name="Fashion", slug="fashion")
            cat_food, _ = Category.objects.get_or_create(name="Food", slug="food")

            # Merchant 1: ABC Electronics
            u1, _ = User.objects.get_or_create(
                username="abc_owner",
                defaults={"email": "owner@abcelectronics.com", "role": "BUSINESS_OWNER", "phone_number": "+2348011112222"}
            )
            u1.set_password("Password123!")
            u1.save()

            b1, _ = Business.objects.get_or_create(
                owner=u1,
                defaults={
                    "name": "ABC Electronics",
                    "description": "Your trusted local gadget and electronics hub.",
                    "phone_number": "+2348011112222",
                    "address": "Plot 12 Commercial Avenue, Wuse 2",
                    "city": "Abuja",
                    "state": "FCT"
                }
            )

            p1, _ = Product.objects.get_or_create(
                business=b1,
                name="Samsung A15",
                defaults={
                    "category": cat_electronics,
                    "description": "128GB ROM, 4GB RAM, Dual SIM Smartphone",
                    "price": 250000.00,
                    "is_active": True
                }
            )
            Inventory.objects.get_or_create(
                product=p1,
                defaults={"quantity": 15, "reserved_quantity": 0, "low_stock_threshold": 3}
            )

            p2, _ = Product.objects.get_or_create(
                business=b1,
                name="Oraimo Power Bank",
                defaults={
                    "category": cat_electronics,
                    "description": "20000mAh Fast Charging Power Bank",
                    "price": 15000.00,
                    "is_active": True
                }
            )
            Inventory.objects.get_or_create(
                product=p2,
                defaults={"quantity": 25, "reserved_quantity": 0, "low_stock_threshold": 5}
            )

            # Merchant 2: Kano Fashion Hub
            u2, _ = User.objects.get_or_create(
                username="kano_owner",
                defaults={"email": "owner@kanofashion.com", "role": "BUSINESS_OWNER", "phone_number": "+2348033334444"}
            )
            u2.set_password("Password123!")
            u2.save()

            b2, _ = Business.objects.get_or_create(
                owner=u2,
                defaults={
                    "name": "Kano Fashion Hub",
                    "description": "Authentic traditional apparel and modern fashion.",
                    "phone_number": "+2348033334444",
                    "address": "No. 45 France Road, Sabon Gari",
                    "city": "Kano",
                    "state": "Kano"
                }
            )

            p3, _ = Product.objects.get_or_create(
                business=b2,
                name="Traditional Wear",
                defaults={
                    "category": cat_fashion,
                    "description": "Premium Handcrafted Kaftan Attire",
                    "price": 35000.00,
                    "is_active": True
                }
            )
            Inventory.objects.get_or_create(
                product=p3,
                defaults={"quantity": 10, "reserved_quantity": 0, "low_stock_threshold": 2}
            )

            # Merchant 3: Northern Foods
            u3, _ = User.objects.get_or_create(
                username="northern_owner",
                defaults={"email": "owner@northernfoods.com", "role": "BUSINESS_OWNER", "phone_number": "+2348055556666"}
            )
            u3.set_password("Password123!")
            u3.save()

            b3, _ = Business.objects.get_or_create(
                owner=u3,
                defaults={
                    "name": "Northern Foods",
                    "description": "Fresh farm produce and wholesale grains store.",
                    "phone_number": "+2348055556666",
                    "address": "Grain Depot Market, Central Area",
                    "city": "Kaduna",
                    "state": "Kaduna"
                }
            )

            p4, _ = Product.objects.get_or_create(
                business=b3,
                name="Rice 50kg",
                defaults={
                    "category": cat_food,
                    "description": "50kg Premium Parboiled Long Grain Rice",
                    "price": 75000.00,
                    "is_active": True
                }
            )
            Inventory.objects.get_or_create(
                product=p4,
                defaults={"quantity": 30, "reserved_quantity": 0, "low_stock_threshold": 5}
            )

            p5, _ = Product.objects.get_or_create(
                business=b3,
                name="Cooking Oil",
                defaults={
                    "category": cat_food,
                    "description": "5 Liters Pure Vegetable Oil",
                    "price": 18000.00,
                    "is_active": True
                }
            )
            Inventory.objects.get_or_create(
                product=p5,
                defaults={"quantity": 20, "reserved_quantity": 0, "low_stock_threshold": 4}
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
        self.stdout.write(self.style.NOTICE("Credentials created:"))
        self.stdout.write("  Admin User: username='admin', password='Password123!'")
        self.stdout.write("  Business 1: username='abc_owner', password='Password123!' (ABC Electronics)")
        self.stdout.write("  Business 2: username='kano_owner', password='Password123!' (Kano Fashion Hub)")
        self.stdout.write("  Business 3: username='northern_owner', password='Password123!' (Northern Foods)")
