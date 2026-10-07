"""Deteccao de duplicados entre lojas do grupo (somente leitura)."""

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Tenant
from app.models_cadastros import Cliente
from app.services.grupo_duplicados_service import pessoas_duplicadas
from app.tenancy.context import clear_current_tenant, set_current_tenant

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not DATABASE_URL.startswith("postgresql"), reason="requer Postgres")


@pytest.fixture()
def sessao():
    engine = create_engine(DATABASE_URL)
    conexao = engine.connect()
    transacao = conexao.begin()
    session = Session(bind=conexao)
    try:
        yield session
    finally:
        session.close()
        transacao.rollback()
        conexao.close()
        engine.dispose()
        clear_current_tenant()


def test_mesmo_cpf_em_duas_lojas_do_grupo_aparece_como_duplicado(sessao):
    loja_a, loja_b = str(uuid4()), str(uuid4())
    for loja, nome in ((loja_a, "Loja A"), (loja_b, "Loja B")):
        sessao.add(Tenant(id=loja, name=nome, name_normalized=nome.lower(), status="active"))
        sessao.flush()
    grupo = GrupoComercial(nome="G", criado_por_empresa_id=loja_a, criado_por_usuario_id=1)
    sessao.add(grupo)
    sessao.flush()
    sessao.add(GrupoComercialMembro(grupo_id=grupo.id, empresa_id=loja_a, status="ativo"))
    sessao.flush()
    sessao.add(GrupoComercialMembro(grupo_id=grupo.id, empresa_id=loja_b, status="ativo"))
    sessao.flush()
    usuario = sessao.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    for loja in (loja_a, loja_b):
        set_current_tenant(loja)
        sessao.add(Cliente(tenant_id=UUID(loja), origem_tenant_id=UUID(loja), user_id=usuario, nome="Maria", cpf="123.456.789-00", is_cliente=True))
        sessao.flush()
        clear_current_tenant()

    achados = pessoas_duplicadas(sessao, grupo.id)
    assert len(achados) == 1
    assert achados[0]["chave"] == "12345678900"
    assert {r["loja_id"] for r in achados[0]["registros"]} == {loja_a, loja_b}
