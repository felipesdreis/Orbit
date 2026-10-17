# Orbit

Assistente virtual por voz para tablet Android (carinha animada, estilo Emo robot). A inteligência roda no PC via Ollama. O plano completo está em [`HANDOFF_ORBIT.md`](HANDOFF_ORBIT.md).

## Estado atual

| Etapa | Situação |
|---|---|
| 1. Carinha (PWA, sem voz) | pronta |
| 2. Servidor + MCP + TTS | pendente |
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
