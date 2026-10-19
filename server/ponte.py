"""Ponte Ollama <-> MCP: o modelo decide se chama uma tool; o resultado volta para ele."""
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

import httpx

log = logging.getLogger("orbit.ponte")

MODELO = os.environ.get("ORBIT_MODELO", "Gemma4-E4B-uncensored:latest")
OLLAMA_URL = os.environ.get("ORBIT_OLLAMA_URL", "http://localhost:11434")

PROMPT_SISTEMA = (
    "Você é o Orbit, um assistente de voz que vive num tablet. "
    "Responda sempre em português do Brasil, em frases curtas e naturais, "
    "porque sua resposta será falada em voz alta: sem listas, sem markdown, sem emojis. "
    "Comece TODA resposta com uma tag de emoção entre colchetes: "
    "[neutro], [feliz], [pensando], [curioso] ou [surpreso]. "
    "Use as ferramentas só quando o pedido depender do PC "
    "(status do computador, achar um arquivo, mostrar a tela). "
    "Para conversa normal, responda direto, sem ferramenta. "
    "Nunca fale caminhos completos, letras de unidade nem endereços da internet: "
    "diga só o nome do arquivo e a pasta onde ele está."
)

_RODADAS_MAX = 4   # idas e vindas com tools por pergunta
_HISTORICO_MAX = 12  # mensagens lembradas por conexão
_IMAGENS = {".png", ".jpg", ".jpeg"}

# Recebe (mensagens, tools) e devolve a mensagem do assistente no formato do Ollama.
Chat = Callable[[list[dict], list[dict]], Awaitable[dict]]


@dataclass
class Resposta:
    texto: str
    imagens: list[Path] = field(default_factory=list)


async def chat_ollama(mensagens: list[dict], tools: list[dict]) -> dict:
    async with httpx.AsyncClient(timeout=120) as http:
        r = await http.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": MODELO, "messages": mensagens, "tools": tools, "stream": False},
        )
        r.raise_for_status()
        return r.json()["message"]


class Ponte:
    def __init__(self, mcp, chat: Chat = chat_ollama):
        self._mcp = mcp
        self._chat = chat

    async def responder(self, historico: list[dict], fala: str) -> Resposta:
        """Responde a `fala`. `historico` (user/assistant) é atualizado no lugar."""
        mensagens = [{"role": "system", "content": PROMPT_SISTEMA}, *historico, {"role": "user", "content": fala}]
        imagens: list[Path] = []
        texto = "[pensando] Não consegui concluir isso."

        for _ in range(_RODADAS_MAX):
            t0 = time.perf_counter()
            msg = await self._chat(mensagens, self._mcp.tools_ollama)
            log.info("LLM respondeu em %.2f s", time.perf_counter() - t0)
            chamadas = msg.get("tool_calls") or []
            if not chamadas:
                texto = msg.get("content", "")
                break
            mensagens.append(msg)
            for chamada in chamadas:
                nome = chamada["function"]["name"]
                args = chamada["function"].get("arguments") or {}
                if isinstance(args, str):
                    args = json.loads(args or "{}")
                t0 = time.perf_counter()
                resultado = await self._mcp.chamar(nome, args)
                log.info("tool %s(%s) levou %.2f s", nome, args, time.perf_counter() - t0)
                caminho = Path(resultado.strip())
                if caminho.suffix.lower() in _IMAGENS and caminho.is_absolute() and caminho.is_file():
                    imagens.append(caminho)
                    resultado = "Imagem capturada; já está sendo mostrada no tablet."
                mensagens.append({"role": "tool", "tool_name": nome, "content": resultado})

        historico += [{"role": "user", "content": fala}, {"role": "assistant", "content": texto}]
        del historico[:-_HISTORICO_MAX]
        return Resposta(texto, imagens)
