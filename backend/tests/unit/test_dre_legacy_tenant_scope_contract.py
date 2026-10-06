import inspect

from app import dre_base_routes, dre_calculos


def test_dre_legado_filtra_receitas_e_despesas_por_tenant():
    source = inspect.getsource(dre_base_routes.gerar_dre)

    assert "_dre_para_exportacao(" in source
    assert "user_and_tenant=user_and_tenant" in source
    assert 'canais=",".join(CANAIS_CONFIG)' in source


def test_dre_detalhado_filtra_despesas_e_receitas_por_tenant():
    source = inspect.getsource(dre_base_routes.gerar_dre_detalhado)

    assert "_current_user, tenant_id = user_and_tenant" in source
    assert "ContaPagar.tenant_id == tenant_id" in source
    assert 'ContaPagar.status != "cancelado"' in source
    assert "Venda.tenant_id == tenant_id" in source


def test_helpers_dre_legado_exigem_tenant_id():
    assert "tenant_id" in inspect.signature(dre_calculos.calcular_cmv).parameters
    assert (
        "tenant_id"
        in inspect.signature(dre_calculos.calcular_custo_servicos).parameters
    )
    assert (
        "tenant_id"
        in inspect.signature(dre_calculos.calcular_frete_notas_entrada).parameters
    )
    assert (
        "tenant_id"
        in inspect.signature(dre_calculos.obter_despesas_por_categoria).parameters
    )
    assert (
        "tenant_id" in inspect.signature(dre_calculos.calcular_taxas_cartao).parameters
    )


def test_helpers_dre_legado_filtram_modelos_por_tenant():
    custos = inspect.getsource(dre_calculos._calcular_custo_itens_por_natureza)
    frete = inspect.getsource(dre_calculos.calcular_frete_notas_entrada)
    despesas = inspect.getsource(dre_calculos.obter_despesas_por_categoria)
    taxas = inspect.getsource(dre_calculos.calcular_taxas_cartao)

    assert "Venda.tenant_id == tenant_id" in custos
    assert "VendaItem.tenant_id == tenant_id" in custos
    assert "NotaEntrada.tenant_id == tenant_id" in frete
    assert "DRESubcategoria.tenant_id == tenant_id" in despesas
    assert "ContaPagar.tenant_id == tenant_id" in despesas
    assert 'ContaPagar.status != "cancelado"' in despesas
    assert "DRESubcategoria.tenant_id == tenant_id" in taxas
    assert "ContaPagar.tenant_id == tenant_id" in taxas
