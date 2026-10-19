"""Testes do servidor: texto, ponte Ollama<->MCP (com MCP real) e WebSocket de ponta a ponta."""
import wave
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from server import tts
from server.arquivos import Arquivos
from server.main import criar_app
from server.mcp_cliente import ClienteMCP
from server.ponte import Ponte, Resposta
from server.texto import dividir_frases, extrair_emocao


# ---- texto ----

def test_emocao_tira_a_tag_e_devolve_a_emocao():
    assert extrair_emocao("[feliz] Oi, tudo bem?") == ("Oi, tudo bem?", "feliz")


def test_emocao_sem_tag_ou_invalida_cai_em_neutro():
    assert extrair_emocao("Oi") == ("Oi", "neutro")
    assert extrair_emocao("[bravo] Oi")[1] == "neutro"


def test_frases_separam_e_grudam_as_curtas():
    assert dividir_frases("Oi. Hoje está calor lá fora! Quer ajuda?") == ["Oi. Hoje está calor lá fora!", "Quer ajuda?"]
    assert dividir_frases("**Olá** `mundo`") == ["Olá mundo"]
    assert dividir_frases("   ") == []


def test_frases_nao_colam_as_palavras_de_nomes_de_arquivo():
    # "_" virava nada e "Discurso_152" era falado como "Discurso152"
    assert dividir_frases("Achei Discurso_152_Armagedom_30min.docx na pasta Documentos.") == [
        "Achei Discurso 152 Armagedom 30min.docx na pasta Documentos."
    ]


def test_frases_longas_sao_quebradas_nas_virgulas():
    longa = (
        "O computador está com a CPU em doze por cento, a memória em quarenta por cento de uso, "
        "o disco com mais da metade livre, e ele está ligado há quase três dias seguidos sem reiniciar."
    )
    pedacos = dividir_frases(longa)
    assert len(pedacos) >= 2 and all(len(p) <= 100 for p in pedacos)
    assert " ".join(pedacos) == longa  # nada se perde nem muda de ordem
    assert pedacos[0].endswith(",")  # o 1º pedaço fecha numa vírgula: a voz começa mais cedo


def test_frase_longa_sem_virgula_quebra_nas_palavras():
    sem_virgula = " ".join(["palavra"] * 40)  # 319 caracteres
    pedacos = dividir_frases(sem_virgula)
    assert all(len(p) <= 100 for p in pedacos) and " ".join(pedacos) == sem_virgula


def test_frases_curtas_ficam_como_estao():
    assert dividir_frases("Tudo certo por aqui. O PC está ótimo hoje!") == ["Tudo certo por aqui.", "O PC está ótimo hoje!"]


def test_threads_do_kokoro_ficam_entre_2_e_4_e_aceitam_override(monkeypatch):
    monkeypatch.delenv("ORBIT_TTS_THREADS", raising=False)
    for fisicos, esperado in [(None, 2), (2, 2), (4, 2), (6, 3), (8, 4), (16, 4)]:
        monkeypatch.setattr(tts.psutil, "cpu_count", lambda logical=True, f=fisicos: f)
        monkeypatch.setattr(tts.os, "cpu_count", lambda: 8)
        assert tts.threads() == esperado  # None: sem a contagem física, usa metade dos 8 lógicos (= 4 físicos)
    monkeypatch.setenv("ORBIT_TTS_THREADS", "6")
    assert tts.threads() == 6
    monkeypatch.setenv("ORBIT_TTS_THREADS", "zero")  # valor inválido cai no padrão
    assert 2 <= tts.threads() <= 4


def test_baixar_prioridade_pede_prioridade_baixa_e_nao_quebra_se_falhar(monkeypatch):
    from server import processo

    chamadas = []

    class Falso:
        def nice(self, valor):
            chamadas.append(valor)

    monkeypatch.setattr(processo.psutil, "Process", Falso)
    processo.baixar_prioridade()
    assert len(chamadas) == 1

    class Proibido:
        def nice(self, valor):
            raise PermissionError("sem permissão")

    monkeypatch.setattr(processo.psutil, "Process", Proibido)
    processo.baixar_prioridade()  # só avisa no log; o servidor sobe do mesmo jeito


