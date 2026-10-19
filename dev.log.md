# Diário de desenvolvimento — Orbit

Registro vivo do que foi feito, por etapa (ver `HANDOFF_ORBIT.md`). Cada entrada traz a data, o que ficou pronto, as decisões e como testar. Mais recente no topo.

## Resumo das etapas

| Etapa | Situação |
|---|---|
| 1. Carinha (PWA, sem voz) | pronta ([PR #1](https://github.com/felipesdreis/Orbit/pull/1)) |
| 2. Servidor + MCP + TTS no PC | pronta e validada no PC (Gemma + Kokoro reais) |
| 3. Voz no PWA | pronta e validada no PC (Chrome, microfone real, Kokoro real) |
| 4. APK | pendente |
| 5. Guia e README | pendente |

## Pendências abertas

- **Latência (medida):** mediana de 7,3 s até o 1º áudio, pior caso 12,9 s; quase tudo é o LLM. Itens 1 a 3 (prompt curto, frases longas quebradas, busca) feitos no polimento. Ainda em aberto: (4) streaming do LLM para falar a 1ª frase enquanto o resto é gerado; (5) pular a 2ª passada do LLM nas tools de resposta curta.
- **Hallucination:** o Orbit não lê o conteúdo de arquivos (as 3 tools só listam nomes) e já inventou um resumo; o prompt agora manda dizer que não consegue. Decidir se vale criar uma tool de leitura (`ler_arquivo`, `[leitura]`).
- Vulnerabilidades restantes (13, só de ferramentas de desenvolvimento, sem correção publicada): resolver só trocando o builder webpack e o Karma. Risco aceito por ora.
- `tools/GUIA_NOVA_TOOL.md` (etapa 5) ainda não existe.
- Nada foi testado em tablet real.

---

## 2026-10-19 — Dependências: Angular 21 e `npm start` só em `localhost` (`feat/dependencias-angular-21`)

**O que ficou pronto**
- Angular 19 → 20 → 21 (`ng update` em duas etapas, que não aceita pular a versão), TypeScript 5.9, build-angular 21.2.27. Ionic segue na 8.x (aceita Angular 18+). A migração para o 20 só acrescentou a config de nomes de arquivos gerados no `angular.json`; para o 21 não houve migração de código.
- **Auditoria: 40 → 13 vulnerabilidades; produção: 7 → 0.** Build sem avisos e 58 testes do app passando.
- `npm start` agora serve só em `localhost`; `npm run start:rede` abre para a rede (usar para o tablet).

**Decisões e por quê**
- **Não rodar `npm audit fix --force`:** ele sugere trocar o `karma` por 4.0.0 e o builder por `0.1002.1`, que são downgrades, não correções. O `npm audit fix` comum não muda nada.
- **Lockfile gerado com npm 11** (o do usuário): o npm 10 quebrou por um erro interno ao resolver as versões 21.
- **`npm start` em `localhost`:** o servidor de desenvolvimento aberto na rede era onde as falhas das ferramentas pesavam mais; agora a rede só é aberta de propósito.
- **As 13 que sobram ficam como risco conhecido:** vêm de duas causas só de ferramentas de desenvolvimento, sem correção publicada. `braces` (alta, intervalo `<=3.0.3` e a 3.0.3 é a última 3.x) arrasta karma, chokidar, micromatch e o servidor de desenvolvimento; `uuid` (moderada) vem do `sockjs` do servidor de desenvolvimento. `overrides` não ajudaria no `braces` e não vale o custo de manutenção para o `uuid`. Só se resolve trocando o builder (webpack) e o runner de testes (Karma), uma migração maior que fica para depois.

---

## 2026-10-19 — Polimento de voz e busca (`feat/polimento-voz-busca`)

**Motivo (do teste no PC):** a primeira busca falhou ("discurso 152" não achou `Discurso_152_...`); a voz "picota nas palavras" (no meio da frase, não entre frases); o Orbit inventou um resumo de um arquivo que ele não tem como ler; e o log mostrou `phonemizer: words count mismatch`.

**O que ficou pronto**
- **Busca:** `_`, `-`, `.` e espaço valem o mesmo, e todas as palavras da busca precisam aparecer no nome ("discurso 152" acha `Discurso_152_Armagedom_30min.docx`).
- **Voz sem engasgo:** o app baixa e decodifica cada WAV inteiro e toca pelo Web Audio, com os trechos agendados colados (sem pausa entre frases). `AudioContext` com `latencyHint: 'playback'`, liberado no toque (`Fala.preparar()`).
- **Kokoro deixa 2 núcleos livres** (`torch.set_num_threads(max(2, cpus - 2))`) para não disputar a CPU com o navegador.
- **Frases longas são quebradas** nas vírgulas (ou nas palavras) em pedaços de até ~100 caracteres: o 1º áudio só sai depois que a 1ª frase é sintetizada (uma frase de 225 caracteres levou 3,7 s).
- **Bug corrigido:** o texto para a voz apagava o `_` em vez de trocar por espaço, e `Discurso_152_Armagedom` virava `Discurso152Armagedom` (origem do aviso do `phonemizer`).
- **Prompt:** no máximo duas frases curtas; e, se não houver ferramenta para o pedido (ex.: ler o conteúdo de um arquivo), dizer que não consegue em vez de inventar.
- Testes: 25 no servidor e 52 no app (6 novos do player).

**Decisões e por quê**
- **Causa do "picotar nas palavras" não provada:** o usuário disse que é no meio das palavras, o que descarta a pausa entre frases. As hipóteses eram (a) streaming do `<audio>` (os `206 Partial Content` do log) travando quando a CPU está saturada, e (b) o Kokoro disputando CPU com o navegador. Atacamos as duas; **só o teste no PC confirma**. Se persistir, o próximo passo é tirar o Kokoro do processo do servidor (outro processo), por causa da disputa do GIL do Python com o servidor de arquivos.
- **Web Audio em vez de `<audio>`:** tocar da memória elimina o streaming como causa e dá agendamento preciso sem pausas.
- **`parar()` por "geração":** tudo o que estava em andamento (downloads, falas nativas) é invalidado de uma vez ao dormir ou ao começar de novo.
- **Pedaços de ~100 caracteres:** a síntese custa ~0,4 s fixos mais ~0,015 s por caractere, e a fala é bem mais lenta que a síntese; pedaços curtos adiantam o 1º áudio sem risco de a síntese não acompanhar.

**Retoque no mesmo dia (print do Gerenciador de Tarefas do usuário: CPU em 90% e VRAM de 8 GB cheia durante a fala):**
- "Todos os núcleos menos 2" deixava o Kokoro com muitos threads em máquinas com muitos núcleos. Agora: metade dos núcleos físicos, entre 2 e 4, com `ORBIT_TTS_THREADS` para sobrescrever (log: `Kokoro com N threads de CPU`).
- O processo do servidor passa a rodar em prioridade **abaixo do normal** (`server/processo.py`), para o Chrome e o áudio do sistema passarem na frente quando a CPU está disputada.
- A VRAM cheia (Gemma ~5,4 GB mais o navegador e o resto) não causa picote de áudio, mas pode atrasar o LLM.

**Filtro do nome:** o Chrome devolveu "hornet" para "Orbit" (e "horbit", que já era aceito). "hornet" fica a distância 3 de "orbit", longe demais para a regra automática, então entrou na lista de variantes (com testes negativos `horn`, `hornets`, `honest`). Regra: variante só entra por evidência do painel "Ouvi:", porque cada uma abre espaço para falso positivo.

**Não verificado (precisa do PC)**
- Se a picotada sumiu (em voz alta, com caixa de som, respostas longas).
- Se o próprio WAV tem o picote: tocar um arquivo de `%TEMP%\orbit_audio\` num player. Se picotar lá, o problema é da síntese e não da reprodução.
- Se o Orbit escuta a própria voz (o teste anterior foi com fone de ouvido, que não prova nada).
- Que o Kokoro com 2 núcleos livres não ficou lento demais (comparar os `TTS da frase` do log).

---

## 2026-10-19 — Validação no PC das etapas 2 (ajustes) e 3 (branch `homolog`)

**Resultado:** o usuário confirmou que a voz funcionou e que todos os comandos funcionaram (Chrome do PC, microfone real, Kokoro `pm_santa` real, Gemma4-E4B). `pytest -q` no venv: 21 passando.

**Tempos medidos (log do servidor, 13 pedidos)**

| Tipo de pedido | Pedidos | 1º áudio |
|---|---|---|
| `screenshot` | 2 | 3,8 s e 3,9 s |
| `pc_status` | 2 | 4,3 s e 8,7 s |
| conversa simples | 4 | 4,2 a 11,4 s |
| `buscar_arquivo` | 5 | 5,7 a 12,9 s |

Mediana 7,3 s; pior caso 12,9 s.

**Onde vai o tempo**
- O LLM é o gargalo: no pior caso, 9,6 s de LLM, 1,8 s de tool e 1,4 s de TTS.
- O TTS é pequeno: de 0,4 a 1,4 s para a 1ª frase (cerca de 0,4 s fixos mais ~0,015 s por caractere). Uma frase única de 225 caracteres levou 3,7 s.
- A 2ª passada do LLM (depois da tool, só para reformular) leva de 0,9 a 5,3 s.
- Resposta longa deixa o LLM lento (7,8 s numa conversa simples).
- A tool de busca leva ~1,8 s quando acha e ~4,6 s quando não acha (perto do limite de 5 s).

**Lições**
- **Rodar fora do `.venv`:** o 1º teste foi feito com o Python do sistema (o mesmo do bot do Telegram) e sem Kokoro (`Kokoro indisponível`). O aviso do pytest `import multipart` e o `sys.prefix` denunciaram. Sempre ativar o `.venv` antes.
- O `phonemizer: words count mismatch` aparece quando o Orbit lê nomes de arquivo com `_` e números (cosmético).
- A conexão do tablet (192.168.3.64) chegou ao servidor: a rede e o firewall estão certos para a etapa 4.

## 2026-10-17 — Ajustes pós-validação da etapa 2 (`feat/ajustes-pos-validacao`)

**O que ficou pronto**
- `buscar_arquivo` devolve "nome (pasta X)" em vez do caminho completo, e o prompt proíbe falar caminhos, letras de unidade e endereços. Antes o Kokoro lia `C:\Users\...` em voz alta.
- Log com o tempo de cada parte: `LLM respondeu em X s` (por rodada), `tool ... levou X s`, `resposta pronta em X s`, `TTS da frase N (M caracteres) em X s` e `1º áudio em X s`.
- Log em UTF-8 (`sys.stdout.reconfigure`): no Windows, redirecionado para arquivo, o "º" saía quebrado.
- README: status da etapa 2 e tabela de tempos preenchidos com as medições reais do PC.

**Decisões e por quê**
- **Caminho tratado na fonte (a tool), não só no prompt:** se o modelo nem recebe o `C:\Users\...`, não tem o que repetir. O prompt fica como segunda proteção.
- **Mediu-se antes de otimizar a busca:** o 10,1 s da busca pode ser da tool (limite de 5 s), do LLM ou das duas rodadas; sem número por parte, qualquer otimização seria chute.
- **Microfone riscado descartado** a pedido do usuário: o ícone continua só em `ouvindo`.

**Verificação**: `pytest -q` (21 passando; o teste da busca agora confere que o caminho completo não aparece no texto falado). **Falta**: rodar no PC para ver os tempos por parte e confirmar que o Gemma fala só nome e pasta.

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

**Verificação de ponta a ponta (Chromium real, STT simulado, servidor real com ponte e TTS falsos, áudio WAV real)** — 7 cenários passaram:
- toque acorda e liga o microfone; frase sem o nome é ignorada;
- pensando → falando (só quando o áudio começa a tocar, +359 ms) → ouvindo (+1,7 s); 2 áudios tocaram em ordem; o reconhecimento só reiniciou no instante em que o último áudio terminou;
- follow-up sem o nome aceito logo após a resposta e ignorado depois de 27 s;
- imagem aparece (640 px) e fecha com um toque;
- com o servidor derrubado aparece "Sem conexão com o PC" e, ao subir de novo, o app reconecta sozinho (< 5 s);
- console sem erros inesperados.

**Não verificado**
- Microfone e reconhecimento reais no Chrome do PC (o STT foi simulado; o falso não reproduz o timeout de silêncio nem os erros de rede do Chrome).
- Áudio audível, Kokoro real, e tempo de resposta ponta a ponta com voz (STT → LLM → TTS).
- Voz nativa de fallback (`audio: false`), expirar dos 15 min e `visibilitychange` só têm teste unitário (relógio simulado).
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
