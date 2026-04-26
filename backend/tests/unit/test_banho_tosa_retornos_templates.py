from datetime import date
from types import SimpleNamespace

from app.banho_tosa_retornos_templates import (
    normalizar_canal,
    renderizar_template_retorno,
    template_aplicavel,
)


def test_renderizar_template_retorno_com_variaveis():
    template = SimpleNamespace(
        assunto="Retorno de {pet_nome}",
        mensagem="Ola {cliente_nome}, {pet_nome} esta {dias_para_acao}: {acao_sugerida}",
    )
    item = {
        "cliente_nome": "Ana",
        "pet_nome": "Luna",
        "data_referencia": date(2026, 4, 26),
        "dias_para_acao": -2,
        "acao_sugerida": "agendar novo banho",
    }

    assunto, mensagem = renderizar_template_retorno(template, item)

    assert assunto == "Retorno de Luna"
    assert mensagem == "Ola Ana, Luna esta 2 dia(s) em atraso: agendar novo banho"


def test_template_retorno_aplicavel_por_tipo():
    template = SimpleNamespace(tipo_retorno="pacote_vencendo")
    assert template_aplicavel(template, "pacote_vencendo")
    assert not template_aplicavel(template, "sem_banho")


def test_normalizar_canal_padrao_app():
    assert normalizar_canal(None) == "app"
    assert normalizar_canal("EMAIL") == "email"