def test_wav_tem_24khz_mono_16bits():
    with wave.open(BytesIO(tts.para_wav(np.zeros(2400, dtype=np.float32)))) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()) == (24000, 1, 2, 2400)


def test_arquivos_so_serve_o_registrado(tmp_path):
    a = Arquivos()
    f = tmp_path / "x.png"
    f.write_bytes(b"png")
    nome = a.registrar(f)
    assert nome.endswith(".png") and a.buscar(nome) == f
    assert a.buscar("../../etc/passwd") is None
    assert a.buscar("inexistente.png") is None


# ---- ponte (Ollama falso + servidor MCP real) ----

class OllamaFalso:
    """Primeiro pede a tool indicada; depois responde com o que a tool devolveu."""

    def __init__(self, tool, args=None):
        self.tool, self.args, self.mensagens = tool, args or {}, []

    async def __call__(self, mensagens, tools):
        self.mensagens.append(list(mensagens))
        if mensagens[-1]["role"] == "tool":
            return {"role": "assistant", "content": f"[feliz] Resultado: {mensagens[-1]['content']}"}
        return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": self.tool, "arguments": self.args}}]}


@asynccontextmanager
async def mcp_real():
    # Não é fixture: o contexto do MCP (anyio) precisa abrir e fechar na mesma task.
    cliente = ClienteMCP()
    await cliente.iniciar()
    try:
        yield cliente
    finally:
        await cliente.encerrar()


async def test_mcp_expoe_as_tools_no_formato_do_ollama():
    async with mcp_real() as mcp:
        nomes = {t["function"]["name"] for t in mcp.tools_ollama}
        assert nomes == {"pc_status", "buscar_arquivo", "screenshot"}
        assert all(t["type"] == "function" and t["function"]["parameters"] for t in mcp.tools_ollama)


async def test_ponte_chama_a_tool_e_devolve_o_texto():
    chat = OllamaFalso("pc_status")
    historico: list[dict] = []
    async with mcp_real() as mcp:
        r = await Ponte(mcp, chat).responder(historico, "orbit como está o pc")
    assert "CPU" in r.texto and r.imagens == []
    assert [m["role"] for m in historico] == ["user", "assistant"]
    assert chat.mensagens[0][0]["role"] == "system"


async def test_ponte_trata_caminho_de_imagem_como_imagem(tmp_path):
    png = tmp_path / "tela.png"
    png.write_bytes(b"png")

    class McpFalso:
        tools_ollama: list = []

        async def chamar(self, nome, args):
            return str(png)

    chat = OllamaFalso("screenshot")
    r = await Ponte(McpFalso(), chat).responder([], "mostra a tela")
    assert r.imagens == [png]
    assert str(png) not in r.texto  # o modelo não recebe o caminho, só o aviso


async def test_ponte_limita_as_rodadas_de_tools():
    async def sempre_tool(mensagens, tools):
        return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "pc_status", "arguments": {}}}]}

    async with mcp_real() as mcp:
        r = await Ponte(mcp, sempre_tool).responder([], "x")
    assert "Não consegui" in r.texto


# ---- WebSocket de ponta a ponta (ponte e TTS falsos) ----

class PonteFalsa:
    def __init__(self, resposta):
        self.resposta = resposta

    async def responder(self, historico, fala):
        return self.resposta


class TtsFalso:
    def __init__(self):
        self.frases = []

    def sintetizar(self, texto):
        self.frases.append(texto)
        return tts.para_wav(np.zeros(240, dtype=np.float32))


def receber_ate_audios(ws, n_audios):
    msgs = []
    while True:
        msgs.append(ws.receive_json())
        if sum(m["type"] == "audio" for m in msgs) == n_audios:
            return msgs


