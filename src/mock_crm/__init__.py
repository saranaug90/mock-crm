"""Mock CRM: a typed, validated data layer for AI integration practice."""

from mock_crm.services import (
    customer_order_total,
    find_tickets,
    orders_by_customer,
    summarize_customer,
)


def main() -> None:
    """Print a quick demo of the CRM services."""
    print("Urgent open tickets:", find_tickets("open", min_priority=4))
    print(summarize_customer("C-1"))
    print(orders_by_customer())
    print("C-1 total spend:", customer_order_total("C-1"))
