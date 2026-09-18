from types import SimpleNamespace

from app import bling_integration_fiscal
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.notas_entrada.produtos import (
    _sincronizar_config_fiscal_produto_por_entrada,
)
from app.produto_config_fiscal_models import ProdutoConfigFiscal


class _Query:
    def __init__(self, value):
        self.value = value

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.value


class _Db:
    def __init__(self, fiscal, empresa):
        self.fiscal = fiscal
        self.empresa = empresa
        self.added = []

    def query(self, model):
        if model is ProdutoConfigFiscal:
            return _Query(self.fiscal)
        if model is EmpresaConfigFiscal:
            return _Query(self.empresa)
        raise AssertionError(f"Consulta inesperada: {model}")

    def add(self, value):
        self.added.append(value)


def _empresa_simples():
    return SimpleNamespace(
        regime_tributario="Simples Nacional",
        simples_ativo=True,
        pis_cst_padrao="49",
        cofins_cst_padrao="49",
        cfop_venda_interna="5102",
        cfop_venda_interestadual="6102",
        icms_aliquota_interna=18,
        pis_aliquota=0,
        cofins_aliquota=0,
    )


def _fiscal_atual():
    return SimpleNamespace(
        herdado_da_empresa=False,
        ncm="23091000",
        cest=None,
        origem_mercadoria="0",
        cst_icms="900",
        icms_st=False,
        icms_aliquota=18,
        cfop_venda="5102",
        cfop_compra="1102",
        pis_cst="49",
        pis_aliquota=0,
        cofins_cst="49",
        cofins_aliquota=0,
        observacao_fiscal=None,
    )


def test_entrada_com_st_atualiza_configuracao_de_saida_do_simples():
    fiscal = _fiscal_atual()
    db = _Db(fiscal, _empresa_simples())
    produto = SimpleNamespace(
        id=5589,
        ncm="23091000",
        cest=None,
        origem="0",
        cfop="5102",
        aliquota_icms=18,
    )
    item = SimpleNamespace(
        numero_item=4,
        ncm="23099010",
        cest="2200100",
        origem="0",
        cfop="6401",
        cst_icms="10",
        icms_st=True,
    )
    nota = SimpleNamespace(serie="1", numero_nota="46270")

    atualizou = _sincronizar_config_fiscal_produto_por_entrada(
        db, "tenant", produto, item, nota
    )

    assert atualizou is True
    assert fiscal.ncm == "23099010"
    assert fiscal.cest == "2200100"
    assert fiscal.cst_icms == "500"
    assert fiscal.icms_st is True
    assert fiscal.icms_aliquota is None
    assert fiscal.cfop_venda == "5405"
    assert fiscal.cfop_compra == "2403"
    assert produto.cfop == "5405"
    assert "NF-e de entrada 46270" in fiscal.observacao_fiscal


def test_lote_com_st_prevalece_sobre_configuracao_geral_do_produto():
    fiscal = _fiscal_atual()
    empresa = _empresa_simples()
    db = _Db(fiscal, empresa)
    produto = SimpleNamespace(
        id=5589,
        tenant_id="tenant",
        tipo_produto="NORMAL",
        ncm="23091000",
        cest=None,
        origem="0",
        cfop="5102",
    )
    lote = SimpleNamespace(
        fiscal_ncm="23099010",
        fiscal_cest="2200100",
        fiscal_origem_mercadoria="0",
        fiscal_icms_st=True,
    )
    item_venda = SimpleNamespace(produto=produto, lote=lote)
    venda = SimpleNamespace(tenant_id="tenant")

    resolvido = bling_integration_fiscal._resolver_fiscal_item_nfe(
        db, venda, item_venda
    )

    assert resolvido["ncm"] == "23099010"
    assert resolvido["cest"] == "2200100"
    assert resolvido["cst_icms"] == "500"
    assert resolvido["cfop_interno"] == "5405"
    assert resolvido["cfop_interestadual_nao_contribuinte"] == "6108"
    assert resolvido["icms_aliquota"] is None
