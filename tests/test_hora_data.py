import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import hora_data  # noqa: E402


def test_formato_exemplo():
    # 19/10/2026 é segunda-feira.
    r = hora_data.hora_data_logica(datetime(2026, 10, 19, 14, 32))
    assert r == "Agora são 14 e 32. Hoje é segunda-feira, 19 de outubro de 2026."


def test_falavel_sem_markdown():
    r = hora_data.hora_data_logica(datetime(2026, 10, 19, 14, 32))
    assert len(r) <= 300
    assert not any(c in r for c in "*_#`|:%")


def test_dias_da_semana_em_portugues():
    # 19 a 25/10/2026: segunda a domingo.
    esperado = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                "sexta-feira", "sábado", "domingo"]
    for i, nome in enumerate(esperado):
        assert nome in hora_data.hora_data_logica(datetime(2026, 10, 19 + i, 10, 15))


def test_meses_em_portugues():
    for m, nome in enumerate(hora_data.MESES, start=1):
        assert f" de {nome} de 2026." in hora_data.hora_data_logica(datetime(2026, m, 15, 10, 15))
    assert "março" in hora_data.hora_data_logica(datetime(2026, 3, 10, 9, 5))


def test_hora_com_minutos():
    assert hora_data.hora_data_logica(datetime(2026, 10, 19, 9, 5)).startswith("Agora são 9 e 5.")
    assert hora_data.hora_data_logica(datetime(2026, 10, 19, 1, 20)).startswith("Agora é uma e 20.")
    assert hora_data.hora_data_logica(datetime(2026, 10, 19, 15, 0)).startswith("Agora são 15 em ponto.")


def test_meia_noite_e_meio_dia():
    assert hora_data.hora_data_logica(datetime(2026, 10, 19, 0, 0)).startswith("Agora é meia-noite.")
    assert hora_data.hora_data_logica(datetime(2026, 10, 19, 12, 0)).startswith("Agora é meio-dia.")
    # Logo depois, volta ao formato normal.
    assert hora_data.hora_data_logica(datetime(2026, 10, 19, 0, 7)).startswith("Agora são 0 e 7.")


def test_dia_primeiro():
    assert "Hoje é domingo, primeiro de março de 2026." in hora_data.hora_data_logica(datetime(2026, 3, 1, 8, 30))


def test_sem_argumento_usa_agora():
    r = hora_data.hora_data_logica()
    assert r.startswith("Agora ") and "Hoje é " in r
