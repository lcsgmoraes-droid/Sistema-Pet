from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from app.services.faturamento_composicao import compor_recebimentos, compor_vendas


def pagamento(valor, forma="PIX", ident=1, **kwargs):
    return NS(
        id=ident,
        valor=Decimal(str(valor)),
        forma_pagamento=forma,
        forma_pagamento_id=kwargs.pop("forma_pagamento_id", None),
        intervalo_crediario=None,
        status=kwargs.pop("status", "pendente"),
        data_pagamento=datetime(2026, 10, 20, 12),
        **kwargs,
    )


def venda(total=100, desconto=0, entrega=0, pagamentos=None, **kwargs):
    return NS(
        id=kwargs.pop("ident", 1),
        numero_venda="202610200001",
        data_venda=datetime(2026, 10, 20, 10),
        total=Decimal(str(total)),
        desconto_valor=Decimal(str(desconto)),
        taxa_entrega=Decimal(str(entrega)),
        status=kwargs.pop("status", "finalizada"),
        pagamentos=pagamentos or [],
        contas_receber=kwargs.pop("contas_receber", []),
        **kwargs,
    )


def resumo(vendas, **kwargs):
    return compor_vendas(
        vendas, data_inicio=date(2026, 10, 20), data_fim=date(2026, 10, 20), **kwargs
    )


def confere_identidades(composicao):
    def d(campo):
        return Decimal(str(composicao[campo]))

    assert d("faturamento_liquido") == d("faturamento_bruto") - d("descontos") - d(
        "devolucoes"
    )
    assert d("total_vendas") == d("faturamento_liquido") + d("taxa_entrega")
    assert d("total_vendas") == sum(
        (
            d(campo)
            for campo in (
                "valor_pago",
                "creditos_utilizados",
                "crediario_receber",
                "em_aberto",
            )
        ),
        Decimal(0),
    )


def test_liquido_comercial_separa_desconto_entrega_beneficios_e_em_aberto():
    resultado = resumo(
        [
            venda(
                total=105,
                desconto=10,
                entrega=15,
                status="baixa_parcial",
                pagamentos=[
                    pagamento(50),
                    pagamento(5, "Cashback", 2),
                    pagamento(10, "Crédito Cliente", 3),
                ],
            )
        ]
    )
    assert resultado["faturamento_bruto"] == 100
    assert resultado["descontos"] == 10
    assert resultado["faturamento_liquido"] == 90
    assert resultado["taxa_entrega"] == 15
    assert resultado["valor_pago"] == 50
    assert resultado["creditos_utilizados"] == 15
    assert resultado["em_aberto"] == 40
    confere_identidades(resultado)


@pytest.mark.parametrize("status", ["cancelado", "cancelada", " CANCELADA "])
def test_cancelamento_comercial_exclui_venda_sem_apagar_historico(status):
    original = venda(pagamentos=[pagamento(100)], status=status)
    resultado = resumo([original])
    assert resultado["quantidade"] == 0
    assert resultado["total_vendas"] == 0
    assert original.pagamentos[0].valor == 100


@pytest.mark.parametrize("status", ["estornado", "recusado", "cancelado", "cancelada"])
def test_pagamento_invalido_nao_e_ressuscitado_pelo_status_finalizada(status):
    resultado = resumo([venda(pagamentos=[pagamento(100, status=status)])])
    assert resultado["valor_pago"] == 0
    assert resultado["em_aberto"] == 100
    confere_identidades(resultado)


def test_contrapartida_negativa_reduz_quitacao_antes_do_piso():
    resultado = resumo([venda(pagamentos=[pagamento(80), pagamento(-30, ident=2)])])
    assert resultado["valor_pago"] == 50
    assert resultado["em_aberto"] == 50
    assert resultado["detalhes"][0]["pagamentos"][1]["valor"] == -30


def test_crediario_gerado_nao_e_pagamento_e_preserva_centavo_em_aberto():
    resultado = resumo(
        [venda(total=100.01, status="aberta", pagamentos=[pagamento(100, "Crediário")])]
    )
    assert resultado["valor_pago"] == 0
    assert resultado["crediario_receber"] == 100
    assert resultado["em_aberto"] == 0.01
    confere_identidades(resultado)


