"""A resposta imediata usa os pagamentos gravados na mesma sessao do PDV."""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
import re
import shutil
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.caixa.service import CaixaService
from app.financeiro_models import ContaReceber, FormaPagamento
from app.models import Cliente
from app.vendas import finalizacao_pos_commit, finalizacao_routes
from app.vendas.schemas import FinalizarVendaRequest
from app.vendas_models import Venda, VendaPagamento
from tests.unit.test_finalizacao_recebiveis_atomicidade import cenario  # noqa: F401


@pytest.fixture
def cupom(request, monkeypatch):
    caso = request.getfixturevalue("cenario")
    # Mesma configuracao de SessionLocal: o commit nao descarta as relacoes.
    assert caso.db.expire_on_commit is False
    caso.db.autoflush = False
    caso.venda.caixa_id = 2
    caso.db.add(Cliente(id=7, tenant_id=caso.tenant, user_id=1, nome="Pessoa do teste"))
    caso.db.commit()
    monkeypatch.setattr(
        CaixaService, "validar_caixa_aberto", lambda **_kwargs: {"caixa_id": 2}
    )
    # Um rollback secundario expiraria a sessao e esconderia a regressao.
    monkeypatch.setattr(
        finalizacao_pos_commit,
        "processar_contas_pagar_taxas",
        lambda **_kwargs: {"success": True, "total_contas": 0, "valor_total": 0},
    )
    monkeypatch.setattr(
        "app.services.crediario_notifications.criar_notificacoes_parcelas_crediario",
        lambda *_args, **_kwargs: 0,
    )
    monkeypatch.setattr(
        finalizacao_routes,
        "get_opportunity_processor",
        lambda **_kwargs: SimpleNamespace(cleanup=lambda: None),
    )
    return caso


def preparar_venda(cupom, total, *, entrega=False):
    cupom.venda.total = cupom.venda.subtotal = Decimal(str(total))
    cupom.venda.tem_entrega = entrega
    cupom.venda.entregador_id = 7 if entrega else None
    cupom.db.commit()


def dinheiro(valor, recebido):
    return {
        "forma_pagamento": "Dinheiro",
        "forma_pagamento_id": 2,
        "valor": valor,
        "valor_recebido": recebido,
        "troco": float(Decimal(str(recebido)) - Decimal(str(valor))),
    }


def finalizar(cupom, pagamentos):
    # Executa a rota e o servico reais; a idempotencia tem cobertura propria.
    # Nao abrir outra sessao nem expirar os objetos antes de conferir a resposta.
    return asyncio.run(
        finalizacao_routes.finalizar_venda.__wrapped__(
            venda_id=cupom.venda.id,
            dados=FinalizarVendaRequest(pagamentos=pagamentos),
            request=None,
            db=cupom.db,
            user_and_tenant=(SimpleNamespace(id=1, nome="Operador"), cupom.tenant),
        )
    )


@pytest.mark.parametrize("entrega", [False, True], ids=["balcao", "entrega"])
@pytest.mark.parametrize("total,recebido,troco", [(14, 20, 6), (17.5, 50, 32.5)])
def test_resposta_imediata_inclui_pagamento_recebido_e_troco(
    cupom, total, recebido, troco, entrega
):
    preparar_venda(cupom, total, entrega=entrega)

    resposta = finalizar(cupom, [dinheiro(total, recebido)])

    assert cupom.db.query(Venda).filter_by(id=cupom.venda.id).one() is cupom.venda
    assert resposta["valor_pago"] == total
    assert resposta["valor_restante"] == 0
    assert resposta["status_pagamento"] == "pago"
    [pagamento] = resposta["pagamentos"]
    assert pagamento["valor"] == total
    assert pagamento["valor_recebido"] == recebido
    assert pagamento["troco"] == troco
    assert len(cupom.venda.contas_receber) == 1
    assert cupom.venda.contas_receber[0].valor_recebido == Decimal(str(total))


