"""Tool clima: tempo agora e previsão do dia (Open-Meteo, sem chave de API), falados em português."""
import json
import urllib.parse
import urllib.request

# Cidade padrão: Mogi Guaçu, SP. Fica fixa aqui para não gastar uma consulta de geocodificação.
PADRAO = {"nome": "Mogi Guaçu", "lat": -22.3689, "lon": -46.9428, "fuso": "America/Sao_Paulo"}
_TIMEOUT = 8

# Códigos WMO usados pelo Open-Meteo, em português falado.
CODIGOS = {
    0: "céu limpo", 1: "céu quase limpo", 2: "parcialmente nublado", 3: "nublado",
    45: "com neblina", 48: "com neblina", 51: "com garoa fraca", 53: "com garoa",
    55: "com garoa forte", 56: "com garoa gelada", 57: "com garoa gelada",
    61: "com chuva fraca", 63: "com chuva", 65: "com chuva forte",
    66: "com chuva gelada", 67: "com chuva gelada", 71: "com neve fraca",
    73: "com neve", 75: "com neve forte", 77: "com grãos de neve",
    80: "com pancadas de chuva fracas", 81: "com pancadas de chuva",
    82: "com pancadas de chuva fortes", 85: "com pancadas de neve",
    86: "com pancadas de neve fortes", 95: "com tempestade",
    96: "com tempestade e granizo", 99: "com tempestade e granizo forte",
}


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=_TIMEOUT) as r:
        return json.load(r)


def _graus(valor: float) -> str:
    n = round(valor)
    return "0" if n == 0 else str(n)


def formatar(nome: str, dados: dict) -> str:
    """Monta a frase falada a partir da resposta do Open-Meteo."""
    atual, dia = dados["current"], dados["daily"]
    estado = CODIGOS.get(atual.get("weather_code"), "")
    partes = [f"Em {nome} agora faz {_graus(atual['temperature_2m'])} graus"]
    sensacao = atual.get("apparent_temperature")
    if sensacao is not None and abs(round(sensacao) - round(atual["temperature_2m"])) >= 2:
        partes[0] += f", sensação de {_graus(sensacao)}"
    partes[0] += f", {estado}." if estado else "."
    partes.append(f"Hoje a mínima é {_graus(dia['temperature_2m_min'][0])} e a máxima {_graus(dia['temperature_2m_max'][0])} graus.")
    chance = (dia.get("precipitation_probability_max") or [None])[0]
    if chance is not None:
        partes.append("Sem previsão de chuva." if chance < 10 else f"Chance de chuva de {round(chance)} por cento.")
    return " ".join(partes)


def clima_logica(cidade: str = "", buscar=_get_json) -> str:
    """Consulta o Open-Meteo. `buscar` é injetável para os testes não usarem a internet."""
    local = dict(PADRAO)
    try:
        if cidade.strip() and cidade.strip().lower() not in ("mogi guaçu", "mogi guacu"):
            q = urllib.parse.urlencode({"name": cidade.strip(), "count": 1, "language": "pt"})
            achados = buscar(f"https://geocoding-api.open-meteo.com/v1/search?{q}").get("results")
            if not achados:
                return f"ERRO: não encontrei a cidade {cidade.strip()}."
            c = achados[0]
            local = {"nome": c["name"], "lat": c["latitude"], "lon": c["longitude"], "fuso": "auto"}
        q = urllib.parse.urlencode({
            "latitude": local["lat"], "longitude": local["lon"], "timezone": local["fuso"],
            "current": "temperature_2m,apparent_temperature,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 1,
        }, safe=",")
        return formatar(local["nome"], buscar(f"https://api.open-meteo.com/v1/forecast?{q}"))
    except Exception:  # sem internet, timeout ou resposta inesperada: a tool não pode levantar exceção
        return "ERRO: não consegui consultar o clima agora."


def registrar(mcp) -> None:
    @mcp.tool()
    def clima(cidade: str = "") -> str:
        """[leitura] Use quando perguntarem como está o tempo, a temperatura, se vai chover ou fazer frio; sem cidade usa Mogi Guaçu."""
        return clima_logica(cidade)