@pytest.mark.parametrize("espelhado", [False, True])
def test_parcela_recebida_so_conta_uma_vez_com_ou_sem_espelho_pagamento(espelhado):
    conta = NS(id=7, forma_pagamento_id=30, valor_recebido=20, status="parcial")
    pagamentos = [pagamento(100, "Crediário", forma_pagamento_id=30)]
    if espelhado:
        pagamentos.append(pagamento(20, ident=2))
    recibo = NS(
        id=9,
        valor_recebido=20,
        forma_pagamento=None,
        observacoes="[venda_pagamento:2]" if espelhado else None,
    )
    resultado = resumo(
        [venda(pagamentos=pagamentos, contas_receber=[conta])],
        recebimentos_por_conta={7: [recibo]},
    )
    assert resultado["valor_pago"] == 20
    assert resultado["crediario_receber"] == 80
    assert resultado["em_aberto"] == 0
    confere_identidades(resultado)


def test_baixa_lote_sem_marcador_usa_vinculo_imutavel_para_nao_duplicar():
    conta = NS(id=7, forma_pagamento_id=30, valor_recebido=20, status="parcial")
    recibo = NS(
        id=9, valor_recebido=20, forma_pagamento=None, observacoes="Baixa em lote - PIX"
    )
    resultado = resumo(
        [
            venda(
                contas_receber=[conta],
                pagamentos=[
                    pagamento(100, "Crediário", forma_pagamento_id=30),
                    pagamento(20, ident=2),
                ],
            )
        ],
        recebimentos_por_conta={7: [recibo]},
        recebimentos_espelhados={9},
    )
    assert resultado["valor_pago"] == 20
    assert resultado["crediario_receber"] == 80
    confere_identidades(resultado)


def test_misto_nao_confunde_repasse_cartao_com_recebimento_de_crediario():
    contas = [
        NS(id=7, forma_pagamento_id=20, valor_recebido=30, status="recebido"),
        NS(id=8, forma_pagamento_id=30, valor_recebido=20, status="parcial"),
    ]
    recibo = NS(id=9, valor_recebido=20, forma_pagamento=None, observacoes=None)
    resultado = resumo(
        [
            venda(
                contas_receber=contas,
                pagamentos=[
                    pagamento(30, "Cartão de crédito", forma_pagamento_id=20),
                    pagamento(70, "Crediário", ident=2, forma_pagamento_id=30),
                ],
            )
        ],
        recebimentos_por_conta={8: [recibo]},
    )
    assert resultado["valor_pago"] == 50
    assert resultado["crediario_receber"] == 50
    confere_identidades(resultado)


@pytest.mark.parametrize("status", ["aberta", "finalizada"])
def test_legado_sem_pagamentos_respeita_recebido_comprovado_nas_contas(status):
    conta = NS(id=7, valor_recebido=20, status="parcial")
    resultado = resumo([venda(status=status, contas_receber=[conta])])
    assert resultado["valor_pago"] == 20
    assert resultado["em_aberto"] == 80
    assert resultado["detalhes"][0]["pagamentos"][0]["origem"] == "conta_legada"
    confere_identidades(resultado)


def test_tenant_dos_pagamentos_contas_e_recibos_nao_pode_contaminar_composicao():
    conta = NS(id=7, valor_recebido=500, status="recebido", tenant_id="outra-empresa")
    resultado = resumo(
        [
            venda(
                status="aberta",
                tenant_id="empresa",
                contas_receber=[conta],
                pagamentos=[pagamento(500, tenant_id="outra-empresa")],
            )
        ]
    )
    assert resultado["valor_pago"] == 0
    assert resultado["em_aberto"] == 100
    confere_identidades(resultado)


@pytest.mark.parametrize(
    "status,valor_recebido,esperado,descricao",
    [
        ("aberta", 20, 20, "Quitação legada (valor recebido salvo)"),
        ("finalizada", 0, 100, "Quitação legada pelo status da venda"),
    ],
)
def test_quitacao_legada_comprovada_expoe_proveniencia_sem_inventar_data(
    status, valor_recebido, esperado, descricao
):
    resultado = resumo([venda(status=status, valor_recebido=valor_recebido)])
    assert resultado["valor_pago"] == esperado
    detalhe = resultado["detalhes"][0]["pagamentos"]
    assert len(detalhe) == 1
    assert detalhe[0]["origem"] == "venda_legada"
    assert detalhe[0]["valor"] == esperado
    assert detalhe[0]["forma_pagamento"] == descricao
    assert detalhe[0]["data_pagamento"] is None
    confere_identidades(resultado)


