from types import SimpleNamespace

import pytest

from app import bling_integration_fiscal as fiscal


@pytest.mark.parametrize("tipo_nota", ["nfce", "nfe"])
@pytest.mark.parametrize("com_produto", [False, True])
def test_servico_nao_pede_classificacao_de_mercadoria(
    monkeypatch, tipo_nota, com_produto
):
    produto = SimpleNamespace(id=42, nome="Banho cadastrado") if com_produto else None
    item = SimpleNamespace(
        id=9,
        tipo="servico",
        produto=produto,
        produto_id=42 if com_produto else None,
        servico_descricao="Banho avulso",
    )
    venda = SimpleNamespace(tenant_id=None, itens=[item])
    monkeypatch.setattr(
        fiscal,
        "_resolver_fiscal_item_nfe",
        lambda *_: pytest.fail("Servico nao deve receber sugestoes fiscais de produto"),
    )
    validacao = fiscal.prevalidar_produtos_fiscais_venda(
        venda, exigir_documento_completo=True, tipo_nota=tipo_nota
    )
    assert validacao["pode_emitir"] is False
    assert validacao["requer_autorizacao"] is False
    assert validacao["correcoes"] == []
    assert len(validacao["bloqueios"]) == 1
    bloqueio = validacao["bloqueios"][0]
    assert bloqueio["codigo"] == "servico_nao_suportado"
    assert bloqueio["item_id"] == 9
    assert bloqueio["item_numero"] == 1
    assert bloqueio["produto_nome"] == "Banho avulso"


def test_taxa_de_entrega_pede_revisao_do_lancamento():
    item = SimpleNamespace(
        id=3, tipo="servico", produto=None, servico_descricao="TAXA DE ENTREGA"
    )
    validacao = fiscal.prevalidar_produtos_fiscais_venda(
        SimpleNamespace(tenant_id=None, itens=[item]),
        exigir_documento_completo=True,
        tipo_nota="nfce",
    )
    assert validacao["correcoes"] == []
    bloqueio = validacao["bloqueios"][0]
    assert bloqueio["codigo"] == "taxa_entrega_como_servico"
    assert "lancamento de entrega" in bloqueio["mensagem"]
    assert "Banho" not in bloqueio["mensagem"]


def test_venda_mista_preserva_validacao_dos_produtos(monkeypatch):
    produto = SimpleNamespace(id=11, nome="Mercadoria", codigo="11")
    itens = [
        SimpleNamespace(id=1, tipo="produto", produto=produto),
        SimpleNamespace(id=2, tipo="servico", produto=None, servico_descricao="Tosa"),
    ]
    consultados = []

    def resolver(_db, _venda, item):
        consultados.append(item.id)
        return {
            "ncm": "23091000",
            "origem_mercadoria": "0",
            "cfop": "5102",
            "cfop_interno": "5102",
            "cst_icms": "00",
            "pis_cst": "01",
            "cofins_cst": "01",
        }

    monkeypatch.setattr(fiscal, "_resolver_fiscal_item_nfe", resolver)
    validacao = fiscal.prevalidar_produtos_fiscais_venda(
        SimpleNamespace(tenant_id=None, itens=itens),
        exigir_documento_completo=True,
        tipo_nota="nfce",
    )
    assert consultados == [1]
    assert validacao["pode_emitir"] is False
    assert validacao["correcoes"] == []
    assert [bloqueio["item_id"] for bloqueio in validacao["bloqueios"]] == [2]
