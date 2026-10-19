# Orbit

Assistente virtual por voz para tablet Android (carinha animada, estilo Emo robot). A inteligência roda no PC via Ollama. O plano completo está em [`HANDOFF_ORBIT.md`](HANDOFF_ORBIT.md).

## Estado atual

| Etapa | Situação |
|---|---|
| 1. Carinha (PWA, sem voz) | pronta |
| 2. Servidor + MCP + TTS | pronta e validada no PC (Gemma + Kokoro reais) |
| 3. Voz no PWA | pronta e validada no PC (Chrome, microfone real, Kokoro real) |
| 4. APK | pronta e validada no tablet (Samsung, Android 11) |
| 5. Guia de novas tools | pronta (`tools/GUIA_NOVA_TOOL.md`, validada criando a tool `hora_data` só com o guia) |

## Etapa 1 — Carinha

Código em `app/src/app/face/`. O componente `<app-face>` recebe dois inputs:

- `estado`: `standby` | `ouvindo` | `pensando` | `falando`
- `emocao`: `neutro` | `feliz` | `pensando` | `curioso` | `surpreso`

Em `standby` e `pensando` o estado define a aparência; em `ouvindo` e `falando` vale a emoção. A carinha pisca e move o olhar sozinha (fora do standby).

### Como testar

```bash
cd app
npm install
npm start          # serve em http://localhost:4200 (só neste PC)
npm run start:rede # serve para a rede local (necessário para abrir no tablet)
```

1. **PC:** abra `http://localhost:4200` no Chrome.
2. **Tablet:** rode `npm run start:rede` (o `npm start` só atende este PC), e na mesma rede abra `http://<IP-do-PC>:4200` (libere a porta 4200 no firewall do Windows). Para testar a carinha, HTTP basta; o microfone (etapa 3) é que exige HTTPS.
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
| PC → tablet | `{"type":"fim"}` no fim de cada vez (depois do último `audio`): é o sinal para o tablet voltar a ouvir |

`audio` em `resposta` é um acréscimo ao plano: com `false` (Kokoro fora do ar) o tablet deve falar o `text` com a voz nativa (fallback).

