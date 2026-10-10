import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

from models import Offer, PriceKind
from services.http import ApiError, request_json
from services.link_builder import google_flights_link
from services.providers.base import ValidationProvider

log = logging.getLogger(__name__)


class SerpApiFlightsProvider(ValidationProvider):
    """Preços do Google Flights em tempo real via SerpApi (engine=google_flights)."""

    name = "Google Flights via SerpApi"

    def __init__(self, cfg, fetch: Callable = request_json):
        self.cfg = cfg
        self._fetch = fetch

    def validate(self, origin: str, destination: str, depart: date, ret: date) -> Optional[Offer]:
        payload = self._fetch(
            self.cfg.serpapi_base_url,
            params={
                "engine": "google_flights",
                "departure_id": origin,
                "arrival_id": destination,
                "outbound_date": depart.isoformat(),
                "return_date": ret.isoformat(),
                "type": 1,  # ida e volta
                "currency": self.cfg.currency,
                "hl": "pt",
                "gl": "br",
                "api_key": self.cfg.serpapi_key,
            },
        )
        return self._parse(payload, origin, destination, depart, ret)

    def _parse(self, payload, origin, destination, depart, ret) -> Optional[Offer]:
        if not isinstance(payload, dict):
            raise ApiError("serpapi: resposta inesperada")
        if payload.get("error"):
            msg = str(payload["error"])
            if "hasn't returned any results" in msg:
                return None
            raise ApiError(f"serpapi: {msg}")

        best = None
        for group in (payload.get("best_flights") or []) + (payload.get("other_flights") or []):
            try:
                price = Decimal(str(group["price"]))
            except (KeyError, InvalidOperation):
                continue
            if best is None or price < best[0]:
                segments = group.get("flights") or []
                airline = segments[0].get("airline") if segments else None
                best = (price, airline)
        if best is None:
            return None

        meta = payload.get("search_metadata") or {}
        link = meta.get("google_flights_url") or google_flights_link(origin, destination, depart, ret)
        return Offer(
            origin=origin,
            destination=destination,
            depart_date=depart,
            return_date=ret,
            price=best[0],
            currency=self.cfg.currency,  # moeda solicitada na consulta
            price_kind=PriceKind.LIVE,
            source=self.name,
            airline=best[1],
            link=link,
        )
