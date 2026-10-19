"""Síntese de voz no PC: Kokoro-82M, voz pm_santa, em CPU (a VRAM é do Gemma)."""
import io
import logging
import os
import wave

import numpy as np

log = logging.getLogger("orbit.tts")

TAXA = 24000


def para_wav(amostras: np.ndarray) -> bytes:
    """Converte áudio float32 mono (24 kHz) em um arquivo WAV 16 bits."""
    pcm = (np.clip(amostras, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


class Kokoro:
    """Carrega o modelo uma única vez; `sintetizar` é bloqueante (rodar em thread)."""

    def __init__(self, voz: str = "pm_santa"):
        import torch
        from kokoro import KPipeline  # import tardio: só existem no venv do PC

        # Deixa 2 núcleos livres: o Kokoro usa todos por padrão e disputa a CPU com o navegador
        # que está tocando a frase anterior, o que faz o áudio engasgar no meio das palavras.
        torch.set_num_threads(max(2, (os.cpu_count() or 4) - 2))
        self.voz = voz
        self._pipeline = KPipeline(lang_code="p", repo_id="hexgrad/Kokoro-82M", device="cpu")

    def sintetizar(self, texto: str) -> bytes:
        pedacos = [np.asarray(audio, dtype=np.float32) for _, _, audio in self._pipeline(texto, voice=self.voz)]
        return para_wav(np.concatenate(pedacos)) if pedacos else b""


def carregar(voz: str = "pm_santa") -> Kokoro | None:
    """Devolve o Kokoro pronto, ou None se não estiver instalado/funcionando.

    Sem Kokoro o servidor segue de pé e o tablet fala com a voz nativa (fallback).
    """
    try:
        return Kokoro(voz)
    except Exception as erro:  # ModuleNotFoundError, falha ao baixar/carregar o modelo...
        log.warning("Kokoro indisponível (%s); o tablet usará a voz nativa.", erro)
        return None
