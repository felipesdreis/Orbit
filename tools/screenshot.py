"""Tool screenshot: captura a tela e devolve só o caminho do PNG."""
import tempfile
import time
from pathlib import Path


def capturar() -> Path:
    from PIL import ImageGrab  # import tardio: falha de display vira ERRO, não derruba o módulo

    pasta = Path(tempfile.gettempdir()) / "orbit_screenshots"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"tela_{time.strftime('%Y%m%d_%H%M%S')}_{time.monotonic_ns() % 1000000}.png"
    ImageGrab.grab().save(destino, "PNG")
    return destino.resolve()


def registrar(mcp) -> None:
    @mcp.tool()
    def screenshot() -> str:
        """[leitura] Use quando pedirem para ver ou mostrar a tela do PC. Retorna o caminho do PNG."""
        try:
            return str(capturar())
        except Exception as e:
            return f"ERRO: não consegui capturar a tela ({type(e).__name__})."
