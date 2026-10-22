"""OPS: historico de alteracoes das lojas (antes, quem e quando)."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.ops_tenant_log_models import OpsTenantChangeLog
from app.services.ops_tenant_log_service import (
    CATEGORIA_COMERCIAL,
    listar_historico,
    registrar_alteracoes,
)

RAIZ = Path(__file__).resolve().parents[2]
ADMIN = SimpleNamespace(id=3, email="ops@corepet.test")


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[OpsTenantChangeLog.__table__])
    return sessionmaker(bind=engine)()


def test_grava_so_o_que_mudou_com_antes_quem_e_quando():
    db = _db()
    loja = str(uuid4())

    gravadas = registrar_alteracoes(
        db,
        tenant_id=loja,
        admin=ADMIN,
        categoria=CATEGORIA_COMERCIAL,
        antes={"plan": "free", "status": "active"},
        depois={"plan": "pet-basico", "status": "active"},
    )
    db.flush()

    assert gravadas == 1
    [linha] = listar_historico(db, tenant_id=loja)
    assert (linha["campo"], linha["antes"], linha["depois"]) == (
        "plan",
        "free",
        "pet-basico",
    )
    assert linha["quem"] == "ops@corepet.test"


def test_historico_e_separado_por_loja():
    db = _db()
    a, b = str(uuid4()), str(uuid4())
    for loja in (a, b):
        registrar_alteracoes(
            db,
            tenant_id=loja,
            admin=ADMIN,
            categoria="modulo",
            antes={"crm": "inativo"},
            depois={"crm": "ativo"},
        )
    db.flush()

    assert len(listar_historico(db, tenant_id=a)) == 1
    assert len(listar_historico(db)) == 2


def test_alteracoes_do_ops_passam_pelo_registro():
    modulos = (RAIZ / "app/services/ops_lojas_modulos_service.py").read_text(
        encoding="utf-8"
    )
    tenants = (RAIZ / "app/routes/ops_tenants_routes.py").read_text(encoding="utf-8")
    assert "registrar_alteracoes(" in modulos
    assert tenants.count("registrar_alteracoes(") == 2  # comercial e acompanhamento
