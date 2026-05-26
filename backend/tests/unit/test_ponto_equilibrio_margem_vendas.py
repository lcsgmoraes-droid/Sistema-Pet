from datetime import date, datetime
from types import SimpleNamespace

import os


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app import dashboard_routes


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def options(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)


class _FakeDb:
    def __init__(self, vendas):
        self.vendas = vendas

    def query(self, *args, **kwargs):
        return _FakeQuery(self.vendas)


def test_ponto_equilibrio_soma_margem_pelo_snapshot_da_venda():
    func = getattr(dashboard_routes, "_somar_componentes_margem_vendas_pe", None)
    assert func is not None

    resultado = func(
        [
            {
                "snapshot": {
                    "venda_id": 10,
                    "numero_venda": "202605250001",
                    "data_venda": "2026-05-25T10:00:00",
                    "cliente_nome": "Cliente Teste",
                    "venda_bruta": 100.0,
                    "taxa_loja": 12.0,
                    "desconto": 5.0,
                    "custo_campanha": 3.0,
                    "taxa_cartao": 4.0,
                    "taxa_entrega": 7.0,
                    "taxa_operacional": 2.0,
                    "comissao": 6.0,
                    "imposto": 8.0,
                    "custo_produtos": 40.0,
                },
                "nf_emitida": True,
            }
        ],
        outros_variaveis=9.0,
        detalhes_outros_variaveis=[
            {
                "id": 99,
                "descricao": "Embalagens",
                "valor": 9.0,
                "data_vencimento": "2026-05-25",
                "origem_classificacao": "Conta variavel operacional",
            }
        ],
    )

    assert resultado["faturamento"] == 112.0
    assert resultado["receita_produtos_servicos"] == 100.0
    assert resultado["receita_entrega"] == 12.0
    assert resultado["descontos"] == 5.0
    assert resultado["beneficios_campanhas"] == 3.0
    assert resultado["taxas_cartao"] == 4.0
    assert resultado["repasse_entrega"] == 7.0
    assert resultado["custo_operacional_entrega"] == 2.0
    assert resultado["comissoes"] == 6.0
    assert resultado["custo_fiscal"] == 8.0
    assert resultado["cmv_estimado"] == 40.0
    assert resultado["outros_variaveis"] == 9.0
    assert resultado["custos_variaveis"] == 84.0
    assert resultado["margem_contribuicao"] == 28.0
    assert resultado["margem_contribuicao_percentual"] == 25.0
    assert resultado["detalhes_margem"]["subtotais"][0]["id"] == "receita_produtos_servicos"
    assert resultado["detalhes_margem"]["componentes"]["custo_fiscal"][0]["valor"] == 8.0
    assert resultado["detalhes_margem"]["componentes"]["outros_variaveis"][0]["descricao"] == "Embalagens"


