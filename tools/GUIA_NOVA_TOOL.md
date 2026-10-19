# Guia: como criar uma tool nova para o Orbit

Uma **tool** é uma função Python que o modelo (o Gemma, no Ollama) pode chamar para fazer algo no PC: ver a hora, achar um arquivo, tirar um print. O Orbit as serve por **MCP** (Model Context Protocol), então as mesmas tools funcionam em qualquer cliente MCP (Claude Code, Hermes etc.).

**Criar uma tool = soltar um `.py` nesta pasta (`tools/`).** O `tools/server.py` descobre sozinho; não existe lista para atualizar.

---

## 1. Receita mínima

Crie `tools/minha_tool.py`:

```python
"""Tool minha_tool: uma frase dizendo o que ela faz."""


def minha_tool_logica(texto: str) -> str:
    """A lógica de verdade, em função pura: fácil de testar sem MCP."""
    return f"Você disse {texto}."


def registrar(mcp) -> None:
    @mcp.tool()
    def minha_tool(texto: str) -> str:
        """[leitura] Use quando o usuário pedir para repetir uma frase."""
        return minha_tool_logica(texto)
```

O que o servidor exige do arquivo:

| Regra | Detalhe |
|---|---|
| Fica em `tools/` | e não se chama `server.py` nem começa com `_` (esses são ignorados) |
| Tem a função `registrar(mcp)` | é por ela que a tool entra; sem ela o arquivo é ignorado |
| Cada tool usa `@mcp.tool()` | dentro de `registrar`; um arquivo pode registrar várias tools |
| Tem **type hints** | o tipo de cada parâmetro e do retorno vira o esquema que o modelo vê |
| Tem **docstring** | a docstring é a descrição que o modelo lê (ver seção 2) |

Detalhes que costumam dar problema:

- **Nunca use `print()`**: o `stdout` é do protocolo MCP, e um `print` o corrompe. Para depurar, escreva no `stderr` (`print(..., file=sys.stderr)`).
- **Arquivo com erro de sintaxe ou de import não derruba o servidor**: ele é pulado, e o motivo aparece no terminal em `[orbit-tools] falha ao carregar minha_tool.py: ...`. Se a tool não aparece, olhe esse log primeiro.
- **Dependência nova** (um pacote pip): instale no `.venv` do Orbit e acrescente em `requirements.txt`. Importações pesadas ou que podem falhar (como `PIL.ImageGrab`) vão **dentro da função**, para uma falha virar mensagem de erro em vez de derrubar o módulo.
- **Separe a lógica do registro**, como no exemplo (`minha_tool_logica`): a lógica fica testável com um `assert` simples. O nome da função de lógica é livre (`pc_status.py` usa `coletar` e `formatar`); a regra dos 2 parâmetros (seção 2) vale só para a função decorada com `@mcp.tool()`, não para a lógica.
- **Se a lógica depende do ambiente** (a hora, o disco, a rede), receba esse valor como parâmetro opcional, para os testes poderem fixá-lo sem simulação: `def hora_logica(agora: datetime | None = None)`, e o `registrar` chama sem argumento.
- **Nunca dependa do `locale` do sistema para textos falados**: o PC pode estar em outro idioma. Nomes de mês, de dia da semana e coisas assim vêm de tabelas fixas em português no próprio código.

---

## 2. Regras para um modelo pequeno acertar

O modelo é pequeno (Gemma 4B) e decide sozinho qual tool chamar, lendo só o **nome** e a **descrição**. Cada regra abaixo existe por causa disso.

**Nome**: verbo e objeto, em português, minúsculas, com `_` e sem acento: `hora_data`, `buscar_arquivo`, `pc_status`. Curto e sem ambiguidade com outra tool.

**Descrição (a docstring)**: **uma linha só** (até 200 caracteres), dizendo **quando usar**, com as palavras que a pessoa realmente diria. Escreva para o modelo, não para um programador:

```text
Bom:  [leitura] Use quando perguntarem a temperatura da CPU, se o PC está esquentando ou quente demais.
Ruim: [leitura] Lê o sensor de temperatura via WMI e retorna o valor em graus Celsius como float.
```

