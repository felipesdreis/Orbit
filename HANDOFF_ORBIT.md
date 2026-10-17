# HANDOFF — Projeto Orbit

Assistente virtual por voz que roda num tablet Android (estilo Emo robot: carinha animada na tela). O tablet cuida de microfone, tela e voz. A inteligência roda no PC do usuário (Ollama).

- **Pasta do projeto:** `C:\Users\Felipe Reis\Documents\GitHub\Orbit` (criar; ao lado do `Locked-In`)
- **Idioma:** pt-BR em tudo (UI, falas, comentários, docs)
- **Status:** planejamento fechado. Nada foi criado ainda. Este documento é a fonte de verdade das decisões.

> Não reabra as decisões da seção 2. Se algo for inviável, pare e reporte o motivo com evidência.

---

## 1. Visão

O usuário toca na tela do tablet, o Orbit acorda e fica ouvindo por um tempo. Quando alguém diz uma frase com "Orbit", o texto vai ao PC, o LLM responde (podendo chamar ferramentas do PC), e o tablet fala a resposta enquanto a carinha muda de expressão.

## 2. Decisões fechadas

| Tema | Decisão |
|---|---|
| Nome | **Orbit** |
| Front | **Ionic + Angular + Capacitor**. Um código gera PWA e APK. React Native descartado |
| STT | **SpeechRecognizer nativo do Android** (plugin `@capacitor-community/speech-recognition`). No navegador cai na Web Speech API. Só **texto** vai ao PC |
| TTS | **Kokoro-82M, voz `pm_santa`** (pt-BR), gerado **no PC em CPU** (não ocupa VRAM) e enviado ao tablet como áudio. O tablet mantém `falar(texto)` com a voz nativa do Android como **fallback** (servidor fora do ar / erro do Kokoro). Voz escolhida pelo usuário após testar no TUI `claude_session_godmode\tools\kokoro_vozes.py` |
| LLM | **Ollama no PC**, modelo padrão `Gemma4-E4B-uncensored` (usuário já validou tool calling). Esta escolha vale para o Orbit mesmo o `CLAUDE.md` pedindo modelos oficiais |
| Ferramentas | Via **MCP** (SDK oficial `mcp`, FastMCP, Python). v1 tem só 3 tools, todas de leitura |
| Roteamento | **Tool calling do Ollama** (o modelo decide). Manter a lista curta |
| Ativação v1 | **Sem wake word.** Toque na tela acorda; ativo por 15 min com timer que renova a cada fala; depois volta ao standby |
| Filtro de escuta | Só responde se a frase contiver "Orbit" (comparação tolerante, ver 5.2) |
| Wake word futura | **openWakeWord** ("Ei Orbit"). Fora da v1, mas a ativação deve ser plugável (ver 5.1) |
| Build do APK | Adaptar `C:\Users\Felipe Reis\Documents\GitHub\Locked-In\build-apk.bat` |

## 3. Fora de escopo da v1

- Wake word / escuta com tela apagada
- Tools que alteram estado (reiniciar bot, mover/deletar arquivos, mexer em config)
- Whisper no PC, clonagem de voz, XTTS
- Publicação em loja, assinatura de release (basta APK debug)
- iOS

## 4. Arquitetura

```
Tablet (APK Ionic / PWA)                         PC (Windows)
┌─────────────────────────────┐              ┌──────────────────────────────┐
│ ativador (toque na tela)    │              │ server/ (FastAPI)            │
│ SpeechRecognizer → texto    │──WebSocket──▶│  - ponte Ollama <-> MCP      │
│ filtro "Orbit"              │              │  - extrai [emoção] da resposta│
│ carinha animada (CSS/SVG)   │◀─────────────│  - serve arquivos (screenshot)│
│ falar(texto) / mostra imagem│  texto+emoção│ tools/ (servidor MCP, Python)│
└─────────────────────────────┘              │  pc_status, buscar_arquivo,  │
                                             │  screenshot                  │
                                             │ Ollama (localhost:11434)     │
                                             └──────────────────────────────┘
```

