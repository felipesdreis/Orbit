"""Servidor do Orbit: WebSocket /ws (fala -> resposta/imagem/audio) e GET /files/<id>."""
import asyncio
import logging
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import tts as tts_mod
from .arquivos import Arquivos
from .mcp_cliente import ClienteMCP
from .ponte import Ponte
from .texto import dividir_frases, extrair_emocao

log = logging.getLogger("orbit.servidor")

PASTA_AUDIO = Path(tempfile.gettempdir()) / "orbit_audio"


def criar_app(ponte=None, tts=None) -> FastAPI:
    """`ponte` e `tts` só são passados nos testes; em produção sobem no lifespan."""

    @asynccontextmanager
    async def vida(app: FastAPI):
        mcp = None
        if ponte is None:
            mcp = ClienteMCP()
            await mcp.iniciar()
            app.state.ponte = Ponte(mcp)
            log.info("tools MCP: %s", [t["function"]["name"] for t in mcp.tools_ollama])
        else:
            app.state.ponte = ponte
        # O modelo carrega uma vez, na subida (não por requisição).
        app.state.tts = tts if tts is not None else await asyncio.to_thread(tts_mod.carregar)
        PASTA_AUDIO.mkdir(exist_ok=True)
        try:
            yield
        finally:
            if mcp:
                await mcp.encerrar()

    app = FastAPI(lifespan=vida)
    app.add_middleware(CORSMiddleware, allow_origins=["*"])  # rede local: o tablet vem de outra origem
    app.state.arquivos = Arquivos()

    @app.get("/files/{nome}")
    def arquivo(nome: str):
        caminho = app.state.arquivos.buscar(nome)
        if caminho is None:
            raise HTTPException(404)
        return FileResponse(caminho)

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        base = f"http://{socket.headers.get('host', 'localhost')}/files/"
        historico: list[dict] = []
        try:
            while True:
                msg = await socket.receive_json()
                if msg.get("type") == "fala" and msg.get("text", "").strip():
                    await _atender(app, socket, base, historico, msg["text"].strip())
                    # Marca o fim da vez: o tablet só volta a ouvir depois que o último áudio tocar.
                    await socket.send_json({"type": "fim"})
        except WebSocketDisconnect:
            pass

    return app


async def _atender(app: FastAPI, socket: WebSocket, base: str, historico: list[dict], fala: str) -> None:
    inicio = time.perf_counter()
    await socket.send_json({"type": "pensando"})
    try:
        resposta = await app.state.ponte.responder(historico, fala)
    except Exception:
        log.exception("falha ao falar com o Ollama/MCP")
        resposta_texto, emocao, imagens = "Não consegui falar com o meu cérebro agora.", "neutro", []
    else:
        log.info("resposta pronta em %.2f s", time.perf_counter() - inicio)
        resposta_texto, emocao = extrair_emocao(resposta.texto)
        imagens = resposta.imagens

    tts = app.state.tts
    await socket.send_json({"type": "resposta", "text": resposta_texto, "emocao": emocao, "audio": tts is not None})
    for imagem in imagens:
        await socket.send_json({"type": "imagem", "url": base + app.state.arquivos.registrar(imagem)})

    if tts is None:
        return
    for i, frase in enumerate(dividir_frases(resposta_texto)):
        t0 = time.perf_counter()
        try:
            wav = await asyncio.to_thread(tts.sintetizar, frase)
            log.info("TTS da frase %d (%d caracteres) em %.2f s", i + 1, len(frase), time.perf_counter() - t0)
        except Exception:
            log.exception("falha no TTS; o tablet usa a voz nativa")
            break
        if not wav:
            continue
        caminho = PASTA_AUDIO / f"{time.time_ns()}.wav"
        caminho.write_bytes(wav)
        await socket.send_json({"type": "audio", "url": base + app.state.arquivos.registrar(caminho, apagar_depois=True)})
        if i == 0:
            log.info("1º áudio em %.2f s", time.perf_counter() - inicio)