def test_ws_resposta_emocao_e_um_audio_por_frase_em_ordem():
    falso = TtsFalso()
    ponte = PonteFalsa(Resposta("[feliz] Está tudo certo por aqui. O PC está ótimo hoje!"))
    with TestClient(criar_app(ponte, falso)) as cliente, cliente.websocket_connect("/ws") as ws:
        ws.send_json({"type": "fala", "text": "orbit como está o pc"})
        msgs = receber_ate_audios(ws, 2)
        assert [m["type"] for m in msgs] == ["pensando", "resposta", "audio", "audio"]
        assert ws.receive_json() == {"type": "fim"}
        assert msgs[1] == {"type": "resposta", "text": "Está tudo certo por aqui. O PC está ótimo hoje!", "emocao": "feliz", "audio": True}
        assert falso.frases == ["Está tudo certo por aqui.", "O PC está ótimo hoje!"]
        wav = cliente.get(msgs[2]["url"].replace("http://testserver", ""))
        assert wav.status_code == 200 and wav.content[:4] == b"RIFF"
        assert msgs[2]["url"].endswith(".wav") and msgs[2]["url"] != msgs[3]["url"]


def test_ws_imagem_e_servida_em_files(tmp_path):
    png = tmp_path / "tela.png"
    png.write_bytes(b"\x89PNG-teste")
    ponte = PonteFalsa(Resposta("[neutro] Mostrando a tela.", [png]))
    with TestClient(criar_app(ponte, TtsFalso())) as cliente, cliente.websocket_connect("/ws") as ws:
        ws.send_json({"type": "fala", "text": "orbit mostra a tela"})
        msgs = receber_ate_audios(ws, 1)
        imagem = next(m for m in msgs if m["type"] == "imagem")
        assert imagem["url"].endswith(".png")
        r = cliente.get(imagem["url"].replace("http://testserver", ""))
        assert r.content == b"\x89PNG-teste"


def test_ws_sem_tts_avisa_o_tablet_para_usar_a_voz_nativa(monkeypatch):
    monkeypatch.setattr(tts, "carregar", lambda *a: None)
    ponte = PonteFalsa(Resposta("[curioso] Oi!"))
    with TestClient(criar_app(ponte)) as cliente, cliente.websocket_connect("/ws") as ws:
        ws.send_json({"type": "fala", "text": "orbit oi"})
        assert ws.receive_json() == {"type": "pensando"}
        assert ws.receive_json() == {"type": "resposta", "text": "Oi!", "emocao": "curioso", "audio": False}
        assert ws.receive_json() == {"type": "fim"}


def test_ws_falha_da_ponte_vira_resposta_amigavel():
    class Quebrada:
        async def responder(self, historico, fala):
            raise ConnectionError("Ollama fora do ar")

    with TestClient(criar_app(Quebrada(), TtsFalso())) as cliente, cliente.websocket_connect("/ws") as ws:
        ws.send_json({"type": "fala", "text": "orbit oi"})
        ws.receive_json()
        assert ws.receive_json()["text"].startswith("Não consegui")
        assert ws.receive_json()["type"] == "audio"  # a mensagem de erro também é falada
        assert ws.receive_json() == {"type": "fim"}


def test_files_desconhecido_da_404():
    with TestClient(criar_app(PonteFalsa(Resposta("x")), TtsFalso())) as cliente:
        assert cliente.get("/files/nada.png").status_code == 404


# ---- chamada HTTP ao Ollama ----

async def test_chat_ollama_monta_o_pedido_e_le_a_mensagem(monkeypatch):
    import json

    import httpx

    from server import ponte as ponte_mod

    visto = {}

    def responder(req: httpx.Request) -> httpx.Response:
        visto["url"], visto["corpo"] = str(req.url), json.loads(req.content)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "[feliz] Oi!"}})

    cliente_real = httpx.AsyncClient
    monkeypatch.setattr(ponte_mod.httpx, "AsyncClient", lambda **kw: cliente_real(transport=httpx.MockTransport(responder), **kw))
    tools = [{"type": "function", "function": {"name": "pc_status"}}]
    msg = await ponte_mod.chat_ollama([{"role": "user", "content": "oi"}], tools)

    assert msg["content"] == "[feliz] Oi!"
    assert visto["url"].endswith("/api/chat")
    assert visto["corpo"]["model"] == ponte_mod.MODELO and visto["corpo"]["stream"] is False
    assert visto["corpo"]["tools"] == tools