### Estrutura de pastas

```
Orbit/
├── app/                     Ionic + Angular + Capacitor
│   └── src/app/
│       ├── face/            carinha e estados visuais
│       ├── voice/           stt.service, tts.service (falar), ativador
│       └── api/             cliente WebSocket
├── server/                  FastAPI (WebSocket /ws, GET /files/<id>)
├── tools/                   servidor MCP (descobre tools/*.py sozinho)
│   ├── server.py
│   ├── pc_status.py
│   ├── buscar_arquivo.py
│   ├── screenshot.py
│   └── GUIA_NOVA_TOOL.md
├── build-apk.bat            adaptado do Locked-In
└── README.md
```

### Protocolo WebSocket (mínimo)

- Cliente → servidor: `{"type":"fala","text":"orbit como está o pc"}`
- Servidor → cliente: `{"type":"resposta","text":"...","emocao":"feliz"}`
- Servidor → cliente (imagem): `{"type":"imagem","url":"http://<ip-pc>:<porta>/files/<id>"}`
- Servidor → cliente (voz): `{"type":"audio","url":"http://<ip-pc>:<porta>/files/<id>.wav"}` — WAV 24 kHz gerado pelo Kokoro. O Kokoro devolve a fala em **pedaços por frase**: gerar e enviar frase a frase (um `audio` por frase, em ordem) para o Orbit começar a falar antes de terminar de sintetizar. O tablet enfileira e toca em sequência.
- Servidor → cliente (opcional): `{"type":"pensando"}` assim que recebe a fala, para a carinha reagir rápido

**Emoção:** instruir o modelo no prompt de sistema a iniciar toda resposta com uma tag (`[neutro]`, `[feliz]`, `[pensando]`, `[curioso]`, `[surpreso]`). O servidor remove a tag do texto falado e envia em `emocao`. Se a tag faltar, usar `neutro`.

## 5. Comportamento do app

### 5.1 Estados e ativador plugável

```
STANDBY  (carinha dormindo, tela escurecida, microfone desligado)
   │ toque
   ▼
ATIVO    (ouvindo, wake lock ligado, timer de 15 min renovado a cada fala)
   │ 15 min sem fala
   ▼
STANDBY
```

O ativador deve ficar atrás de uma interface simples, por exemplo `Ativador { onAcordar(cb) }`. A v1 tem só a implementação por toque. A v2 acrescenta openWakeWord sem mexer no resto.

### 5.2 Escuta

- **Loop de reinício:** o SpeechRecognizer encerra sozinho após silêncio. Reiniciar enquanto estiver ATIVO. Em alguns aparelhos cada reinício faz um "bip": se acontecer, silenciar o stream de notificação durante a janela ativa e restaurar ao sair.
- **Half-duplex:** parar de ouvir **enquanto o Orbit fala** e voltar quando terminar. Sem isso ele responde à própria voz.
- **Filtro de nome:** só enviar ao PC se a transcrição contiver "Orbit". Aceitar variantes comuns do STT em pt-BR (`órbita`, `orbite`, `or bit`, `obit`...) por lista de variantes ou distância de edição pequena. Não usar só `"orbit" in texto`.
- **Follow-up:** depois de cada resposta, abrir uma janela de ~20–30 s em que o nome **não** é exigido. Fora dela, volta a exigir.
- **Timer:** os 15 min renovam a cada fala reconhecida.
- **Privacidade:** verificar se o reconhecimento está offline ou indo para a nuvem do Google (ver seção 9).

## 6. Ferramentas (MCP)

### v1 (somente leitura)

| Tool | Reaproveita | Retorno |
|---|---|---|
| `pc_status` | lógica de `claude_session_godmode\tools\pc_status.py` | texto curto (CPU, RAM, disco, uptime) |
| `buscar_arquivo` | lógica de `...\tools\buscar_arquivo.py` | até ~5 caminhos, texto curto |
| `screenshot` | lógica de `...\tools\screenshot.py` | **caminho do PNG** (ver abaixo) |

