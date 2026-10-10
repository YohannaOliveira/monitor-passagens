from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from models import Offer


class DiscoveryProvider(ABC):
    """Fonte barata de candidatas (pode usar preços em cache)."""

    name: str

    @abstractmethod
    def discover(self, origin: str, destination: str) -> List[Offer]: ...


class ValidationProvider(ABC):
    """Fonte que confirma o preço de uma combinação exata de datas."""

    name: str

    @abstractmethod
    def validate(self, origin: str, destination: str, depart: date, ret: date) -> Optional[Offer]:
        """Retorna a oferta mais barata ou None quando a fonte não tem resultados."""
