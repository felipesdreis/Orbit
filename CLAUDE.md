# Orbit

Assistente virtual por voz para tablet Android (carinha animada, estilo Emo robot), com a inteligência rodando no PC via Ollama.

## Antes de qualquer coisa

**Leia `HANDOFF_ORBIT.md` por inteiro antes de começar.** Ele é a fonte de verdade das decisões, da arquitetura, das etapas e dos riscos. Não reabra as decisões fechadas; se algo for inviável, pare e reporte com evidência.

Comece pela **etapa 1** do handoff, salvo instrução em contrário do usuário.

## Regras

- Responder em pt-BR.
- O usuário acompanha pelo celular: ao fim de cada etapa, relatar o que ficou pronto e como testar.
- Confirmar antes de ações destrutivas ou fora desta pasta.
- Nunca ler por inteiro o `tools/.env` de `claude_session_godmode` (tem tokens); usar `grep "^CHAVE="` para uma variável específica.
