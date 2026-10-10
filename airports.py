NAMES = {
    "GRU": "Guarulhos (São Paulo)",
    "CGH": "Congonhas (São Paulo)",
    "RBR": "Rio Branco",
    "MAO": "Manaus",
    "MCP": "Macapá",
    "BEL": "Belém",
    "PVH": "Porto Velho",
    "BVB": "Boa Vista",
    "PMW": "Palmas",
    "SLZ": "São Luís",
    "THE": "Teresina",
    "FOR": "Fortaleza",
    "NAT": "Natal",
    "JPA": "João Pessoa",
    "REC": "Recife",
    "AJU": "Aracaju",
    "SSA": "Salvador",
    "CNF": "Belo Horizonte (Confins)",
    "BSB": "Brasília",
    "GYN": "Goiânia",
    "CGB": "Cuiabá",
    "CGR": "Campo Grande",
    "CWB": "Curitiba",
    "FLN": "Florianópolis",
    "POA": "Porto Alegre",
}


def airport_name(code: str) -> str:
    return NAMES.get(code, code)
