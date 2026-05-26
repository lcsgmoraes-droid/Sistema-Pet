from types import SimpleNamespace

import os


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app import dashboard_routes


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
