import logging
from datetime import date
from typing import Callable, Dict, List

from dates import is_valid_pair, valid_date_pairs
from models import Offer
from repositories.offers_repository import OffersRepository
from rules import should_notify, within_limit
from services.http import ApiError, AuthError
from services.message import format_message
from services.notifiers.base import NotificationError, Notifier
from services.providers.base import DiscoveryProvider, ValidationProvider

log = logging.getLogger(__name__)

CURSOR_NAME = "rotating_sample"


class SearchService:
    def __init__(
        self,
        cfg,
        discovery: DiscoveryProvider,
        validation: ValidationProvider,
        repo: OffersRepository,
        notifier: Notifier,
        today: Callable[[], date] = date.today,
    ):
        self.cfg, self.discovery, self.validation = cfg, discovery, validation
        self.repo, self.notifier, self._today = repo, notifier, today

    def run_once(self) -> int:
        """Executa uma rodada completa e retorna quantos alertas foram enviados."""
        candidates = self._discover()
        targets = [(o.origin, o.destination, o.depart_date, o.return_date) for o in candidates]
        targets = self._with_rotating_sample(targets)
        confirmed = self._validate(targets)
        return self._notify(confirmed)

    def _with_rotating_sample(self, targets: list) -> list:
        """Completa o orçamento da rodada com combinações rotativas.

        O cache de descoberta costuma estar vazio para datas distantes; sem isso nada seria
        validado. O cursor persistido faz cada rodada cobrir rotas e datas diferentes: todas as
        rotas são visitadas antes de repetir, e o par de datas avança a cada volta completa.
        """
        budget = self.cfg.max_validations_per_run - len(targets)
        if budget <= 0:
            return targets
        routes = [(o, d) for o in self.cfg.origins for d in self.cfg.destinations]
        pairs = list(valid_date_pairs(self.cfg))
        if not routes or not pairs:
            return targets
        seen = set(targets)
        cursor = self.repo.get_cursor(CURSOR_NAME)
        added = 0
        for i in range(cursor, cursor + len(routes) * len(pairs)):
            if added >= budget:
                break
            origin, dest = routes[i % len(routes)]
            depart, ret = pairs[(i // len(routes) + (i % len(routes)) * 7) % len(pairs)]
            t = (origin, dest, depart, ret)
            if t not in seen:
                seen.add(t)
                targets.append(t)
                added += 1
        self.repo.set_cursor(CURSOR_NAME, cursor + max(added, 1))
        return targets

    def _discover(self) -> List[Offer]:
        cfg = self.cfg
        limit = cfg.max_price * cfg.discovery_margin
        best: Dict[str, Offer] = {}
        for origin in cfg.origins:
            for dest in cfg.destinations:
                try:
                    offers = self.discovery.discover(origin, dest)
                except AuthError:
                    log.error("Descoberta: credenciais rejeitadas; abortando a fase.")
                    return sorted(best.values(), key=lambda o: o.price)
                except ApiError as exc:
                    log.warning("Descoberta %s->%s falhou: %s", origin, dest, exc)
                    continue
                for o in offers:
                    if o.currency != cfg.currency or o.price > limit:
                        continue
                    if not is_valid_pair(o.depart_date, o.return_date, cfg):
                        continue
                    if o.key not in best or o.price < best[o.key].price:
                        best[o.key] = o
        found = sorted(best.values(), key=lambda o: o.price)
        log.info("Descoberta: %d candidatas (preços em cache, não confirmados)", len(found))
        return found

    def _validate(self, targets: list) -> List[Offer]:
        cfg = self.cfg
        provider = self.validation.name
        confirmed: List[Offer] = []
        done = 0
        for origin, dest, depart, ret in targets:
            key = f"{origin}-{dest}-{depart.isoformat()}-{ret.isoformat()}"
            if done >= cfg.max_validations_per_run:
                break
            month = self._today().strftime("%Y-%m")
            if self.repo.searches_this_month(provider, month) >= cfg.monthly_search_limit:
                log.warning("Limite mensal de buscas (%d) atingido; validação suspensa.", cfg.monthly_search_limit)
                break
            self.repo.record_search(provider, month)
            done += 1
            try:
                live = self.validation.validate(origin, dest, depart, ret)
            except AuthError:
                log.error("Validação: credenciais rejeitadas; abortando a fase.")
                break
            except ApiError as exc:
                log.warning("Validação %s falhou: %s", key, exc)
                continue
            if live is None:
                log.info("Sem resultados ao vivo para %s", key)
            elif live.currency != cfg.currency:
                log.warning("%s retornou %s (esperado %s); oferta descartada", key, live.currency, cfg.currency)
            elif within_limit(live, cfg.max_price, cfg.currency):
                confirmed.append(live)
        log.info("Validação: %d buscas, %d ofertas confirmadas dentro do limite", done, len(confirmed))
        return confirmed

    def _notify(self, offers: List[Offer]) -> int:
        sent = 0
        for offer in sorted(offers, key=lambda o: o.price):
            last = self.repo.last_notified_price(offer.key)
            if not should_notify(offer, last, self.cfg.max_price, self.cfg.min_notify_drop):
                continue
            text = format_message(offer)
            if self.cfg.dry_run:
                log.info("[DRY_RUN] enviaria:\n%s", text)
                continue
            try:
                self.notifier.send(text)
            except NotificationError as exc:
                log.error("Falha ao enviar alerta de %s: %s", offer.key, exc)
                continue  # não registra como notificada
            self.repo.mark_notified(offer)
            sent += 1
        return sent
