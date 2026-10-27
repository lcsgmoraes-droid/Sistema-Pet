import os
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.services.pessoa_merge_service import (
    _mesclar_perfis_app,
    _obter_pessoas,
    _perfis_inerentes,
    _unir_listas_json,
    _unir_textos,
    _snapshot_perfis_app,
)
from app.models import AppAccessProfile
from app.tenancy.context import clear_current_tenant, set_current_tenant


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
    pessoa = SimpleNamespace(
        is_cliente=False,
        is_fornecedor=False,
        is_veterinario=False,
        is_funcionario=True,
        is_entregador=True,
    )

    assert _perfis_inerentes(pessoa) == {"funcionario", "entregador"}


def test_fusao_preserva_todos_os_perfis_quando_pessoa_tem_varios():
    pessoa = SimpleNamespace(
        is_cliente=True,
        is_fornecedor=False,
        is_veterinario=True,
        is_funcionario=True,
        is_entregador=False,
    )

    assert _perfis_inerentes(pessoa) == {"cliente", "veterinario", "funcionario"}


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


def test_preview_obtem_pessoas_sem_bloquear_linhas():
    principal = SimpleNamespace(id=1, ativo=True, merged_into_id=None)
    duplicado = SimpleNamespace(id=2, ativo=True, merged_into_id=None)
    consulta = MagicMock()
    consulta.filter.return_value = consulta
    consulta.populate_existing.return_value = consulta
    consulta.all.return_value = [principal, duplicado]
    db = MagicMock()
    db.query.return_value = consulta

    assert _obter_pessoas(db, uuid4(), 1, 2, bloquear=False) == (principal, duplicado)
    consulta.populate_existing.assert_called_once()
    consulta.with_for_update.assert_not_called()


def test_fusao_preserva_grants_e_metadados_inclusive_perfis_em_conflito():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            CreateTable(AppAccessProfile.__table__, include_foreign_key_constraints=[])
        )
    tenant = uuid4()
    set_current_tenant(tenant)
    data_original = datetime(2020, 5, 4, 10, 30)
    try:
        with Session(engine) as db:

            def criar(cliente_id, perfil, ativo, nota):
                grant = AppAccessProfile(
                    tenant_id=tenant,
                    cliente_id=cliente_id,
                    user_id=84,
                    profile_type=perfil,
                    is_active=ativo,
                    granted_by_user_id=7,
                    notes=nota,
                    created_at=data_original,
                    updated_at=data_original,
                )
                db.add(grant)
                return grant

            principal_inativo = criar(
                1, "cliente", False, "Concessao original principal"
            )
            duplicado_ativo = criar(2, "cliente", True, "Concessao original duplicada")
            transferido = criar(2, "funcionario", True, "Equipe desde 2020")
            inativo_transferido = criar(
                2, "gestor", False, "Permissao revogada em 2021"
            )
            db.flush()
            ids_antes = {grant.id for grant in db.query(AppAccessProfile).all()}
            snapshot = _snapshot_perfis_app(db, tenant_id=tenant, pessoa_ids=[1, 2])
            pessoa = dict(
                is_cliente=False,
                is_funcionario=False,
                is_veterinario=False,
                is_entregador=False,
            )
            principal = SimpleNamespace(id=1, auth_user_id=84, **pessoa)
            duplicado = SimpleNamespace(id=2, auth_user_id=None, **pessoa)

            perfis, preservacao = _mesclar_perfis_app(
                db,
                principal=principal,
                duplicado=duplicado,
                tenant_id=tenant,
                user_id=99,
            )
            db.flush()

            assert set(perfis) == {"cliente", "funcionario"}
            assert {grant.id for grant in db.query(AppAccessProfile).all()} == ids_antes
            assert principal_inativo.is_active
            assert principal_inativo.notes == "Concessao original principal"
            assert duplicado_ativo.cliente_id == 2 and not duplicado_ativo.is_active
            assert duplicado_ativo.notes == "Concessao original duplicada"
            assert transferido.cliente_id == 1 and transferido.is_active
            assert (
                inativo_transferido.cliente_id == 1
                and not inativo_transferido.is_active
            )
            assert transferido.notes == "Equipe desde 2020"
            assert inativo_transferido.notes == "Permissao revogada em 2021"
            assert all(
                grant.created_at == data_original
                and grant.granted_by_user_id == 7
                and grant.user_id == 84
                for grant in db.query(AppAccessProfile).all()
            )
            antes = next(
                grant for grant in snapshot["2"] if grant["id"] == duplicado_ativo.id
            )
            assert antes["is_active"] is True
            assert antes["notes"] == "Concessao original duplicada"
            assert antes["created_at"] == data_original.isoformat()
            assert antes["updated_at"] == data_original.isoformat()
            assert {item["resolucao"] for item in preservacao} == {
                "transferido",
                "historico_no_duplicado",
            }
    finally:
        clear_current_tenant()
        engine.dispose()
