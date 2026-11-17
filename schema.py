from typing import Optional
from pydantic import BaseModel


class LineItem(BaseModel):
    description: str
    quantity: float = 1
    unit_price: Optional[float] = None
    total: float


class Receipt(BaseModel):
    vendor: Optional[str] = None
    date: Optional[str] = None      # we'll ask for YYYY-MM-DD
    currency: Optional[str] = None  # e.g. "USD", "EUR"
    line_items: list[LineItem] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tip: Optional[float] = None
    total: Optional[float] = None