**Poucos parâmetros**: de 0 a 2, com tipos simples (`str`, `int`, `bool`) e nomes que se explicam sozinhos. Cada parâmetro é uma chance de o modelo errar. Se a tool pode funcionar sem parâmetro, deixe sem.

**Retorno curto e falável**: o texto devolvido é **lido em voz alta** e também volta para o modelo. Então:
- 1 a 3 frases, mirando uns 300 caracteres (é uma meta, não um limite duro; o `testar_tool` mostra o tamanho);
- números e unidades como se fala: "14 por cento", "3 gigas", não "14%" nem "3 GB";
- horas e datas como se fala: "meia-noite" e "meio-dia" (e "meia-noite e 7", não "0 e 7"), "uma e 20" para 1h20, sem zero à esquerda ("9 e 5", não "9 e 05"), dia 1 do mês como "primeiro", mês por extenso ("19 de outubro de 2026");
- sem markdown, sem listas, sem tabelas, sem emojis;
- sem caminhos completos (`C:\Users\...`) nem endereços da internet: diga o nome e a pasta.
- Dica: leia o retorno em voz alta antes de commitar.

**Erros**: devolva um texto começando com `ERRO:` e uma frase curta ("ERRO: não consegui capturar a tela."). **Não levante exceção**: o modelo receberia uma mensagem confusa. O modelo explica o erro em voz alta a partir desse texto.

**Poucas tools**: cada tool a mais piora a escolha do modelo pequeno. Se duas descrições se parecem, junte as tools ou reescreva as descrições para ficarem bem distintas. Mantenha o total em torno de 6 a 8.

**Sem estado**: cada chamada é independente. Não conte com lembrar do que a chamada anterior fez.

---

## 3. Convenção de risco: `[leitura]` ou `[escrita]`

A docstring **começa** com uma destas marcas:

| Marca | Quando |
|---|---|
| `[leitura]` | só consulta: não altera nada no PC (hora, status, buscar arquivo, tirar print) |
| `[escrita]` | altera algo: cria, move ou apaga arquivos, muda configuração, abre ou fecha programas, envia mensagens, reinicia o que for |

A v1 do Orbit só tem tools `[leitura]`. A v2 usará essa marca para **pedir confirmação por voz** antes de executar as `[escrita]`. Em dúvida, marque `[escrita]`.

Um teste automático (`test_toda_tool_segue_a_convencao_do_guia`) reprova a tool sem a marca, com descrição de mais de uma linha, com mais de 2 parâmetros ou com nome fora do padrão.

---

## 4. Como testar

### 4.1. Isolada: sem tablet e sem LLM

Todos os comandos deste guia rodam **na raiz do projeto**, com o `.venv` do Orbit ativo:

| Sistema | Ativar o `.venv` |
|---|---|
| Windows (`cmd`) | `.venv\Scripts\activate` |
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Linux / macOS | `. .venv/bin/activate` |

Depois:

```text
python -m server.testar_tool --listar
python -m server.testar_tool minha_tool "{\"texto\": \"oi\"}"
python -m server.testar_tool hora_data "{}"
```

- `--listar` mostra todas as tools e as descrições **exatamente como o modelo as vê**. Sua tool precisa aparecer aqui; se não aparecer, veja a linha `[orbit-tools] falha ao carregar ...` no terminal.
- A chamada isolada manda os argumentos em JSON e mostra o retorno, o tempo, e se ele seria falado (com o tamanho), mostrado como imagem ou tratado como erro. **Tool sem parâmetros: passe `"{}"`.**
- As linhas `INFO Processing request of type ...` misturadas na saída são normais (vêm da biblioteca MCP). O que importa é o bloco `Retorno:` e a linha com a seta `→`.
- Aspas no JSON: no `cmd` e no bash, `"{\"texto\": \"oi\"}"` funciona; no PowerShell e no bash, também `'{"texto": "oi"}'` (aspas simples por fora).

### 4.2. Testes automáticos

