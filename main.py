import argparse
import logging
import sys
import time

from config import ConfigError, load_config
from repositories.sqlite_repository import SqliteOffersRepository
from services.notifiers.callmebot import CallMeBotNotifier
from services.providers.ignav_flights import IgnavFlightsProvider
from services.providers.serpapi_flights import SerpApiFlightsProvider
from services.providers.travelpayouts import TravelpayoutsProvider
from services.search_service import SearchService

log = logging.getLogger("monitor")


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor de passagens baratas")
    parser.add_argument("--once", action="store_true", help="executa uma rodada e encerra")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx loga URLs completas (com chaves)

    try:
        cfg = load_config()
    except ConfigError as exc:
        log.error("Configuração inválida: %s", exc)
        return 2

    repo = SqliteOffersRepository(cfg.db_path)
    service = SearchService(
        cfg,
        discovery=TravelpayoutsProvider(cfg),
        validation=IgnavFlightsProvider(cfg) if cfg.validation_provider == "ignav" else SerpApiFlightsProvider(cfg),
        repo=repo,
        notifier=CallMeBotNotifier(cfg.callmebot_url, cfg.callmebot_phone, cfg.callmebot_apikey),
    )

    try:
        while True:
            try:
                sent = service.run_once()
                log.info("Rodada concluída: %d alerta(s) enviado(s)", sent)
            except Exception:
                log.exception("Erro inesperado na rodada; seguindo para a próxima")
            if args.once:
                return 0
            log.info("Próxima rodada em %s h", cfg.interval_hours)
            time.sleep(cfg.interval_hours * 3600)  # contado após o fim da rodada
    except KeyboardInterrupt:
        log.info("Encerrado pelo usuário")
        return 0
    finally:
        repo.close()


if __name__ == "__main__":
    sys.exit(main())