### Instalar e rodar no PC (Windows)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install kokoro==0.9.4 :: TTS real; traz o torch (é grande)
python -m server           :: sobe em 0.0.0.0:8765
```

Variáveis opcionais: `ORBIT_TTS_THREADS` (núcleos de CPU do Kokoro; padrão: metade dos núcleos físicos, entre 2 e 4; se a voz ainda engasgar, tente `1` ou `2`), `ORBIT_MODELO` (padrão `Gemma4-E4B-uncensored:latest`), `ORBIT_OLLAMA_URL`, `ORBIT_PORTA`, `ORBIT_BUSCA_RAIZES` (pastas do `buscar_arquivo`). Libere a porta 8765 no firewall do Windows para o tablet alcançar o PC.

### Testar

```bash
pytest -q                                   # 21 testes; não precisam de Ollama, Kokoro nem tablet
python -m server.teste_ws "orbit como está o pc"
python -m server.teste_ws "orbit mostra a tela"
python -m server.teste_ws "orbit conta uma piada"
```

O `teste_ws` imprime cada mensagem com o tempo desde o envio e, no fim, `Tempo até o 1º áudio`.

### Tempo até o 1º áudio

Medido no PC do usuário (Gemma4-E4B-uncensored no Ollama + Kokoro `pm_santa` em CPU). O servidor também registra no log o tempo do LLM, de cada tool, de cada frase do TTS e do 1º áudio.

| Frase | Tool chamada | Resposta (s) | 1º áudio (s) |
|---|---|---|---|
| orbit como está o pc | `pc_status` | 5,37 | 6,16 |
| orbit mostra a tela | `screenshot` | 4,24 | 4,84 |
| orbit procura o arquivo HANDOFF_ORBIT | `buscar_arquivo` | 10,13 | 11,59 |
| orbit conta uma piada curta | nenhuma | 1,81 | 2,46 |

Segunda medição (13 pedidos, com a voz completa, depois dos ajustes):

| Tipo de pedido | Pedidos | 1º áudio |
|---|---|---|
| `screenshot` | 2 | 3,8 s e 3,9 s |
| `pc_status` | 2 | 4,3 s e 8,7 s |
| conversa simples | 4 | 4,2 a 11,4 s |
| `buscar_arquivo` | 5 | 5,7 a 12,9 s |

Mediana 7,3 s. O LLM responde por quase todo o tempo; o TTS leva de 0,4 a 1,4 s para a 1ª frase.

O 1º teste incluiu a carga do modelo no Ollama, então o `pc_status` pode estar inflado. A busca de arquivo é a mais lenta; o log por parte mostra se o tempo vai para o LLM, para a tool ou para o TTS.

## Etapa 3 — Voz no PWA

Código em `app/src/app/voice/` e `app/src/app/api/`.

- `orbit.service.ts`: a conversa inteira (ativação, escuta, filtro do nome, servidor, voz).
- `stt-webspeech.ts`: reconhecimento pela Web Speech API (pt-BR), reinicia sozinho enquanto estiver ativo. `stt.ts`, `fala.ts` e `api/api.ts` são as interfaces; o plugin nativo do APK (etapa 4) entra no lugar do `stt-webspeech.ts`.
- `fala-navegador.ts`: baixa e decodifica cada WAV do servidor inteiro (em paralelo com o que toca) e agenda os trechos colados um no outro pelo Web Audio, tocando da memória (sem engasgo de streaming nem pausa entre frases). Com a voz nativa do navegador (`falarNativo`) quando o servidor avisa `audio: false`.
- `ativador.ts`: o que acorda o Orbit. Hoje só o toque na carinha; a wake word entra aqui na v2.
- `nome.ts`: filtro do nome "Orbit" (aceita `órbita`, `orbite`, `or bit`, `obit`... por palavra inteira).
- `api/api-websocket.ts`: conexão com o servidor; reconecta sozinha a cada 2 s.

### Como funciona

1. **Standby:** carinha dormindo, microfone desligado. Tocar na carinha acorda (tocar nos botões do painel de teste não acorda).
2. **Ativo:** o microfone ouve e a tela fica acesa (wake lock). Sem nenhuma fala por **15 min**, volta ao standby; toda fala reconhecida renova o prazo.
3. **Filtro:** só frases com "Orbit" são enviadas ao PC. Depois de cada resposta há uma janela de **25 s** em que o nome não é exigido.
4. **Half-duplex:** o microfone para ao enviar a fala e só volta depois que o servidor manda `fim` e o último áudio termina, para o Orbit não ouvir a própria voz.
5. O rosto fica em "pensando" até o som começar e só então passa a "falando".

### Como testar (Chrome do PC)

```bash
python -m server            # raiz do projeto, venv ativo; sobe em :8765
cd app && npm start         # :4200
```

1. Abra `http://localhost:4200` no Chrome e **toque na carinha**. O Chrome pede o microfone: permita.
2. Diga "Orbit, como está o PC?". A carinha deve ouvir, pensar, falar e voltar a ouvir. O painel de teste (⚙) mostra "Ouvi: … — enviado/ignorado".
3. Diga algo **sem** "Orbit" logo depois da resposta (follow-up): deve ser enviado. Espere mais de 25 s e repita: deve ser ignorado.
4. Diga "Orbit, mostra a tela": a imagem aparece sobre a carinha; toque nela para fechar.
5. Pare o servidor e fale com o nome: aparece "Sem conexão com o PC".

Servidor em outro endereço: `http://localhost:4200/?pc=192.168.0.10` (o endereço fica salvo).

**Sempre ative o `.venv` antes** (`.venv\Scripts\activate`). Fora dele, o servidor roda no Python do sistema (o do bot do Telegram) e o Kokoro não é encontrado.

**Atenção:** no Chrome, o reconhecimento de voz usa o serviço do Google (precisa de internet). No tablet via `http://<IP>` o microfone é bloqueado (exige HTTPS); o APK da etapa 4 resolve com o plugin nativo.

Testes automáticos: `cd app && CHROME_BIN=<caminho do chrome> npx ng test --watch=false`.

## Etapa 4 — APK (tablet Android)

