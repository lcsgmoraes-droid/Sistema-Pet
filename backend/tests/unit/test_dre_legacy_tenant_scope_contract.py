import inspect

from app import dre_base_routes, dre_calculos


def test_dre_legado_filtra_receitas_e_despesas_por_tenant():
    source = inspect.getsource(dre_base_routes.gerar_dre)

    assert "_current_user, tenant_id = user_and_tenant" in source
    assert "Venda.tenant_id == tenant_id" in source
    assert "calcular_cmv(db, mes, ano, tenant_id)" in source
    assert "obter_despesas_por_categoria(db, mes, ano, tenant_id)" in source
    assert "calcular_taxas_cartao(db, mes, ano, tenant_id)" in source
    bloco_frete = source.split("frete_compras = calcular_frete_notas_entrada(", 1)[1]
    bloco_frete = bloco_frete.split(")  # Frete de notas de entrada", 1)[0]
    assert "tenant_id" in bloco_frete


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
    cmv = inspect.getsource(dre_calculos.calcular_cmv)
    frete = inspect.getsource(dre_calculos.calcular_frete_notas_entrada)
    despesas = inspect.getsource(dre_calculos.obter_despesas_por_categoria)
    taxas = inspect.getsource(dre_calculos.calcular_taxas_cartao)

    assert "Venda.tenant_id == tenant_id" in cmv
    assert "VendaItem.tenant_id == tenant_id" in cmv
    assert "NotaEntrada.tenant_id == tenant_id" in frete
    assert "DRESubcategoria.tenant_id == tenant_id" in despesas
    assert "ContaPagar.tenant_id == tenant_id" in despesas
    assert 'ContaPagar.status != "cancelado"' in despesas
    assert "DRESubcategoria.tenant_id == tenant_id" in taxas
    assert "ContaPagar.tenant_id == tenant_id" in taxas
