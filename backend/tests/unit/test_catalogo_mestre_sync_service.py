import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.catalogo_mestre_models import (
    CatalogoMestreImagem,
    CatalogoMestrePendencia,
    CatalogoMestreProduto,
    CatalogoMestreSincronizacao,
)
from app.db import Base
from app.services.catalogo_mestre_service import (
    normalize_gtin,
    sync_catalogo_mestre_from_tenant,
)

SOURCE_TENANT = "11111111-1111-1111-1111-111111111111"


@pytest.fixture()
def catalog_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            CatalogoMestreProduto.__table__,
            CatalogoMestreImagem.__table__,
            CatalogoMestrePendencia.__table__,
            CatalogoMestreSincronizacao.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    ddl = [
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, email TEXT, tenant_id TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE marcas (
            id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, nome TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE categorias (
            id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, nome TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE departamentos (
            id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, nome TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, codigo TEXT,
            nome TEXT NOT NULL, tipo TEXT, situacao BOOLEAN, ativo BOOLEAN,
            is_sellable BOOLEAN, tipo_produto TEXT, deleted_at TEXT,
            codigo_barras TEXT, gtin_ean TEXT, gtin_ean_tributario TEXT,
            codigos_barras_alternativos TEXT, marca_id INTEGER,
            categoria_id INTEGER, departamento_id INTEGER, subcategoria TEXT,
            descricao_curta TEXT, descricao_completa TEXT, tags TEXT,
            unidade TEXT, ncm TEXT, cest TEXT, origem TEXT, cfop TEXT,
            peso_liquido REAL, peso_bruto REAL, peso_embalagem REAL,
            largura REAL, altura REAL, profundidade REAL, volume REAL,
            itens_por_caixa INTEGER, classificacao_racao TEXT,
            categoria_racao TEXT, especie_compativel TEXT,
            especies_indicadas TEXT, porte_animal TEXT, fase_publico TEXT,
            tipo_tratamento TEXT, sabor_proteina TEXT,
            tabela_nutricional TEXT, tabela_consumo TEXT,
            imagem_principal TEXT, updated_at TEXT
        )
        """,
        """
        CREATE TABLE produto_imagens (
            id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL,
            produto_id INTEGER NOT NULL, url TEXT NOT NULL, ordem INTEGER,
            e_principal BOOLEAN, tamanho INTEGER, largura INTEGER, altura INTEGER
        )
        """,
        """
        CREATE TABLE produto_config_fiscal (
            id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL,
            produto_id INTEGER NOT NULL, ncm TEXT, cest TEXT,
            origem_mercadoria TEXT, cst_icms TEXT, icms_aliquota REAL,
            cfop_venda TEXT, cfop_compra TEXT, pis_cst TEXT,
            pis_aliquota REAL, cofins_cst TEXT, cofins_aliquota REAL
        )
        """,
    ]
    for statement in ddl:
        session.execute(text(statement))
    session.execute(
        text(
            "INSERT INTO users (id, email, tenant_id) "
            "VALUES (2, 'atacadaopetpp@gmail.com', :tenant)"
        ),
        {"tenant": SOURCE_TENANT},
    )
    for table, name in (
        ("marcas", "Royal Canin"),
        ("categorias", "Racoes"),
        ("departamentos", "Alimentos"),
    ):
        session.execute(
            text(
                f"INSERT INTO {table} (id, tenant_id, nome) VALUES (1, :tenant, :name)"
            ),
            {"tenant": SOURCE_TENANT, "name": name},
        )
    session.execute(
        text("""
            INSERT INTO produtos (
                id, tenant_id, codigo, nome, tipo, situacao, ativo, is_sellable,
                tipo_produto, codigo_barras, marca_id, categoria_id,
                departamento_id, descricao_curta, descricao_completa, unidade,
                ncm, cest, origem, peso_embalagem, classificacao_racao,
                categoria_racao, especie_compativel, sabor_proteina,
                tabela_nutricional, tabela_consumo, imagem_principal, updated_at
            ) VALUES (
                10, :tenant, 'RC-10', 'Royal Canin Adulto 10kg', 'produto',
                1, 1, 1, 'SIMPLES', '7898242036467', 1, 1, 1,
                'Racao completa para caes adultos',
                'Alimento completo, balanceado e indicado para caes adultos.',
                'UN', '00000000', NULL, '0', 10, 'super_premium', 'adulto',
                'dog', 'frango', '{"proteina": 28}', '{"10kg": "150g"}',
                'https://img.test/royal-frente.webp', '2026-08-29T10:00:00Z'
            )
            """),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text("""
            INSERT INTO produto_imagens (
                id, tenant_id, produto_id, url, ordem, e_principal,
                tamanho, largura, altura
            ) VALUES
                (20, :tenant, 10, 'https://img.test/royal-frente.webp', 0, 1,
                 1000, 800, 800),
                (21, :tenant, 10, 'https://img.test/royal-verso.webp', 1, 0,
                 1200, 800, 800)
            """),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text("""
            INSERT INTO produto_config_fiscal (
                id, tenant_id, produto_id, ncm, cest, origem_mercadoria,
                cst_icms, icms_aliquota, cfop_venda
            ) VALUES (
                30, :tenant, 10, '23099010', '2200100', '0', '000', 18, '5102'
            )
            """),
        {"tenant": SOURCE_TENANT},
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()


def _source_snapshot(session):
    return dict(
        session.execute(text("SELECT * FROM produtos WHERE id=10")).mappings().one()
    )


def test_normalize_gtin_validates_check_digit():
    assert normalize_gtin("7898242036467") == "7898242036467"
    assert normalize_gtin("7898242036468") is None
    assert normalize_gtin("SEM-EAN") is None


def test_dry_run_reports_catalog_and_never_writes(catalog_session):
    source_before = _source_snapshot(catalog_session)

    result = sync_catalogo_mestre_from_tenant(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        dry_run=True,
        image_target=5,
    )

    assert result["eligible_products"] == 1
    assert result["would_create_products"] == 1
    assert result["would_import_images"] == 2
    assert result["products_below_image_target"] == 1
    assert result["image_slots_missing"] == 3
    assert result["would_create_pending_tasks"] == 3
    assert (
        catalog_session.execute(
            text("SELECT count(*) FROM catalogo_mestre_produtos")
        ).scalar()
        == 0
    )
    assert _source_snapshot(catalog_session) == source_before


def test_apply_is_idempotent_and_only_writes_master_tables(catalog_session):
    source_before = _source_snapshot(catalog_session)

    first = sync_catalogo_mestre_from_tenant(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        source_identifier="atacadaopetpp@gmail.com",
        dry_run=False,
        image_target=5,
    )
    catalog_session.commit()

    master = dict(
        catalog_session.execute(text("SELECT * FROM catalogo_mestre_produtos"))
        .mappings()
        .one()
    )
    assert first["created_products"] == 1
    assert first["imported_images"] == 2
    assert first["created_pending_tasks"] == 3
    assert master["ncm"] == "23099010"
    assert master["cest"] == "2200100"
    assert master["imagem_quantidade"] == 2
    assert master["imagem_faltantes"] == 3
    assert _source_snapshot(catalog_session) == source_before
    assert (
        catalog_session.execute(
            text("SELECT count(*) FROM catalogo_mestre_pendencias WHERE tipo='imagem'")
        ).scalar()
        == 3
    )

    second = sync_catalogo_mestre_from_tenant(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        source_identifier="atacadaopetpp@gmail.com",
        dry_run=False,
        image_target=5,
    )
    catalog_session.commit()

    assert second["created_products"] == 0
    assert second["updated_products"] == 0
    assert second["unchanged_products"] == 1
    assert second["imported_images"] == 0
    assert second["created_pending_tasks"] == 0
    assert _source_snapshot(catalog_session) == source_before


def test_duplicate_gtin_is_queued_for_review_without_automatic_merge(catalog_session):
    catalog_session.execute(
        text("""
            INSERT INTO produtos (
                id, tenant_id, codigo, nome, tipo, situacao, ativo, is_sellable,
                tipo_produto, codigo_barras, marca_id, categoria_id, departamento_id
            ) VALUES (
                11, :tenant, 'DUP-11', 'Outro produto com EAN repetido', 'produto',
                1, 1, 1, 'SIMPLES', '7898242036467', 1, 1, 1
            )
            """),
        {"tenant": SOURCE_TENANT},
    )
    catalog_session.commit()

    result = sync_catalogo_mestre_from_tenant(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        dry_run=True,
    )

    assert result["eligible_products"] == 2
    assert result["duplicate_gtins"] == 2
    assert result["valid_gtins"] == 0
    assert "sem fusao automatica" in result["warnings"][0]


def test_new_source_image_reduces_backlog_without_touching_source_product(
    catalog_session,
):
    sync_catalogo_mestre_from_tenant(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        dry_run=False,
        image_target=5,
    )
    catalog_session.commit()
    source_before = _source_snapshot(catalog_session)
    catalog_session.execute(
        text("""
            INSERT INTO produto_imagens (
                id, tenant_id, produto_id, url, ordem, e_principal
            ) VALUES (
                22, :tenant, 10, 'https://img.test/royal-lateral.webp', 2, 0
            )
            """),
        {"tenant": SOURCE_TENANT},
    )
    catalog_session.commit()

    result = sync_catalogo_mestre_from_tenant(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        dry_run=False,
        image_target=5,
    )
    catalog_session.commit()

    master = catalog_session.execute(
        text(
            "SELECT imagem_quantidade, imagem_faltantes "
            "FROM catalogo_mestre_produtos"
        )
    ).one()
    assert result["imported_images"] == 1
    assert result["resolved_pending_tasks"] == 1
    assert tuple(master) == (3, 2)
    assert (
        catalog_session.execute(
            text(
                "SELECT status FROM catalogo_mestre_pendencias "
                "WHERE tipo='imagem' AND posicao_alvo=3"
            )
        ).scalar()
        == "resolvida"
    )
    assert _source_snapshot(catalog_session) == source_before


def test_curated_field_is_not_overwritten_by_source_resync(catalog_session):
    sync_catalogo_mestre_from_tenant(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        dry_run=False,
    )
    catalog_session.commit()
    master = dict(
        catalog_session.execute(
            text("SELECT id, proveniencia FROM catalogo_mestre_produtos")
        )
        .mappings()
        .one()
    )
    provenance = json.loads(master["proveniencia"])
    provenance["campos"]["descricao_completa"] = {
        "tipo": "curadoria_humana",
        "revisor": 99,
    }
    catalog_session.execute(
        text(
            "UPDATE catalogo_mestre_produtos "
            "SET descricao_completa=:description, proveniencia=:provenance "
            "WHERE id=:product_id"
        ),
        {
            "description": "Descricao revisada e aprovada.",
            "provenance": json.dumps(provenance),
            "product_id": master["id"],
        },
    )
    catalog_session.execute(
        text(
            "UPDATE produtos SET descricao_completa='Texto novo da origem' WHERE id=10"
        )
    )
    catalog_session.commit()

    result = sync_catalogo_mestre_from_tenant(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        dry_run=False,
    )
    catalog_session.commit()

    assert result["updated_products"] == 1
    assert (
        catalog_session.execute(
            text("SELECT descricao_completa FROM catalogo_mestre_produtos")
        ).scalar()
        == "Descricao revisada e aprovada."
    )


def test_master_product_has_no_operational_commercial_columns():
    columns = {column.name for column in CatalogoMestreProduto.__table__.columns}
    forbidden = {
        "preco_custo",
        "preco_venda",
        "estoque_atual",
        "fornecedor_id",
        "comissao_padrao",
        "limite_desconto",
    }
    assert not columns.intersection(forbidden)
    assert {"gtin", "ncm", "cest", "bula_conteudo", "posologia"}.issubset(columns)


def test_sync_service_has_no_write_statement_for_tenant_product_tables():
    service_path = (
        Path(__file__).resolve().parents[2]
        / "app/services/catalogo_mestre_sync_service.py"
    )
    source = service_path.read_text(encoding="utf-8").casefold()
    for operation in ("insert into", "update", "delete from"):
        for table_name in (
            "produtos",
            "produto_imagens",
            "produto_config_fiscal",
            "marcas",
            "categorias",
            "departamentos",
        ):
            assert f"{operation} {table_name}" not in source
