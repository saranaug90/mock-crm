"""Helpers for turning validation errors into readable messages."""

from pydantic import ValidationError


def format_errors(error: ValidationError) -> str:
    """Return one line per problem, e.g. 'items.0.quantity: Input should be greater than 0'."""
    lines: list[str] = []
    for err in error.errors():
        location = ".".join(str(part) for part in err["loc"]) or "(whole record)"
        lines.append(f"{location}: {err['msg']}")
    return "\n".join(lines)
