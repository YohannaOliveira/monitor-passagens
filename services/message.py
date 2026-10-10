from airports import airport_name
from models import Offer


def _brl(value) -> str:
    s = f"{value:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def format_message(offer: Offer) -> str:
    lines = [
        "✈️ PASSAGEM BARATA ENCONTRADA!",
        "",
        f"Origem: {airport_name(offer.origin)} ({offer.origin})",
        f"Destino: {airport_name(offer.destination)} ({offer.destination})",
        f"Ida: {offer.depart_date:%d/%m/%Y}",
        f"Volta: {offer.return_date:%d/%m/%Y}",
        f"Duração: {offer.duration_days} dias",
        f"Preço total (ida e volta): {_brl(offer.price)}",
    ]
    if offer.airline:
        lines.append(f"Companhia: {offer.airline}")
    lines.append(f"Fonte: {offer.source} ({offer.price_kind.value})")
    if offer.link:
        lines += ["", f"Conferir: {offer.link}"]
    lines += ["", "Preço e disponibilidade podem mudar. Confira as condições antes de comprar."]
    return "\n".join(lines)
