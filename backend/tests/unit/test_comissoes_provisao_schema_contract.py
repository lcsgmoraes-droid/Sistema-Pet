from app.comissoes_models import ComissaoItem


def test_comissao_item_declares_provisioning_columns():
    assert hasattr(ComissaoItem, "comissao_provisionada")
    assert hasattr(ComissaoItem, "conta_pagar_id")
    assert hasattr(ComissaoItem, "data_provisao")