def test_ponto_equilibrio_calcula_snapshots_em_lote_sem_get_or_build_por_venda(monkeypatch):
    vendas = [
        SimpleNamespace(
            id=1,
            numero_venda="202605010001",
            status="pago",
            data_venda=datetime(2026, 5, 1, 10, 0),
            canal="loja_fisica",
            subtotal=100.0,
            nfe_status=None,
            nfe_bling_id=None,
            nfe_chave=None,
            nfe_numero=None,
        ),
        SimpleNamespace(
            id=2,
            numero_venda="202605010002",
            status="pago",
            data_venda=datetime(2026, 5, 1, 11, 0),
            canal="loja_fisica",
            subtotal=50.0,
            nfe_status=None,
            nfe_bling_id=None,
            nfe_chave=None,
            nfe_numero=None,
        ),
    ]
    chamados = {
        "build": 0,
        "formas": 0,
        "impostos": 0,
        "comissoes": 0,
        "cupons": 0,
        "cashback": 0,
        "taxa_operacional": 0,
        "estoque": 0,
    }

    def falha_get_or_build(*args, **kwargs):
        raise AssertionError("nao deve reconstruir snapshots com consultas por venda")

    def build_rapido(venda, db, tenant_id, **kwargs):
        chamados["build"] += 1
        assert kwargs["formas_pagamento_map"] == {}
        assert kwargs["impostos_percentual"] == 7.0
        assert kwargs["comissao_total"] == 0.0
        assert kwargs["taxa_operacional_entrega"] == 0.0
        assert kwargs["estoque_custos_por_produto"] == {}
        return {
            "venda_id": venda.id,
            "numero_venda": venda.numero_venda,
            "data_venda": venda.data_venda.isoformat(),
            "cliente_nome": "Cliente Teste",
            "venda_bruta": venda.subtotal,
            "taxa_loja": 0.0,
            "desconto": 0.0,
            "custo_campanha": 0.0,
            "taxa_cartao": 0.0,
            "taxa_entrega": 0.0,
            "taxa_operacional": 0.0,
            "comissao": 0.0,
            "imposto": 0.0,
            "custo_produtos": 10.0,
        }

    monkeypatch.setattr(dashboard_routes, "get_or_build_venda_rentabilidade_snapshot", falha_get_or_build, raising=False)
    monkeypatch.setattr(dashboard_routes, "build_venda_rentabilidade_snapshot", build_rapido, raising=False)
    monkeypatch.setattr(dashboard_routes, "_formas_pagamento_map", lambda db, tenant_id: chamados.update(formas=chamados["formas"] + 1) or {}, raising=False)
    monkeypatch.setattr(dashboard_routes, "_impostos_percentual", lambda db, tenant_id: chamados.update(impostos=chamados["impostos"] + 1) or 7.0, raising=False)
    monkeypatch.setattr(dashboard_routes, "_bulk_comissoes_por_venda", lambda db, tenant_id, venda_ids: chamados.update(comissoes=chamados["comissoes"] + 1) or {}, raising=False)
    monkeypatch.setattr(dashboard_routes, "_bulk_cupons_por_venda", lambda db, tenant_id, vendas: chamados.update(cupons=chamados["cupons"] + 1) or {}, raising=False)
    monkeypatch.setattr(dashboard_routes, "_bulk_cashback_por_venda", lambda db, tenant_id, venda_ids: chamados.update(cashback=chamados["cashback"] + 1) or {}, raising=False)
    monkeypatch.setattr(dashboard_routes, "_bulk_taxa_operacional_por_venda", lambda db, tenant_id, vendas: chamados.update(taxa_operacional=chamados["taxa_operacional"] + 1) or {}, raising=False)
    monkeypatch.setattr(dashboard_routes, "_bulk_estoque_custos_por_venda", lambda db, tenant_id, venda_ids: chamados.update(estoque=chamados["estoque"] + 1) or {}, raising=False)

    resultado = dashboard_routes._calcular_margem_periodo_ponto_equilibrio(
        _FakeDb(vendas),
        "tenant-1",
        date(2026, 5, 1),
        date(2026, 5, 31),
        ["loja_fisica"],
        outros_variaveis=0.0,
    )

    assert resultado["quantidade_vendas"] == 2
    assert resultado["faturamento"] == 150.0
    assert resultado["cmv_estimado"] == 20.0
    assert chamados == {
        "build": 2,
        "formas": 1,
        "impostos": 1,
        "comissoes": 1,
        "cupons": 1,
        "cashback": 1,
        "taxa_operacional": 1,
        "estoque": 1,
    }


def test_ponto_equilibrio_modo_documentos_emitidos_remove_custo_fiscal_sem_nf():
    ajustar = getattr(dashboard_routes, "_ajustar_snapshot_custo_fiscal_pe", None)
    somar = getattr(dashboard_routes, "_somar_componentes_margem_vendas_pe", None)
    assert ajustar is not None
    assert somar is not None

    snapshot = {
        "venda_id": 11,
        "numero_venda": "202605250002",
        "venda_bruta": 100.0,
        "taxa_loja": 0.0,
        "imposto": 7.0,
        "custo_produtos": 50.0,
    }

    ajustado = ajustar(snapshot, venda_tem_documento=False, modo_custo_fiscal="documentos_emitidos")
    resultado = somar([{"snapshot": ajustado, "nf_emitida": False}])

    assert ajustado["imposto"] == 0.0
    assert ajustado["custo_fiscal_original"] == 7.0
    assert ajustado["custo_fiscal_desconsiderado"] == 7.0
    assert resultado["custo_fiscal"] == 0.0
    assert resultado["cmv_estimado"] == 50.0
    assert resultado["margem_contribuicao"] == 50.0
    assert resultado["detalhes_margem"]["componentes"]["custo_fiscal"][0]["observacao"] == (
        "Custo fiscal estimado desconsiderado nesta visao"
    )


def test_ponto_equilibrio_identifica_conta_variavel_ja_coberta_pelo_snapshot():
    func = getattr(dashboard_routes, "_conta_variavel_ja_coberta_pelo_snapshot_pe", None)
    assert func is not None

    taxa_cartao = SimpleNamespace(descricao="Taxa Credito - Venda 202604130015")
    embalagem = SimpleNamespace(descricao="Embalagens para delivery")

    assert func(taxa_cartao, "Taxas de Cartao de Credito", "Taxas") is True
    assert func(embalagem, "Embalagens", "Custos variaveis") is False


def test_ponto_equilibrio_pagina_detalhes_sob_demanda():
    func = getattr(dashboard_routes, "_paginar_detalhes_ponto_equilibrio", None)
    assert func is not None

    resultado = func(
        [{"id": item_id, "valor": item_id} for item_id in range(1, 6)],
        page=2,
        page_size=2,
    )

    assert resultado["page"] == 2
    assert resultado["page_size"] == 2
    assert resultado["pages"] == 3
    assert resultado["total_itens"] == 5
    assert [item["id"] for item in resultado["items"]] == [3, 4]
