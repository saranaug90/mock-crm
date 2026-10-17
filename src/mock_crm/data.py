"""Sample CRM records. Stand in for a real database until Week 2."""

from mock_crm.models import Customer, LineItem, Order, Ticket

CUSTOMERS: list[Customer] = [
    Customer(id="C-1", name="Asha Rao", email="asha@example.com", tier="gold"),
    Customer(id="C-2", name="Leo Martin", email="leo@example.com", tier="platinum"),
    Customer(id="C-3", name="Mei Chen", email="mei@example.com"),
]

TICKETS: list[Ticket] = [
    Ticket(id="T-1", customer="C-1", status="open", priority=3),
    Ticket(id="T-2", customer="C-2", status="closed", priority=1, assignee="agent-7"),
    Ticket(id="T-3", customer="C-1", status="open", priority=5),
    Ticket(id="T-4", customer="C-3", status="pending", priority=2),
]

ORDERS: list[Order] = [
    Order(
        id="O-1",
        customer="C-1",
        items=[
            LineItem(sku="KB-01", quantity=2, unit_price=49.5),
            LineItem(sku="MS-02", quantity=1, unit_price=25.25),
        ],
    ),
    Order(
        id="O-2",
        customer="C-2",
        items=[LineItem(sku="MN-27", quantity=1, unit_price=199.0)],
    ),
    Order(
        id="O-3",
        customer="C-1",
        items=[LineItem(sku="CB-03", quantity=3, unit_price=12.0)],
    ),
]
