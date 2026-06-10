"""
Isolamento multi-tenant da busca de DREPeriodo.
================================================

`DREPeriodo` agora adota o mixin `TenantScoped` (tenant_id UUID NOT NULL) e entra no
filtro global de tenant + fail-fast: o isolamento é AUTOMÁTICO — toda query escopa por
`tenant_id = <contexto>` e uma query SEM contexto LEVANTA RuntimeError.

O helper `buscar_periodo_dre_do_tenant` segue em uso (Simples/provisão/reconciliação):
com o contexto da loja setado, devolve o período (mês/ano) da loja e nunca o de outra.
Pré-requisito da migração: backfill 100% de `tenant_id` (migration pn20260610a1) — sem
linhas órfãs, o ramo `usuario_id` do OR do helper fica redundante, mas inócuo.
"""
from uuid import UUID

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.main  # noqa: F401  (garante o registro completo dos modelos ORM)
from app.ia.aba7_models import DREPeriodo
from app.services.dre_periodo_tenant_scope import (
    buscar_periodo_dre_do_tenant,
    tenant_id_do_usuario,
    tenant_id_para_escrita_dre,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant


TENANT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _hex(tenant_id):
    return UUID(str(tenant_id)).hex


def _engine():
    clear_current_tenant()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, tenant_id TEXT NULL)"))
        conn.execute(
            text(
                """
                CREATE TABLE dre_periodos (
                    id INTEGER PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    usuario_id INTEGER,
                    data_inicio DATE,
                    data_fim DATE,
                    mes INTEGER,
                    ano INTEGER,
                    canal TEXT,
                    canais_incluidos TEXT,
                    receita_bruta NUMERIC DEFAULT 0,
                    deducoes_receita NUMERIC DEFAULT 0,
                    receita_liquida NUMERIC DEFAULT 0,
                    custo_produtos_vendidos NUMERIC DEFAULT 0,
                    lucro_bruto NUMERIC DEFAULT 0,
                    margem_bruta_percent NUMERIC DEFAULT 0,
                    despesas_vendas NUMERIC DEFAULT 0,
                    despesas_administrativas NUMERIC DEFAULT 0,
                    despesas_financeiras NUMERIC DEFAULT 0,
                    outras_despesas NUMERIC DEFAULT 0,
                    total_despesas_operacionais NUMERIC DEFAULT 0,
                    lucro_operacional NUMERIC DEFAULT 0,
                    margem_operacional_percent NUMERIC DEFAULT 0,
                    impostos NUMERIC DEFAULT 0,
                    impostos_detalhamento TEXT,
                    aliquota_efetiva_percent NUMERIC DEFAULT 0,
                    regime_tributario TEXT,
                    lucro_liquido NUMERIC DEFAULT 0,
                    margem_liquida_percent NUMERIC DEFAULT 0,
                    status TEXT,
                    tendencia TEXT,
                    score_saude INTEGER DEFAULT 0,
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        # u1 -> Tenant A, u2 -> Tenant B
        conn.execute(
            text("INSERT INTO users (id, tenant_id) VALUES (1, :a), (2, :b)"),
            {"a": _hex(TENANT_A), "b": _hex(TENANT_B)},
        )
        # p1: período da loja A; p2: período da loja B (ambos com tenant_id — pós-backfill 100%).
        conn.execute(
            text(
                """
                INSERT INTO dre_periodos (id, tenant_id, usuario_id, mes, ano, status, impostos)
                VALUES
                    (1, :a, 1, 5, 2026, 'aberto', 0),
                    (2, :b, 2, 5, 2026, 'aberto', 0)
                """
            ),
            {"a": _hex(TENANT_A), "b": _hex(TENANT_B)},
        )
    return engine


def test_query_sem_contexto_da_failfast():
    """Sob TenantScoped, query em DREPeriodo SEM tenant no contexto LEVANTA fail-fast —
    o isolamento automático substituiu o filtro manual (antes a query ingênua vazava)."""
    engine = _engine()
    db = sessionmaker(bind=engine)()
    try:
        with pytest.raises(RuntimeError, match="ORM FAIL-FAST"):
            (
                db.query(DREPeriodo)
                .filter(DREPeriodo.mes == 5, DREPeriodo.ano == 2026)
                .all()
            )
    finally:
        db.close()
        clear_current_tenant()


def test_helper_isola_periodo_por_tenant():
    engine = _engine()
    db = sessionmaker(bind=engine)()
    try:
        set_current_tenant(TENANT_A)
        periodo_a = buscar_periodo_dre_do_tenant(db, TENANT_A, 5, 2026)
        assert periodo_a is not None
        assert periodo_a.id == 1

        clear_current_tenant()
        set_current_tenant(TENANT_B)
        periodo_b = buscar_periodo_dre_do_tenant(db, TENANT_B, 5, 2026)
        assert periodo_b is not None
        assert periodo_b.id == 2
    finally:
        db.close()
        clear_current_tenant()


def test_helper_nao_inventa_periodo_de_outra_loja():
    """Loja sem período no mês não 'herda' o período de outra loja."""
    engine = _engine()
    db = sessionmaker(bind=engine)()
    try:
        TENANT_C = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        set_current_tenant(TENANT_C)
        assert buscar_periodo_dre_do_tenant(db, TENANT_C, 5, 2026) is None
    finally:
        db.close()
        clear_current_tenant()


def test_tenant_id_do_usuario_resolve_e_trata_ausencias():
    """O helper de CRIAÇÃO resolve o tenant 'casa' do usuário (mesma lógica do backfill).

    Garante que novos DREPeriodo criados pelos serviços (aba7_dre/aba7_dre_canal)
    nasçam com tenant_id em vez de nulo — e que ausências não inventem dono.
    """
    engine = _engine()
    db = sessionmaker(bind=engine)()
    try:
        assert tenant_id_do_usuario(db, 1) == TENANT_A
        assert tenant_id_do_usuario(db, 2) == TENANT_B
        # usuario_id None -> None (não inventa tenant; a linha segue como antes)
        assert tenant_id_do_usuario(db, None) is None
        # usuário inexistente -> None
        assert tenant_id_do_usuario(db, 999) is None
    finally:
        db.close()
        clear_current_tenant()


def test_tenant_id_para_escrita_usa_contexto_ativo():
    """A ESCRITA usa o tenant ATIVO do contexto (não a 'casa' do usuário), evitando o
    descasamento que faria o DRE de um usuário multi-loja nascer na loja errada e sumir.
    """
    engine = _engine()
    db = sessionmaker(bind=engine)()
    try:
        # Usuário 1 tem casa = TENANT_A, mas opera no contexto da loja B -> grava B.
        set_current_tenant(TENANT_B)
        assert tenant_id_para_escrita_dre(db, 1) == TENANT_B

        # Sem contexto (chamada fora de request) -> fallback para a 'casa' do usuário.
        clear_current_tenant()
        assert tenant_id_para_escrita_dre(db, 1) == TENANT_A
    finally:
        db.close()
        clear_current_tenant()
