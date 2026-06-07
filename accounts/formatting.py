from decimal import Decimal, InvalidOperation


def format_quantity(value):
    if value in {None, ""}:
        return ""
    try:
        normalized = Decimal(str(value)).normalize()
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    formatted = format(normalized, "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    if formatted in {"", "-0"}:
        return "0"
    return formatted

