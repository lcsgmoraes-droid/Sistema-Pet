import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.services.base_catalog_enrichment_service import (
    enrich_existing_products_by_gtin,
)


SOURCE_TENANT = "11111111-1111-1111-1111-111111111111"
TARGET_TENANT = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def enrichment_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session = sessionmaker(bind=engine)()
    ddl = [
        "CREATE TABLE tenants (id TEXT PRIMARY KEY)",
        """
        CREATE TABLE departamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL,
            user_id INTEGER, nome TEXT NOT NULL, descricao TEXT, ativo BOOLEAN,
            created_at TEXT, updated_at TEXT
        )
        """,
        """
        CREATE TABLE categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL,
            user_id INTEGER, nome TEXT NOT NULL, departamento_id INTEGER,
            categoria_pai_id INTEGER, descricao TEXT, ativo BOOLEAN,
            created_at TEXT, updated_at TEXT
        )
        """,
        """
        CREATE TABLE marcas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL,
            user_id INTEGER, nome TEXT NOT NULL, descricao TEXT, ativo BOOLEAN,
            created_at TEXT, updated_at TEXT
        )
        """,
        """
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL,
            user_id INTEGER, codigo TEXT NOT NULL, nome TEXT NOT NULL,
            codigo_barras TEXT, descricao_curta TEXT, descricao_completa TEXT,
            categoria_id INTEGER, marca_id INTEGER, departamento_id INTEGER,
            ncm TEXT, cest TEXT, origem TEXT, cfop TEXT, imagem_principal TEXT,
            preco_custo REAL, preco_venda REAL, estoque_atual REAL,
            situacao BOOLEAN, ativo BOOLEAN, deleted_at TEXT,
            created_at TEXT, updated_at TEXT
        )
        """,
        """
        CREATE TABLE produto_imagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL,
            produto_id INTEGER NOT NULL, url TEXT NOT NULL, ordem INTEGER,
            e_principal BOOLEAN, tamanho INTEGER, largura INTEGER, altura INTEGER,
            created_at TEXT, updated_at TEXT
        )
        """,
    ]
    for statement in ddl:
        session.execute(text(statement))
    session.execute(
        text("INSERT INTO tenants (id) VALUES (:source), (:target)"),
        {"source": SOURCE_TENANT, "target": TARGET_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO departamentos (id, tenant_id, user_id, nome, ativo)
            VALUES (1, :tenant, 1, 'Produtos', 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO categorias
                (id, tenant_id, user_id, nome, departamento_id, ativo)
            VALUES (2, :tenant, 1, 'Racoes', 1, 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO categorias (id, tenant_id, user_id, nome, ativo)
            VALUES (3, :tenant, 10, 'A classificar', 1)
            """
        ),
        {"tenant": TARGET_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO marcas (id, tenant_id, user_id, nome, ativo)
            VALUES (4, :tenant, 1, 'Special Dog', 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO produtos (
                id, tenant_id, user_id, codigo, nome, codigo_barras,
                descricao_curta, categoria_id, marca_id, departamento_id,
                ncm, cest, origem, cfop, imagem_principal,
                preco_custo, preco_venda, estoque_atual, situacao, ativo
            ) VALUES (
                11, :tenant, 1, 'BASE-11', 'Special Dog Base', '7898242036467',
                'Racao completa', 2, 4, 1,
                '23099010', '2200100', '0', '5102',
                'https://img.test/special-dog.webp',
                1, 2, 3, 1, 1
            )
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO produtos (
                id, tenant_id, user_id, codigo, nome, codigo_barras,
                categoria_id, preco_custo, preco_venda, estoque_atual,
                situacao, ativo
            ) VALUES (
                22, :tenant, 10, 'LEGADO-22', 'Special Dog Base do cliente',
                '7898242036467', 3, 59.85, 97, 7, 1, 1
            )
            """
        ),
        {"tenant": TARGET_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO produto_imagens
                (id, tenant_id, produto_id, url, ordem, e_principal)
            VALUES (31, :tenant, 11, 'https://img.test/special-dog.webp', 0, 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()


def _target_product(session):
    return dict(
        session.execute(
            text("SELECT * FROM produtos WHERE id=22 AND tenant_id=:tenant"),
            {"tenant": TARGET_TENANT},
        )
        .mappings()
        .one()
    )


def test_dry_run_nao_grava_e_mostra_campos_seguros(enrichment_session):
    before = _target_product(enrichment_session)

    result = enrich_existing_products_by_gtin(
        db=enrichment_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=True,
    )

    assert result["matched_products"] == 1
    assert result["compatible_products"] == 1
    assert result["incompatible_products"] == 0
    assert result["would_update_products"] == 1
    assert result["would_copy_images"] == 1
    assert result["fields"]["ncm"] == 1
    assert result["fields"]["categoria_id"] == 1
    assert _target_product(enrichment_session) == before


def test_apply_enriquece_sem_criar_produto_ou_mudar_dados_comerciais(
    enrichment_session,
):
    result = enrich_existing_products_by_gtin(
        db=enrichment_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=False,
    )
    enrichment_session.commit()

    target = _target_product(enrichment_session)
    assert result["updated_products"] == 1
    assert result["copied_images"] == 1
    assert target["nome"] == "Special Dog Base do cliente"
    assert target["descricao_curta"] == "Racao completa"
    assert target["ncm"] == "23099010"
    assert target["cest"] == "2200100"
    assert target["origem"] == "0"
    assert target["cfop"] == "5102"
    assert target["preco_custo"] == 59.85
    assert target["preco_venda"] == 97
    assert target["estoque_atual"] == 7
    assert target["imagem_principal"] == "https://img.test/special-dog.webp"
    assert (
        enrichment_session.execute(text("SELECT count(*) FROM produtos")).scalar() == 2
    )

    rerun = enrich_existing_products_by_gtin(
        db=enrichment_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=False,
    )
    assert rerun["updated_products"] == 0
    assert rerun["copied_images"] == 0


def test_apply_bloqueia_gtin_com_nomes_e_dosagens_incompativeis(
    enrichment_session,
):
    enrichment_session.execute(
        text(
            "UPDATE produtos "
            "SET nome='Maxicam Dipy 2.0mg com 10 Comprimidos' WHERE id=11"
        )
    )
    enrichment_session.execute(
        text("UPDATE produtos SET nome='PREDIDERM 20MG - DISPLAY 15X10CP' WHERE id=22")
    )
    enrichment_session.commit()

    result = enrich_existing_products_by_gtin(
        db=enrichment_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=False,
    )
    enrichment_session.commit()

    target = _target_product(enrichment_session)
    assert result["matched_products"] == 1
    assert result["compatible_products"] == 0
    assert result["incompatible_products"] == 1
    assert result["updated_products"] == 0
    assert result["copied_images"] == 0
    assert result["rejected_samples"][0]["gtin"] == "7898242036467"
    assert target["descricao_curta"] is None
    assert target["imagem_principal"] is None
    assert target["preco_custo"] == 59.85
    assert target["preco_venda"] == 97
