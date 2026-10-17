"""Cliente MCP: sobe tools/server.py (stdio) e expõe as tools no formato do Ollama."""
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVIDOR_TOOLS = Path(__file__).resolve().parent.parent / "tools" / "server.py"


class ClienteMCP:
    def __init__(self):
        self._pilha = AsyncExitStack()
        self._sessao: ClientSession | None = None
        self.tools_ollama: list[dict] = []

    async def iniciar(self) -> None:
        params = StdioServerParameters(command=sys.executable, args=[str(SERVIDOR_TOOLS)])
        leitura, escrita = await self._pilha.enter_async_context(stdio_client(params))
        self._sessao = await self._pilha.enter_async_context(ClientSession(leitura, escrita))
        await self._sessao.initialize()
        listadas = (await self._sessao.list_tools()).tools
        self.tools_ollama = [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema},
            }
            for t in listadas
        ]

    async def chamar(self, nome: str, argumentos: dict) -> str:
        resultado = await self._sessao.call_tool(nome, argumentos)
        texto = "\n".join(c.text for c in resultado.content if getattr(c, "type", "") == "text")
        return f"ERRO: {texto}" if resultado.isError else texto

    async def encerrar(self) -> None:
        await self._pilha.aclose()
