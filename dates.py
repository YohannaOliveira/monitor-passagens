from datetime import date, timedelta
from typing import Iterator, Tuple


def trip_days(depart: date, ret: date) -> int:
    return (ret - depart).days


def is_valid_pair(depart: date, ret: date, cfg) -> bool:
    """Ida na janela configurada, volta até RETURN_BY e duração dentro dos limites."""
    if not (cfg.depart_start <= depart <= cfg.depart_end):
        return False
    if ret > cfg.return_by:
        return False
    return cfg.min_days <= trip_days(depart, ret) <= cfg.max_days


def valid_date_pairs(cfg) -> Iterator[Tuple[date, date]]:
    depart = cfg.depart_start
    while depart <= cfg.depart_end:
        for days in range(cfg.min_days, cfg.max_days + 1):
            ret = depart + timedelta(days=days)
            if is_valid_pair(depart, ret, cfg):
                yield depart, ret
        depart += timedelta(days=1)
