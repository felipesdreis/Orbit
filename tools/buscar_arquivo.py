"""Tool buscar_arquivo: procura arquivos pelo nome nas pastas do usuário."""
import os
import re
import time
import unicodedata
from pathlib import Path

MAX_RESULTADOS = 5
MAX_PROFUNDIDADE = 6
LIMITE_S = 5.0
IGNORAR = {
    "node_modules", ".git", "appdata", ".venv", "venv", "__pycache__", "windows",
    "program files", "program files (x86)", "programdata", "$recycle.bin",
    "system volume information", ".cache", "site-packages",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.casefold())
    return "".join(c for c in s if not unicodedata.combining(c))


def _palavras(s: str) -> list[str]:
    """Texto normalizado em palavras: '_', '-', '.' e espaço separam igual."""
    return re.findall(r"[a-z0-9]+", _norm(s))


def raizes() -> list[Path]:
    env = os.environ.get("ORBIT_BUSCA_RAIZES", "")
    lista = [Path(p) for p in env.split(os.pathsep) if p.strip()]
    return lista or [Path.home()]


def buscar(nome: str, raizes_: list[Path], limite_s: float = LIMITE_S) -> list[Path]:
    """Até 5 arquivos/pastas cujo nome contém TODAS as palavras de `nome`.

    Sem acento/maiúscula e com '_', '-', '.' e espaço tratados como iguais:
    "discurso 152" acha "Discurso_152_Armagedom_30min.docx".
    """
    alvo = _palavras(nome)
    if not alvo:
        return []
    fim = time.monotonic() + limite_s
    achados: list[Path] = []
    for raiz in raizes_:
        base = len(Path(raiz).parts)
        for pasta, subs, arqs in os.walk(raiz):
            if time.monotonic() > fim:
                return achados
            subs[:] = [d for d in subs if _norm(d) not in IGNORAR]
            if len(Path(pasta).parts) - base >= MAX_PROFUNDIDADE:
                subs[:] = []
            for n in arqs + subs:
                chave = " ".join(_palavras(n))
                if all(palavra in chave for palavra in alvo):
                    achados.append(Path(pasta) / n)
                    if len(achados) >= MAX_RESULTADOS:
                        return achados
    return achados


def formatar(nome: str, achados: list[Path]) -> str:
    if not achados:
        return f"Não achei nada com o nome {nome}."
    # Só nome e pasta final: o resultado é falado em voz alta, caminho completo não.
    return f"Achei {len(achados)}:\n" + "\n".join(f"{p.name} (pasta {p.parent.name or p.parent})" for p in achados)


def registrar(mcp) -> None:
    @mcp.tool()
    def buscar_arquivo(nome: str) -> str:
        """[leitura] Use para achar um arquivo ou pasta do PC pelo nome (ou parte dele)."""
        return formatar(nome, buscar(nome, raizes()))
