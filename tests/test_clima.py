import clima

RESPOSTA = {
    "current": {"temperature_2m": 24.4, "apparent_temperature": 26.9, "weather_code": 2},
    "daily": {"temperature_2m_min": [17.2], "temperature_2m_max": [29.8],
              "precipitation_probability_max": [35]},
}


def test_formatar_exemplo():
    assert clima.formatar("Mogi Guaçu", RESPOSTA) == (
        "Em Mogi Guaçu agora faz 24 graus, sensação de 27, parcialmente nublado. "
        "Hoje a mínima é 17 e a máxima 30 graus. Chance de chuva de 35 por cento."
    )


def test_sem_chuva_e_sensacao_parecida():
    d = {"current": {"temperature_2m": 20, "apparent_temperature": 21, "weather_code": 0},
         "daily": {"temperature_2m_min": [12], "temperature_2m_max": [28],
                   "precipitation_probability_max": [3]}}
    r = clima.formatar("Mogi Guaçu", d)
    assert "sensação" not in r and "Sem previsão de chuva." in r and "céu limpo" in r


def test_falavel():
    r = clima.formatar("Mogi Guaçu", RESPOSTA)
    assert len(r) <= 300 and not any(c in r for c in "*_#`|:%°")


def test_cidade_padrao_nao_geocodifica():
    chamadas = []

    def falso(url):
        chamadas.append(url)
        return RESPOSTA

    assert clima.clima_logica("", falso).startswith("Em Mogi Guaçu agora")
    assert len(chamadas) == 1 and "latitude=-22.3689" in chamadas[0]


def test_outra_cidade_usa_geocodificacao():
    def falso(url):
        if "geocoding" in url:
            return {"results": [{"name": "Campinas", "latitude": -22.9, "longitude": -47.06}]}
        assert "timezone=auto" in url
        return RESPOSTA

    assert clima.clima_logica("Campinas", falso).startswith("Em Campinas agora")


def test_cidade_inexistente():
    assert clima.clima_logica("Xyzabc", lambda url: {}).startswith("ERRO:")


def test_sem_internet_nao_levanta_excecao():
    def cai(url):
        raise OSError("sem rede")

    assert clima.clima_logica("", cai) == "ERRO: não consegui consultar o clima agora."