Crie um arquivo **novo** `tests/test_<sua_tool>.py` (não edite o `tests/test_tools.py`). A pasta `tools/` já está no caminho de importação dos testes (`tests/conftest.py`), então basta `import minha_tool`:

```python
from datetime import datetime

import minha_tool


def test_formato():
    assert minha_tool.minha_tool_logica("oi") == "Você disse oi."
```

Teste a **função de lógica**, com valores fixos (é por isso que a lógica recebe a hora ou o disco como parâmetro opcional, seção 1). Cubra os casos de borda do que a tool fala (meia-noite, zero, lista vazia). Veja `tests/test_hora_data.py` e `tests/test_tools.py` como modelo. Depois:

```text
pytest -q
```

Isso também roda o teste de convenção da seção 3 sobre a sua tool, sem você escrever nada.

### 4.3. Com o Ollama (o modelo escolhendo a tool de verdade)

Este passo precisa do Ollama rodando com o modelo do Orbit. Sem ele, pule e anote que pulou: as seções 4.1 e 4.2 já provam que a tool funciona, e só este passo prova que o **modelo** a escolhe.

```text
python -m server
```

No log de subida, a linha `orbit.servidor: tools MCP: [...]` deve listar a sua tool. Em outro terminal:

```text
python -m server.teste_ws "orbit <uma frase natural que pede a tool>"
```

No log do servidor, procure `orbit.ponte: tool minha_tool({...}) levou X s`: é a prova de que o modelo a escolheu. Teste **três frases diferentes** que pedem a mesma coisa. Se o modelo não chamar a tool, ou chamar com argumento errado, **reescreva a descrição** (seção 2) antes de pensar em outra coisa. Se ele chamar a tool quando não devia, a descrição está larga demais.

### 4.4. Em outro cliente MCP (Claude Code, Hermes)

O servidor é um MCP padrão por stdio. Aponte o cliente para o comando:

```text
C:\caminho\Orbit\.venv\Scripts\python.exe C:\caminho\Orbit\tools\server.py
```

---

## 5. Devolver arquivos (o padrão do `screenshot`)

O modelo não "vê" imagens, e o texto de retorno é falado em voz alta. Para mostrar uma **imagem** no tablet:

1. Salve o arquivo numa pasta temporária, com nome único (por exemplo, com a data e a hora): `Path(tempfile.gettempdir()) / "orbit_minha_tool" / "arquivo_20261019_153000.png"`.
2. Devolva **só o caminho absoluto** como o retorno inteiro da tool: `return str(caminho)`. Nada de frase junto.

O servidor reconhece um caminho absoluto terminado em `.png`, `.jpg` ou `.jpeg` que existe no disco, registra o arquivo, manda ao tablet a mensagem `imagem` (que aparece sobre a carinha) e entrega ao modelo apenas "Imagem capturada; já está sendo mostrada no tablet.". Por isso o modelo só comenta o que fez, sem falar o caminho. Veja `screenshot.py` e a função `capturar`.

Limites de hoje: só **imagens** são exibidas. Outros tipos (PDF, áudio, texto) ainda não têm tela no tablet. Quando falhar, devolva `ERRO: ...` em vez do caminho.

---

## 6. Checklist antes de commitar

- [ ] O arquivo está em `tools/`, tem `registrar(mcp)` e `@mcp.tool()` com type hints.
- [ ] A docstring é uma linha, começa com `[leitura]` ou `[escrita]` e diz quando usar.
- [ ] No máximo 2 parâmetros; nome em português, minúsculo, sem acento.
- [ ] O retorno é curto e falável; erros começam com `ERRO:`; nenhum `print()`.
- [ ] `python -m server.testar_tool --listar` mostra a tool, e a chamada isolada devolve o esperado.
- [ ] `tests/test_<sua_tool>.py` existe, testa a lógica pura com valores fixos, e `pytest -q` passa.
- [ ] Textos falados não dependem do `locale` do sistema.
- [ ] Com o Ollama, três frases diferentes fazem o modelo chamar a tool (`tool ... levou` no log). Sem o Ollama no momento, anote que pulou.
- [ ] Se usou uma biblioteca nova, ela está em `requirements.txt`.
