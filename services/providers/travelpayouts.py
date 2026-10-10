import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Callable, List

from models import Offer, PriceKind
from services.http import ApiError, request_json
from services.providers.base import DiscoveryProvider

log = logging.getLogger(__name__)


def _months(start: date, end: date) -> List[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


class TravelpayoutsProvider(DiscoveryProvider):
    """Preços em cache da Aviasales (Travelpayouts Data API).

    ATENÇÃO: o endpoint v3 (`prices_for_dates`) e os nomes de campos abaixo não puderam ser
    conferidos na documentação oficial (a página de suporte bloqueou a consulta automática).
    Valide com a sua conta; a URL é configurável via TRAVELPAYOUTS_BASE_URL.
    """

    name = "Travelpayouts (cache)"

    def __init__(self, cfg, fetch: Callable = request_json):
        self.cfg = cfg
        self._fetch = fetch

    def discover(self, origin: str, destination: str) -> List[Offer]:
        cfg = self.cfg
        offers: List[Offer] = []
        for dep_month in _months(cfg.depart_start, cfg.depart_end):
            for ret_month in _months(cfg.depart_start, cfg.return_by):
                if ret_month < dep_month:
                    continue
                payload = self._fetch(
                    cfg.travelpayouts_base_url,
                    params={
                        "origin": origin,
                        "destination": destination,
                        "departure_at": dep_month,
                        "return_at": ret_month,
                        "one_way": "false",
                        "currency": cfg.currency.lower(),
                        "sorting": "price",
                        "limit": 1000,
                    },
                    headers={"X-Access-Token": cfg.travelpayouts_token},
                )
                offers.extend(self._parse(payload, origin, destination))
        return offers

    def _parse(self, payload, origin: str, destination: str) -> List[Offer]:
        if not isinstance(payload, dict) or payload.get("success") is False:
            raise ApiError(f"travelpayouts: resposta de erro ({payload.get('error') if isinstance(payload, dict) else '?'})")
        out = []
        for item in payload.get("data") or []:
            try:
                depart = date.fromisoformat(str(item["departure_at"])[:10])
                ret = date.fromisoformat(str(item["return_at"])[:10])
                price = Decimal(str(item["price"]))
            except (KeyError, ValueError, InvalidOperation):
                continue  # item incompleto: ignorar em vez de inventar dados
            out.append(
                Offer(
                    origin=origin,
                    destination=destination,
                    depart_date=depart,
                    return_date=ret,
                    price=price,
                    currency=str(payload.get("currency") or self.cfg.currency).upper(),
                    price_kind=PriceKind.CACHED,
                    source=self.name,
                    airline=item.get("airline"),
                )
            )
        return out