def test_fallback_valor_recebido_salvo_adiciona_somente_diferenca_das_contas():
    conta = NS(id=7, valor_recebido=30, status="parcial")
    resultado = resumo(
        [venda(status="aberta", contas_receber=[conta], valor_recebido=40)]
    )
    assert resultado["valor_pago"] == 40
    detalhes = resultado["detalhes"][0]["pagamentos"]
    assert [p["valor"] for p in detalhes] == [30, 10]
    assert [p["origem"] for p in detalhes] == ["conta_legada", "venda_legada"]
    confere_identidades(resultado)


@pytest.mark.parametrize(
    "devolucao,status,liquido,total",
    [(25, "finalizada_devolucao", 65, 80), (90, "devolvida_total", 0, 15)],
)
def test_devolucao_abate_apenas_valor_rastreado_e_preserva_entrega(
    devolucao, status, liquido, total
):
    original = venda(
        total=105, desconto=10, entrega=15, status=status, pagamentos=[pagamento(105)]
    )
    resultado = resumo(
        [original],
        devolucoes_por_venda={1: [NS(valor_devolvido=devolucao, resposta={})]},
    )
    assert resultado["faturamento_liquido"] == liquido
    assert resultado["total_vendas"] == total
    assert resultado["valor_pago"] == total
    assert original.total == 105
    confere_identidades(resultado)


def test_restituicao_beneficio_na_origem_reduz_quitacao_apos_devolucao():
    resultado = resumo(
        [
            venda(
                pagamentos=[pagamento(80), pagamento(20, "Cashback", 2)],
                status="finalizada_devolucao",
            )
        ],
        devolucoes_por_venda={
            1: [
                NS(
                    valor_devolvido=50,
                    resposta={"restituicao": {"cashback": 10, "credito_cliente": 0}},
                )
            ]
        },
    )
    assert resultado["faturamento_liquido"] == 50
    assert resultado["valor_pago"] == 40
    assert resultado["creditos_utilizados"] == 10
    confere_identidades(resultado)


def test_arredondamento_decimal_nao_perde_centavo_em_muitas_vendas():
    resultado = resumo(
        [
            venda(
                total="0.01", desconto="0.01", ident=i, pagamentos=[pagamento("0.01")]
            )
            for i in range(1, 1001)
        ]
    )
    assert resultado["faturamento_bruto"] == 20
    assert resultado["descontos"] == 10
    assert resultado["faturamento_liquido"] == 10
    confere_identidades(resultado)


def test_recebimentos_caixa_separam_anteriores_beneficios_planos_e_estornos():
    eventos = [
        {
            "id": "p1",
            "valor": 100,
            "forma_pagamento": "PIX",
            "data_venda": "2026-10-20",
        },
        {
            "id": "p2",
            "valor": 95.9,
            "forma_pagamento": "Cartão de crédito",
            "data_venda": "2026-10-15",
        },
        {
            "id": "p3",
            "valor": 20,
            "forma_pagamento": "Crédito Cliente",
            "data_venda": "2026-10-19",
        },
        {
            "id": "plano",
            "valor": 500,
            "forma_pagamento": "Crediário",
            "data_venda": "2026-10-20",
        },
        {
            "id": "p4",
            "valor": -10,
            "forma_pagamento": "PIX",
            "data_venda": "2026-10-20",
        },
        {
            "id": "m1",
            "valor": -5,
            "forma_pagamento": "Dinheiro",
            "data_venda": "2026-10-19",
        },
    ]
    resultado = compor_recebimentos(
        eventos, data_inicio="2026-10-20", data_fim="2026-10-20"
    )
    assert resultado["total_recebido"] == 180.9
    assert resultado["vendas_periodo"] == 100
    assert resultado["vendas_anteriores"] == 95.9
    assert resultado["devolucoes"] == 15
    assert resultado["creditos_utilizados"] == 20
    assert len(resultado["detalhes_creditos"]) == 1
    assert sum(
        Decimal(str(d["total"])) for d in resultado["por_forma_pagamento"].values()
    ) == Decimal("180.90")
