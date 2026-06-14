import inspect

from app.ia.aba7_dre_detalhada_service import DREDetalhadaService


def test_calcular_dre_por_canal_sincroniza_rls_e_filtra_tabelas_por_tenant():
    source = inspect.getsource(DREDetalhadaService.calcular_dre_por_canal)

    assert "tenant_id = tenant_id_para_escrita_dre(self.db, usuario_id)" in source
    assert "sync_rls_tenant(self.db, tenant_id)" in source
    assert "Venda.tenant_id == tenant_id" in source
    assert "VendaItem.tenant_id == tenant_id" in source
    assert "Produto.tenant_id == tenant_id" in source
    assert "LancamentoManual.tenant_id == tenant_id" in source
    assert "AlocacaoDespesaCanal.tenant_id == tenant_id" in source
    assert "DREDetalheCanal.tenant_id == tenant_id" in source
    assert "tenant_id=tenant_id" in source


def test_salvar_alocacao_despesa_sincroniza_rls_e_grava_tenant():
    source = inspect.getsource(DREDetalhadaService.salvar_alocacao_despesa)

    assert "tenant_id = tenant_id_para_escrita_dre(self.db, usuario_id)" in source
    assert "sync_rls_tenant(self.db, tenant_id)" in source
    assert "tenant_id=tenant_id" in source
