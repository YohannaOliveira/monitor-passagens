from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class PriceKind(Enum):
    CACHED = "cache"  # estimativa vinda de cache; nunca dispara alerta
    LIVE = "confirmado"  # retornado pela fonte em tempo real


@dataclass(frozen=True)
class Offer:
    origin: str
    destination: str
    depart_date: date
    return_date: date
    price: Decimal
    currency: str
    price_kind: PriceKind
    source: str
    airline: Optional[str] = None
    link: Optional[str] = None

    @property
    def duration_days(self) -> int:
        return (self.return_date - self.depart_date).days

    @property
    def key(self) -> str:
        """Identifica a oferta pela rota e pelas datas."""
        return f"{self.origin}-{self.destination}-{self.depart_date.isoformat()}-{self.return_date.isoformat()}"
