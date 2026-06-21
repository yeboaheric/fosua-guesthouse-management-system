import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    """Require the character classes used by the hotel's password policy."""

    message = _(
        "Password must contain at least one uppercase letter, one number, "
        "and one special character."
    )

    def validate(self, password, user=None):
        if not (
            re.search(r"[A-Z]", password or "")
            and re.search(r"\d", password or "")
            and re.search(r"[^A-Za-z0-9]", password or "")
        ):
            raise ValidationError(self.message, code="password_not_strong")

    def get_help_text(self):
        return self.message
