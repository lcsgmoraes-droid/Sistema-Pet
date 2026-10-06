import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db  # noqa: F401 - registra hooks multitenant
from app.services.tenant_onboarding_service import (
    TenantOnboardingError,
    onboard_tenant_defaults,
)
from tests.multi_tenant.tenant_onboarding_test_helpers import (
    BASE_EXPECTED_COUNTS,
    TENANT_A,
    TENANT_B,
    _count,
    _tenant_params,
)


pytest_plugins = ["tests.multi_tenant.tenant_onboarding_test_helpers"]


def test_onboarding_dry_run_does_not_create_tenant_data(onboarding_session):
    result = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=True,
    )

    assert result["dry_run"] is True
    for key, expected in BASE_EXPECTED_COUNTS.items():
        assert result["would_create"][key] == expected
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0
    assert _count(onboarding_session, "contas_bancarias", TENANT_A) == 0
    assert _count(onboarding_session, "linhas_racao", TENANT_A) == 0
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 0
    assert _count(onboarding_session, "tenant_template_installs") == 0


def test_onboarding_apply_creates_default_copy_for_tenant(onboarding_session):
    result = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=False,
    )
    onboarding_session.commit()

    for key, expected in BASE_EXPECTED_COUNTS.items():
        assert result["created"][key] == expected
    assert result["template_source"] == "database"
    assert _count(onboarding_session, "template_items") >= 1
    assert _count(onboarding_session, "tenant_template_installs") == 1
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 5
    crediario = onboarding_session.execute(
        text(
            """
            SELECT nome, ativo, gera_contas_receber, prazo_dias
            FROM formas_pagamento
            WHERE tenant_id = :tenant_id AND tipo = 'crediario'
            """
        ),
        {"tenant_id": TENANT_A},
    ).one()
    assert crediario == ("Crediário", 1, 1, 30)
    assert _count(onboarding_session, "contas_bancarias", TENANT_A) == 2
    assert _count(onboarding_session, "especies", TENANT_A) == 2
    assert _count(onboarding_session, "racas", TENANT_A) == 2
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 12
    assert _count(onboarding_session, "tipo_despesas", TENANT_A) == 17
    assert _count(onboarding_session, "categorias", TENANT_A) == 2
    assert _count(onboarding_session, "linhas_racao", TENANT_A) == 4
    assert _count(onboarding_session, "portes_animal", TENANT_A) == 6
    assert _count(onboarding_session, "fases_publico", TENANT_A) == 4
    assert _count(onboarding_session, "tipos_tratamento", TENANT_A) == 9
    assert _count(onboarding_session, "sabores_proteina", TENANT_A) == 10
    assert _count(onboarding_session, "apresentacoes_peso", TENANT_A) == 11
    assert _count(onboarding_session, "vet_catalogo_procedimentos", TENANT_A) == 70
    assert _count(onboarding_session, "produtos", TENANT_A) == 0
    enum_values = onboarding_session.execute(
        text(
            "SELECT DISTINCT tipo_custo, escopo_rateio FROM dre_subcategorias WHERE tenant_id = :tenant_id"
        ),
        {"tenant_id": TENANT_A},
    ).all()
    assert enum_values
    assert {tipo_custo for tipo_custo, _escopo in enum_values} == {
        "DIRETO",
        "INDIRETO_RATEAVEL",
        "CORPORATIVO",
    }
    assert all(escopo == "AMBOS" for _tipo_custo, escopo in enum_values)


