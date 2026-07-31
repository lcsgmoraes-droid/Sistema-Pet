import os
from types import SimpleNamespace


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.services.pessoa_merge_service import (
    _perfis_inerentes,
    _unir_listas_json,
    _unir_textos,
)


def test_fusao_preserva_observacoes_dos_dois_cadastros():
    assert _unir_textos("Historico principal", "Historico duplicado") == (
        "Historico principal\n\nHistorico duplicado"
    )


def test_fusao_preserva_enderecos_adicionais_sem_repetir():
    principal = [{"tipo": "casa", "cep": "19000-000"}]
    duplicado = [
        {"tipo": "casa", "cep": "19000-000"},
        {"tipo": "trabalho", "cep": "19010-000"},
    ]

    assert _unir_listas_json(principal, duplicado) == [
        {"tipo": "casa", "cep": "19000-000"},
        {"tipo": "trabalho", "cep": "19010-000"},
    ]


def test_fusao_preserva_perfis_operacionais_da_pessoa():
    pessoa = SimpleNamespace(tipo_cadastro="funcionario", is_entregador=True)

    assert _perfis_inerentes(pessoa) == {"funcionario", "entregador"}
