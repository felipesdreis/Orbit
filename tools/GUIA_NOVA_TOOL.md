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
- **Separe a lógica do registro**, como no exemplo (`minha_tool_logica`): a lógica fica testável com um `assert` simples. Veja `pc_status.py` (`coletar` e `formatar`) como modelo.

---

## 2. Regras para um modelo pequeno acertar

O modelo é pequeno (Gemma 4B) e decide sozinho qual tool chamar, lendo só o **nome** e a **descrição**. Cada regra abaixo existe por causa disso.

**Nome**: verbo e objeto, em português, minúsculas, com `_` e sem acento: `hora_data`, `buscar_arquivo`, `pc_status`. Curto e sem ambiguidade com outra tool.

**Descrição (a docstring)**: **uma linha só** (até 200 caracteres), dizendo **quando usar**, com as palavras que a pessoa realmente diria. Escreva para o modelo, não para um programador:

```text
Bom:  [leitura] Use quando perguntarem que horas são, que dia é hoje ou a data.
Ruim: [leitura] Retorna um objeto datetime formatado de acordo com o fuso local.
```

**Poucos parâmetros**: de 0 a 2, com tipos simples (`str`, `int`, `bool`) e nomes que se explicam sozinhos. Cada parâmetro é uma chance de o modelo errar. Se a tool pode funcionar sem parâmetro, deixe sem.

**Retorno curto e falável**: o texto devolvido é **lido em voz alta** e também volta para o modelo. Então:
- 1 a 3 frases, até uns 300 caracteres;
- números e unidades como se fala: "14 por cento", "3 gigas", não "14%" nem "3 GB";
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

Com o `.venv` ativo, na raiz do projeto:

```bat
python -m server.testar_tool --listar
python -m server.testar_tool minha_tool "{\"texto\": \"oi\"}"
```

- `--listar` mostra todas as tools e as descrições **exatamente como o modelo as vê**. Sua tool precisa aparecer aqui; se não aparecer, veja a linha `[orbit-tools] falha ao carregar ...` no terminal.
- A segunda forma chama a tool com os argumentos em JSON e mostra o retorno, o tempo, e se ele seria falado, mostrado como imagem ou tratado como erro.

No PowerShell, as aspas dentro do JSON pedem cuidado: use `'{"texto": "oi"}'` (aspas simples por fora). No `cmd`, use `"{\"texto\": \"oi\"}"`.

### 4.2. Testes automáticos

Escreva testes da lógica pura em `tests/` (veja `tests/test_tools.py`, que testa `coletar` e `buscar` com um simples `assert`). Depois:

```bat
pytest -q
```

Isso também roda o teste de convenção da seção 3 sobre a sua tool.

### 4.3. Com o Ollama (o modelo escolhendo a tool de verdade)

```bat
python -m server
```

No log de subida, a linha `orbit.servidor: tools MCP: [...]` deve listar a sua tool. Em outro terminal:

```bat
python -m server.teste_ws "orbit <uma frase natural que pede a tool>"
```

No log do servidor, procure `orbit.ponte: tool minha_tool({...}) levou X s`: é a prova de que o modelo a escolheu. Teste **três frases diferentes** que pedem a mesma coisa. Se o modelo não chamar a tool, ou chamar com argumento errado, **reescreva a descrição** (seção 2) antes de pensar em outra coisa. Se ele chamar a tool quando não devia, a descrição está larga demais.

### 4.4. Em outro cliente MCP (Claude Code, Hermes)

O servidor é um MCP padrão por stdio. Aponte o cliente para o comando:

```bat
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
- [ ] `pytest -q` passa, com testes da lógica pura.
- [ ] Com o Ollama, três frases diferentes fazem o modelo chamar a tool (`tool ... levou` no log).
- [ ] Se usou uma biblioteca nova, ela está em `requirements.txt`.
