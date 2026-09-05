from sqlalchemy import select

import pytest

from app.produtos_models import Produto
from tests.unit.test_app_mobile_produto_rapido import (
    TENANT_A,
    TENANT_B,
    ambiente as ambiente,
)
from tests.unit.test_app_mobile_produto_rapido_detalhes import (
    consultar_sku,
    db_session as db_session,
)

CHAVE = "43c7286f-2117-4a5f-9aba-94aa67f8b3b2"
MINIMO = {"nome": "Brinquedo artesanal", "preco_venda": 12.50}
ROTA = "/app/funcionario/produtos/rapido"


@pytest.mark.parametrize(
    "extras",
    [{}, {"codigo_barras": None}, {"codigo_barras": ""}, {"codigo_barras": "   "}],
)
def test_sem_codigo_de_barras_salva_nulo_no_erp(ambiente, extras):
    client, db, _ = ambiente
    resposta = client.post(ROTA, json={**MINIMO, **extras})
    assert resposta.status_code == 201, resposta.text
    produto = db.execute(select(Produto.__table__)).mappings().one()
    assert resposta.json()["codigo_barras"] is None
    assert produto["codigo_barras"] is None
    assert produto["codigo"].startswith("APP-")
    assert produto["estoque_atual"] == 0
    assert produto["anunciar_app"] is False


def test_inicia_pelo_sku_longo_sem_usar_como_codigo_de_barras(ambiente):
    client, _, _ = ambiente
    sku = "SKU/" + "a" * 46
    assert consultar_sku(client, sku).json()["disponivel"] is True
    resposta = client.post(ROTA, json={**MINIMO, "codigo": sku})
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["codigo"] == sku.upper()
    assert resposta.json()["codigo_barras"] is None
    consulta = consultar_sku(client, sku).json()
    assert consulta["disponivel"] is False
    assert consulta["produto"]["id"] == resposta.json()["id"]


def test_sku_preserva_zeros_e_nao_confunde_com_ean(ambiente):
    client, db, _ = ambiente
    primeiro = client.post(ROTA, json={**MINIMO, "codigo": "00123"}).json()
    segundo = client.post(ROTA, json={**MINIMO, "codigo": "123"}).json()
    db.execute(
        Produto.__table__.update()
        .where(Produto.id == primeiro["id"])
        .values(ativo=False)
    )
    db.commit()
    assert consultar_sku(client, "00123").json()["produto"]["id"] == primeiro["id"]
    assert consultar_sku(client, "00123").json()["produto"]["ativo"] is False
    assert consultar_sku(client, "123").json()["produto"]["id"] == segundo["id"]
    assert consultar_sku(client, "000123").json()["produto"] is None


def test_sku_existente_sem_ean_nao_duplica_ou_sobrescreve(ambiente):
    client, db, _ = ambiente
    assert client.post(ROTA, json={**MINIMO, "codigo": "ART-1"}).status_code == 201
    resposta = client.post(ROTA, json={**MINIMO, "nome": "Outro", "codigo": "art-1"})
    assert resposta.status_code == 409
    assert resposta.json()["detail"]["campo"] == "codigo"
    produto = db.execute(select(Produto.__table__)).mappings().one()
    assert produto["nome"] == MINIMO["nome"]


def test_reenvio_sem_identificadores_confirma_o_mesmo_cadastro(ambiente):
    client, db, _ = ambiente
    payload = {**MINIMO, "chave_cadastro": CHAVE}
    primeira = client.post(ROTA, json=payload)
    segunda = client.post(ROTA, json={**payload, "nome": "Nome alterado apos timeout"})
    assert primeira.status_code == 201, primeira.text
    assert segunda.status_code == 200, segunda.text
    assert segunda.json() == primeira.json()
    assert len(db.execute(select(Produto.__table__)).all()) == 1
    outra = client.post(
        ROTA, json={**MINIMO, "chave_cadastro": "894d715e-248d-47fa-ae1e-220a70a29938"}
    )
    assert outra.status_code == 201
    assert outra.json()["codigo"] != primeira.json()["codigo"]


def test_mesma_chave_em_outra_empresa_nao_retorna_produto_alheio(
    ambiente, tenant_context
):
    client, _, user = ambiente
    payload = {**MINIMO, "chave_cadastro": CHAVE}
    primeira = client.post(ROTA, json=payload).json()
    user.tenant_id = TENANT_B
    tenant_context(TENANT_B)
    segunda = client.post(ROTA, json=payload)
    assert segunda.status_code == 201, segunda.text
    assert segunda.json()["id"] != primeira["id"]
    assert segunda.json()["codigo"] != primeira["codigo"]
    assert consultar_sku(client, primeira["codigo"]).json()["produto"] is None
    user.tenant_id = TENANT_A
    tenant_context(TENANT_A)
    assert client.post(ROTA, json=payload).json()["id"] == primeira["id"]


def test_sku_nao_expoe_produto_sem_perfil_operacional(ambiente):
    client, _, user = ambiente
    client.post(ROTA, json={**MINIMO, "codigo": "ART-1"})
    user.permitido = False
    assert consultar_sku(client, "ART-1").status_code == 403
    assert client.post(ROTA, json=MINIMO).status_code == 403
