"""Servidor MCP (stdio) do Orbit.

Descobre todo tools/*.py (exceto server.py e arquivos iniciados por "_") e chama
`registrar(mcp)` de cada módulo que a definir. Criar tool nova = soltar um .py aqui.
"""
import importlib.util
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PASTA = Path(__file__).resolve().parent


def _log(msg: str) -> None:
    # stdout é do protocolo MCP; logs só em stderr
    print(f"[orbit-tools] {msg}", file=sys.stderr, flush=True)


def descobrir(mcp: FastMCP, pasta: Path = PASTA) -> None:
    for arq in sorted(pasta.glob("*.py")):
        if arq.name == "server.py" or arq.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"orbit_tool_{arq.stem}", arq)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "registrar"):
                mod.registrar(mcp)
        except Exception as e:  # módulo quebrado não derruba o servidor
            _log(f"falha ao carregar {arq.name}: {e!r}")


mcp = FastMCP("orbit")
descobrir(mcp)

if __name__ == "__main__":
    mcp.run()
