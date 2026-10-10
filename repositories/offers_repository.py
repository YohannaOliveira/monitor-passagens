from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from models import Offer


class OffersRepository(ABC):
    @abstractmethod
    def last_notified_price(self, key: str) -> Optional[Decimal]:
        """Último preço notificado com sucesso para a oferta, ou None."""

    @abstractmethod
    def mark_notified(self, offer: Offer) -> None:
        """Registra a oferta como notificada (chamar só após envio bem-sucedido)."""

    @abstractmethod
    def searches_this_month(self, provider: str, month: str) -> int: ...

    @abstractmethod
    def record_search(self, provider: str, month: str) -> None: ...

    @abstractmethod
    def get_cursor(self, name: str) -> int:
        """Posição persistida da amostragem rotativa (0 se inexistente)."""

    @abstractmethod
    def set_cursor(self, name: str, value: int) -> None: ...
