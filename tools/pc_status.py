"""Tool pc_status: situação do PC (CPU, RAM, disco, uptime)."""
import time
from pathlib import Path

import psutil


def coletar() -> dict:
    """Coleta os números crus do PC."""
    raiz = Path.home().anchor or "/"  # "C:\\" no Windows, "/" no Linux
    mem = psutil.virtual_memory()
    disco = psutil.disk_usage(raiz)
    return {
        "cpu": psutil.cpu_percent(interval=0.5),
        "ram_usada_gb": mem.used / 1e9,
        "ram_total_gb": mem.total / 1e9,
        "disco_pct": disco.percent,
        "disco_nome": raiz,
        "uptime_s": time.time() - psutil.boot_time(),
    }


def formatar(d: dict) -> str:
    horas, resto = divmod(int(d["uptime_s"]), 3600)
    dias, horas = divmod(horas, 24)
    ligado = f"{dias} dias e {horas} horas" if dias else f"{horas} horas e {resto // 60} minutos"
    return (
        f"CPU em {d['cpu']:.0f} por cento. "
        f"Memória: {d['ram_usada_gb']:.1f} de {d['ram_total_gb']:.1f} gigas em uso. "
        f"Disco {d['disco_nome']} com {d['disco_pct']:.0f} por cento usado. "
        f"Ligado há {ligado}."
    )


def registrar(mcp) -> None:
    @mcp.tool()
    def pc_status() -> str:
        """[leitura] Use quando perguntarem como está o PC: CPU, memória, disco ou tempo ligado."""
        return formatar(coletar())
