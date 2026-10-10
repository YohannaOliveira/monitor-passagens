import logging
import time
from typing import Any, Callable, Optional

import httpx

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}


class ApiError(Exception):
    """Falha ao consultar uma API externa (mensagem sem credenciais)."""


class AuthError(ApiError):
    """Credenciais rejeitadas (401/403); não adianta tentar de novo."""


def request_json(
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    retries: int = 3,
    timeout: float = 20.0,
    backoff: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
    client: Optional[httpx.Client] = None,
    json_body: Optional[dict] = None,
) -> Any:
    """GET (ou POST, se json_body) com timeout e novas tentativas com espera progressiva.

    As mensagens de erro nunca incluem a URL completa, pois ela pode conter chaves.
    """
    own_client = client is None
    client = client or httpx.Client(timeout=timeout)
    host = httpx.URL(url).host
    last = "erro desconhecido"
    try:
        for attempt in range(retries + 1):
            try:
                if json_body is None:
                    resp = client.get(url, params=params, headers=headers)
                else:
                    resp = client.post(url, params=params, headers=headers, json=json_body)
            except httpx.HTTPError as exc:
                last = f"{type(exc).__name__}"
            else:
                if resp.status_code in (401, 403):
                    raise AuthError(f"{host}: credenciais rejeitadas (HTTP {resp.status_code})")
                if resp.status_code in RETRY_STATUS:
                    last = f"HTTP {resp.status_code}"
                elif resp.status_code >= 400:
                    raise ApiError(f"{host}: HTTP {resp.status_code}")
                else:
                    try:
                        return resp.json()
                    except ValueError:
                        raise ApiError(f"{host}: resposta não é JSON")
            if attempt < retries:
                wait = backoff * (2**attempt)
                log.warning("%s falhou (%s); nova tentativa em %.0fs", host, last, wait)
                sleep(wait)
        raise ApiError(f"{host}: falhou após {retries + 1} tentativas ({last})")
    finally:
        if own_client:
            client.close()
