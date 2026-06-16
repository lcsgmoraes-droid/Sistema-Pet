
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.services import base_catalog_import_service
from app.services.base_catalog_import_service import (
    BaseCatalogImportError,
    import_base_catalog,
)


SOURCE_TENANT = "11111111-1111-1111-1111-111111111111"
TARGET_TENANT = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def catalog_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    ddl = [
        """
        CREATE TABLE tenants (
            id TEXT PRIMARY KEY,
            status TEXT
        )
        """,
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            tenant_id TEXT,
            is_active BOOLEAN
        )
        """,
        """
        CREATE TABLE tenant_template_installs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            bundle_code TEXT NOT NULL,
            bundle_version TEXT NOT NULL,
            status TEXT NOT NULL,
            dry_run BOOLEAN NOT NULL,
            created_by_user_id INTEGER,
            summary JSON NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE tenant_template_item_installs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            bundle_code TEXT NOT NULL,
            bundle_version TEXT NOT NULL,
            item_type TEXT NOT NULL,
            template_code TEXT NOT NULL,
            target_table TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_by_user_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE departamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER,
            nome TEXT NOT NULL,
            descricao TEXT,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER,
            nome TEXT NOT NULL,
            categoria_pai_id INTEGER,
            departamento_id INTEGER,
            descricao TEXT,
            icone TEXT,
            cor TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE marcas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER,
            nome TEXT NOT NULL,
            descricao TEXT,
            logo TEXT,
            site TEXT,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE linhas_racao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE portes_animal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE fases_publico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE tipos_tratamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE sabores_proteina (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE apresentacoes_peso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            peso_kg REAL NOT NULL,
            descricao TEXT,
            ordem INTEGER,
            ativo BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT,
            situacao BOOLEAN,
            tipo_produto TEXT,
            produto_pai_id INTEGER,
            is_parent BOOLEAN,
            is_sellable BOOLEAN,
            tipo_kit TEXT,
            descricao_curta TEXT,
            descricao_completa TEXT,
            tags TEXT,
            codigo_barras TEXT,
            codigos_barras_alternativos TEXT,
            categoria_id INTEGER,
            subcategoria TEXT,
            marca_id INTEGER,
            fornecedor_id INTEGER,
            departamento_id INTEGER,
            preco_custo REAL,
            preco_venda REAL,
            preco_promocional REAL,
            promocao_inicio TEXT,
            promocao_fim TEXT,
            promocao_ativa BOOLEAN,
            preco_ecommerce REAL,
            preco_ecommerce_promo REAL,
            preco_ecommerce_promo_inicio TEXT,
            preco_ecommerce_promo_fim TEXT,
            preco_app REAL,
            preco_app_promo REAL,
            preco_app_promo_inicio TEXT,
            preco_app_promo_fim TEXT,
            estoque_atual REAL,
            estoque_minimo REAL,
            estoque_maximo REAL,
            estoque_fisico REAL,
            estoque_ecommerce REAL,
            localizacao TEXT,
            crossdocking_dias INTEGER,
            controle_lote BOOLEAN,
            unidade TEXT,
            condicao TEXT,
            e_granel BOOLEAN,
            participa_sugestao_compra BOOLEAN,
            peso_liquido REAL,
            peso_bruto REAL,
            ncm TEXT,
            origem TEXT,
            tem_recorrencia BOOLEAN,
            tipo_recorrencia TEXT,
            intervalo_dias INTEGER,
            numero_doses INTEGER,
            especie_compativel TEXT,
            classificacao_racao TEXT,
            peso_embalagem REAL,
            categoria_racao TEXT,
            especies_indicadas TEXT,
            porte_animal TEXT,
            fase_publico TEXT,
            tipo_tratamento TEXT,
            sabor_proteina TEXT,
            linha_racao_id INTEGER,
            porte_animal_id INTEGER,
            fase_publico_id INTEGER,
            tipo_tratamento_id INTEGER,
            sabor_proteina_id INTEGER,
            apresentacao_peso_id INTEGER,
            imagem_principal TEXT,
            ativo BOOLEAN,
            produto_predecessor_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE produto_imagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            produto_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            ordem INTEGER,
            e_principal BOOLEAN,
            tamanho INTEGER,
            largura INTEGER,
            altura INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE produto_kit_componentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            kit_id INTEGER NOT NULL,
            produto_componente_id INTEGER NOT NULL,
            quantidade REAL,
            opcional BOOLEAN,
            ordem INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE produto_granel_vinculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            produto_origem_id INTEGER NOT NULL,
            produto_granel_id INTEGER NOT NULL,
            ativo BOOLEAN,
            observacao TEXT,
            user_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE produto_lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade_disponivel REAL
        )
        """,
        """
        CREATE TABLE produto_fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            produto_id INTEGER NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            preco_custo REAL
        )
        """,
        """
        CREATE TABLE produtos_historico_precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            produto_id INTEGER NOT NULL,
            preco_custo_novo REAL,
            preco_venda_novo REAL
        )
        """,
    ]
    for statement in ddl:
        session.execute(text(statement))

    session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": SOURCE_TENANT})
    session.execute(text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"), {"id": TARGET_TENANT})
    session.execute(
        text("INSERT INTO users (id, email, tenant_id, is_active) VALUES (10, 'admin@destino.test', :tenant, 1)"),
        {"tenant": TARGET_TENANT},
    )
    session.commit()

    try:
        yield session
    finally:
        session.close()


def count(session, table, tenant_id):
    return session.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tenant_id"),
        {"tenant_id": tenant_id},
    ).scalar()


def one_target_product(session, codigo="BASE-001"):
    row = session.execute(
        text("SELECT * FROM produtos WHERE tenant_id = :tenant_id AND codigo = :codigo"),
        {"tenant_id": TARGET_TENANT, "codigo": codigo},
    ).mappings().one()
    return dict(row)


def _insert_base_support(session):
    session.execute(
        text(
            """
            INSERT INTO departamentos (id, tenant_id, user_id, nome, descricao, ativo)
            VALUES (1, :tenant, 1, 'Produtos', 'Grupo principal', 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO categorias (id, tenant_id, user_id, nome, departamento_id, descricao, icone, cor, ordem, ativo)
            VALUES (11, :tenant, 1, 'Racoes', 1, 'Alimentos', 'package', '#111111', 1, 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text(
            """
            INSERT INTO marcas (id, tenant_id, user_id, nome, descricao, logo, site, ativo)
            VALUES (21, :tenant, 1, 'Marca Base', 'Marca de referencia', 'logo.png', 'https://marca.test', 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )


def _insert_base_options(session):
    option_rows = [
        ("linhas_racao", 31, "Super Premium"),
        ("portes_animal", 32, "Pequeno"),
        ("fases_publico", 33, "Adulto"),
        ("tipos_tratamento", 34, "Digestivo"),
        ("sabores_proteina", 35, "Frango"),
    ]
    for table_name, row_id, name in option_rows:
        session.execute(
            text(
                f"""
                INSERT INTO {table_name} (id, tenant_id, nome, descricao, ordem, ativo)
                VALUES (:id, :tenant, :nome, :descricao, 1, 1)
                """
            ),
            {"id": row_id, "tenant": SOURCE_TENANT, "nome": name, "descricao": name},
        )
    session.execute(
        text(
            """
            INSERT INTO apresentacoes_peso (id, tenant_id, peso_kg, descricao, ordem, ativo)
            VALUES (36, :tenant, 15.0, '15kg', 1, 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )


def _insert_source_product(session, *, product_id=101, codigo="BASE-001", nome="Racao Base", **overrides):
    values = {
        "id": product_id,
        "tenant_id": SOURCE_TENANT,
        "user_id": 1,
        "codigo": codigo,
        "nome": nome,
        "tipo": "produto",
        "situacao": 1,
        "tipo_produto": "SIMPLES",
        "produto_pai_id": None,
        "is_parent": 0,
        "is_sellable": 1,
        "tipo_kit": None,
        "descricao_curta": "Descricao curta",
        "categoria_id": 11,
        "marca_id": 21,
        "fornecedor_id": 900,
        "departamento_id": 1,
        "preco_custo": 123.45,
        "preco_venda": 199.9,
        "preco_promocional": 179.9,
        "promocao_ativa": 1,
        "preco_ecommerce": 209.9,
        "preco_app": 189.9,
        "estoque_atual": 7,
        "estoque_minimo": 2,
        "estoque_maximo": 20,
        "estoque_fisico": 8,
        "estoque_ecommerce": 6,
        "localizacao": "A1",
        "crossdocking_dias": 3,
        "controle_lote": 1,
        "unidade": "UN",
        "condicao": "novo",
        "e_granel": 0,
        "participa_sugestao_compra": 1,
        "linha_racao_id": 31,
        "porte_animal_id": 32,
        "fase_publico_id": 33,
        "tipo_tratamento_id": 34,
        "sabor_proteina_id": 35,
        "apresentacao_peso_id": 36,
        "imagem_principal": f"https://img.mlprohub.com.br/produtos/{SOURCE_TENANT}/{product_id}/originais/main.webp",
        "ativo": 1,
        "produto_predecessor_id": None,
    }
    values.update(overrides)
    columns = ", ".join(values)
    params = ", ".join(f":{key}" for key in values)
    session.execute(text(f"INSERT INTO produtos ({columns}) VALUES ({params})"), values)


def _seed_basic_catalog(session):
    _insert_base_support(session)
    _insert_base_options(session)
    _insert_source_product(session)
    session.execute(
        text(
            """
            INSERT INTO produto_imagens (id, tenant_id, produto_id, url, ordem, e_principal, tamanho, largura, altura)
            VALUES (1001, :tenant, 101, :url, 0, 1, 1234, 800, 600)
            """
        ),
        {
            "tenant": SOURCE_TENANT,
            "url": f"https://img.mlprohub.com.br/produtos/{SOURCE_TENANT}/101/originais/main.webp",
        },
    )
    session.execute(
        text("INSERT INTO produto_lotes (tenant_id, produto_id, quantidade_disponivel) VALUES (:tenant, 101, 5)"),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text("INSERT INTO produto_fornecedores (tenant_id, produto_id, fornecedor_id, preco_custo) VALUES (:tenant, 101, 900, 123.45)"),
        {"tenant": SOURCE_TENANT},
    )
    session.execute(
        text("INSERT INTO produtos_historico_precos (tenant_id, produto_id, preco_custo_novo, preco_venda_novo) VALUES (:tenant, 101, 123.45, 199.9)"),
        {"tenant": SOURCE_TENANT},
    )
    session.commit()


def fake_image_copier(url, *, source_tenant_id, source_product_id, target_tenant_id, target_product_id):
    return (
        str(url)
        .replace(str(source_tenant_id), str(target_tenant_id))
        .replace(f"/{source_product_id}/", f"/{target_product_id}/")
    )


def test_import_base_catalog_dry_run_does_not_create_rows(catalog_session):
    _seed_basic_catalog(catalog_session)

    result = import_base_catalog(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=True,
        image_copier=fake_image_copier,
    )

    assert result["dry_run"] is True
    assert result["would_create"]["departamentos"] == 1
    assert result["would_create"]["categorias"] == 1
    assert result["would_create"]["marcas"] == 1
    assert result["would_create"]["linhas_racao"] == 1
    assert result["would_create"]["produtos"] == 1
    assert result["would_create"]["produto_imagens"] == 1
    assert count(catalog_session, "produtos", TARGET_TENANT) == 0
    assert count(catalog_session, "produto_lotes", TARGET_TENANT) == 0
    assert count(catalog_session, "produto_fornecedores", TARGET_TENANT) == 0


def test_import_base_catalog_apply_sanitizes_operational_product_fields(catalog_session):
    _seed_basic_catalog(catalog_session)

    result = import_base_catalog(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=False,
        image_copier=fake_image_copier,
    )
    catalog_session.commit()

    assert result["created"]["produtos"] == 1
    product = one_target_product(catalog_session)
    assert product["estoque_atual"] == 0
    assert product["estoque_fisico"] == 0
    assert product["estoque_ecommerce"] == 0
    assert product["estoque_minimo"] == 0
    assert product["estoque_maximo"] == 0
    assert product["preco_custo"] == 0
    assert product["preco_venda"] == 0
    assert product["preco_promocional"] is None
    assert product["preco_app"] is None
    assert product["preco_ecommerce"] is None
    assert product["promocao_ativa"] == 0
    assert product["fornecedor_id"] is None
    assert product["controle_lote"] == 0
    assert product["localizacao"] is None
    assert count(catalog_session, "produto_lotes", TARGET_TENANT) == 0
    assert count(catalog_session, "produto_fornecedores", TARGET_TENANT) == 0
    assert count(catalog_session, "produtos_historico_precos", TARGET_TENANT) == 0


def test_import_remaps_catalog_support_records(catalog_session):
    _seed_basic_catalog(catalog_session)
    catalog_session.execute(
        text(
            """
            INSERT INTO categorias (id, tenant_id, user_id, nome, categoria_pai_id, departamento_id, descricao, ordem, ativo)
            VALUES (12, :tenant, 1, 'Racoes Secas', 11, 1, 'Subcategoria', 2, 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    catalog_session.execute(
        text("UPDATE produtos SET categoria_id = 12 WHERE id = 101 AND tenant_id = :tenant"),
        {"tenant": SOURCE_TENANT},
    )
    catalog_session.commit()

    import_base_catalog(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=False,
        image_copier=fake_image_copier,
    )
    catalog_session.commit()

    target_product = one_target_product(catalog_session)
    assert target_product["categoria_id"] not in {11, 12}
    assert target_product["departamento_id"] != 1
    assert target_product["marca_id"] != 21
    assert target_product["linha_racao_id"] != 31

    category = catalog_session.execute(
        text("SELECT * FROM categorias WHERE tenant_id=:tenant AND nome='Racoes Secas'"),
        {"tenant": TARGET_TENANT},
    ).mappings().one()
    parent = catalog_session.execute(
        text("SELECT * FROM categorias WHERE tenant_id=:tenant AND nome='Racoes'"),
        {"tenant": TARGET_TENANT},
    ).mappings().one()
    assert category["categoria_pai_id"] == parent["id"]
    assert category["departamento_id"] == target_product["departamento_id"]


def test_import_remaps_product_relations_and_images(catalog_session):
    _seed_basic_catalog(catalog_session)
    _insert_source_product(
        catalog_session,
        product_id=102,
        codigo="BASE-PAI",
        nome="Produto Pai",
        tipo_produto="PAI",
        is_parent=1,
        is_sellable=0,
        imagem_principal=None,
    )
    _insert_source_product(
        catalog_session,
        product_id=103,
        codigo="BASE-FILHO",
        nome="Produto Filho",
        produto_pai_id=102,
        produto_predecessor_id=101,
    )
    _insert_source_product(
        catalog_session,
        product_id=104,
        codigo="BASE-KIT",
        nome="Kit Base",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
    )
    _insert_source_product(
        catalog_session,
        product_id=105,
        codigo="BASE-GRANEL",
        nome="Granel Base",
        e_granel=1,
    )
    catalog_session.execute(
        text(
            """
            INSERT INTO produto_kit_componentes (id, tenant_id, kit_id, produto_componente_id, quantidade, opcional, ordem)
            VALUES (2001, :tenant, 104, 101, 2, 0, 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    catalog_session.execute(
        text(
            """
            INSERT INTO produto_granel_vinculos (id, tenant_id, produto_origem_id, produto_granel_id, ativo, observacao, user_id)
            VALUES (3001, :tenant, 101, 105, 1, 'granel', 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    catalog_session.commit()

    import_base_catalog(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=False,
        image_copier=fake_image_copier,
    )
    catalog_session.commit()

    filho = one_target_product(catalog_session, "BASE-FILHO")
    predecessor = one_target_product(catalog_session, "BASE-001")
    pai = one_target_product(catalog_session, "BASE-PAI")
    assert filho["produto_pai_id"] == pai["id"]
    assert filho["produto_predecessor_id"] == predecessor["id"]

    kit_component = catalog_session.execute(
        text("SELECT * FROM produto_kit_componentes WHERE tenant_id=:tenant"),
        {"tenant": TARGET_TENANT},
    ).mappings().one()
    assert kit_component["kit_id"] == one_target_product(catalog_session, "BASE-KIT")["id"]
    assert kit_component["produto_componente_id"] == predecessor["id"]

    granel = catalog_session.execute(
        text("SELECT * FROM produto_granel_vinculos WHERE tenant_id=:tenant"),
        {"tenant": TARGET_TENANT},
    ).mappings().one()
    assert granel["produto_origem_id"] == predecessor["id"]
    assert granel["produto_granel_id"] == one_target_product(catalog_session, "BASE-GRANEL")["id"]

    image = catalog_session.execute(
        text("SELECT * FROM produto_imagens WHERE tenant_id=:tenant"),
        {"tenant": TARGET_TENANT},
    ).mappings().one()
    assert SOURCE_TENANT not in image["url"]
    assert TARGET_TENANT in image["url"]
    assert f"/{predecessor['id']}/" in image["url"]
    assert one_target_product(catalog_session)["imagem_principal"] == image["url"]


def test_import_syncs_rls_context_for_source_and_target_product_relations(catalog_session, monkeypatch):
    _seed_basic_catalog(catalog_session)
    _insert_source_product(
        catalog_session,
        product_id=104,
        codigo="BASE-KIT",
        nome="Kit Base",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
    )
    _insert_source_product(
        catalog_session,
        product_id=105,
        codigo="BASE-GRANEL",
        nome="Granel Base",
        e_granel=1,
    )
    catalog_session.execute(
        text(
            """
            INSERT INTO produto_kit_componentes (id, tenant_id, kit_id, produto_componente_id, quantidade, opcional, ordem)
            VALUES (2001, :tenant, 104, 101, 2, 0, 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    catalog_session.execute(
        text(
            """
            INSERT INTO produto_granel_vinculos (id, tenant_id, produto_origem_id, produto_granel_id, ativo, observacao, user_id)
            VALUES (3001, :tenant, 101, 105, 1, 'granel', 1)
            """
        ),
        {"tenant": SOURCE_TENANT},
    )
    catalog_session.commit()

    synced_tenants = []

    def fake_sync_rls_tenant(db, tenant_id=None):
        synced_tenants.append(str(tenant_id))
        return True

    monkeypatch.setattr(
        base_catalog_import_service,
        "sync_rls_tenant",
        fake_sync_rls_tenant,
        raising=False,
    )

    import_base_catalog(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=False,
        image_copier=fake_image_copier,
    )

    assert SOURCE_TENANT in synced_tenants
    assert TARGET_TENANT in synced_tenants
    assert synced_tenants.count(SOURCE_TENANT) >= 3
    assert synced_tenants.count(TARGET_TENANT) >= 3


def test_import_is_idempotent_and_preserves_target_edits(catalog_session):
    _seed_basic_catalog(catalog_session)
    import_base_catalog(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=False,
        image_copier=fake_image_copier,
    )
    catalog_session.commit()
    target_id = one_target_product(catalog_session)["id"]
    catalog_session.execute(
        text("UPDATE produtos SET nome='Nome editado no cliente', preco_venda=55 WHERE id=:id"),
        {"id": target_id},
    )
    catalog_session.commit()

    second = import_base_catalog(
        db=catalog_session,
        source_tenant_id=SOURCE_TENANT,
        target_tenant_id=TARGET_TENANT,
        user_id=10,
        dry_run=False,
        image_copier=fake_image_copier,
    )
    catalog_session.commit()

    assert second["created"] == {}
    assert second["skipped"]["produtos"] == 1
    product = one_target_product(catalog_session)
    assert product["nome"] == "Nome editado no cliente"
    assert product["preco_venda"] == 55
    assert count(catalog_session, "produtos", TARGET_TENANT) == 1


def test_import_rejects_same_source_and_target(catalog_session):
    with pytest.raises(BaseCatalogImportError, match="fonte e destino"):
        import_base_catalog(
            db=catalog_session,
            source_tenant_id=SOURCE_TENANT,
            target_tenant_id=SOURCE_TENANT,
            user_id=10,
            dry_run=True,
        )
