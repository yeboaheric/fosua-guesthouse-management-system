from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create default role groups for Fosua Guesthouse."

    def handle(self, *args, **options):
        for role_name in ("Admin", "Receptionist"):
            Group.objects.get_or_create(name=role_name)
            self.stdout.write(self.style.SUCCESS(f"Role ready: {role_name}"))
