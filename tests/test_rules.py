from datetime import date
from decimal import Decimal

import pytest

from config import ConfigError, load_config
from dates import is_valid_pair, trip_days, valid_date_pairs
from models import PriceKind
from rules import should_notify, within_limit
from tests.conftest import make_offer

LIMIT = Decimal("1000")


def test_duracao_da_viagem():
    assert trip_days(date(2027, 5, 5), date(2027, 5, 10)) == 5
    assert make_offer().duration_days == 5


def test_validacao_de_datas(cfg):
    assert is_valid_pair(date(2027, 5, 5), date(2027, 5, 10), cfg)
    assert not is_valid_pair(date(2027, 5, 2), date(2027, 5, 8), cfg)   # ida antes da janela
    assert not is_valid_pair(date(2027, 5, 13), date(2027, 5, 16), cfg)  # ida depois da janela
    assert not is_valid_pair(date(2027, 5, 8), date(2027, 5, 17), cfg)  # volta depois do limite
    assert not is_valid_pair(date(2027, 5, 5), date(2027, 5, 8), cfg)   # 3 dias < mínimo
    assert not is_valid_pair(date(2027, 5, 3), date(2027, 5, 14), cfg)  # 11 dias > máximo


def test_todas_as_combinacoes_geradas_sao_validas(cfg):
    pairs = list(valid_date_pairs(cfg))
    assert pairs and all(is_valid_pair(d, r, cfg) for d, r in pairs)


def test_config_rejeita_datas_invertidas():
    env = {"IGNAV_API_KEY": "k", "TRAVELPAYOUTS_TOKEN": "t", "DRY_RUN": "true",
           "DEPART_START": "2027-05-12", "DEPART_END": "2027-05-03"}
    with pytest.raises(ConfigError):
        load_config(env)


def test_config_exige_credenciais():
    with pytest.raises(ConfigError, match="IGNAV_API_KEY"):
        load_config({"DRY_RUN": "true", "TRAVELPAYOUTS_TOKEN": "t"})


def test_limite_de_preco():
    assert within_limit(make_offer("1000"), LIMIT)
    assert not within_limit(make_offer("1000.01"), LIMIT)


def test_moedas_diferentes_nao_sao_comparadas():
    assert not within_limit(make_offer("100", currency="USD"), LIMIT)


def test_preco_em_cache_nunca_notifica():
    assert not should_notify(make_offer("500", kind=PriceKind.CACHED), None, LIMIT)


def test_oferta_inedita_notifica():
    assert should_notify(make_offer("800"), None, LIMIT)


def test_oferta_ja_notificada_nao_repete():
    assert not should_notify(make_offer("800"), Decimal("800"), LIMIT)
    assert not should_notify(make_offer("850"), Decimal("800"), LIMIT)


def test_queda_de_preco_notifica_de_novo():
    assert should_notify(make_offer("700"), Decimal("800"), LIMIT)
