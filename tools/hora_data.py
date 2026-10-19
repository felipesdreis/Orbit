"""Tool hora_data: hora, data e dia da semana locais, falados em português."""
from datetime import datetime

# Fixos no código para não depender do locale do sistema.
DIAS = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]
MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def hora_data_logica(agora: datetime | None = None) -> str:
    """Monta a frase falada a partir de um datetime (padrão: agora, horário local)."""
    agora = agora or datetime.now()
    if agora.minute == 0 and agora.hour == 0:
        hora = "Agora é meia-noite."
    elif agora.minute == 0 and agora.hour == 12:
        hora = "Agora é meio-dia."
    elif agora.minute == 0:
        hora = f"Agora são {agora.hour} em ponto."
    elif agora.hour == 1:
        hora = f"Agora é uma e {agora.minute}."
    else:
        hora = f"Agora são {agora.hour} e {agora.minute}."
    dia = agora.day if agora.day != 1 else "primeiro"
    data = f"Hoje é {DIAS[agora.weekday()]}, {dia} de {MESES[agora.month - 1]} de {agora.year}."
    return f"{hora} {data}"


def registrar(mcp) -> None:
    @mcp.tool()
    def hora_data() -> str:
        """[leitura] Use quando perguntarem que horas são, que dia é hoje, a data ou o dia da semana."""
        return hora_data_logica()
