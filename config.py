import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Mapping, Tuple

from dotenv import load_dotenv

# Capitais brasileiras, exceto Vitória, São Paulo, Rio de Janeiro e Maceió.
DEFAULT_DESTINATIONS = (
    "RBR,MAO,MCP,BEL,PVH,BVB,PMW,SLZ,THE,FOR,NAT,JPA,REC,AJU,SSA,CNF,BSB,GYN,CGB,CGR,CWB,FLN,POA"
)


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    origins: Tuple[str, ...]
    destinations: Tuple[str, ...]
    depart_start: date
    depart_end: date
    return_by: date
    min_days: int
    max_days: int
    max_price: Decimal
    currency: str
    interval_hours: float
    discovery_margin: Decimal
    max_validations_per_run: int
    monthly_search_limit: int
    min_notify_drop: Decimal
    db_path: str
    dry_run: bool
    travelpayouts_token: str
    travelpayouts_base_url: str
    validation_provider: str
    serpapi_key: str
    serpapi_base_url: str
    ignav_api_key: str
    ignav_base_url: str
    callmebot_phone: str
    callmebot_apikey: str
    callmebot_url: str


def _get(env: Mapping[str, str], name: str, default: str = "") -> str:
    return (env.get(name) or default).strip()


def _int(env, name, default) -> int:
    raw = _get(env, name, str(default))
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"{name} deve ser um número inteiro (recebido: {raw!r})")


def _decimal(env, name, default) -> Decimal:
    raw = _get(env, name, str(default)).replace(",", ".")
    try:
        return Decimal(raw)
    except InvalidOperation:
        raise ConfigError(f"{name} deve ser numérico (recebido: {raw!r})")


def _date(env, name, default) -> date:
    raw = _get(env, name, default)
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ConfigError(f"{name} deve estar no formato AAAA-MM-DD (recebido: {raw!r})")


def _codes(env, name, default) -> Tuple[str, ...]:
    codes = tuple(c.strip().upper() for c in _get(env, name, default).split(",") if c.strip())
    for c in codes:
        if len(c) != 3 or not c.isalpha():
            raise ConfigError(f"{name}: código IATA inválido: {c!r}")
    return codes


def load_config(env: Mapping[str, str] = None) -> Config:
    if env is None:
        load_dotenv()
        env = os.environ

    cfg = Config(
        origins=_codes(env, "ORIGINS", "GRU,CGH"),
        destinations=_codes(env, "DESTINATIONS", DEFAULT_DESTINATIONS),
        depart_start=_date(env, "DEPART_START", "2027-05-03"),
        depart_end=_date(env, "DEPART_END", "2027-05-12"),
        return_by=_date(env, "RETURN_BY", "2027-05-16"),
        min_days=_int(env, "MIN_DAYS", 4),
        max_days=_int(env, "MAX_DAYS", 10),
        max_price=_decimal(env, "MAX_PRICE_BRL", 1000),
        currency="BRL",
        interval_hours=float(_decimal(env, "INTERVAL_HOURS", 24)),
        discovery_margin=_decimal(env, "DISCOVERY_MARGIN", "1.3"),
        max_validations_per_run=_int(env, "MAX_VALIDATIONS_PER_RUN", 10),
        monthly_search_limit=_int(env, "VALIDATION_MONTHLY_LIMIT", 900),
        min_notify_drop=_decimal(env, "MIN_NOTIFY_DROP_BRL", 1),
        db_path=_get(env, "DB_PATH", "monitor.db"),
        dry_run=_get(env, "DRY_RUN", "false").lower() in ("1", "true", "yes", "sim"),
        travelpayouts_token=_get(env, "TRAVELPAYOUTS_TOKEN"),
        travelpayouts_base_url=_get(
            env, "TRAVELPAYOUTS_BASE_URL", "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
        ),
        validation_provider=_get(env, "VALIDATION_PROVIDER", "ignav").lower(),
        serpapi_key=_get(env, "SERPAPI_API_KEY"),
        serpapi_base_url=_get(env, "SERPAPI_BASE_URL", "https://serpapi.com/search.json"),
        ignav_api_key=_get(env, "IGNAV_API_KEY"),
        ignav_base_url=_get(env, "IGNAV_BASE_URL", "https://ignav.com/api/fares/round-trip"),
        callmebot_phone=_get(env, "CALLMEBOT_PHONE"),
        callmebot_apikey=_get(env, "CALLMEBOT_APIKEY"),
        callmebot_url=_get(env, "CALLMEBOT_URL", "https://api.callmebot.com/whatsapp.php"),
    )
    validate(cfg)
    return cfg


def validate(cfg: Config) -> None:
    if not cfg.origins or not cfg.destinations:
        raise ConfigError("ORIGINS e DESTINATIONS não podem ficar vazios")
    if cfg.depart_start > cfg.depart_end:
        raise ConfigError("DEPART_START deve ser anterior ou igual a DEPART_END")
    if cfg.min_days < 1 or cfg.min_days > cfg.max_days:
        raise ConfigError("MIN_DAYS deve ser >= 1 e <= MAX_DAYS")
    if cfg.return_by < cfg.depart_start:
        raise ConfigError("RETURN_BY deve ser posterior a DEPART_START")
    if cfg.max_price <= 0:
        raise ConfigError("MAX_PRICE_BRL deve ser positivo")
    if cfg.interval_hours <= 0:
        raise ConfigError("INTERVAL_HOURS deve ser positivo")
    if cfg.discovery_margin < 1:
        raise ConfigError("DISCOVERY_MARGIN deve ser >= 1")
    missing = []
    if cfg.validation_provider not in ("ignav", "serpapi"):
        raise ConfigError("VALIDATION_PROVIDER deve ser 'ignav' ou 'serpapi'")
    if cfg.validation_provider == "ignav" and not cfg.ignav_api_key:
        missing.append("IGNAV_API_KEY")
    if cfg.validation_provider == "serpapi" and not cfg.serpapi_key:
        missing.append("SERPAPI_API_KEY")
    if not cfg.travelpayouts_token:
        missing.append("TRAVELPAYOUTS_TOKEN")
    if not cfg.dry_run:
        if not cfg.callmebot_phone:
            missing.append("CALLMEBOT_PHONE")
        if not cfg.callmebot_apikey:
            missing.append("CALLMEBOT_APIKEY")
    if missing:
        raise ConfigError("Variáveis de ambiente ausentes: " + ", ".join(missing))
