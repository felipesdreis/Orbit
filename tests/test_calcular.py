import pytest

import calcular


@pytest.mark.parametrize("conta,esperado", [
    ("2+2", "O resultado é 4."),
    ("240*15/100", "O resultado é 36."),
    ("10/4", "O resultado é 2,5."),
    ("1/3", "O resultado é 0,33."),
    ("(2+3)*4", "O resultado é 20."),
    ("2**10", "O resultado é 1024."),
    ("7 x 6", "O resultado é 42."),
    ("3,5*2", "O resultado é 7."),
    ("-5+2", "O resultado é -3."),
    ("0.1+0.2", "O resultado é 0,3."),
])
def test_contas(conta, esperado):
    assert calcular.calcular_logica(conta) == esperado


@pytest.mark.parametrize("conta", [
    "", "   ", "abc", "__import__('os').system('x')", "open('a')", "2+", "1/0",
    "2**1000", "9**9**9", "[1,2]", "'a'*5", "x",
])
def test_erros_comecam_com_erro(conta):
    assert calcular.calcular_logica(conta).startswith("ERRO:")


def test_nao_executa_codigo():
    r = calcular.calcular_logica("__import__('os').getcwd()")
    assert r.startswith("ERRO:")


def test_falavel():
    r = calcular.calcular_logica("100/7")
    assert not any(c in r for c in "*_#`|:%")
