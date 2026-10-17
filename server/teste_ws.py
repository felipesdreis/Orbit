"""Cliente de teste: `python -m server.teste_ws "orbit como está o pc"`.

Imprime cada mensagem com o tempo desde o envio e, no fim, o tempo até a resposta
e até o 1º áudio (o número que a etapa 2 manda registrar no README).
"""
import argparse
import asyncio
import json
import time

import websockets


async def main(url: str, fala: str) -> None:
    tempos: dict[str, float] = {}
    async with websockets.connect(url) as ws:
        inicio = time.perf_counter()
        await ws.send(json.dumps({"type": "fala", "text": fala}))
        espera = 120.0  # a 1ª resposta pode demorar (modelo frio no Ollama)
        while True:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), espera))
            except asyncio.TimeoutError:
                break
            t = time.perf_counter() - inicio
            tempos.setdefault(msg["type"], t)
            print(f"{t:6.2f}s  {json.dumps(msg, ensure_ascii=False)}")
            if msg["type"] == "resposta":
                espera = 30.0 if msg.get("audio") else 2.0  # TTS lento vs. só imagens
            elif msg["type"] in ("audio", "imagem"):
                espera = 8.0
    print("\nResumo:", {k: round(v, 2) for k, v in tempos.items()})
    if "audio" in tempos:
        print(f"Tempo até o 1º áudio: {tempos['audio']:.2f} s")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("fala")
    p.add_argument("--url", default="ws://localhost:8765/ws")
    a = p.parse_args()
    asyncio.run(main(a.url, a.fala))
