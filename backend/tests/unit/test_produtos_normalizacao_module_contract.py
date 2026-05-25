import pytest
from fastapi import HTTPException

from app.produtos.normalizacao import (
    nome_indica_granel,
    normalizar_payload_granel,
    normalizar_promocao_erp_payload,
    normalizar_sku_produto,
    produto_sku_value,
)


def test_normalizar_sku_produto_limpa_e_padroniza_codigo():
    assert normalizar_sku_produto(" abc-123 ") == "ABC-123"


def test_normalizar_sku_produto_rejeita_vazio_com_mesma_mensagem_da_rota():
    with pytest.raises(HTTPException) as exc_info:
        normalizar_sku_produto("   ")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "SKU do produto e obrigatorio"


def test_produto_sku_value_le_sku_sem_exigir_modelo_sqlalchemy():
    produto = type("ProdutoStub", (), {"sku": "PET-001"})()

    assert produto_sku_value(produto) == "PET-001"


def test_normalizar_promocao_erp_payload_marca_promocao_quando_preco_informado():
    dados = {"preco_promocional": "12.50"}

    normalizado = normalizar_promocao_erp_payload(dados)

    assert normalizado is dados
    assert normalizado["promocao_ativa"] is True


def test_normalizar_promocao_erp_payload_preserva_edicao_sem_campos_promocionais():
    produto_atual = type("ProdutoAtual", (), {"preco_promocional": 10})()
    dados = {"nome": "Racao Teste"}

    normalizado = normalizar_promocao_erp_payload(dados, produto_atual)

    assert normalizado == {"nome": "Racao Teste"}


def test_normalizar_payload_granel_forca_campos_estruturais():
    dados = {"nome": "Racao a granel", "tipo_produto": "KIT"}

    normalizado = normalizar_payload_granel(dados)

    assert nome_indica_granel("Racao a granel") is True
    assert normalizado["e_granel"] is True
    assert normalizado["tipo_produto"] == "SIMPLES"
    assert normalizado["tipo_kit"] is None
    assert normalizado["e_kit_fisico"] is False
    assert normalizado["unidade"] == "KG"
    assert normalizado["participa_sugestao_compra"] is False
