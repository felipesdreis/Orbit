"""Tool calcular: resolve contas com números e fala o resultado em português."""
import ast
import operator

_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Pow: operator.pow,
}
_UNA = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_EXPOENTE = 100
_MAX_TAMANHO = 200


def _avaliar(no):
    """Avalia só números e operadores aritméticos (sem eval: nada além de conta passa)."""
    if isinstance(no, ast.Expression):
        return _avaliar(no.body)
    if isinstance(no, ast.Constant) and type(no.value) in (int, float):
        return no.value
    if isinstance(no, ast.UnaryOp) and type(no.op) in _UNA:
        return _UNA[type(no.op)](_avaliar(no.operand))
    if isinstance(no, ast.BinOp) and type(no.op) in _BIN:
        a, b = _avaliar(no.left), _avaliar(no.right)
        if isinstance(no.op, ast.Pow) and abs(b) > _MAX_EXPOENTE:
            raise ValueError("expoente grande demais")
        return _BIN[type(no.op)](a, b)
    raise ValueError("expressão não suportada")


def _falar(numero: float) -> str:
    """Número como se fala: vírgula decimal, até 2 casas, sem zeros sobrando."""
    if numero == int(numero) and abs(numero) < 1e15:
        return str(int(numero))
    texto = f"{numero:.2f}".rstrip("0").rstrip(",.")
    return texto.replace(".", ",") if texto not in ("-0", "") else "0"


def calcular_logica(expressao: str) -> str:
    """Resolve a conta e devolve a frase falada, ou 'ERRO: ...'."""
    limpa = (expressao or "").strip().lower()
    if not limpa or len(limpa) > _MAX_TAMANHO:
        return "ERRO: não entendi a conta."
    # O modelo pode mandar "x" ou "×" para vezes e vírgula como decimal.
    limpa = limpa.replace("×", "*").replace("÷", "/").replace("x", "*").replace(",", ".")
    try:
        resultado = _avaliar(ast.parse(limpa, mode="eval"))
    except ZeroDivisionError:
        return "ERRO: não dá para dividir por zero."
    except (ValueError, SyntaxError, OverflowError, TypeError):
        return "ERRO: não entendi a conta."
    if resultado != resultado or resultado in (float("inf"), float("-inf")):
        return "ERRO: o resultado é grande demais."
    return f"O resultado é {_falar(resultado)}."


def registrar(mcp) -> None:
    @mcp.tool()
    def calcular(expressao: str) -> str:
        """[leitura] Use quando pedirem uma conta de matemática; passe só números e + - * / ( ), por exemplo 240*15/100."""
        return calcular_logica(expressao)
