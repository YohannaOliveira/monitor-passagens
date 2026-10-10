from datetime import date
from decimal import Decimal

from models import PriceKind
from repositories.sqlite_repository import SqliteOffersRepository
from services.http import ApiError, AuthError
from services.search_service import SearchService
from tests.conftest import FakeDiscovery, FakeNotifier, FakeValidation, make_offer


def build(cfg, repo, validation, notifier=None, discovery=None):
    notifier = notifier or FakeNotifier()
    svc = SearchService(cfg, discovery or FakeDiscovery(), validation, repo, notifier,
                        today=lambda: date(2026, 10, 10))
    return svc, notifier


def test_envia_alerta_para_oferta_confirmada_abaixo_do_limite(cfg, repo):
    svc, notifier = build(cfg, repo, FakeValidation(default=800))
    assert svc.run_once() > 0
    assert "PASSAGEM BARATA" in notifier.sent[0]
    assert "R$ 800,00" in notifier.sent[0]


def test_nao_envia_acima_do_limite(cfg, repo):
    svc, notifier = build(cfg, repo, FakeValidation(default=1200))
    assert svc.run_once() == 0 and notifier.sent == []


def test_sem_resultados_nao_quebra(cfg, repo):
    svc, notifier = build(cfg, repo, FakeValidation(default=None))
    assert svc.run_once() == 0


def one_candidate(cfg, repo, live_price, notifier):
    """Rodada com um único candidato de cache (sem amostragem rotativa)."""
    cfg1 = cfg.__class__(**{**cfg.__dict__, "max_validations_per_run": 1})
    cached = make_offer("900", kind=PriceKind.CACHED)
    svc, _ = build(cfg1, repo, FakeValidation(default=live_price), notifier, FakeDiscovery([cached]))
    return svc, cached


def test_nao_duplica_notificacao_entre_rodadas(cfg, repo):
    notifier = FakeNotifier()
    svc, cached = one_candidate(cfg, repo, 800, notifier)
    svc.run_once()
    svc.run_once()
    assert len(notifier.sent) == 1


def test_reenvia_quando_preco_cai(cfg, repo):
    notifier = FakeNotifier()
    svc, cached = one_candidate(cfg, repo, 900, notifier)
    svc.run_once()
    svc2, _ = one_candidate(cfg, repo, 700, notifier)
    svc2.run_once()
    assert repo.last_notified_price(cached.key) == Decimal("700")
    assert len(notifier.sent) == 2


def test_falha_no_whatsapp_nao_registra_como_notificada(cfg, repo):
    svc, notifier = build(cfg, repo, FakeValidation(default=800), FakeNotifier(fail=True))
    assert svc.run_once() == 0
    assert _notified_keys(repo) == []


def test_erro_em_um_destino_nao_interrompe_a_rodada(cfg, repo):
    val = FakeValidation(prices={"SSA": 800}, errors={"REC"})
    svc, notifier = build(cfg, repo, val)
    assert svc.run_once() > 0
    assert all("Salvador" in m for m in notifier.sent)


def test_falha_na_descoberta_nao_interrompe(cfg, repo):
    svc, _ = build(cfg, repo, FakeValidation(default=800), discovery=FakeDiscovery(error=ApiError("x")))
    assert svc.run_once() > 0


def test_credencial_rejeitada_na_validacao_encerra_a_fase(cfg, repo):
    class Auth(FakeValidation):
        def validate(self, *a):
            self.calls.append(a)
            raise AuthError("401")

    val = Auth()
    svc, notifier = build(cfg, repo, val)
    assert svc.run_once() == 0
    assert len(val.calls) == 1


def test_respeita_limite_mensal_de_buscas(cfg, repo):
    cfg2 = cfg.__class__(**{**cfg.__dict__, "monthly_search_limit": 2})
    val = FakeValidation(default=1500)
    svc, _ = build(cfg2, repo, val)
    svc.run_once()
    svc.run_once()
    assert len(val.calls) == 2


def test_amostragem_rotativa_avanca_entre_rodadas(cfg, repo):
    val = FakeValidation(default=1500)
    svc, _ = build(cfg, repo, val)
    svc.run_once()
    n = len(val.calls)
    svc.run_once()
    assert len(set(val.calls)) > n  # a segunda rodada cobre combinações novas


def test_historico_persiste_apos_reiniciar(cfg, tmp_path):
    path = str(tmp_path / "p.db")
    r1 = SqliteOffersRepository(path)
    offer = make_offer("750")
    r1.mark_notified(offer)
    r1.record_search("p", "2026-10")
    r1.close()
    r2 = SqliteOffersRepository(path)
    assert r2.last_notified_price(offer.key) == Decimal("750")
    assert r2.searches_this_month("p", "2026-10") == 1
    r2.close()


def _notified_keys(repo):
    return [r[0] for r in repo._conn.execute("SELECT key FROM notified_offers")]
