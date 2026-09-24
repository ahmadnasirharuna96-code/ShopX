from django.core.management.base import BaseCommand
from orders.services import release_expired_reservations


class Command(BaseCommand):
    help = "Safely releases expired inventory reservations for pending orders past their expiration time."

    def handle(self, *args, **options):
        self.stdout.write("Checking for expired inventory reservations...")
        count = release_expired_reservations()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully released {count} expired order reservation(s).")
        )