def test_new_onboarding_separates_stock_purchases_from_sales_cmv(onboarding_session):
    onboarding_session.execute(
        text(
            """
            INSERT INTO template_items (
                bundle_code, bundle_version, item_type, template_code,
                name, payload, sort_order, active
            ) VALUES (
                'petshop-br', 'v2', 'financial_category', 'fin_cmv',
                'CMV', :payload, 410, 1
            )
            """
        ),
        {
            "payload": json.dumps(
                {"nome": "CMV", "dre_subcategory_code": "dre_cmv_produtos"}
            )
        },
    )
    onboarding_session.execute(
        text(
            """
            INSERT INTO categorias_financeiras (
                tenant_id, user_id, nome, tipo, dre_subcategoria_id
            ) VALUES (:tenant_id, 1, 'CMV', 'despesa', 77)
            """
        ),
        {"tenant_id": TENANT_A},
    )
    onboarding_session.commit()

    result = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_B,
        user_id=2,
        dry_run=False,
        strict_required=True,
    )
    onboarding_session.commit()

    assert result["bundle_version"] == "v3"
    assert result["warnings"] == []
    assert onboarding_session.execute(
        text(
            """
            SELECT nome, dre_subcategoria_id
            FROM categorias_financeiras
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": TENANT_A},
    ).one() == ("CMV", 77)
    legacy_payload = onboarding_session.execute(
        text(
            """
            SELECT payload FROM template_items
            WHERE bundle_version = 'v2' AND template_code = 'fin_cmv'
            """
        )
    ).scalar_one()
    assert json.loads(legacy_payload)["dre_subcategory_code"] == "dre_cmv_produtos"

    compra = onboarding_session.execute(
        text(
            """
            SELECT nome, dre_subcategoria_id
            FROM categorias_financeiras
            WHERE tenant_id = :tenant_id AND nome = 'Produto para Revenda'
            """
        ),
        {"tenant_id": TENANT_B},
    ).one()
    assert compra == ("Produto para Revenda", None)
    assert (
        onboarding_session.execute(
            text(
                """
            SELECT COUNT(*) FROM tipo_despesas
            WHERE tenant_id = :tenant_id AND nome IN ('CMV', 'Produto para Revenda')
            """
            ),
            {"tenant_id": TENANT_B},
        ).scalar_one()
        == 0
    )
    assert (
        onboarding_session.execute(
            text(
                """
            SELECT COUNT(*)
            FROM categorias_financeiras AS categoria
            JOIN dre_subcategorias AS subcategoria
              ON subcategoria.id = categoria.dre_subcategoria_id
            WHERE categoria.tenant_id = :tenant_id
              AND subcategoria.nome = 'CMV - Produtos'
            """
            ),
            {"tenant_id": TENANT_B},
        ).scalar_one()
        == 0
    )
    assert onboarding_session.execute(
        text(
            """
            SELECT subcategoria.nome
            FROM dre_subcategorias AS subcategoria
            JOIN dre_categorias AS categoria ON categoria.id = subcategoria.categoria_id
            WHERE categoria.tenant_id = :tenant_id
              AND categoria.nome = 'Custo das Mercadorias Vendidas'
            ORDER BY subcategoria.nome
            """
        ),
        {"tenant_id": TENANT_B},
    ).scalars().all() == ["CMV - Produtos", "Fretes sobre Compras"]


def test_onboarding_is_idempotent_for_same_tenant(onboarding_session):
    onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False
    )
    onboarding_session.commit()

    second = onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False
    )
    onboarding_session.commit()

    assert second["created"] == {}
    for key, expected in BASE_EXPECTED_COUNTS.items():
        assert second["skipped"][key] == expected
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 5
    assert _count(onboarding_session, "contas_bancarias", TENANT_A) == 2
    assert _count(onboarding_session, "linhas_racao", TENANT_A) == 4
    assert _count(onboarding_session, "vet_catalogo_procedimentos", TENANT_A) == 70
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 12
    assert _count(onboarding_session, "tipo_despesas", TENANT_A) == 17
    assert _count(onboarding_session, "tenant_template_installs") == 1


def test_onboarding_item_mapping_survives_tenant_payment_edit(onboarding_session):
    onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False
    )
    onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_B, user_id=2, dry_run=False
    )
    onboarding_session.commit()

    pix_id = onboarding_session.execute(
        text(
            """
            SELECT id
            FROM formas_pagamento
            WHERE tenant_id = :tenant_id AND tipo = 'pix'
            """
        ),
        {"tenant_id": TENANT_A},
    ).scalar_one()
    onboarding_session.execute(
        text("UPDATE formas_pagamento SET nome = 'PIX Loja Centro' WHERE id = :id"),
        {"id": pix_id},
    )
    onboarding_session.commit()

    second = onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False
    )
    onboarding_session.commit()

    assert second["created"] == {}
    assert second["skipped"]["payment_methods"] == 5
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 5
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 5
    assert (
        onboarding_session.execute(
            text(
                "SELECT COUNT(*) FROM formas_pagamento WHERE tenant_id = :tenant_id AND tipo = 'pix'"
            ),
            {"tenant_id": TENANT_A},
        ).scalar()
        == 1
    )
    assert (
        onboarding_session.execute(
            text(
                "SELECT nome FROM formas_pagamento WHERE tenant_id = :tenant_id AND tipo = 'pix'"
            ),
            {"tenant_id": TENANT_A},
        ).scalar()
        == "PIX Loja Centro"
    )
    assert (
        onboarding_session.execute(
            text(
                "SELECT nome FROM formas_pagamento WHERE tenant_id = :tenant_id AND tipo = 'pix'"
            ),
            {"tenant_id": TENANT_B},
        ).scalar()
        == "PIX"
    )
    assert (
        onboarding_session.execute(
            text("SELECT name FROM template_items WHERE template_code = 'payment_pix'")
        ).scalar()
        == "PIX"
    )
    assert onboarding_session.execute(
        text(
            """
                SELECT target_table, target_id
                FROM tenant_template_item_installs
                WHERE tenant_id IN (:tenant_id, :tenant_id_hex)
                  AND template_code = 'payment_pix'
                """
        ),
        _tenant_params(TENANT_A),
    ).one() == ("formas_pagamento", pix_id)


def test_onboarding_item_mapping_survives_tenant_dre_category_edit(onboarding_session):
    onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False
    )
    onboarding_session.commit()

    receitas_id = onboarding_session.execute(
        text(
            """
            SELECT target_id
            FROM tenant_template_item_installs
            WHERE tenant_id IN (:tenant_id, :tenant_id_hex)
              AND template_code = 'dre_receitas'
            """
        ),
        _tenant_params(TENANT_A),
    ).scalar_one()
    onboarding_session.execute(
        text(
            "UPDATE dre_categorias SET nome = 'Receitas Loja Principal' WHERE id = :id"
        ),
        {"id": receitas_id},
    )
    onboarding_session.commit()

    second = onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False
    )
    onboarding_session.commit()

    assert second["created"] == {}
    assert second["skipped"]["dre_categories"] == 12
    assert second["skipped"]["dre_subcategories"] == 37
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 12
    assert _count(onboarding_session, "dre_subcategorias", TENANT_A) == 37
    assert (
        onboarding_session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM dre_subcategorias
                WHERE tenant_id = :tenant_id AND categoria_id = :categoria_id
                """
            ),
            {"tenant_id": TENANT_A, "categoria_id": receitas_id},
        ).scalar()
        == 2
    )