O mesmo app Angular roda no tablet dentro do Capacitor 7. A diferença está em dois lugares: o reconhecimento de voz é o **nativo do Android** (`stt-nativo.ts`, plugin `@capacitor-community/speech-recognition`) em vez da Web Speech API, e o endereço do PC é informado na tela (campo **PC** do painel ⚙), porque no tablet não existe o `?pc=` da URL.

### Compilar o APK (no PC)

Pré-requisitos (os mesmos do Locked-In): JDK 21 em `C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot` e o Android SDK em `C:\Android` com as licenças aceitas (o Gradle baixa sozinho a plataforma `android-35` se faltar). Caminhos diferentes: edite as duas linhas `set` no topo do `build-apk.bat`.

```bat
build-apk.bat
```

Pergunta o nome do APK (Enter = `orbit`) e gera `app\android\app\build\outputs\apk\debug\<nome>.apk`. A 1ª vez baixa o Gradle e as dependências (alguns minutos, precisa de internet). Copie o APK para o tablet e instale (permita "fontes desconhecidas").

### Primeiro uso no tablet

1. No PC: `python -m server` (porta 8765 liberada no firewall; PC e tablet na mesma rede; de preferência reserve um IP fixo para o PC no roteador).
2. No tablet: abra o Orbit, abra o painel **⚙**, escreva o IP do PC no campo **PC** (ex.: `192.168.3.10`) e toque em **Conectar**. O painel mostra "conectado". O endereço fica salvo.
3. Toque na carinha: o Android pede o microfone (permita). Diga "Orbit, como está o PC?".

No tablet, o reconhecimento de voz usa o serviço de voz do Android (normalmente o app **Google**): ele precisa estar instalado e atualizado, e o **Android System WebView** também. Sem internet, instale o pacote de voz offline em português (Configurações do Google → Voz → Reconhecimento offline).

### Se algo não funcionar

| Sintoma | O que olhar |
|---|---|
| "Sem conexão com o PC" | IP no campo PC; servidor rodando; firewall da porta 8765; mesma rede |
| "Este aparelho não tem reconhecimento de voz" | instalar/atualizar o app Google |
| "Microfone bloqueado" | Configurações do Android → Apps → Orbit → Permissões → Microfone |
| "precisa de internet" | baixar o pacote de voz offline em português |
| Um "bip" a cada reinício da escuta | me avise: dá para silenciar o fluxo de notificação durante a janela ativa |
| Sai do app e o Orbit para de ouvir | é proposital: em segundo plano o Android não deixa o app usar o microfone |

### Detalhes do projeto Android

- `app/capacitor.config.ts`: a página é servida em `http://localhost` (`androidScheme: 'http'`), e não em `https`, para o `ws://<IP-do-PC>` não ser bloqueado como conteúdo misto. `localhost` continua sendo um contexto seguro (microfone, Web Audio e wake lock funcionam).
- `AndroidManifest.xml`: `usesCleartextTraffic="true"`, porque o Android 9+ bloqueia tráfego sem HTTPS para endereços que não sejam `localhost`.
- Ícone e tela de abertura: gerados a partir de `app/assets/` (já estão em `res/`). Para refazer: `cd app && npx @capacitor/assets generate --android`.
- Depois de mexer no código do app: `cd app && npm run build:android` (faz o `ng build` e o `cap sync`).

## Etapa 5 — Guia para criar tools

O guia completo está em [`tools/GUIA_NOVA_TOOL.md`](tools/GUIA_NOVA_TOOL.md): receita mínima, regras para o modelo pequeno acertar, convenção `[leitura]`/`[escrita]`, como testar e checklist.

Resumo: criar uma tool é soltar um `.py` em `tools/` com `registrar(mcp)` e `@mcp.tool()`. Não há lista para atualizar.

```text
python -m server.testar_tool --listar
python -m server.testar_tool hora_data "{}"
pytest -q
```

- `server/testar_tool.py` chama uma tool isolada (sem tablet e sem LLM) e mostra retorno, tempo e se seria falado, exibido como imagem ou tratado como erro.
- `tests/test_tools.py` reprova automaticamente tool sem `[leitura]`/`[escrita]`, com descrição de mais de uma linha, com mais de 2 parâmetros ou com nome fora do padrão.
- `tools/hora_data.py` (hora e data em português falado) é a tool de exemplo criada seguindo só o guia.
