"""Tool buscar_arquivo: procura arquivos pelo nome nas pastas do usuário."""
import os
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


def raizes() -> list[Path]:
    env = os.environ.get("ORBIT_BUSCA_RAIZES", "")
    lista = [Path(p) for p in env.split(os.pathsep) if p.strip()]
    return lista or [Path.home()]


def buscar(nome: str, raizes_: list[Path], limite_s: float = LIMITE_S) -> list[Path]:
    """Até 5 arquivos/pastas cujo nome contém `nome` (sem acento/maiúscula)."""
    alvo = _norm(nome.strip())
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
                if alvo in _norm(n):
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
