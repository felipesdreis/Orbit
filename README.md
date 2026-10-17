# Orbit

Assistente virtual por voz para tablet Android (carinha animada, estilo Emo robot). A inteligência roda no PC via Ollama. O plano completo está em [`HANDOFF_ORBIT.md`](HANDOFF_ORBIT.md).

## Estado atual

| Etapa | Situação |
|---|---|
| 1. Carinha (PWA, sem voz) | pronta |
| 2. Servidor + MCP + TTS | código pronto e testado com LLM/TTS falsos; **falta validar no PC** (Ollama e Kokoro reais) |
| 3. Voz no PWA | pendente |
| 4. APK | pendente |
| 5. Guia de novas tools | pendente |

## Etapa 1 — Carinha

Código em `app/src/app/face/`. O componente `<app-face>` recebe dois inputs:

- `estado`: `standby` | `ouvindo` | `pensando` | `falando`
- `emocao`: `neutro` | `feliz` | `pensando` | `curioso` | `surpreso`

Em `standby` e `pensando` o estado define a aparência; em `ouvindo` e `falando` vale a emoção. A carinha pisca e move o olhar sozinha (fora do standby).

### Como testar

```bash
cd app
npm install
npm start          # serve em http://0.0.0.0:4200
```

1. **PC:** abra `http://localhost:4200` no Chrome.
2. **Tablet:** na mesma rede, abra `http://<IP-do-PC>:4200` (libere a porta 4200 no firewall do Windows). Para testar a carinha, HTTP basta; o microfone (etapa 3) é que exige HTTPS.
3. Use o painel de teste (botão ⚙ abre/fecha): botões de **Estado** e **Emoção**, e **Demo (23 s)**, que percorre tudo sozinho.

Build de produção: `npm run build` (saída em `app/dist/app`).

## Etapa 2 — Servidor, MCP e TTS (rodam no PC)

```
tablet ──WebSocket /ws──▶ server/ (FastAPI) ──HTTP──▶ Ollama (localhost:11434)
                              │  └─ MCP stdio ──▶ tools/server.py (pc_status, buscar_arquivo, screenshot)
                              └─ Kokoro (CPU) ──▶ WAV por frase ──▶ GET /files/<id>.wav
```

- `server/`: `main.py` (WebSocket e `/files`), `ponte.py` (Ollama ↔ MCP), `mcp_cliente.py`, `tts.py` (Kokoro `pm_santa`, CPU), `texto.py` (tag de emoção e frases), `teste_ws.py` (cliente de teste).
- `tools/`: servidor MCP que descobre sozinho todo `tools/*.py`. Cada arquivo define `registrar(mcp)` com as tools dentro. As 3 tools são só de leitura.

### Protocolo (como implementado)

| Direção | Mensagem |
|---|---|
| tablet → PC | `{"type":"fala","text":"orbit como está o pc"}` |
| PC → tablet | `{"type":"pensando"}` assim que recebe a fala |
| PC → tablet | `{"type":"resposta","text":"...","emocao":"feliz","audio":true}` |
| PC → tablet | `{"type":"imagem","url":"http://<ip>:8765/files/<id>.png"}` |
| PC → tablet | `{"type":"audio","url":"http://<ip>:8765/files/<id>.wav"}`, um por frase, em ordem |

`audio` em `resposta` é um acréscimo ao plano: com `false` (Kokoro fora do ar) o tablet deve falar o `text` com a voz nativa (fallback).

### Instalar e rodar no PC (Windows)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install kokoro==0.9.4 :: TTS real; traz o torch (é grande)
python -m server           :: sobe em 0.0.0.0:8765
```

Variáveis opcionais: `ORBIT_MODELO` (padrão `Gemma4-E4B-uncensored:latest`), `ORBIT_OLLAMA_URL`, `ORBIT_PORTA`, `ORBIT_BUSCA_RAIZES` (pastas do `buscar_arquivo`). Libere a porta 8765 no firewall do Windows para o tablet alcançar o PC.

### Testar

```bash
pytest -q                                   # 21 testes; não precisam de Ollama, Kokoro nem tablet
python -m server.teste_ws "orbit como está o pc"
python -m server.teste_ws "orbit mostra a tela"
python -m server.teste_ws "orbit conta uma piada"
```

O `teste_ws` imprime cada mensagem com o tempo desde o envio e, no fim, `Tempo até o 1º áudio`.

### Tempo até o 1º áudio

**A medir no PC** (o servidor também registra `1º áudio em X s` no log). Ainda não foi medido: o Ollama e o Kokoro reais não estão disponíveis onde o código foi escrito.

| Frase | Resposta (s) | 1º áudio (s) |
|---|---|---|
| _pendente_ | | |
