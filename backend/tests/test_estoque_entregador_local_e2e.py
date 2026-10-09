"""Aceite dos ajustes operacionais em homologação local com dados fictícios."""

from uuid import uuid4

import pytest

from tests import test_plano_basico_e2e as jornada_basica

api = jornada_basica.api
e2e_config = jornada_basica.e2e_config
pytestmark = pytest.mark.e2e_long


@pytest.fixture(autouse=True)
def somente_local(e2e_config):
    from urllib.parse import urlparse

    assert urlparse(e2e_config.base_url).hostname in {"localhost", "127.0.0.1"}


def test_informar_lote_preserva_estoque_e_custo_sem_duplicacao(api):
    codigo = "E2E-VALIDADE-" + uuid4().hex[:12]
    produto = api.expect(
        "POST",
        "/produtos/",
        {200, 201},
        "produto.validade.criar",
        json={
            "codigo": codigo,
            "nome": codigo,
            "unidade": "UN",
            "preco_custo": 6,
            "preco_venda": 10,
            "tipo_produto": "SIMPLES",
        },
    ).json()
    produto_id = produto["id"]
    api.expect(
        "POST",
        "/estoque/entrada",
        {200, 201},
        "produto.validade.saldo_teste",
        json={
            "produto_id": produto_id,
            "quantidade": 5,
            "custo_unitario": 6,
            "motivo": "ajuste",
            "observacao": codigo,
        },
    )
    antes = api.expect(
        "GET", f"/produtos/{produto_id}", {200}, "produto.validade.antes"
    ).json()
    assert antes["estoque_atual"] == 5
    movimentos_antes = api.expect(
        "GET",
        f"/estoque/movimentacoes/produto/{produto_id}",
        {200},
        "produto.validade.movimentos_antes",
    ).json()
    dados = {"nome_lote": codigo, "quantidade": 3, "data_validade": "2030-10-09"}
    primeiro = api.expect(
        "PUT",
        f"/produtos/{produto_id}/lotes-validade",
        {200},
        "produto.validade.informar",
        json=dados,
    ).json()
    repetido = api.expect(
        "PUT",
        f"/produtos/{produto_id}/lotes-validade",
        {200},
        "produto.validade.repetir",
        json=dados,
    ).json()
    depois = api.expect(
        "GET", f"/produtos/{produto_id}", {200}, "produto.validade.depois"
    ).json()
    movimentos_depois = api.expect(
        "GET",
        f"/estoque/movimentacoes/produto/{produto_id}",
        {200},
        "produto.validade.movimentos_depois",
    ).json()
    assert primeiro["id"] == repetido["id"]
    assert repetido["quantidade_disponivel"] == 3
    assert repetido["apenas_identificacao"] is True
    assert antes["estoque_atual"] == depois["estoque_atual"] == 5
    assert antes["preco_custo"] == depois["preco_custo"] == 6
    assert antes["controle_lote"] == depois["controle_lote"]
    assert movimentos_antes == movimentos_depois


def test_cadastro_entregador_sem_acerto_persiste_sem_periodicidade(api):
    nome = "E2E-ENTREGADOR-" + uuid4().hex[:12]
    pessoa = api.expect(
        "POST",
        "/clientes/",
        {200, 201},
        "entregador.sem_acerto.criar",
        json={
            "nome": nome,
            "tipo_cadastro": "fornecedor",
            "tipo_pessoa": "PF",
            "telefone": "11987654321",
            "is_entregador": True,
            "entregador_ativo": True,
            "tipo_acerto_entrega": None,
            "dia_semana_acerto": None,
            "dia_mes_acerto": None,
        },
    ).json()
    salvo = api.expect(
        "GET", f"/clientes/{pessoa['id']}", {200}, "entregador.sem_acerto.reler"
    ).json()
    assert salvo["is_entregador"] is True
    assert salvo["entregador_ativo"] is True
    assert salvo["tipo_acerto_entrega"] is None
    assert salvo["dia_semana_acerto"] is None
    assert salvo["dia_mes_acerto"] is None