def test_complemento_preserva_pagamento_anterior_e_inclui_o_novo(cupom):
    preparar_venda(cupom, 17.5)

    parcial = finalizar(cupom, [dinheiro(10, 10)])
    assert parcial["valor_pago"] == 10
    assert parcial["valor_restante"] == 7.5
    assert parcial["status_pagamento"] == "parcial"

    completo = finalizar(cupom, [dinheiro(7.5, 10)])

    assert completo["valor_pago"] == 17.5
    assert completo["valor_restante"] == 0
    assert completo["status_pagamento"] == "pago"
    assert [p["valor"] for p in completo["pagamentos"]] == [10, 7.5]
    assert [p["troco"] for p in completo["pagamentos"]] == [0, 2.5]
    assert sum(c.valor_recebido for c in cupom.venda.contas_receber) == Decimal("17.50")


def test_crediario_pendente_continua_sem_declarar_recebimento(cupom):
    preparar_venda(cupom, 100)
    cupom.venda.cliente_id = 7
    cupom.venda.nao_gerar_beneficios = True
    forma = cupom.db.get(FormaPagamento, 1)
    forma.nome = "Crediario"
    forma.tipo = "crediario"
    cupom.db.commit()

    resposta = finalizar(
        cupom,
        [
            {
                "forma_pagamento": "Crediario",
                "forma_pagamento_id": 1,
                "valor": 100,
                "numero_parcelas": 2,
                "data_recebimento_prevista": date.today() + timedelta(days=30),
                "intervalo_crediario": "mensal",
            }
        ],
    )

    assert resposta["valor_pago"] == 0
    assert resposta["valor_restante"] == 100
    assert resposta["status_pagamento"] == "em_aberto"
    assert len(resposta["pagamentos"]) == 1
    assert len(cupom.venda.contas_receber) == 2
    assert all(c.valor_recebido == 0 for c in cupom.venda.contas_receber)


def test_relacoes_recarregadas_respeitam_o_tenant(cupom, tenant_context):
    preparar_venda(cupom, 14)
    outro_tenant = uuid4()
    tenant_context(outro_tenant)
    # Simula vinculos legados inconsistentes na mesma venda, de outra empresa.
    cupom.db.add(
        VendaPagamento(
            tenant_id=outro_tenant,
            venda_id=cupom.venda.id,
            forma_pagamento="Dinheiro",
            valor=999,
        )
    )
    cupom.db.add(
        ContaReceber(
            tenant_id=outro_tenant,
            venda_id=cupom.venda.id,
            descricao="Conta de outra empresa",
            valor_original=999,
            valor_final=999,
            valor_recebido=999,
            status="recebido",
            user_id=1,
            dre_subcategoria_id=1,
            canal="loja_fisica",
            data_emissao=date.today(),
            data_vencimento=date.today(),
        )
    )
    cupom.db.commit()
    tenant_context(cupom.tenant)

    resposta = finalizar(cupom, [dinheiro(14, 20)])

    assert resposta["valor_pago"] == 14
    assert len(resposta["pagamentos"]) == 1
    assert all(p.tenant_id == cupom.tenant for p in cupom.venda.pagamentos)
    assert len(cupom.venda.contas_receber) == 1
    assert all(c.tenant_id == cupom.tenant for c in cupom.venda.contas_receber)


@pytest.mark.skipif(
    shutil.which("node") is None, reason="Node necessario para gerar cupom real"
)
@pytest.mark.parametrize(
    "total,recebido,pago_brl,troco_brl",
    [(14, 20, "14,00", "6,00"), (17.5, 50, "17,50", "32,50")],
)
def test_cupom_gerado_da_resposta_real_imprime_pago_e_troco(
    cupom, total, recebido, pago_brl, troco_brl
):
    preparar_venda(cupom, total, entrega=total == 17.5)
    resposta = finalizar(cupom, [dinheiro(total, recebido)])
    resultado = subprocess.run(
        [
            shutil.which("node"),
            "--input-type=module",
            "-e",
            "import { montarCupomVenda } from './src/utils/pdvReceipt.js'; "
            "let dados=''; for await (const pedaco of process.stdin) dados+=pedaco; "
            "process.stdout.write(montarCupomVenda(JSON.parse(dados)));",
        ],
        input=json.dumps(resposta),
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
        cwd=Path(__file__).resolve().parents[3] / "frontend",
    )

    assert re.search(r"VALOR PAGO:\s+R\$ " + re.escape(pago_brl), resultado.stdout)
    assert re.search(r"TROCO:\s+R\$ " + re.escape(troco_brl), resultado.stdout)
    assert "VALOR A RECEBER:" not in resultado.stdout
