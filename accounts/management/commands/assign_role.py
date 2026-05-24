from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Assign a role group (Admin or Receptionist) to an existing user."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("role", type=str, choices=["Admin", "Receptionist"])

    def handle(self, *args, **options):
        username = options["username"]
        role = options["role"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"User '{username}' does not exist.") from exc

        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
        self.stdout.write(self.style.SUCCESS(f"Assigned role '{role}' to '{username}'."))
