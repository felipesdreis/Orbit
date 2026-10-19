"""Prioridade do processo do servidor."""
import logging
import os

import psutil

log = logging.getLogger("orbit.processo")


def baixar_prioridade() -> None:
    """Põe o servidor em prioridade abaixo do normal.

    Quando a CPU está disputada (o Kokoro sintetizando a próxima frase), o navegador e o áudio do
    sistema passam na frente em vez de engasgar. Só pesa na hora em que há disputa.
    """
    try:
        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 5)
    except Exception as erro:  # sem permissão ou sem suporte: segue com a prioridade normal
        log.warning("Não consegui baixar a prioridade do processo (%s)", erro)
