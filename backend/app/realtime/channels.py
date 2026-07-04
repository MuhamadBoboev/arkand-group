"""Имена WS-каналов (§12). Клиент подписан только на доступное по правам."""
from __future__ import annotations


def business(business_id: str) -> str:
    return f"business:{business_id}"


def cash(cash_id: str) -> str:
    return f"cash:{cash_id}"


SUPPLY = "supply"
FINANCE = "finance"
OWNERS = "owners"
AUDIT = "audit"


def employee(user_id: str) -> str:
    return f"employee:{user_id}"
