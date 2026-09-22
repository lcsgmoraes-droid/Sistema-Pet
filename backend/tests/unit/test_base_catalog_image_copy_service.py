import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.services import base_catalog_image_copy_service as service

SOURCE = "11111111-1111-1111-1111-111111111111"
TARGET = "22222222-2222-2222-2222-222222222222"
GTIN = "7898242036467"


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session = sessionmaker(bind=engine)()
    for ddl in (
        "CREATE TABLE tenants (id TEXT PRIMARY KEY)",
        """
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY, tenant_id TEXT, codigo TEXT, nome TEXT,
            codigo_barras TEXT, imagem_principal TEXT, preco_venda REAL,
            estoque_atual REAL, descricao_curta TEXT, ativo BOOLEAN,
            situacao BOOLEAN, deleted_at TEXT, updated_at TEXT
        )
        """,
        """
        CREATE TABLE produto_imagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT,
            produto_id INTEGER, url TEXT, ordem INTEGER, e_principal BOOLEAN,
            tamanho INTEGER, largura INTEGER, altura INTEGER, created_at TEXT
        )
        """,
    ):
        session.execute(text(ddl))
    session.execute(
        text("INSERT INTO tenants (id) VALUES (:source), (:target)"),
        {"source": SOURCE, "target": TARGET},
    )
    session.execute(
        text("""
            INSERT INTO produtos (id,tenant_id,codigo,nome,codigo_barras,
                                  preco_venda,estoque_atual,ativo,situacao)
            VALUES (11,:source,'BASE-11','Special Dog Base',:gtin,12,3,1,1),
                   (22,:target,'LOJA-22','Special Dog Base',:gtin,97,7,1,1)
        """),
        {"source": SOURCE, "target": TARGET, "gtin": GTIN},
    )
    session.execute(
        text("""
            INSERT INTO produto_imagens
                (id,tenant_id,produto_id,url,ordem,e_principal)
            VALUES (31,:source,11,:main,0,1),
                   (32,:source,11,:side,1,0)
        """),
        {
            "source": SOURCE,
            "main": f"https://img.corepet.com.br/{SOURCE}/11/main.webp",
            "side": f"https://img.corepet.com.br/{SOURCE}/11/side.webp",
        },
    )
    session.commit()
    monkeypatch.setattr(service, "get_product_image_storage_backend", lambda: "s3")
    monkeypatch.setattr(service, "is_s3_product_image_url", lambda url: True)
    monkeypatch.setattr(
        service,
        "copy_product_image_url",
        lambda url, **kwargs: url.replace(SOURCE, TARGET).replace("/11/", "/22/"),
    )
    try:
        yield session
    finally:
        session.close()


def run(db, *, dry_run=True):
    return service.copy_missing_images_by_gtin(
        db=db,
        source_tenant_ids=[SOURCE],
        target_tenant_id=TARGET,
        user_id=10,
        dry_run=dry_run,
    )


def test_simula_sem_alterar_o_produto(db):
    before = dict(
        db.execute(text("SELECT * FROM produtos WHERE id=22")).mappings().one()
    )
    result = run(db)
    after = dict(
        db.execute(text("SELECT * FROM produtos WHERE id=22")).mappings().one()
    )

    assert result["candidate_products"] == 1
    assert result["candidate_images"] == 2
    assert result["copied_images"] == 0
    assert after == before


def test_copia_apenas_fotos_e_preserva_cadastro_da_loja(db):
    result = run(db, dry_run=False)
    db.commit()
    product = dict(
        db.execute(text("SELECT * FROM produtos WHERE id=22")).mappings().one()
    )
    images = db.execute(
        text(
            "SELECT url, ordem, e_principal FROM produto_imagens WHERE produto_id=22 ORDER BY ordem"
        )
    ).all()

    assert result["copied_products"] == 1
    assert result["copied_images"] == 2
    assert product["nome"] == "Special Dog Base"
    assert product["codigo"] == "LOJA-22"
    assert product["preco_venda"] == 97
    assert product["estoque_atual"] == 7
    assert product["descricao_curta"] is None
    assert product["imagem_principal"] == images[0].url
    assert [(row.ordem, row.e_principal) for row in images] == [(0, 1), (1, 0)]
    assert run(db)["candidate_products"] == 0


def test_nao_copia_gtin_duplicado_nem_identidade_incompativel(db):
    db.execute(
        text("""
            INSERT INTO produtos (id,tenant_id,codigo,nome,codigo_barras,ativo,situacao)
            VALUES (12,:source,'BASE-12','Outro produto',:gtin,1,1)
        """),
        {"source": SOURCE, "gtin": GTIN},
    )
    assert run(db)["candidate_products"] == 0

    db.execute(text("DELETE FROM produtos WHERE id=12"))
    db.execute(text("UPDATE produtos SET nome='Racao Gato 10kg' WHERE id=22"))
    assert run(db)["candidate_products"] == 0


def test_foto_existente_e_preservada(db):
    db.execute(
        text(
            "UPDATE produtos SET imagem_principal='https://img.corepet.com.br/atual.webp' WHERE id=22"
        )
    )
    assert run(db)["candidate_products"] == 0
