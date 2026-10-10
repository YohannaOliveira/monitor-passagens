import logging
from typing import Callable

import httpx

from services.http import ApiError, request_json
from services.notifiers.base import NotificationError, Notifier

log = logging.getLogger(__name__)


class CallMeBotNotifier(Notifier):
    """WhatsApp via CallMeBot (envia apenas para o número que ativou o serviço)."""

    def __init__(self, url: str, phone: str, apikey: str, post: Callable = None):
        self._url, self._phone, self._apikey = url, phone, apikey
        self._post = post or self._default_get

    def send(self, text: str) -> None:
        try:
            body = self._post(self._url, {"phone": self._phone, "text": text, "apikey": self._apikey})
        except (ApiError, httpx.HTTPError) as exc:
            raise NotificationError(f"callmebot: {exc}") from None
        if "error" in str(body).lower():
            raise NotificationError("callmebot: serviço respondeu com erro")

    @staticmethod
    def _default_get(url: str, params: dict):
        with httpx.Client(timeout=20.0) as client:
            try:
                resp = client.get(url, params=params)
            except httpx.HTTPError as exc:
                raise NotificationError(f"callmebot: {type(exc).__name__}") from None
        if resp.status_code != 200:
            raise NotificationError(f"callmebot: HTTP {resp.status_code}")
        return resp.text