def test_onboarding_creates_isolated_copies_for_each_tenant(onboarding_session):
    onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False
    )
    onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_B, user_id=2, dry_run=False
    )
    onboarding_session.commit()

    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 5
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 5
    assert _count(onboarding_session, "dre_categorias", TENANT_A) == 12
    assert _count(onboarding_session, "dre_categorias", TENANT_B) == 12
    assert _count(onboarding_session, "tipo_despesas", TENANT_A) == 17
    assert _count(onboarding_session, "tipo_despesas", TENANT_B) == 17
    assert _count(onboarding_session, "vet_catalogo_procedimentos", TENANT_A) == 70
    assert _count(onboarding_session, "vet_catalogo_procedimentos", TENANT_B) == 70

    names_a = {
        row[0]
        for row in onboarding_session.execute(
            text("SELECT nome FROM formas_pagamento WHERE tenant_id = :tenant_id"),
            {"tenant_id": TENANT_A},
        )
    }
    names_b = {
        row[0]
        for row in onboarding_session.execute(
            text("SELECT nome FROM formas_pagamento WHERE tenant_id = :tenant_id"),
            {"tenant_id": TENANT_B},
        )
    }
    assert names_a == names_b


def test_onboarding_include_products_dry_run_does_not_create_catalog(
    onboarding_session,
):
    result = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=True,
        include_products=True,
    )

    assert result["would_create"]["product_references"] == 3
    assert _count(onboarding_session, "produtos", TENANT_A) == 0


def test_onboarding_include_products_apply_creates_inactive_reference_catalog(
    onboarding_session,
):
    result = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=False,
        include_products=True,
    )
    onboarding_session.commit()

    assert result["created"]["product_references"] == 3
    assert _count(onboarding_session, "produtos", TENANT_A) == 3
    products = onboarding_session.execute(
        text(
            """
            SELECT codigo, ativo, situacao, estoque_atual
            FROM produtos
            WHERE tenant_id = :tenant_id
            ORDER BY codigo
            """
        ),
        {"tenant_id": TENANT_A},
    ).all()
    assert {row[0] for row in products} == {
        "TPL-BRINQUEDO",
        "TPL-PETISCO-100G",
        "TPL-RACAO-ADULTO-1KG",
    }
    assert not any(bool(row[1]) for row in products)
    assert not any(bool(row[2]) for row in products)
    assert all(float(row[3]) == 0 for row in products)

    second = onboard_tenant_defaults(
        onboarding_session,
        tenant_id=TENANT_A,
        user_id=1,
        dry_run=False,
        include_products=True,
    )
    onboarding_session.commit()

    assert second["created"] == {}
    assert second["skipped"]["product_references"] == 3
    assert _count(onboarding_session, "produtos", TENANT_A) == 3


def test_onboarding_requires_tenant_and_user(onboarding_session):
    with pytest.raises(TenantOnboardingError, match="tenant_id"):
        onboard_tenant_defaults(onboarding_session, tenant_id=None, user_id=1)

    with pytest.raises(TenantOnboardingError, match="user_id"):
        onboard_tenant_defaults(onboarding_session, tenant_id=TENANT_A, user_id=None)


def test_onboarding_skips_sections_when_operational_schema_is_absent():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        result = onboard_tenant_defaults(
            session,
            tenant_id=TENANT_A,
            user_id=1,
            dry_run=False,
        )
    finally:
        session.close()

    assert result["created"] == {}
    assert result["would_create"] == {}
    assert any("schema ausente" in warning for warning in result["warnings"])
    assert any("tenant_template_installs" in warning for warning in result["warnings"])


def test_onboarding_strict_required_fails_when_operational_schema_is_absent():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        with pytest.raises(
            TenantOnboardingError, match="Onboarding obrigatorio incompleto"
        ):
            onboard_tenant_defaults(
                session,
                tenant_id=TENANT_A,
                user_id=1,
                dry_run=False,
                strict_required=True,
            )
    finally:
        session.close()
