import shutil
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

import buscar_arquivo  # tools/ já está no caminho de importação (tests/conftest.py)
import pc_status
import screenshot

TOOLS = Path(__file__).resolve().parent.parent / "tools"


NUCLEO = {"pc_status", "buscar_arquivo", "screenshot"}


def test_coletar():
    d = pc_status.coletar()
    assert 0 <= d["cpu"] <= 100
    assert d["ram_total_gb"] > 0 and d["uptime_s"] > 0
    texto = pc_status.formatar(d)
    assert "CPU" in texto and "gigas" in texto


def test_busca(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "Relatório Final.txt").write_text("x")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "relatorio.js").write_text("x")
    for i in range(7):
        (tmp_path / f"foto{i}.png").write_text("x")
    r = buscar_arquivo.buscar("RELATORIO", [tmp_path])
    assert [p.name for p in r] == ["Relatório Final.txt"]
    assert len(buscar_arquivo.buscar("foto", [tmp_path])) == 5
    assert "Não achei" in buscar_arquivo.formatar("zzz", buscar_arquivo.buscar("zzz", [tmp_path]))
    # Separadores tratados como iguais e todas as palavras exigidas (o caso real: "discurso 152").
    (tmp_path / "docs" / "Discurso_152_Armagedom_30min.docx").write_text("x")
    nomes = lambda q: [p.name for p in buscar_arquivo.buscar(q, [tmp_path])]
    assert nomes("discurso 152") == ["Discurso_152_Armagedom_30min.docx"]
    assert nomes("152 armagedom") == ["Discurso_152_Armagedom_30min.docx"]
    assert nomes("Discurso_152_Armagedom_30min.docx") == ["Discurso_152_Armagedom_30min.docx"]
    assert nomes("discurso 999") == []
    assert nomes("relatório-final") == ["Relatório Final.txt"]
    # Resultado é falado em voz alta: só nome e pasta, nunca o caminho completo.
    falado = buscar_arquivo.formatar("relatorio", r)
    assert "Relatório Final.txt (pasta docs)" in falado and str(tmp_path) not in falado


def test_screenshot_erro(monkeypatch):
    from PIL import ImageGrab

    def falha():
        raise OSError("sem display")

    monkeypatch.setattr(ImageGrab, "grab", falha)
    from mcp.server.fastmcp import FastMCP

    m = FastMCP("t")
    screenshot.registrar(m)
    assert m._tool_manager.get_tool("screenshot").fn().startswith("ERRO:")


def test_screenshot_ok(monkeypatch):
    from PIL import Image, ImageGrab

    monkeypatch.setattr(ImageGrab, "grab", lambda: Image.new("RGB", (4, 4)))
    caminho = screenshot.capturar()
    assert caminho.is_absolute() and caminho.suffix == ".png" and caminho.exists()
    caminho.unlink()




async def test_servidor_stdio():
    async with stdio_client(StdioServerParameters(command=sys.executable, args=[str(TOOLS / "server.py")])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            nomes = {t.name for t in (await s.list_tools()).tools}
            assert NUCLEO <= nomes  # tools novas não quebram o teste: só o núcleo é obrigatório
            res = await s.call_tool("pc_status", {})
            assert "CPU" in res.content[0].text


async def test_modulo_quebrado_nao_derruba(tmp_path):
    copia = tmp_path / "tools"
    shutil.copytree(TOOLS, copia, ignore=shutil.ignore_patterns("__pycache__"))
    (copia / "quebrado.py").write_text("raise RuntimeError('boom')\n")
    (copia / "_ignorado.py").write_text("raise RuntimeError('nao deveria importar')\n")
    async with stdio_client(StdioServerParameters(command=sys.executable, args=[str(copia / "server.py")])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            nomes = {t.name for t in (await s.list_tools()).tools}
            assert NUCLEO <= nomes and "quebrado" not in nomes


async def test_toda_tool_segue_a_convencao_do_guia():
    """tools/GUIA_NOVA_TOOL.md: risco declarado, descrição de uma linha e poucos parâmetros."""
    async with stdio_client(StdioServerParameters(command=sys.executable, args=[str(TOOLS / "server.py")])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for t in (await s.list_tools()).tools:
                descricao = (t.description or "").strip()
                assert descricao.startswith(("[leitura]", "[escrita]")), f"{t.name}: a descrição deve começar com [leitura] ou [escrita]"
                assert "\n" not in descricao and len(descricao) <= 200, f"{t.name}: a descrição deve ter uma linha só e até 200 caracteres"
                assert len(t.inputSchema.get("properties", {})) <= 2, f"{t.name}: use no máximo 2 parâmetros"
                assert t.name.islower() and t.name.replace("_", "").isalnum(), f"{t.name}: nome em minúsculas, com _ e sem acento"
