"""Testa uma tool do Orbit sem tablet e sem LLM.

    python -m server.testar_tool --listar
    python -m server.testar_tool pc_status
    python -m server.testar_tool buscar_arquivo '{"nome": "relatorio"}'

Sobe o servidor MCP de tools/ (o mesmo que o Orbit usa), chama a tool e mostra o que o modelo receberia.
"""
import argparse
import asyncio
import json
import time
from pathlib import Path

from .mcp_cliente import ClienteMCP

_IMAGENS = {".png", ".jpg", ".jpeg"}


async def executar(nome: str | None, argumentos: dict, listar: bool = False) -> int:
    mcp = ClienteMCP()
    await mcp.iniciar()
    try:
        tools = {t["function"]["name"]: t["function"] for t in mcp.tools_ollama}
        if listar or nome is None:
            for n, f in tools.items():
                params = ", ".join(f["parameters"].get("properties", {})) or "sem parâmetros"
                print(f"{n}({params})\n    {f['description']}")
            return 0
        if nome not in tools:
            print(f"Tool '{nome}' não encontrada. Disponíveis: {', '.join(tools) or 'nenhuma'}.")
            print("Se o arquivo existe, veja no terminal a linha '[orbit-tools] falha ao carregar ...'.")
            return 2
        inicio = time.perf_counter()
        resultado = await mcp.chamar(nome, argumentos)
        print(f"({time.perf_counter() - inicio:.2f} s) Retorno:\n{resultado}")
        caminho = Path(resultado.strip())
        if caminho.suffix.lower() in _IMAGENS and caminho.is_absolute() and caminho.is_file():
            print("\n→ É um caminho de imagem: o servidor a mostraria no tablet.")
        elif resultado.startswith("ERRO:"):
            print("\n→ Começa com 'ERRO:': o modelo recebe o erro e explica em voz alta.")
        else:
            print(f"\n→ Será falado em voz alta ({len(resultado)} caracteres).")
        return 0
    finally:
        await mcp.encerrar()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tool", nargs="?", help="nome da tool")
    p.add_argument("argumentos", nargs="?", default="{}", help='argumentos em JSON, ex.: \'{"nome": "x"}\'')
    p.add_argument("--listar", action="store_true", help="lista as tools e as descrições que o modelo vê")
    a = p.parse_args()
    try:
        argumentos = json.loads(a.argumentos)
    except json.JSONDecodeError as erro:
        p.error(f"os argumentos precisam ser um JSON válido ({erro})")
    return asyncio.run(executar(a.tool, argumentos, a.listar))


if __name__ == "__main__":
    raise SystemExit(main())