Os scripts originais usam `psutil`, `Pillow` e `argparse`. Extrair a lógica para funções e **não** chamar `screenshot.py` nem `telegram_send_photo.py` com efeitos colaterais (a v1 do Orbit não envia nada ao Telegram).

### Screenshot

O modelo não "vê" a imagem. A tool devolve o caminho, o servidor registra o arquivo com um id, serve em `/files/<id>` e manda `{"type":"imagem","url":...}` ao tablet, que exibe. O modelo só responde algo como "mostrando a tela".

### Padrão aberto para novas tools

Referência no próprio ambiente: `claude_session_godmode\tools\mcp_web_extract.py` (servidor MCP stdio com o SDK oficial).

- `tools/server.py` **descobre automaticamente** todo `tools/*.py` que registre tools. Criar uma ferramenta = soltar um `.py` na pasta, sem registrar em outro lugar.
- Escrever `tools/GUIA_NOVA_TOOL.md` (pt-BR) com:
  1. Template mínimo (`@mcp.tool()`, type hints, docstring).
  2. Regras para o modelo pequeno acertar: nome claro, descrição de uma linha dizendo **quando** usar, poucos parâmetros, retorno curto (vai ser falado em voz alta).
  3. Convenção de risco no docstring: `[leitura]` ou `[escrita]`. A v2 usará isso para exigir confirmação por voz nas de escrita.
  4. Como testar uma tool isolada (sem tablet nem LLM) e depois com o Ollama.
  5. Como devolver arquivos (padrão do screenshot).
- As mesmas tools devem funcionar em qualquer cliente MCP (Claude Code, Hermes), por serem MCP padrão.

## 7. Ambiente já existente (não instalar nada novo sem necessidade)

| Item | Estado |
|---|---|
| Node 24.16 / npm 11.13 | instalado |
| Ionic CLI 7.2 | instalado |
| JDK 21 | instalado (`C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot`) |
| Android SDK | em `C:\Android` (o `ANDROID_HOME` global está vazio; o `.bat` do Locked-In seta só durante a execução. **Confirmar que a pasta existe antes de assumir**) |
| Ollama | rodando no PC; modelo `Gemma4-E4B-uncensored:latest` instalado |
| Kokoro (TTS) | já testado no PC: venv `claude_session_godmode\tools\.venv-kokoro` (criado com `--system-site-packages`, pacote `kokoro` 0.9.4) e modelo já baixado no cache do Hugging Face. Código de referência: `claude_session_godmode\tools\kokoro_vozes.py` (funções `carregar()` e `sintetizar()`: `KPipeline(lang_code="p", repo_id="hexgrad/Kokoro-82M", device="cpu")`, voz `pm_santa`, 24 kHz). **O Orbit deve ter o próprio venv** (não instalar no Python do sistema, que o bot do Telegram usa) |
| Bot do Telegram | `C:\botScript\main.py` roda no Python do sistema e usa Whisper em GPU (agora descarrega após 5 min ocioso). Não mexer nele para o Orbit |
| GPU | RTX 4060 8 GB (o Gemma usa ~5,4 GB; manter TTS/extras em CPU) |
| Tablet | Android, Termux com SSH na porta 8022, 3,6 GB RAM, só CPU. **Versão do Android desconhecida: verificar** |

**Segredos:** `claude_session_godmode\tools\.env` tem tokens. Nunca ler o arquivo inteiro; use `grep "^CHAVE="` para uma variável específica. O Orbit não precisa de nenhum desses segredos na v1.

### Build do APK

Copiar `build-apk.bat` do Locked-In e ajustar: título, nome padrão do APK, e conferir que o `package.json` do Orbit tenha o script `build:android`. Fluxo: `capacitor-assets generate --android` → `npm run build:android` → `gradlew.bat assembleDebug` → renomear. Instalação no tablet: `adb install` ou cópia manual (perguntar ao usuário como instalou o Locked-In).

