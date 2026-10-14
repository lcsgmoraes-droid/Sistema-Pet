import os
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.services.pessoa_merge_service import (
    _obter_pessoas,
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


def test_fusao_recarrega_credito_de_pessoas_ja_carregadas_antes_do_lock():
    tenant_id = uuid4()
    principal = SimpleNamespace(
        id=1, ativo=True, merged_into_id=None, credito=Decimal("10.00")
    )
    duplicado = SimpleNamespace(
        id=2, ativo=True, merged_into_id=None, credito=Decimal("5.00")
    )
    consulta = MagicMock()
    consulta.filter.return_value = consulta

    def recarregar_saldo():
        # Simula crédito recebido após os objetos entrarem na identity map.
        principal.credito = Decimal("35.00")
        return consulta

    consulta.populate_existing.side_effect = recarregar_saldo
    consulta.with_for_update.return_value = consulta
    consulta.all.return_value = [principal, duplicado]
    db = MagicMock()
    db.query.return_value = consulta

    carregado_principal, carregado_duplicado = _obter_pessoas(
        db, tenant_id, principal.id, duplicado.id
    )

    consulta.populate_existing.assert_called_once()
    consulta.with_for_update.assert_called_once()
    assert carregado_principal is principal
    assert carregado_duplicado is duplicado
    assert carregado_principal.credito + carregado_duplicado.credito == Decimal("40.00")
