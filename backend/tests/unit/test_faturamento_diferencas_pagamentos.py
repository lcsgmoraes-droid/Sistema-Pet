"""Origem das diferenças, sem reclassificar pagamentos ou alterar a conferência."""

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace as NS

from app.caixa.auditoria import assinatura_item
from app.services.faturamento_composicao import (
    _formas_pagamento_vendas,
    compor_vendas,
)


def pagamento(valor, forma="Pix", ident=1):
    return NS(
        id=ident,
        valor=Decimal(str(valor)),
        forma_pagamento=forma,
        forma_pagamento_id=None,
        intervalo_crediario=None,
        status="pendente",
        data_pagamento=datetime(2026, 10, 22, 12),
    )


def venda(total, pagamentos, ident=21, desconto=0, status="finalizada"):
    return NS(
        id=ident,
        numero_venda=f"20261022{ident:04d}",
        data_venda=datetime(2026, 10, 22, 10),
        total=Decimal(str(total)),
        desconto_valor=Decimal(str(desconto)),
        taxa_entrega=Decimal("0.00"),
        status=status,
        pagamentos=pagamentos,
        contas_receber=[],
    )


def resumo(vendas, **kwargs):
    return compor_vendas(
        vendas, data_inicio=date(2026, 10, 22), data_fim=date(2026, 10, 22), **kwargs
    )


def test_excesso_identifica_venda_e_cartao_original_sem_inventar_reembolso():
    original = venda("109.90", [pagamento("119.90", "Cartão de crédito")], desconto=10)
    pagamentos_antes = deepcopy(original.pagamentos)
    resultado = resumo([original])

    assert resultado["valor_pago"] == 109.90
    assert resultado["total_formas_pagamento"] == 119.90
    assert resultado["ajustes_formas_pagamento"] == -10
    assert resultado["diferencas_pagamentos"] == [
        {
            "venda_id": 21,
            "numero_venda": "202610220021",
            "data_venda": "2026-10-22T10:00:00",
            "valor_pago": 109.90,
            "total_pagamentos_registrados": 119.90,
            "diferenca": -10.0,
            "descontos": 10.0,
            "devolucoes": 0.0,
            "total_vendas": 109.90,
            "formas_pagamento": [
                {
                    "forma_pagamento": "Cartão de crédito",
                    "total": 119.90,
                    "quantidade": 1,
                }
            ],
            "motivo": "pagamento_acima_total_venda",
        }
    ]
    assert resultado["resumo_diferencas_pagamentos"] == [
        {
            "motivo": "pagamento_acima_total_venda",
            "diferenca": -10.0,
            "quantidade": 1,
        }
    ]
    assert original.pagamentos == pagamentos_antes
    assert original.total == Decimal("109.90")
    assert original.desconto_valor == 10


def test_devolucoes_identificam_duas_vendas_e_pagamentos_originais():
    vendas = [
        venda(100, [pagamento(100, "PIX")], ident=1, status="devolvida_total"),
        venda(200, [pagamento(200, "Pix")], ident=4, status="devolvida_total"),
    ]
    resultado = resumo(
        vendas,
        devolucoes_por_venda={
            1: [NS(valor_devolvido=100, resposta={})],
            4: [NS(valor_devolvido=200, resposta={})],
        },
    )

    assert resultado["total_formas_pagamento"] == 300
    assert resultado["ajustes_formas_pagamento"] == -300
    assert resultado["valor_pago"] == 0
    assert resultado["resumo_diferencas_pagamentos"] == [
        {"motivo": "devolucao", "diferenca": -300.0, "quantidade": 2}
    ]
    diferencas = resultado["diferencas_pagamentos"]
    assert [item["venda_id"] for item in diferencas] == [4, 1]
    assert [item["diferenca"] for item in diferencas] == [-200, -100]
    for item in diferencas:
        assert item["motivo"] == "devolucao"
        assert item["total_vendas"] == 0
        assert item["formas_pagamento"] == [
            {
                "forma_pagamento": "Pix",
                "total": -item["diferenca"],
                "quantidade": 1,
            }
        ]
        assert "forma_devolucao" not in item
        assert "reembolso" not in item


def test_pagamentos_mistos_preservam_as_formas_sem_ratear_diferenca():
    resultado = resumo(
        [venda(90, [pagamento(40, "Dinheiro"), pagamento(60, "Pix", 2)])]
    )

    diferenca = resultado["diferencas_pagamentos"][0]
    assert diferenca["diferenca"] == -10
    assert diferenca["total_pagamentos_registrados"] == 100
    assert diferenca["formas_pagamento"] == [
        {"forma_pagamento": "Dinheiro", "total": 40.0, "quantidade": 1},
        {"forma_pagamento": "Pix", "total": 60.0, "quantidade": 1},
    ]
    assert diferenca["formas_pagamento"] == resultado["formas_pagamento"]