## 8. Etapas e critérios de pronto

1. **Carinha (PWA, sem voz):** estados standby/ouvindo/pensando/falando e emoções, alternáveis por botões de teste. *Pronto:* animações fluidas no Chrome do PC e no tablet.
2. **Servidor + MCP + TTS no PC:** FastAPI, ponte Ollama↔MCP, 3 tools, síntese com Kokoro `pm_santa` em CPU. *Pronto:* uma frase de texto enviada por WebSocket de teste chama a tool certa e volta resposta com emoção **e áudio WAV por frase**; medir e registrar no README o tempo até o 1º áudio.
3. **Voz no PWA:** STT (Web Speech API), reprodução da fila de áudios do servidor (com `falar()` nativo como fallback), ativação por toque, loop de escuta, half-duplex (parar de ouvir enquanto toca o áudio), filtro de nome, timer, follow-up. *Pronto:* conversa por voz completa no Chrome do PC.
4. **APK:** Capacitor, plugin nativo de STT, `build-apk.bat`. *Pronto:* APK instalado no tablet reproduz o fluxo da etapa 3 pela rede local.
5. **Guia e README:** `GUIA_NOVA_TOOL.md` validado criando uma tool de exemplo (ex.: `hora_data`) seguindo só o guia.

## 9. Riscos e pontos a verificar

- **Rede no APK:** o Capacitor serve a página em `https://localhost`; conectar a `ws://IP-do-PC` pode ser bloqueado como conteúdo misto. Testar cedo. Soluções possíveis: `server.androidScheme: "http"` e `allowMixedContent` no `capacitor.config`, ou HTTPS/WSS no PC.
- **Rede no PC:** liberar a porta do servidor no firewall do Windows; sugerir reservar IP fixo para o PC no roteador. PC e tablet precisam estar na mesma rede.
- **Microfone no PWA:** exige HTTPS (em `localhost` no PC funciona). No tablet via IP http será bloqueado: para testar o PWA lá, usar HTTPS (ex.: mkcert/Tailscale) ou ir direto ao APK.
- **STT offline:** conferir se o pt-BR offline está instalado no tablet (Configurações → Idioma → Entrada de voz → Reconhecimento offline). Se não estiver, o áudio pode ir à nuvem do Google; avisar o usuário.
- **Microfone único:** quando a wake word entrar (v2), só um recorder por vez no Android. O fluxo será: detector solta o mic → STT capta → detector volta.
- **Tool calling em modelo pequeno:** manter poucas tools; se errar chamadas, reforçar o prompt de sistema e as descrições, antes de pensar em trocar de abordagem.
- **Kokoro em CPU:** a latência da primeira frase é o ponto a medir (a síntese de ~4 s de fala funcionou no teste, mas o tempo exato não foi cronometrado). Carregar o modelo **uma vez** na subida do servidor (não por requisição) e gerar frase a frase. Não rodar o Kokoro em GPU: a VRAM de 8 GB já é do Gemma (~5,4 GB).
- **Latência:** medir STT→LLM→TTS ponta a ponta. A mensagem `pensando` existe para a carinha reagir antes da resposta chegar.

## 10. Regras de trabalho para o agente

- Idioma: pt-BR (código, identificadores técnicos em inglês quando convencional).
- Fazer o mínimo que atenda ao critério de cada etapa (ponytail): sem abstrações sem uso, sem config para valor que não muda. A única abstração pedida é a do ativador e a do `falar()`.
- Cada etapa deixa uma verificação executável (teste simples ou roteiro manual no README).
- Ações destrutivas ou fora da pasta do projeto: confirmar com o usuário antes.
- O usuário acompanha pelo celular: relatar ao fim de cada etapa o que ficou pronto e como ele pode testar.
