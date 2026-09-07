"""Reparo autorizado preserva o original e recusa casos nao comprovados."""

import json
from decimal import Decimal
from uuid import uuid4

import pytest

from app.financeiro import ContasReceberService
from app.financeiro_models import ContaReceber, Recebimento
from app.models import AuditLog
from app.scripts.reparar_recebimento_duplicado import reparar
from tests.unit.test_finalizacao_recebiveis_atomicidade import cenario  # noqa: F401


@pytest.fixture
def duplicidade(cenario):
    cenario.finalizar(121)
    cenario.venda.total = Decimal("121")
    cenario.venda.status = "finalizada"
    ContasReceberService.criar_de_venda(
        venda=cenario.venda,
        pagamentos=[{"forma_pagamento": "PIX", "forma_pagamento_id": 1, "valor": 121}],
        user_id=1,
        db=cenario.db,
    )
    cenario.db.commit()
    contas = cenario.db.query(ContaReceber).order_by(ContaReceber.id).all()
    baixas = cenario.db.query(Recebimento).order_by(Recebimento.id).all()
    args = dict(
        tenant_id=cenario.tenant,
        venda_id=1,
        conta_original_id=contas[0].id,
        conta_duplicada_id=contas[1].id,
        recebimento_duplicado_id=baixas[1].id,
        motivo="Reparo autorizado em teste",
    )
    return cenario.db, args


def test_dry_run_nao_altera_registros(duplicidade):
    db, args = duplicidade
    plano = reparar(db, **args)
    assert plano["aplicado"] is False
    assert plano["valor_corrigido"] == "121.00"
    assert db.query(Recebimento).count() == 2
    assert (
        db.query(AuditLog).filter_by(action="repair_duplicate_sale_receipt").count()
        == 0
    )


def test_reparo_atomico_auditado_e_idempotente(duplicidade):
    db, args = duplicidade
    plano = reparar(db, **args, aplicar=True)
    db.expire_all()
    assert db.query(Recebimento).count() == 1
    original = db.get(ContaReceber, args["conta_original_id"])
    duplicada = db.get(ContaReceber, args["conta_duplicada_id"])
    assert original.valor_recebido == Decimal("121")
    assert duplicada.status == "cancelado"
    assert duplicada.valor_recebido == 0
    log = db.get(AuditLog, plano["audit_id"])
    assert len(json.loads(log.old_value)["recebimentos"]) == 2
    repetido = reparar(db, **args, aplicar=True)
    assert repetido["ja_aplicado"] is True
    assert repetido["audit_id"] == plano["audit_id"]
    assert db.query(Recebimento).count() == 1


def test_reparo_recusa_outro_tenant(duplicidade):
    db, args = duplicidade
    with pytest.raises(ValueError, match="tenant"):
        reparar(db, **{**args, "tenant_id": uuid4()}, aplicar=True)
    assert db.query(Recebimento).count() == 2


def test_reparo_recusa_valor_modificado(duplicidade):
    db, args = duplicidade
    db.get(Recebimento, args["recebimento_duplicado_id"]).valor_recebido = 120
    db.commit()
    with pytest.raises(ValueError, match="Baixa"):
        reparar(db, **args, aplicar=True)
    assert db.query(Recebimento).count() == 2


def test_falha_de_auditoria_desfaz_reparo(duplicidade, monkeypatch):
    db, args = duplicidade
    original = db.execute

    def executar(statement, *a, **kw):
        if "INSERT INTO audit_logs" in str(statement):
            raise RuntimeError("Auditoria indisponivel")
        return original(statement, *a, **kw)

    monkeypatch.setattr(db, "execute", executar)
    with pytest.raises(RuntimeError):
        reparar(db, **args, aplicar=True)
    db.rollback()
    assert db.query(Recebimento).count() == 2
    assert db.get(ContaReceber, args["conta_duplicada_id"]).status == "recebido"
