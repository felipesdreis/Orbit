# Diário de desenvolvimento — Orbit

Registro vivo do que foi feito, por etapa (ver `HANDOFF_ORBIT.md`). Cada entrada traz a data, o que ficou pronto, as decisões e como testar. Mais recente no topo.

## Resumo das etapas

| Etapa | Situação |
|---|---|
| 1. Carinha (PWA, sem voz) | pronta ([PR #1](https://github.com/felipesdreis/Orbit/pull/1)) |
| 2. Servidor + MCP + TTS no PC | pronta e validada no PC (Gemma + Kokoro reais) |
| 3. Voz no PWA | código pronto e testado com microfone simulado; falta testar com microfone real no Chrome do PC |
| 4. APK | pendente |
| 5. Guia e README | pendente |

## Pendências abertas

- Latência: a busca de arquivo levou 11,6 s até o 1º áudio (10,1 s só até a resposta do LLM). Avaliar antes da etapa 3.
- A resposta da busca traz o caminho completo e o Kokoro o lê em voz alta; considerar pedir no prompt só nome e pasta.
- Tabela de tempos ainda não está no README (critério da etapa 2).
- `tools/GUIA_NOVA_TOOL.md` (etapa 5) ainda não existe.

- Microfone riscado/esmaecido nos estados em que o Orbit não está ouvindo (falando, pensando). Hoje o ícone só aparece em `ouvindo`. Aguardando decisão.
- Nada foi testado em tablet real.

---

## 2026-10-17 — Etapa 3: voz no PWA (`feat/etapa-3-voz`)

**O que ficou pronto**
- `app/src/app/voice/orbit.service.ts`: máquina de estados da conversa. Toque na carinha acorda; ativo por 15 min (renova a cada fala reconhecida); filtro do nome; janela de follow-up de 25 s; half-duplex; wake lock; avisos (sem conexão, microfone bloqueado, navegador sem STT).
- `stt-webspeech.ts` (Web Speech API, pt-BR, reinicia no `onend`), `fala-navegador.ts` (fila de áudios + voz nativa de fallback), `ativador.ts` (interface plugável; implementação por toque), `nome.ts` (filtro do nome), `api/api-websocket.ts` (WebSocket com reconexão e `?pc=<ip>`).
- Painel de teste agora mostra "Ouvi: … — enviado/ignorado" e os botões de estado/emoção só mexem na aparência.
- Servidor: nova mensagem `fim` no fim de cada vez (protocolo acrescentado, testes atualizados).
- Testes: 45 no app (Karma/Jasmine em Chrome headless: 31 do filtro do nome + 14 da máquina de estados) e 21 no servidor.

**Decisões e por quê**
- **Mensagem `fim` no protocolo:** o servidor manda um `audio` por frase e nada marcava o fim da fala. Sem isso o microfone voltaria a ouvir numa pausa entre frases e o Orbit escutaria a própria voz (half-duplex).
- **STT, voz e API como classes abstratas** com a implementação real ligada em `app.config.ts`: os testes trocam por falsas e cobrem toda a máquina de estados sem microfone; o APK troca só o STT.
- **O rosto só vira "falando" quando o som começa:** entre a resposta e o 1º áudio ficam ~1 s de síntese; antes a boca mexeria em silêncio.
- **Qualquer fala reconhecida renova os 15 min**, mesmo a ignorada pelo filtro: alguém está por perto.
- **Toque só acorda na área da carinha:** os botões do painel de teste não ligam o microfone sem querer.
- **Filtro do nome por palavra inteira** (subagente): "exorbitante" não casa; "órbita" casa porque o handoff pede essa variante (efeito colateral: "a lua está em órbita" também acorda); "o bit" casa por virar "obit".
- **Se o servidor nunca mandar `fim`,** o Orbit volta a ouvir depois de 90 s.

**Não verificado**
- Microfone e reconhecimento reais no Chrome do PC (aqui o STT foi simulado).
- Áudio audível, e tempo de resposta ponta a ponta com voz (STT → LLM → TTS).
- Tablet/Android (etapa 4).

**Como testar**: roteiro no `README.md`, seção "Etapa 3".

## 2026-10-17 — Etapa 2: validação no PC (Gemma4-E4B-uncensored + Kokoro pm_santa em CPU)

`pytest -q`: 21 passed. Venv `.venv` na raiz (Python 3.10.11), `kokoro==0.9.4`. Ollama 0.40.5.

| Frase | Tool chamada | Emoção | Resposta (s) | 1º áudio (s) | Áudios |
|---|---|---|---|---|---|
| orbit como está o pc | `pc_status` | neutro | 5,37 | **6,16** | 3 |
| orbit mostra a tela | `screenshot` | curioso | 4,24 | **4,84** | 1 |
| orbit procura o arquivo HANDOFF_ORBIT | `buscar_arquivo` | curioso | 10,13 | **11,59** | 1 |
| orbit conta uma piada curta | nenhuma | feliz | 1,81 | **2,46** | 2 |

- Gemma acertou a tool nas 3 frases que pediam uma; na piada não chamou nenhuma.
- Mensagem `imagem` chegou com a resposta; a URL serviu o PNG (200, 1920x1080). WAVs: 24 kHz, abrem.
- Do fim da resposta ao 1º áudio, o Kokoro levou de 0,6 s a 1,5 s; o gargalo é o LLM/tool.
- O 1º teste incluiu carga do modelo no Ollama, então o `pc_status` pode estar inflado.
- Log do servidor mostra "1º áudio" com acento quebrado quando redirecionado para arquivo no Windows (cosmético).

## 2026-10-17 — Etapa 2: servidor, MCP e TTS (código pronto)

**O que ficou pronto**
- `tools/`: servidor MCP (`server.py`) que descobre sozinho todo `tools/*.py` e chama `registrar(mcp)`; módulo quebrado só gera log, não derruba o servidor. Tools de leitura: `pc_status`, `buscar_arquivo`, `screenshot` (devolve só o caminho do PNG).
- `server/`: FastAPI com WebSocket `/ws` e `GET /files/<id>`; ponte Ollama ↔ MCP com tool calling (até 4 rodadas, últimas 12 mensagens lembradas por conexão); extração da tag de emoção; TTS Kokoro `pm_santa` em CPU, carregado uma vez na subida, um WAV por frase enviado em ordem.
- `server/teste_ws.py`: cliente de teste que imprime os tempos até a resposta e até o 1º áudio.
- `tests/`: 21 testes (`pytest -q`). Cobrem texto, ponte com o servidor MCP real, WebSocket de ponta a ponta e o pedido HTTP ao Ollama. LLM e TTS são falsos nos testes.
- Teste de fumaça: o servidor real sobe, abre o MCP e acha as 3 tools; sem Ollama responde "Não consegui falar com o meu cérebro agora."; sem Kokoro avisa `audio: false`.

**Decisões e por quê**
- **`mcp<2` (1.30):** o `mcp` 2.x renomeou o FastMCP para `MCPServer`. O handoff pede FastMCP e o servidor de referência do PC usa a API 1.x; ficar na 1.x evita uma API nova e pouco testada.
- **Ollama por HTTP (`httpx`)**, sem biblioteca extra: um endpoint (`/api/chat`) e menos dependências no venv do Orbit.
- **LLM e TTS injetados, sem "modo falso" no código de produção:** os testes passam versões falsas; o servidor real nunca finge uma resposta.
- **Kokoro opcional:** se não estiver instalado ou falhar, o servidor segue de pé. A mensagem `resposta` ganhou o campo `audio` (acréscimo ao protocolo do plano): com `false`, o tablet fala o texto com a voz nativa (fallback do handoff).
- **`/files` só serve o que foi registrado** (nada de caminho arbitrário), e CORS aberto porque o tablet vem de outra origem na rede local.
- **Imagem = caminho de arquivo devolvido por uma tool:** o modelo recebe só "imagem capturada" e o servidor manda `imagem` ao tablet. Vale para qualquer tool futura que devolva um PNG/JPG.
- **Subagente** escreveu `tools/`; eu escrevi `server/`. Conferi os arquivos e rodei os testes antes de aceitar.

**Não verificado (precisa do PC)**
- Gemma4-E4B escolhendo a tool certa; formato real de `tool_calls` do Ollama (o teste usa o formato documentado).
- Kokoro real: voz, instalação no venv do Orbit, latência da 1ª frase.
- `screenshot` real (sem display aqui), `buscar_arquivo` e `pc_status` no Windows.

**Como testar**: `pytest -q`; no PC, `python -m server` e `python -m server.teste_ws "orbit como está o pc"`. Detalhes no `README.md`.

## 2026-10-17 — Etapa 1: carinha (pronta)

**O que ficou pronto**
- Projeto `app/` com Angular 19 + Ionic 8. O template do Ionic CLI não baixou pelo proxy, então o esqueleto veio do Angular CLI. Capacitor fica para a etapa 4.
- Componente `<app-face>` (`app/src/app/face/`) em SVG + CSS:
  - estados: `standby`, `ouvindo`, `pensando`, `falando`;
  - emoções: `neutro`, `feliz`, `pensando`, `curioso`, `surpreso`;
  - pisca e move o olhar sozinha fora do standby.
- Painel de teste (botão ⚙) com botões de estado/emoção e demo automática de 23 s.
- Manifest e ícone de PWA (sem service worker).
- Microfone desenhado em SVG no canto superior esquerdo, visível só em `ouvindo`.
- No `feliz` falando, a boca é um sorriso aberto que abre e fecha; nas outras emoções é uma elipse.

**Decisões e por quê**
- Boca e pálpebras em SVG/CSS puro: um código só para PWA e APK, sem imagens.
- Pálpebra e bochecha apagam o olho por máscara, em vez de pintar com a cor do fundo, para o brilho dos olhos não ganhar discos escuros.
- Microfone em SVG, não emoji: o emoji muda de aparência em cada aparelho.

**Como testar**: `cd app && npm install && npm start`, abrir `http://localhost:4200`. Detalhes no `README.md`.

**Verificação**: `ng build` sem avisos; capturas no Chromium em 1280x800, 800x1280 e 360x640, sem erros no console.
