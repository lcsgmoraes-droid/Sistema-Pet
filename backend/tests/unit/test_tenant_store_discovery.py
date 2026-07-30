from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Tenant
from app.tenant_identity import normalize_tenant_name
from app.routes.ecommerce_public import (
    _distance_km,
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


def test_store_search_contract_keeps_name_global_and_gps_limited_to_eight():
    source = (
        REPO_ROOT / "backend/app/routes/ecommerce_public.py"
    ).read_text(encoding="utf-8")

    assert '@router.get("/tenants/buscar")' in source
    assert "le=8" in source
    assert '"distancia_km"' in source


def test_tenant_database_migration_enforces_unique_normalized_names():
    source = (
        REPO_ROOT
        / "backend/alembic/versions/zwo20260729a1_tenant_discovery_identity.py"
    ).read_text(encoding="utf-8")

    assert '"ux_tenants_name_normalized"' in source
    assert "unique=True" in source
    assert "Existem lojas com nomes duplicados" in source


def test_tenant_registration_rejects_an_existing_store_name():
    source = (
        REPO_ROOT / "backend/app/auth/auth_multitenant_account_routes.py"
    ).read_text(encoding="utf-8")

    assert "Tenant.name_normalized == tenant_name_normalized" in source
    assert "Ja existe uma loja com este nome" in source
    assert "HTTP_409_CONFLICT" in source
