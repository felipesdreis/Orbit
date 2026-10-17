"""Tratamento do texto da resposta: tag de emoção e divisão em frases para o TTS."""
import re

EMOCOES = ("neutro", "feliz", "pensando", "curioso", "surpreso")

_TAG = re.compile(r"\[(" + "|".join(EMOCOES) + r")\]", re.IGNORECASE)
_FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+")
_MARCAS_MARKDOWN = re.compile(r"[*_#`>]+")
_MIN_FRASE = 12  # frases menores que isso (ex.: "Oi.") grudam na seguinte


def extrair_emocao(texto: str) -> tuple[str, str]:
    """Devolve (texto sem tags, emoção). Vale a primeira tag; sem tag, 'neutro'."""
    achou = _TAG.search(texto)
    emocao = achou.group(1).lower() if achou else "neutro"
    return _TAG.sub("", texto).strip(), emocao


def dividir_frases(texto: str) -> list[str]:
    """Quebra o texto em frases para sintetizar e enviar uma a uma."""
    limpo = _MARCAS_MARKDOWN.sub("", texto)
    frases: list[str] = []
    for parte in _FIM_DE_FRASE.split(" ".join(limpo.split())):
        parte = parte.strip()
        if not parte:
            continue
        if frases and len(frases[-1]) < _MIN_FRASE:
            frases[-1] = f"{frases[-1]} {parte}"
        else:
            frases.append(parte)
    return frases
