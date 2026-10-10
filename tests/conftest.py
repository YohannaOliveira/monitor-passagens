from datetime import date
from decimal import Decimal

import pytest

from config import load_config
from models import Offer, PriceKind
from repositories.sqlite_repository import SqliteOffersRepository
from services.http import ApiError
from services.notifiers.base import NotificationError, Notifier
from services.providers.base import DiscoveryProvider, ValidationProvider


@pytest.fixture
def cfg():
    return load_config(
        {
            "IGNAV_API_KEY": "k",
            "TRAVELPAYOUTS_TOKEN": "t",
            "CALLMEBOT_PHONE": "+5500000000000",
            "CALLMEBOT_APIKEY": "x",
            "ORIGINS": "GRU",
            "DESTINATIONS": "REC,SSA",
            "MAX_VALIDATIONS_PER_RUN": "5",
        }
    )


@pytest.fixture
def repo(tmp_path):
    r = SqliteOffersRepository(str(tmp_path / "t.db"))
    yield r
    r.close()


def make_offer(price="800", kind=PriceKind.LIVE, currency="BRL", origin="GRU", dest="REC",
               depart=date(2027, 5, 5), ret=date(2027, 5, 10)):
    return Offer(origin, dest, depart, ret, Decimal(str(price)), currency, kind, "fake")


class FakeNotifier(Notifier):
    def __init__(self, fail=False):
        self.fail, self.sent = fail, []

    def send(self, text):
        if self.fail:
            raise NotificationError("falhou")
        self.sent.append(text)


class FakeDiscovery(DiscoveryProvider):
    name = "fake-discovery"

    def __init__(self, offers=None, error=None):
        self.offers, self.error = offers or [], error

    def discover(self, origin, destination):
        if self.error:
            raise self.error
        return [o for o in self.offers if o.origin == origin and o.destination == destination]


class FakeValidation(ValidationProvider):
    name = "fake-validation"

    def __init__(self, prices=None, default=None, errors=()):
        self.prices, self.default, self.errors = prices or {}, default, set(errors)
        self.calls = []

    def validate(self, origin, destination, depart, ret):
        self.calls.append((origin, destination, depart, ret))
        if destination in self.errors:
            raise ApiError("indisponivel")
        price = self.prices.get(destination, self.default)
        if price is None:
            return None
        return make_offer(price, origin=origin, dest=destination, depart=depart, ret=ret)
