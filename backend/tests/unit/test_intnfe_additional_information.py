from types import SimpleNamespace

from app.intnfe.additional_information import sale_context_lines
from app.intnfe.emission import _additional_information


def test_referencia_amazon_registrada_e_rastreio_sao_preservados_com_canal():
    sale = SimpleNamespace(
        numero_venda="202610260007",
        canal="amazon",
        loja_origem="Loja CorePet",
        observacoes="Nº Pedido Loja: 701-8373817-8649038",
        observacoes_entrega="Código de rastreamento: AA123456789BR",
    )

    result = _additional_information(sale, [])

    assert "Canal de venda: Amazon" in result
    assert "Loja de origem: Loja CorePet" in result
    assert "Nº Pedido Loja: 701-8373817-8649038" in result
    assert "Código de rastreamento: AA123456789BR" in result
    assert "IBPT" not in result
    assert "Tributos aproximados" not in result


def test_nao_inventa_referencia_ou_rastreio_quando_venda_nao_tem_dados():
    sale = SimpleNamespace(numero_venda="VEN-1", canal="site")

    result = _additional_information(sale, [])

    assert result == "Venda VEN-1 | Canal de venda: Site"
    assert "Pedido" not in result and "rastre" not in result.lower()


def test_loja_igual_ao_canal_nao_repete_identificacao():
    sale = SimpleNamespace(canal="Mercado Livre", loja_origem="Mercado Livre")

    assert sale_context_lines(sale) == ["Canal de venda: Mercado Livre"]


def test_pdv_padrao_preserva_texto_sem_contexto_duplicado():
    sale = SimpleNamespace(
        numero_venda="VEN-1", canal="loja_fisica", loja_origem="Loja física"
    )

    assert _additional_information(sale, []) == "Venda VEN-1"


def test_complemento_fiscal_normaliza_quebras_e_preserva_limite_do_emissor():
    sale = SimpleNamespace(
        numero_venda="VEN-1",
        canal="site",
        observacoes="x" * 6000,
        observacoes_entrega="Entregar\nna portaria",
    )

    result = _additional_information(sale, [])

    assert "Observacoes de entrega: Entregar na portaria" in result
    assert len(result) == 5000


def test_observacao_fiscal_do_produto_vai_para_nota_sem_inventar_tributo():
    product = SimpleNamespace(
        codigo="SKU-123", informacoes_adicionais_nf="Lote identificado\nno rótulo"
    )
    item = SimpleNamespace(produto=product)
    sale = SimpleNamespace(
        numero_venda="VEN-1", canal="loja_fisica", itens=[item, item]
    )

    result = _additional_information(sale, [])

    assert "Dados adicionais do produto SKU-123: Lote identificado no rótulo" in result
    assert result.count("Lote identificado") == 1
    assert "IBPT" not in result
