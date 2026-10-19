"""Tratamento do texto da resposta: tag de emoção e divisão em frases para o TTS."""
import re

EMOCOES = ("neutro", "feliz", "pensando", "curioso", "surpreso")

_TAG = re.compile(r"\[(" + "|".join(EMOCOES) + r")\]", re.IGNORECASE)
_FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+")
_MARCAS_MARKDOWN = re.compile(r"[*#`>]+")
_SEPARADORES_DE_NOME = re.compile(r"[_]+")  # "Discurso_152" -> "Discurso 152", e não "Discurso152"
_ENTRE_ORACOES = re.compile(r"(?<=[,;:])\s+")
_MIN_FRASE = 12  # frases menores que isso (ex.: "Oi.") grudam na seguinte
_MAX_FRASE = 100  # frases maiores são quebradas: a 1ª fala só sai depois que ela é sintetizada


def extrair_emocao(texto: str) -> tuple[str, str]:
    """Devolve (texto sem tags, emoção). Vale a primeira tag; sem tag, 'neutro'."""
    achou = _TAG.search(texto)
    emocao = achou.group(1).lower() if achou else "neutro"
    return _TAG.sub("", texto).strip(), emocao


def dividir_frases(texto: str) -> list[str]:
    """Quebra o texto em frases para sintetizar e enviar uma a uma."""
    limpo = _SEPARADORES_DE_NOME.sub(" ", _MARCAS_MARKDOWN.sub("", texto))
    frases: list[str] = []
    for parte in _FIM_DE_FRASE.split(" ".join(limpo.split())):
        parte = parte.strip()
        if not parte:
            continue
        if frases and len(frases[-1]) < _MIN_FRASE:
            frases[-1] = f"{frases[-1]} {parte}"
        else:
            frases.append(parte)
    return [pedaco for frase in frases for pedaco in _quebrar(frase)]


def _quebrar(frase: str) -> list[str]:
    """Quebra uma frase longa nas vírgulas (ou, sem vírgula, nas palavras), em pedaços de até ~100 caracteres."""
    if len(frase) <= _MAX_FRASE:
        return [frase]
    pedacos: list[str] = []
    atual = ""
    for oracao in _ENTRE_ORACOES.split(frase):
        for palavra in oracao.split():  # a oração é juntada palavra a palavra; só corta ao estourar o limite
            if atual and len(atual) + 1 + len(palavra) > _MAX_FRASE:
                pedacos.append(atual)
                atual = palavra
            else:
                atual = f"{atual} {palavra}".strip()
        if atual and oracao.rstrip().endswith((",", ";", ":")) and len(atual) >= _MAX_FRASE // 2:
            pedacos.append(atual)  # chegou numa vírgula com pedaço já razoável: fecha aqui
            atual = ""
    if atual:
        pedacos.append(atual)
    return pedacos
