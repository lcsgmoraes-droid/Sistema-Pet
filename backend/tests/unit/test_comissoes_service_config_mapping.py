from datetime import datetime
from decimal import Decimal

from app import comissoes_service


class FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


def test_buscar_configuracao_comissao_nao_depende_da_ordem_fisica_da_tabela(
    monkeypatch,
):
    tenant_id = "11111111-1111-1111-1111-111111111111"

    def fake_execute_tenant_safe(db, query, params, **kwargs):
        if "tipo = 'produto'" not in query:
            return FakeResult(None)

        if "SELECT *" in query:
            # Ordem fisica criada pela migration base:
            # percentual vem antes de ativo/tipo_calculo.
            return FakeResult(
                (
                    10,
                    7,
                    "produto",
                    99,
                    Decimal("12.5"),
                    True,
                    "percentual",
                    True,
                    True,
                    False,
                    True,
                    Decimal("0"),
                    True,
                    "obs",
                    datetime(2026, 1, 1),
                    datetime(2026, 1, 1),
                    tenant_id,
                )
            )

        return FakeResult(
            (
                10,
                7,
                "produto",
                99,
                "percentual",
                Decimal("12.5"),
                Decimal("0"),
                True,
                True,
                False,
                True,
                True,
                "obs",
                True,
            )
        )

    monkeypatch.setattr(
        comissoes_service, "execute_tenant_safe", fake_execute_tenant_safe
    )

    config = comissoes_service.buscar_configuracao_comissao(
        db=object(),
        funcionario_id=7,
        produto_id=99,
        tenant_id=tenant_id,
    )

    assert config["id"] == 10
    assert config["funcionario_id"] == 7
    assert config["tipo"] == "produto"
    assert config["referencia_id"] == 99
    assert config["tipo_calculo"] == "percentual"
    assert config["percentual"] == Decimal("12.5")
    assert config["percentual_loja"] == Decimal("0")
    assert config["ativo"] is True
    assert config["desconta_taxa_cartao"] is True
    assert config["desconta_impostos"] is True
    assert config["desconta_custo_entrega"] is False
    assert config["comissao_venda_parcial"] is True
