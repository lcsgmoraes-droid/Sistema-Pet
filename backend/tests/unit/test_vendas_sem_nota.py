"""A fila fiscal não pode misturar empresas nem repetir tentativas de nota."""

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.caixa_models import Caixa  # noqa: F401 - registra a FK de Venda
from app.financeiro_models import (
    ContaReceber,
)  # noqa: F401 - registra a relação de Venda
from app.models import Cliente
from app.produtos_models import Produto  # noqa: F401 - registra a relação de VendaItem
from app.nfe.vendas_sem_nota_routes import listar_vendas_sem_nota
from app.tenancy.context import tenant_context
from app.vendas_models import Venda
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.empresa_config_routes import (
    EmpresaConfigGeralCreate,
    EmpresaConfigGeralUpdate,
    get_config_pdv,
    update_config_empresa,
)


def test_lista_somente_vendas_finalizadas_sem_tentativa_no_periodo():
    engine = create_engine("sqlite:///:memory:")
    Cliente.__table__.create(engine)
    Venda.__table__.create(engine)
    tenant, outra_empresa = uuid4(), uuid4()

    def inserir(db, numero, data, *, empresa=tenant, status="finalizada", **extras):
        with tenant_context(empresa):
            db.execute(
                Venda.__table__.insert().values(
                    tenant_id=empresa,
                    numero_venda=numero,
                    vendedor_id=1,
                    user_id=1,
                    subtotal=100,
                    total=100,
                    data_venda=data,
                    status=status,
                    **extras,
                )
            )

    with Session(engine) as db:
        inserir(db, "inicio", datetime(2026, 10, 1, 0, 0))
        inserir(db, "fim", datetime(2026, 10, 14, 23, 59, 59))
        inserir(db, "antes", datetime(2026, 9, 30, 23, 59, 59))
        inserir(db, "aberta", datetime(2026, 10, 14), status="aberta")
        inserir(db, "emitida", datetime(2026, 10, 14), nfe_numero=123)
        inserir(db, "enviando", datetime(2026, 10, 14), nfe_idempotency_key="envio")
        inserir(db, "correlacao", datetime(2026, 10, 14), nfe_correlation_id="envio")
        inserir(db, "bling", datetime(2026, 10, 14), nfe_bling_id=123)
        inserir(db, "chave", datetime(2026, 10, 14), nfe_chave="1" * 44)
        inserir(db, "rejeitada", datetime(2026, 10, 14), nfe_status="rejeitada")
        inserir(db, "outra", datetime(2026, 10, 14), empresa=outra_empresa)
        db.commit()

        with tenant_context(tenant):
            resultado = listar_vendas_sem_nota(
                data_inicial=date(2026, 10, 1),
                data_final=date(2026, 10, 14),
                pagina=1,
                por_pagina=20,
                db=db,
                user_and_tenant=(None, tenant),
            )
            assert resultado["total"] == 2
            assert [venda["numero_venda"] for venda in resultado["vendas"]] == [
                "fim",
                "inicio",
            ]

            paginada = listar_vendas_sem_nota(
                data_inicial=date(2026, 10, 1),
                data_final=date(2026, 10, 14),
                pagina=2,
                por_pagina=1,
                db=db,
                user_and_tenant=(None, tenant),
            )
            assert paginada["total"] == 2
            assert paginada["vendas"][0]["numero_venda"] == "inicio"

    engine.dispose()


def test_recusa_periodo_invertido():
    try:
        listar_vendas_sem_nota(
            data_inicial=date(2026, 10, 15),
            data_final=date(2026, 10, 14),
            db=None,
            user_and_tenant=(None, uuid4()),
        )
    except HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Período invertido deveria ser recusado")


class _ConfigQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, condition):
        self.rows = [row for row in self.rows if row.tenant_id == condition.right.value]
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class _ConfigSession:
    def __init__(self, rows):
        self.rows = rows

    def query(self, model):
        assert model is EmpresaConfigGeral
        return _ConfigQuery(self.rows.copy())

    def commit(self):
        pass

    def refresh(self, _row):
        pass


def test_emissao_automatica_comeca_desativada_e_valida_modelo():
    assert EmpresaConfigGeralCreate().emitir_nota_automatica_pdv is False
    assert EmpresaConfigGeralCreate().tipo_nota_automatica_pdv == "nfce"
    assert "emitir_nota_automatica_pdv" not in (
        EmpresaConfigGeralUpdate().model_dump(exclude_unset=True)
    )
    for dados in (
        {"emitir_nota_automatica_pdv": None},
        {"tipo_nota_automatica_pdv": None},
        {"tipo_nota_automatica_pdv": "nfse"},
    ):
        with pytest.raises(ValidationError):
            EmpresaConfigGeralUpdate(**dados)
    resposta = get_config_pdv.__wrapped__(
        user_and_tenant=(None, uuid4()), db=_ConfigSession([])
    )
    assert resposta["emitir_nota_automatica_pdv"] is False
    assert resposta["tipo_nota_automatica_pdv"] == "nfce"


def test_emissao_automatica_e_persistida_somente_na_empresa_selecionada(monkeypatch):
    tenant, outro_tenant = uuid4(), uuid4()
    rows = [
        EmpresaConfigGeral(
            id=indice,
            tenant_id=empresa,
            emitir_nota_automatica_pdv=False,
            tipo_nota_automatica_pdv="nfce",
            vendedor_obrigatorio_pdv=True,
            mostrar_endereco_cliente_pdv=True,
        )
        for indice, empresa in enumerate((tenant, outro_tenant), 1)
    ]
    db = _ConfigSession(rows)
    monkeypatch.setattr("app.empresa_config_routes._obter_nome_acesso", lambda *_: None)
    resposta = update_config_empresa.__wrapped__(
        config_data=EmpresaConfigGeralUpdate(
            emitir_nota_automatica_pdv=True, tipo_nota_automatica_pdv="nfe"
        ),
        user_and_tenant=(SimpleNamespace(id=42), tenant),
        db=db,
    )
    assert resposta.emitir_nota_automatica_pdv is True
    assert resposta.tipo_nota_automatica_pdv == "nfe"
    assert resposta.vendedor_obrigatorio_pdv is True
    assert resposta.mostrar_endereco_cliente_pdv is True
    for empresa, ativa, tipo in ((tenant, True, "nfe"), (outro_tenant, False, "nfce")):
        pdv = get_config_pdv.__wrapped__(user_and_tenant=(None, empresa), db=db)
        assert pdv["emitir_nota_automatica_pdv"] is ativa
        assert pdv["tipo_nota_automatica_pdv"] == tipo
