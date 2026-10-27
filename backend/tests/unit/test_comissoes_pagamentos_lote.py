"""Reenvio do lote não aplica regra nova aos pagamentos anteriores."""

from decimal import Decimal
from types import SimpleNamespace

from app.vendas import comissoes
from app.comissoes_config_service import calcular_comissao_fixa_parcela


def test_so_pagamentos_do_lote_geram_comissao_fixa_e_reenvio_nao_duplica(monkeypatch):
    venda = SimpleNamespace(id=100, funcionario_id=7, total=Decimal("100"))
    pagamentos = [
        (11, "PIX", Decimal("50"), None, None, "confirmado"),
        (12, "PIX", Decimal("25"), None, 8, "confirmado"),
        (13, "PIX", Decimal("25"), None, 9, "confirmado"),
    ]
    snapshots = {}
    chamadas = []
    monkeypatch.setattr(comissoes, "_bloquear_venda_para_comissao", lambda *a: venda)
    monkeypatch.setattr(
        comissoes, "_listar_pagamentos_venda_para_comissao", lambda *a: pagamentos
    )
    monkeypatch.setattr(
        comissoes, "_parcelas_com_comissao_funcionario", lambda *a: set(snapshots)
    )

    def gerar(**kwargs):
        parcela = kwargs["parcela_numero"]
        chamadas.append(parcela)
        pago_antes = kwargs["valor_pago_anterior"]
        valor = calcular_comissao_fixa_parcela(
            "3.25", kwargs["valor_pago"], venda.total, pago_antes
        )
        snapshots[parcela] = valor
        return {"success": True, "total_comissao": valor}

    monkeypatch.setattr("app.comissoes_service.gerar_comissoes_venda", gerar)
    primeiro = comissoes._gerar_comissoes_pendentes_venda(
        None, venda, "tenant-qa", "lote", pagamento_ids={12}
    )
    assert chamadas == [2]
    assert primeiro["comissoes_geradas"] == 1
    segundo = comissoes._gerar_comissoes_pendentes_venda(
        None, venda, "tenant-qa", "lote", pagamento_ids={13}
    )
    assert chamadas == [2, 3]
    assert segundo["comissoes_geradas"] == 1
    repetido = comissoes._gerar_comissoes_pendentes_venda(
        None, venda, "tenant-qa", "lote", pagamento_ids={12, 13}
    )
    assert repetido["comissoes_geradas"] == 0
    assert chamadas == [2, 3]
    assert (
        1 not in snapshots
    )  # O pagamento anterior não recebe retroativamente uma regra nova.
    assert sum(snapshots.values()) == Decimal("1.62")
