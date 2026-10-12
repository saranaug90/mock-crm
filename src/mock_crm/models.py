"""Pydantic models for the Mock CRM : customers, tickets and orders."""

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Status = Literal["open", "pending", "closed"]
Tier = Literal["standard", "gold", "platinum"]


def normalize_text(value: Any) -> Any:
    """Strip and apply lower case for the string. Other values will be handled by pydantic."""
    if isinstance(value, str):
        return value.lower().strip()
    return value


class CRMModel(BaseModel):
    """Base class for all CRM models. reject the fields that are not decalred."""

    model_config = ConfigDict(extra="forbid")


class Customer(CRMModel):
    """A CRM Customer Account."""

    id: str = Field(pattern=r"^C-\d+$", description="Customer ID, e.g. C-1")
    name: str = Field(min_length=1, description="Customer's full name")
    email: str = Field(description="Contact email, e.g. jane@example.com")
    tier: Tier = Field(default="standard", description="Service tier")

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("email must contain @")
        return value.lower()

    @field_validator("tier", mode="before")
    @classmethod
    def normalize_tier(cls, value: Any) -> Any:
        return normalize_text(value)

    def is_premium(self) -> bool:
        """Return True for gold and platinum customers."""
        return self.tier in ("gold", "platinum")


class Ticket(CRMModel):
    """A customer support ticket."""

    id: str = Field(pattern=r"^T-\d+$", description="Ticket ID, e.g. T-42")
    customer: str = Field(
        pattern=r"^C-\d+$", description="ID of the customer who raised it"
    )
    status: Status = Field(description="Current ticket status")
    priority: int = Field(default=3, ge=1, le=5, description="1 = low, 5 = urgent")
    assignee: str | None = Field(default=None, description="Support agent handling it")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        return normalize_text(value)

    @model_validator(mode="after")
    def closed_needs_assignee(self) -> Self:
        if self.status == "closed" and self.assignee is None:
            raise ValueError("closed tickets must have an assignee")
        return self


class LineItem(CRMModel):
    """One product line within an order."""

    sku: str = Field(min_length=1, description="Product code, e.g. KB-01")
    quantity: int = Field(gt=0, description="Number of units")
    unit_price: float = Field(gt=0, description="Price per unit")


class Order(CRMModel):
    """A customer order made up of one or more line items."""

    id: str = Field(pattern=r"^O-\d+$", description="Order ID, e.g. O-7")
    customer: str = Field(pattern=r"^C-\d+$", description="ID of the ordering customer")
    items: list[LineItem] = Field(min_length=1, description="Products ordered")

    @model_validator(mode="after")
    def skus_must_be_unique(self) -> Self:
        skus = [item.sku for item in self.items]
        if len(skus) != len(set(skus)):
            raise ValueError("each SKU may appear only once per order")
        return self

    def total(self) -> float:
        """Return the order total across all line items."""
        return sum(item.quantity * item.unit_price for item in self.items)


class CustomerSummary(CRMModel):
    """Ticket statistics for one customer."""

    customer: str
    ticket_count: int
    open_count: int
    max_priority: int
