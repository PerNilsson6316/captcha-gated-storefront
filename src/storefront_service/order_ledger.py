from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class OrderStatus(StrEnum):
    CHECKED_OUT = "checked_out"
    FULFILLED = "fulfilled"


@dataclass
class Customer:
    id: str
    email: str
    name: str


@dataclass
class Order:
    id: str
    customer_id: str
    sku: str
    quantity: int
    status: OrderStatus = OrderStatus.CHECKED_OUT
    updates: list[str] = field(default_factory=lambda: ["Order accepted"])
    receipt_id: str | None = None


class StoreLedger:
    def __init__(self) -> None:
        self.customers: dict[str, Customer] = {}
        self.orders: dict[str, Order] = {}

    def register(self, email: str, name: str) -> Customer:
        customer = Customer(id=str(uuid4()), email=email, name=name)
        self.customers[customer.id] = customer
        return customer

    def checkout(self, customer_id: str, sku: str, quantity: int) -> Order:
        if customer_id not in self.customers:
            raise KeyError("customer not found")
        order = Order(id=str(uuid4()), customer_id=customer_id, sku=sku, quantity=quantity)
        self.orders[order.id] = order
        return order

    def fulfill(self, order_id: str) -> Order:
        order = self.orders[order_id]
        if order.status is OrderStatus.FULFILLED:
            return order
        order.status = OrderStatus.FULFILLED
        order.receipt_id = f"receipt-{order.id}"
        order.updates.append("Order fulfilled")
        return order

