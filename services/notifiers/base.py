from abc import ABC, abstractmethod


class NotificationError(Exception):
    """O envio falhou; a oferta não deve ser marcada como notificada."""


class Notifier(ABC):
    @abstractmethod
    def send(self, text: str) -> None:
        """Envia a mensagem ou levanta NotificationError."""
