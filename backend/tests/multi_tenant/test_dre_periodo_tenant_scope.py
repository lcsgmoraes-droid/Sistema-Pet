"""
Isolamento multi-tenant da busca de DREPeriodo.
================================================

Regressão: os serviços de Simples Nacional (provisão, fechamento, reconciliação)
buscavam o período DRE filtrando SÓ por mês/ano — sem tenant nem usuário. Como
`DREPeriodo` herda Base direto (fora do filtro global), isso devolvia o período de
QUALQUER loja com aquele mês/ano → leitura e até escrita (provisão de imposto) no
DRE de outra loja.

O helper `buscar_periodo_dre_do_tenant` escopa o período à loja, casando por
`tenant_id` OU pelos usuários da loja (`usuario_id`). Funciona mesmo quando
`DREPeriodo.tenant_id` ainda está nulo (backfill incompleto), e nunca devolve
período de outra loja.
"""
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.main  # noqa: F401  (garante o registro completo dos modelos ORM)
from app.ia.aba7_models import DREPeriodo
from app.services.dre_periodo_tenant_scope import buscar_periodo_dre_do_tenant
from app.tenancy.context import clear_current_tenant


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
                    tenant_id TEXT NULL,
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
        # p1: legado da loja A (tenant_id NULO, dono = usuario 1)  -> casa pelo usuário
        # p2: período da loja B (tenant_id setado, sem usuário)    -> casa pelo tenant_id
        conn.execute(
            text(
                """
                INSERT INTO dre_periodos (id, tenant_id, usuario_id, mes, ano, status, impostos)
                VALUES
                    (1, NULL, 1, 5, 2026, 'aberto', 0),
                    (2, :b, NULL, 5, 2026, 'aberto', 0)
                """
            ),
            {"b": _hex(TENANT_B)},
        )
    return engine


def test_query_ingenua_por_mes_ano_vaza_entre_lojas():
    """Documenta o vazamento: filtrar só por mês/ano enxerga as duas lojas."""
    engine = _engine()
    db = sessionmaker(bind=engine)()
    try:
        ingenua = (
            db.query(DREPeriodo)
            .filter(DREPeriodo.mes == 5, DREPeriodo.ano == 2026)
            .all()
        )
        assert len(ingenua) == 2  # vê A e B -> isolamento ausente
    finally:
        db.close()
        clear_current_tenant()


def test_helper_isola_periodo_por_tenant():
    engine = _engine()
    db = sessionmaker(bind=engine)()
    try:
        periodo_a = buscar_periodo_dre_do_tenant(db, TENANT_A, 5, 2026)
        periodo_b = buscar_periodo_dre_do_tenant(db, TENANT_B, 5, 2026)

        # A recebe o seu (casado pelo usuário, mesmo com tenant_id nulo)
        assert periodo_a is not None
        assert periodo_a.id == 1
        # B recebe o seu (casado pelo tenant_id, mesmo sem usuário)
        assert periodo_b is not None
        assert periodo_b.id == 2
        # E nunca o da outra loja
        assert periodo_a.id != 2
        assert periodo_b.id != 1
    finally:
        db.close()
        clear_current_tenant()


def test_helper_nao_inventa_periodo_de_outra_loja():
    """Loja sem período no mês não 'herda' o período de outra loja."""
    engine = _engine()
    db = sessionmaker(bind=engine)()
    try:
        # Tenant A em mês onde só B tem período seria o caso perigoso; aqui usamos
        # um terceiro tenant sem nenhum período -> deve devolver None, não o de A/B.
        TENANT_C = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        assert buscar_periodo_dre_do_tenant(db, TENANT_C, 5, 2026) is None
    finally:
        db.close()
        clear_current_tenant()
