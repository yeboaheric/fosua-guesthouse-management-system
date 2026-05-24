from decimal import Decimal

from django.core.management.base import BaseCommand

from rooms.models import Room


class Command(BaseCommand):
    help = "Create 12 default room records for Fosua Guesthouse."

    def handle(self, *args, **options):
        default_rooms = [
            ("101", Room.RoomType.DELUXE, Decimal("320.00")),
            ("102", Room.RoomType.DELUXE, Decimal("320.00")),
            ("103", Room.RoomType.DELUXE, Decimal("320.00")),
            ("104", Room.RoomType.DELUXE, Decimal("320.00")),
            ("105", Room.RoomType.DELUXE, Decimal("320.00")),
            ("106", Room.RoomType.DELUXE, Decimal("320.00")),
            ("107", Room.RoomType.DELUXE, Decimal("320.00")),
            ("108", Room.RoomType.DELUXE, Decimal("320.00")),
            ("109", Room.RoomType.STANDARD, Decimal("180.00")),
            ("110", Room.RoomType.STANDARD, Decimal("180.00")),
            ("111", Room.RoomType.STANDARD, Decimal("180.00")),
            ("112", Room.RoomType.STANDARD, Decimal("180.00")),
        ]

        created_count = 0
        updated_count = 0
        for room_number, room_type, base_rate in default_rooms:
            _, created = Room.objects.update_or_create(
                room_number=room_number,
                defaults={"room_type": room_type, "base_rate": base_rate},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Room setup complete. Added {created_count} and updated {updated_count} rooms."
            )
        )
