from decimal import Decimal
from typing import Optional

from models import Offer, PriceKind


def within_limit(offer: Offer, max_price: Decimal, currency: str = "BRL") -> bool:
    """Moedas diferentes nunca são comparadas como se fossem equivalentes."""
    return offer.currency == currency and offer.price <= max_price


def should_notify(
    offer: Offer, last_price: Optional[Decimal], max_price: Decimal, min_drop: Decimal = Decimal("1")
) -> bool:
    """Alerta só para preço confirmado dentro do limite, inédito ou menor que o último notificado."""
    if offer.price_kind is not PriceKind.LIVE:
        return False
    if not within_limit(offer, max_price):
        return False
    if last_price is None:
        return True
    return offer.price <= last_price - min_drop
