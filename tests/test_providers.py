from datetime import date
from decimal import Decimal

import httpx
import pytest

from models import PriceKind
from services.http import ApiError, AuthError, request_json
from services.notifiers.base import NotificationError
from services.notifiers.callmebot import CallMeBotNotifier
from services.providers.ignav_flights import IgnavFlightsProvider
from services.providers.travelpayouts import TravelpayoutsProvider

D, R = date(2027, 5, 5), date(2027, 5, 10)


def ignav_payload(*prices, currency="BRL"):
    return {"itineraries": [
        {"price": {"amount": p, "currency": currency, "status": "verified"},
         "outbound": {"carrier": "Azul", "segments": []}} for p in prices]}


def test_ignav_escolhe_a_tarifa_mais_barata(cfg):
    prov = IgnavFlightsProvider(cfg, fetch=lambda *a, **k: ignav_payload(1116, 780, 900))
    offer = prov.validate("GRU", "REC", D, R)
    assert offer.price == Decimal("780") and offer.currency == "BRL"
    assert offer.price_kind is PriceKind.LIVE and offer.airline == "Azul"


def test_ignav_sem_resultados(cfg):
    prov = IgnavFlightsProvider(cfg, fetch=lambda *a, **k: {"itineraries": []})
    assert prov.validate("GRU", "REC", D, R) is None


def test_ignav_preserva_moeda_original(cfg):
    prov = IgnavFlightsProvider(cfg, fetch=lambda *a, **k: ignav_payload(150, currency="USD"))
    assert prov.validate("GRU", "REC", D, R).currency == "USD"


def test_ignav_resposta_invalida(cfg):
    prov = IgnavFlightsProvider(cfg, fetch=lambda *a, **k: "lixo")
    with pytest.raises(ApiError):
        prov.validate("GRU", "REC", D, R)


def test_travelpayouts_marca_preco_como_cache(cfg):
    payload = {"success": True, "currency": "brl",
               "data": [{"departure_at": "2027-05-05T10:00:00-03:00", "return_at": "2027-05-10T10:00:00-03:00",
                         "price": 650, "airline": "G3"}, {"price": 1}]}
    prov = TravelpayoutsProvider(cfg, fetch=lambda *a, **k: payload)
    offers = prov.discover("GRU", "REC")
    assert len(offers) == 1  # item incompleto ignorado
    assert offers[0].price_kind is PriceKind.CACHED and offers[0].price == Decimal("650")


def test_travelpayouts_erro_da_api(cfg):
    prov = TravelpayoutsProvider(cfg, fetch=lambda *a, **k: {"success": False, "error": "x"})
    with pytest.raises(ApiError):
        prov.discover("GRU", "REC")


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_http_tenta_de_novo_com_espera_progressiva():
    calls, waits = [], []

    def handler(req):
        calls.append(1)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, json={"ok": True})

    out = request_json("https://x.test/a", client=_client(handler), sleep=waits.append)
    assert out == {"ok": True} and waits == [2.0, 4.0]


def test_http_desiste_apos_tentativas_sem_vazar_credenciais():
    with pytest.raises(ApiError) as exc:
        request_json("https://x.test/a", params={"api_key": "SEGREDO"},
                     client=_client(lambda r: httpx.Response(429)), sleep=lambda s: None)
    assert "SEGREDO" not in str(exc.value)


def test_http_401_nao_repete():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(401)

    with pytest.raises(AuthError):
        request_json("https://x.test/a", client=_client(handler), sleep=lambda s: None)
    assert len(calls) == 1


def test_callmebot_falha_vira_notification_error():
    def post(url, params):
        raise ApiError("fora do ar")

    with pytest.raises(NotificationError):
        CallMeBotNotifier("u", "+55", "k", post=post).send("oi")


def test_callmebot_resposta_de_erro():
    with pytest.raises(NotificationError):
        CallMeBotNotifier("u", "+55", "k", post=lambda u, p: "Error: apikey invalid").send("oi")


def test_callmebot_sucesso():
    sent = []
    CallMeBotNotifier("u", "+55", "k", post=lambda u, p: sent.append(p) or "Message queued").send("oi")
    assert sent[0]["text"] == "oi"