def test_teto_apos_beneficio_separa_pagamento_monetario_do_credito_utilizado():
    resultado = resumo(
        [
            venda(
                100,
                [pagamento(100, "Pix"), pagamento(10, "Crédito Cliente", 2)],
            )
        ]
    )

    assert resultado["valor_pago"] == 90
    assert resultado["creditos_utilizados"] == 10
    diferenca = resultado["diferencas_pagamentos"][0]
    assert diferenca["diferenca"] == -10
    assert diferenca["motivo"] == "pagamento_acima_total_venda"
    assert diferenca["formas_pagamento"] == [
        {"forma_pagamento": "Pix", "total": 100.0, "quantidade": 1}
    ]


def test_aliases_e_quantidades_tem_mesma_regra_no_total_e_na_origem():
    resultado = resumo(
        [
            venda(
                100,
                [
                    pagamento(20, "Débito"),
                    pagamento(30, "cartao_debito", 2),
                    pagamento(60, "PIX", 3),
                ],
            )
        ]
    )

    esperado = [
        {"forma_pagamento": "Cartão de débito", "total": 50.0, "quantidade": 2},
        {"forma_pagamento": "Pix", "total": 60.0, "quantidade": 1},
    ]
    assert resultado["formas_pagamento"] == esperado
    assert resultado["diferencas_pagamentos"][0]["formas_pagamento"] == esperado


def test_vendas_conciliadas_e_planos_nao_criam_diferencas():
    resultado = resumo(
        [
            venda(100, [pagamento(100)]),
            venda(100, [pagamento(100, "Crediário")], ident=2),
            venda(100, [pagamento(100, "Cashback")], ident=3),
        ]
    )

    assert resultado["ajustes_formas_pagamento"] == 0
    assert resultado["diferencas_pagamentos"] == []
    assert resultado["resumo_diferencas_pagamentos"] == []
    assert resumo([])["diferencas_pagamentos"] == []


def test_resumo_separa_motivos_e_nao_esconde_diferencas_que_se_compensam():
    base = {
        "data_venda": "2026-10-22",
        "descontos": 0,
        "devolucoes": 0,
        "total_vendas": 100,
    }
    resultado = _formas_pagamento_vendas(
        [
            {
                **base,
                "venda_id": 1,
                "numero_venda": "202610220001",
                "valor_pago": 90,
                "pagamentos": [
                    {"tipo": "pagamento", "forma_pagamento": "Pix", "valor": 100}
                ],
            },
            {
                **base,
                "venda_id": 2,
                "numero_venda": "202610220002",
                "valor_pago": 10,
                "pagamentos": [],
            },
        ]
    )

    assert resultado["ajustes_formas_pagamento"] == 0
    assert len(resultado["diferencas_pagamentos"]) == 2
    assert resultado["resumo_diferencas_pagamentos"] == [
        {
            "motivo": "pagamento_acima_total_venda",
            "diferenca": -10.0,
            "quantidade": 1,
        },
        {
            "motivo": "quitacao_sem_historico_correspondente",
            "diferenca": 10.0,
            "quantidade": 1,
        },
    ]


def test_metadados_ausentes_no_helper_nao_inventam_total_ou_identidade():
    resultado = _formas_pagamento_vendas([{"valor_pago": 10, "pagamentos": []}])

    diferenca = resultado["diferencas_pagamentos"][0]
    assert diferenca["motivo"] == "quitacao_sem_historico_correspondente"
    assert diferenca["venda_id"] is None
    assert diferenca["numero_venda"] is None
    assert diferenca["data_venda"] is None
    assert diferenca["total_vendas"] is None
    assert diferenca["total_pagamentos_registrados"] == 0
    assert diferenca["formas_pagamento"] == []


def test_detalhe_e_assinatura_da_conferencia_mantem_contrato_anterior():
    resultado = resumo(
        [venda("109.90", [pagamento("119.90", "Cartão de crédito")], desconto=10)]
    )
    esperado = {
        "venda_id": 21,
        "numero_venda": "202610220021",
        "data_venda": "2026-10-22T10:00:00",
        "status": "finalizada",
        "faturamento_bruto": 119.90,
        "descontos": 10.0,
        "devolucoes": 0.0,
        "faturamento_liquido": 109.90,
        "taxa_entrega": 0.0,
        "total_vendas": 109.90,
        "valor_pago": 109.90,
        "creditos_utilizados": 0.0,
        "crediario_receber": 0.0,
        "em_aberto": 0.0,
        "pagamentos": [
            {
                "id": 1,
                "origem": "pagamento",
                "forma_pagamento": "Cartão de crédito",
                "valor": 119.90,
                "data_pagamento": "2026-10-22T12:00:00",
                "status": "pendente",
                "tipo": "pagamento",
            }
        ],
    }

    assert resultado["detalhes"] == [esperado]
    assert assinatura_item({"composicao_comercial": resultado["detalhes"][0]}) == (
        assinatura_item({"composicao_comercial": esperado})
    )
    assert "diferencas_pagamentos" not in resultado["detalhes"][0]
