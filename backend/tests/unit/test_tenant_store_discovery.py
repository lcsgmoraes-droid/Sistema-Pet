import importlib.util
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import financeiro_models, produtos_models  # noqa: F401 - completa o registry ORM
from app.models import Tenant
from app.tenant_identity import normalize_tenant_name
from app.routes.ecommerce_public import (
    _distance_km,
    _tenant_public_payload,
    buscar_tenants_por_nome,
    sugerir_tenants_por_localidade,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _temporary_session():
    engine = create_engine("sqlite:///:memory:")
    Tenant.__table__.create(engine)
    return sessionmaker(bind=engine)()


def _store(name: str, slug: str, latitude: float, longitude: float) -> Tenant:
    return Tenant(
        id=str(uuid4()),
        name=name,
        ecommerce_slug=slug,
        ecommerce_ativo=True,
        status="active",
        cidade="Presidente Prudente",
        uf="SP",
        latitude=latitude,
        longitude=longitude,
    )


def test_tenant_name_normalization_blocks_case_accents_and_extra_spaces():
    assert normalize_tenant_name("  Atacadao   das Racoes  ") == (
        normalize_tenant_name("Atacadão das Rações")
    )


def test_store_distance_uses_real_coordinates():
    sao_paulo = (-23.5505, -46.6333)
    rio_de_janeiro = (-22.9068, -43.1729)

    distance = _distance_km(*sao_paulo, *rio_de_janeiro)

    assert 350 < distance < 370
    assert _distance_km(*sao_paulo, *sao_paulo) == 0


def test_gps_store_suggestion_is_nearest_first_and_limited_to_eight():
    db = _temporary_session()
    try:
        for index in range(10):
            db.add(
                _store(
                    f"Loja {index}",
                    f"loja-{index}",
                    -22.12 + index * 0.01,
                    -51.39,
                )
            )
        db.commit()

        response = sugerir_tenants_por_localidade(
            latitude=-22.12,
            longitude=-51.39,
            cidade=None,
            uf=None,
            limit=8,
            db=db,
        )

        assert len(response["lojas"]) == 8
        assert response["lojas"][0]["nome"] == "Loja 0"
        distances = [store["distancia_km"] for store in response["lojas"]]
        assert distances == sorted(distances)
    finally:
        db.close()


def test_name_search_finds_store_without_geographic_filter():
    db = _temporary_session()
    try:
        distant_store = _store(
            "Atacadão das Rações",
            "atacadao",
            -3.119,
            -60.0217,
        )
        distant_store.cidade = "Manaus"
        distant_store.uf = "AM"
        db.add(distant_store)
        db.commit()

        response = buscar_tenants_por_nome(q="atacadao", limit=20, db=db)

        assert [store["slug"] for store in response["lojas"]] == ["atacadao"]
    finally:
        db.close()


def test_public_store_image_prefers_logo_and_falls_back_to_first_banner():
    store = _store("Loja com imagem", "loja-com-imagem", -22.12, -51.39)
    store.banner_1_url = "/uploads/ecommerce/loja/banner_1.jpg"

    assert _tenant_public_payload(store)["imagem_url"] == store.banner_1_url

    store.logo_url = "/uploads/ecommerce/loja/logo.png"

    assert _tenant_public_payload(store)["imagem_url"] == store.logo_url


def test_store_search_contract_keeps_name_global_and_gps_limited_to_eight():
    source = (REPO_ROOT / "backend/app/routes/ecommerce_public.py").read_text(
        encoding="utf-8"
    )

    assert '@router.get("/tenants/buscar")' in source
    assert "le=8" in source
    assert '"distancia_km"' in source


def test_tenant_login_name_migration_separates_login_from_fantasy_name():
    source = (
        REPO_ROOT / "backend/alembic/versions/zzt20260916a1_tenant_login_names.py"
    ).read_text(encoding="utf-8")

    assert '"tenant_login_names"' in source
    assert '"ux_tenant_login_names_name_normalized"' in source
    assert '"ux_tenant_login_names_primary_tenant"' in source
    assert '"ix_tenants_name_normalized"' in source
    assert "unique=True" in source
    assert "SELECT id, name, name_normalized" in source


def test_tenant_login_name_migration_backfills_and_keeps_aliases_on_sqlite():
    migration_path = (
        REPO_ROOT / "backend/alembic/versions/zzt20260916a1_tenant_login_names.py"
    )
    spec = importlib.util.spec_from_file_location(
        "tenant_login_name_migration", migration_path
    )
    assert spec and spec.loader
    login_name_migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(login_name_migration)

    engine = create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    tenants = sa.Table(
        "tenants",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_normalized", sa.String(255), nullable=False),
    )
    sa.Index("ux_tenants_name_normalized", tenants.c.name_normalized, unique=True)
    sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    metadata.create_all(engine)

    tenant_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            tenants.insert().values(
                id=tenant_id,
                name="Casa de Racao Vira Lata",
                name_normalized="casa de racao vira lata",
            )
        )
        original_op = login_name_migration.op
        login_name_migration.op = Operations(MigrationContext.configure(connection))
        try:
            login_name_migration.upgrade()
        finally:
            login_name_migration.op = original_op

        row = (
            connection.execute(
                sa.text(
                    "SELECT tenant_id, name, name_normalized, is_primary "
                    "FROM tenant_login_names"
                )
            )
            .mappings()
            .one()
        )
        primary_index_sql = connection.execute(
            sa.text(
                "SELECT sql FROM sqlite_master "
                "WHERE name = 'ux_tenant_login_names_primary_tenant'"
            )
        ).scalar_one()

    assert row["tenant_id"] == tenant_id
    assert row["name"] == "Casa de Racao Vira Lata"
    assert row["name_normalized"] == "casa de racao vira lata"
    assert bool(row["is_primary"]) is True
    assert "WHERE is_primary = 1" in primary_index_sql


def test_tenant_registration_uses_the_unique_login_name_service():
    source = (
        REPO_ROOT / "backend/app/auth/auth_multitenant_account_routes.py"
    ).read_text(encoding="utf-8")

    assert "set_primary_tenant_login_name" in source
    assert "payload.nome_acesso or tenant_name" in source
    assert "Tenant.name_normalized ==" not in source
    assert "Este nome de acesso ja esta em uso" in source
