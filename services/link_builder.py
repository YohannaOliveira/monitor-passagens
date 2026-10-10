from datetime import date
from urllib.parse import quote


def google_flights_link(origin: str, destination: str, depart: date, ret: date) -> str:
    """Link de pesquisa (não de compra) no Google Flights para conferir a oferta."""
    q = f"Flights from {origin} to {destination} on {depart.isoformat()} through {ret.isoformat()}"
    return f"https://www.google.com/travel/flights?q={quote(q)}&curr=BRL&hl=pt-BR"
