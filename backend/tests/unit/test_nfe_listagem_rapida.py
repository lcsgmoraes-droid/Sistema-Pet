from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

import app.db.base  # noqa: F401
from app.nfe import listagem_rapida as modulo
from app.nfe_cache_models import BlingNotaFiscalCache as Nota
from app.tenancy.context import tenant_context


@pytest.fixture
def base(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Nota.__table__.create(engine)
    monkeypatch.setattr(modulo, "tenant_pode_usar_bling_global", lambda _: True)
    monkeypatch.setattr(modulo, "_enriquecer_notas_com_vendas", lambda *args: None)
    with Session(engine) as db:
        yield db


def inserir(db, tenant, **kwargs):
    with tenant_context(tenant):
        db.add(
            Nota(
                tenant_id=tenant,
                modelo=65,
                status="Autorizada",
                source="bling_api",
                **kwargs,
            )
        )
        db.commit()


def test_pagina_filtra_canal_tenant_e_ordena_por_data_antes_de_numero(base):
    tenant, outro = uuid4(), uuid4()
    inserir(
        base,
        tenant,
        bling_id="100",
        numero="9000",
        canal="shopee",
        data_emissao=datetime(2026, 9, 8),
    )
    inserir(
        base,
        tenant,
        bling_id="101",
        numero="44",
        canal="loja_fisica",
        data_emissao=datetime(2026, 9, 9),
    )
    inserir(
        base,
        outro,
        bling_id="102",
        numero="45",
        canal="loja_fisica",
        data_emissao=datetime(2026, 9, 10),
    )
    with tenant_context(tenant):
        pagina = modulo.consultar_pagina(base, tenant, por_pagina=1)
        assert pagina["total"] == 2
        assert [n["numero"] for n in pagina["notas"]] == ["44"]
        assert (
            modulo.consultar_pagina(base, tenant, pagina=2, por_pagina=1)["notas"][0][
                "numero"
            ]
            == "9000"
        )
        pdv = modulo.consultar_pagina(base, tenant, canal="loja_fisica")
        assert pdv["total"] == 1
        assert pdv["notas"][0]["numero"] == "44"
        assert {c["value"] for c in pdv["canais"]} == {"shopee", "loja_fisica"}


def test_busca_no_banco_encontra_cliente_fora_da_primeira_pagina_sem_payloads(base):
    tenant = uuid4()
    inserir(
        base,
        tenant,
        bling_id="1",
        numero="1",
        canal="loja_fisica",
        cliente={"nome": "Maria"},
    )
    inserir(
        base,
        tenant,
        bling_id="2",
        numero="2",
        canal="loja_fisica",
        cliente={"nome": "Angelica"},
    )
    queries = []
    event.listen(
        base.bind,
        "before_cursor_execute",
        lambda conn, cursor, statement, *a: queries.append(statement),
    )
    with tenant_context(tenant):
        resultado = modulo.consultar_pagina(base, tenant, busca="Maria", por_pagina=1)
    assert resultado["total"] == 1
    assert resultado["notas"][0]["cliente"]["nome"] == "Maria"
    consulta = queries[-1].split("FROM")[0]
    assert "detalhe_payload" not in consulta
    assert "resumo_payload" not in consulta


def test_fontes_remotas_nao_vazam_para_tenant_sem_bling(base, monkeypatch):
    tenant = uuid4()
    inserir(base, tenant, bling_id="1", numero="1", canal="amazon")
    monkeypatch.setattr(modulo, "tenant_pode_usar_bling_global", lambda _: False)
    with tenant_context(tenant):
        resultado = modulo.consultar_pagina(base, tenant)
    assert resultado["total"] == 0
    assert resultado["canais"] == []


def test_filtro_pdv_inclui_aliases_do_canal(base):
    tenant = uuid4()
    for i, canal in enumerate(["loja_fisica", "PDV", "Loja Física", "shopee"]):
        inserir(base, tenant, bling_id=str(i), numero=str(i), canal=canal)
    with tenant_context(tenant):
        resultado = modulo.consultar_pagina(base, tenant, canal="loja_fisica")
    assert resultado["total"] == 3
