import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

from models import Offer, PriceKind
from services.http import ApiError, request_json
from services.link_builder import google_flights_link
from services.providers.base import ValidationProvider

log = logging.getLogger(__name__)


class IgnavFlightsProvider(ValidationProvider):
    """Tarifas de ida e volta via Ignav (POST /api/fares/round-trip).

    Campos baseados na documentação pública (ignav.com/docs). A documentação não confirma
    BRL para market=BR: a moeda é lida da resposta e ofertas que não vierem em BRL são
    descartadas pelas regras de negócio, nunca convertidas ou comparadas como se fossem BRL.
    """

    name = "Ignav"

    def __init__(self, cfg, fetch: Callable = request_json):
        self.cfg = cfg
        self._fetch = fetch

    def validate(self, origin: str, destination: str, depart: date, ret: date) -> Optional[Offer]:
        payload = self._fetch(
            self.cfg.ignav_base_url,
            headers={"X-Api-Key": self.cfg.ignav_api_key},
            json_body={
                "origin": origin,
                "destination": destination,
                "departure_date": depart.isoformat(),
                "return_date": ret.isoformat(),
                "adults": 1,
                "cabin_class": "economy",
                "market": "BR",
            },
        )
        return self._parse(payload, origin, destination, depart, ret)

    def _parse(self, payload, origin, destination, depart, ret) -> Optional[Offer]:
        if not isinstance(payload, dict):
            raise ApiError("ignav: resposta inesperada")
        best = None
        for it in payload.get("itineraries") or []:
            price = it.get("price") or {}
            try:
                amount = Decimal(str(price["amount"]))
                currency = str(price["currency"]).upper()
            except (KeyError, InvalidOperation):
                continue
            if best is None or (currency, amount) < (best[1], best[0]):
                best = (amount, currency, it)
        if best is None:
            return None

        amount, currency, it = best
        outbound = it.get("outbound") or {}
        airline = outbound.get("carrier")
        if not airline:
            segs = outbound.get("segments") or []
            airline = segs[0].get("operating_carrier_name") if segs else None
        return Offer(
            origin=origin,
            destination=destination,
            depart_date=depart,
            return_date=ret,
            price=amount,
            currency=currency,
            price_kind=PriceKind.LIVE,
            source=self.name,
            airline=airline,
            link=google_flights_link(origin, destination, depart, ret),
        )
