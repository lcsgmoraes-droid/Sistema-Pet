"""Recebimento excedente preserva banco/caixa e exige consentimento dos valores."""

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.caixa.service import CaixaService
from app.caixa_models import MovimentacaoCaixa
from app.financeiro_models import ContaReceber, Recebimento
from app.models import AuditLog
from app.vendas import finalizacao
from app.vendas.finalizacao_pagamentos import _calcular_pagamentos_finalizacao
from app.vendas.finalizacao_pagamentos import preparar_formas_pagamentos_finalizacao
from app.vendas.pagamento_excedente import (
    ACAO_EXCESSO,
    snapshot_pagamentos_excedente,
    validar_excesso_pagamento,
)
from app.vendas.schemas import FinalizarVendaRequest
from app.vendas_models import VendaPagamento
from tests.unit.test_finalizacao_recebiveis_atomicidade import cenario  # noqa: F401


@pytest.fixture
def caso(request, monkeypatch):
    caso = request.getfixturevalue("cenario")
    caso.venda.subtotal = Decimal("119.90")
    caso.venda.desconto_valor = Decimal("10")
    caso.venda.total = Decimal("109.90")
    caso.db.commit()
    monkeypatch.setattr(
        CaixaService, "validar_caixa_aberto", lambda **_: {"caixa_id": 2}
    )
    return caso


def executar(caso, pagamentos, *, motivo=None, contexto=None, db_session=None):
    return finalizacao.finalizar_venda(
        venda_id=caso.venda.id,
        pagamentos=pagamentos,
        user_id=1,
        user_nome="Operador DEV",
        tenant_id=caso.tenant,
        db=db_session or caso.db,
        justificativa_pagamento_excedente=motivo,
        contexto_pagamento_excedente=contexto,
        processar_baixa_estoque_item=lambda **_: [],
    )


def pix(valor):
    return {"forma_pagamento": "Pix", "forma_pagamento_id": 1, "valor": valor}


def desafiar(caso, pagamentos):
    with pytest.raises(HTTPException) as erro:
        executar(caso, pagamentos)
    assert erro.value.status_code == 409
    assert erro.value.detail["code"] == "PAGAMENTO_EXCEDENTE_REQUER_JUSTIFICATIVA"
    return erro.value.detail


def test_importacao_fria_composicao_e_guardas_financeiras_nao_tem_ciclo():
    resultado = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.services.faturamento_composicao; "
            "import app.contas_receber_saldo_venda; "
            "import app.vendas.recebimentos_independentes",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, "DATABASE_URL": "sqlite://"},
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert resultado.returncode == 0, resultado.stderr


def _receber_avulso_depois_do_pix(caso):
    caso.venda.total = caso.venda.subtotal = 100
    caso.venda.desconto_valor = 0
    caso.db.commit()
    executar(caso, [pix(30)])
    conta = ContaReceber(
        tenant_id=caso.tenant,
        venda_id=caso.venda.id,
        forma_pagamento_id=1,
        descricao="Baixa independente da previsão da venda",
        valor_original=70,
        valor_final=70,
        valor_recebido=70,
        valor_juros=0,
        valor_multa=0,
        valor_desconto=0,
        status="recebido",
        user_id=1,
        dre_subcategoria_id=1,
        canal="loja_fisica",
        data_emissao=date(2026, 10, 22),
        data_vencimento=date(2026, 10, 22),
        data_recebimento=date(2026, 10, 22),
    )
    caso.db.add(conta)
    caso.db.flush()
    caso.db.add(
        Recebimento(
            tenant_id=caso.tenant,
            conta_receber_id=conta.id,
            forma_pagamento_id=1,
            valor_recebido=70,
            data_recebimento=date(2026, 10, 22),
            user_id=1,
        )
    )
    caso.db.commit()
    caso.db.expire(caso.venda, ["pagamentos", "contas_receber"])
    return conta


def test_pix_30_e_baixa_avulsa_70_bloqueiam_novo_pagamento_pdv(caso):
    _receber_avulso_depois_do_pix(caso)
    fotografia = snapshot_pagamentos_excedente(caso.db, caso.venda, caso.tenant)
    assert fotografia["recebido_monetario"] == 100
    assert fotografia["total_ja_pago"] == 100
    with pytest.raises(HTTPException) as erro:
        executar(caso, [pix(70)])
    assert erro.value.status_code == 400
    assert "totalmente paga" in erro.value.detail
    assert caso.db.query(VendaPagamento).count() == 1
    assert caso.db.query(Recebimento).count() == 2


def test_refinalizacao_sem_novos_preserva_pix_e_baixa_avulsa(caso):
    _receber_avulso_depois_do_pix(caso)
    resultado = executar(caso, [])
    assert resultado["venda"]["total_pago"] == 100
    assert resultado["venda"]["total_recebido"] == 100
    assert caso.db.query(VendaPagamento).count() == 1
    assert caso.db.query(Recebimento).count() == 2
    assert caso.db.query(AuditLog).filter(AuditLog.action == ACAO_EXCESSO).count() == 0


def test_recebimento_11990_venda_liquida_10990_exige_contexto_e_preserva_contrapartidas(
    caso,
):
    desafio = desafiar(caso, [pix(119.90)])
    assert desafio["contexto_pagamento_excedente"] == {
        "total_venda": 109.90,
        "total_ja_pago": 0,
        "total_novos_pagamentos": 119.90,
        "crediario_pendente": 0,
    }
    assert desafio["excedente"] == 10
    assert caso.db.query(VendaPagamento).count() == 0
    assert caso.db.query(Recebimento).count() == 0
    assert caso.db.query(AuditLog).filter(AuditLog.action == ACAO_EXCESSO).count() == 0
    resultado = executar(
        caso,
        [pix(119.90)],
        motivo="Cliente transferiu o valor antes do desconto",
        contexto=desafio["contexto_pagamento_excedente"],
    )
    assert resultado["venda"]["total"] == 109.90
    assert resultado["venda"]["total_pago"] == 109.90
    assert resultado["venda"]["total_recebido"] == 119.90
    assert resultado["venda"]["excedente_recebido"] == 10
    pagamento = caso.db.query(VendaPagamento).one()
    assert pagamento.valor == Decimal("119.90")
    assert pagamento.valor_recebido == Decimal("119.90")
    assert pagamento.troco == 0
    assert sum(
        (c.valor_final for c in caso.db.query(ContaReceber).all()), Decimal(0)
    ) == Decimal("119.90")
    assert sum(
        (r.valor_recebido for r in caso.db.query(Recebimento).all()), Decimal(0)
    ) == Decimal("119.90")
    evento = caso.db.query(AuditLog).filter(AuditLog.action == ACAO_EXCESSO).one()
    assert evento.tenant_id == caso.tenant and evento.user_id == 1
    dados = json.loads(evento.new_value)
    assert dados["contexto"] == desafio["contexto_pagamento_excedente"]
    assert dados["excedente"] == 10
    assert dados["destinacao"] == "recebimento_excedente_sem_destinacao_automatica"
    assert caso.db.query(MovimentacaoCaixa).count() == 0


def test_dinheiro_entregue_maior_gera_troco_sem_auditoria_excecao(caso):
    resultado = executar(
        caso,
        [
            {
                "forma_pagamento": "Dinheiro",
                "forma_pagamento_id": 2,
                "valor": 109.90,
                "valor_recebido": 119.90,
            }
        ],
    )
    pagamento = caso.db.query(VendaPagamento).one()
    assert pagamento.valor == Decimal("109.90")
    assert pagamento.valor_recebido == Decimal("119.90")
    assert pagamento.troco == 10
    assert Decimal(str(caso.db.query(MovimentacaoCaixa).one().valor)) == Decimal(
        "109.90"
    )
    assert resultado["venda"]["total_recebido"] == 109.90
    assert resultado["venda"]["excedente_recebido"] == 0
    assert caso.db.query(AuditLog).filter(AuditLog.action == ACAO_EXCESSO).count() == 0


def test_misto_dinheiro_e_pix_nao_inventa_troco_do_excedente_eletronico(caso):
    pagamentos = [
        {"forma_pagamento": "Dinheiro", "forma_pagamento_id": 2, "valor": 30},
        pix(89.90),
    ]
    desafio = desafiar(caso, pagamentos)
    executar(
        caso,
        pagamentos,
        motivo="Recebimento Pix maior confirmado no banco",
        contexto=desafio["contexto_pagamento_excedente"],
    )
    assert caso.db.query(MovimentacaoCaixa).one().valor == 30
    assert all(p.troco == 0 for p in caso.db.query(VendaPagamento).all())
    assert sum(
        (p.valor for p in caso.db.query(VendaPagamento).all()), Decimal(0)
    ) == Decimal("119.90")


def test_segunda_requisicao_com_contexto_antigo_nao_autoriza_outros_valores(caso):
    contexto = desafiar(caso, [pix(119.90)])["contexto_pagamento_excedente"]
    executar(caso, [pix(20)])
    with pytest.raises(HTTPException) as erro:
        executar(
            caso,
            [pix(119.90)],
            motivo="Cliente autorizou conferir aquele excedente",
            contexto=contexto,
        )
    assert erro.value.status_code == 409
    assert erro.value.detail["code"] == "PAGAMENTO_EXCEDENTE_DESATUALIZADO"
    assert erro.value.detail["contexto_pagamento_excedente"]["total_ja_pago"] == 20
    assert caso.db.query(VendaPagamento).count() == 1
    assert caso.db.query(VendaPagamento).one().valor == 20


@pytest.mark.parametrize("campo,valor", [("troco", 10), ("valor_recebido", 119.90)])
def test_pix_nao_aceita_campos_de_troco_mesmo_sem_excesso_aplicado(caso, campo, valor):
    with pytest.raises(HTTPException) as erro:
        executar(caso, [pix(109.90) | {campo: valor}])
    assert erro.value.status_code == 400
    assert "Somente dinheiro" in erro.value.detail
    assert caso.db.query(VendaPagamento).count() == 0


def test_nome_dinheiro_nao_burla_tipo_pix_do_cadastro(caso):
    with pytest.raises(HTTPException) as erro:
        executar(
            caso,
            [
                {
                    "forma_pagamento": "Dinheiro",
                    "forma_pagamento_id": 1,
                    "valor": 109.90,
                    "valor_recebido": 119.90,
                }
            ],
        )
    assert erro.value.status_code == 400
    assert "cadastro" in erro.value.detail
    assert caso.db.query(VendaPagamento).count() == 0


def test_aliases_legados_sem_id_mantem_mesma_natureza_na_validacao_e_execucao(caso):
    pagamentos = [
        {"forma_pagamento": "  Dinheiro  ", "valor": 10},
        {"forma_pagamento": "Credito_cliente", "valor": 10},
        {"forma_pagamento": "Cashback (campanha)", "valor": 10},
    ]
    preparar_formas_pagamentos_finalizacao(caso.db, caso.tenant, pagamentos)
    assert [p["forma_pagamento"] for p in pagamentos] == [
        "Dinheiro",
        "Crédito Cliente",
        "Cashback",
    ]
    falso_beneficio = pix(10) | {"forma_pagamento": "Crédito Cliente"}
    preparar_formas_pagamentos_finalizacao(caso.db, caso.tenant, [falso_beneficio])
    assert falso_beneficio["forma_pagamento"] == "Pix"


def test_credito_legitimo_mais_pix_excedente_exige_autorizacao_somente_do_monetario():
    pagamentos = [
        {"forma_pagamento": "Crédito Cliente", "valor": 10},
        {"forma_pagamento": "Pix", "valor": 100},
    ]
    resultado = _calcular_pagamentos_finalizacao(
        total_venda=100,
        pagamentos_existentes=[],
        pagamentos_novos=pagamentos,
        justificativa_pagamento_excedente="Cliente transferiu antes da aplicação do crédito",
        contexto_pagamento_excedente={
            "total_venda": 100,
            "total_ja_pago": 0,
            "total_novos_pagamentos": 110,
            "crediario_pendente": 0,
        },
    )
    assert resultado["excesso_pagamento"]["excedente"] == 10
    assert pagamentos[0]["valor"] == 10 and pagamentos[0]["troco"] == 0
    assert pagamentos[1]["valor"] == 100 and pagamentos[1]["troco"] == 0


@pytest.mark.parametrize(
    "forma", ["Dinheiro", "Cashback", "Crédito Cliente", "Crediário"]
)
def test_justificativa_nao_autoriza_excesso_da_forma_fixa(forma):
    with pytest.raises(HTTPException) as erro:
        _calcular_pagamentos_finalizacao(
            total_venda=109.90,
            pagamentos_existentes=[],
            pagamentos_novos=[{"forma_pagamento": forma, "valor": 119.90}],
            justificativa_pagamento_excedente="Tentativa não pode estourar o próprio saldo",
            contexto_pagamento_excedente={
                "total_venda": 109.90,
                "total_ja_pago": 0,
                "total_novos_pagamentos": 119.90,
                "crediario_pendente": 0,
            },
        )
    assert erro.value.status_code == 400


def test_motivo_curto_e_contexto_de_outro_saldo_nao_sao_aceitos():
    with pytest.raises(ValidationError):
        FinalizarVendaRequest(
            pagamentos=[], justificativa_pagamento_excedente="    curto    "
        )
    with pytest.raises(HTTPException) as erro:
        validar_excesso_pagamento(
            total_venda=100,
            total_ja_pago=0,
            total_novos_pagamentos=110,
            crediario_pendente=0,
            justificativa="Motivo para uma fotografia antiga",
            contexto={
                "total_venda": 99,
                "total_ja_pago": 0,
                "total_novos_pagamentos": 110,
                "crediario_pendente": 0,
            },
        )
    assert erro.value.detail["code"] == "PAGAMENTO_EXCEDENTE_DESATUALIZADO"


def test_refinalizar_excesso_pede_motivo_sem_auditoria_e_reutiliza_fotografia_justificada(
    caso,
):
    executar(caso, [pix(109.90)])
    caso.venda.status = "aberta"
    caso.venda.total = Decimal("99.90")
    caso.db.commit()
    contexto = desafiar(caso, [])["contexto_pagamento_excedente"]
    executar(
        caso,
        [],
        motivo="Desconto concedido depois do recebimento bancário",
        contexto=contexto,
    )
    assert caso.db.query(VendaPagamento).one().valor == Decimal("109.90")
    caso.venda.status = "aberta"
    caso.db.commit()
    executar(caso, [])
    assert caso.db.query(AuditLog).filter(AuditLog.action == ACAO_EXCESSO).count() == 1


def test_falha_no_processamento_reverte_tambem_a_justificativa(caso, monkeypatch):
    contexto = desafiar(caso, [pix(119.90)])["contexto_pagamento_excedente"]

    def falhar(**_):
        raise HTTPException(400, "Falha operacional simulada")

    monkeypatch.setattr(finalizacao, "processar_pagamentos_finalizacao", falhar)
    with pytest.raises(HTTPException, match="Falha operacional"):
        executar(
            caso,
            [pix(119.90)],
            motivo="Cliente transferiu o excedente conscientemente",
            contexto=contexto,
        )
    assert caso.db.query(AuditLog).filter(AuditLog.action == ACAO_EXCESSO).count() == 0
    assert caso.db.query(VendaPagamento).count() == 0
    assert caso.db.query(Recebimento).count() == 0
    assert caso.venda.status == "aberta"


def test_contexto_rele_pagamento_que_ja_estava_na_identity_map(caso):
    executar(caso, [pix(20)])
    pagamento_em_cache = caso.db.query(VendaPagamento).one()
    caso.db.execute(
        VendaPagamento.__table__.update()
        .where(VendaPagamento.id == pagamento_em_cache.id)
        .values(valor=25)
    )
    caso.db.commit()
    assert pagamento_em_cache.valor == 20
    desafio = desafiar(caso, [pix(100)])
    assert desafio["contexto_pagamento_excedente"]["total_ja_pago"] == 25
    assert pagamento_em_cache.valor == 25


def test_duas_requisicoes_postgres_reconferem_o_contexto_apos_lock(caso, monkeypatch):
    if caso.db.bind.dialect.name != "postgresql":
        pytest.skip("Lock concorrente exige PostgreSQL DEV local")
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from threading import Event
    import time
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from app.tenancy.context import tenant_context
    from app.vendas_models import Venda

    entrou, liberar = Event(), Event()
    segundo_pid = Queue()
    calcular = finalizacao._calcular_pagamentos_finalizacao

    def com_pausa(**kwargs):
        if not entrou.is_set():
            entrou.set()
            assert liberar.wait(8)
        return calcular(**kwargs)

    monkeypatch.setattr(finalizacao, "_calcular_pagamentos_finalizacao", com_pausa)
    contexto = {
        "total_venda": 109.90,
        "total_ja_pago": 0,
        "total_novos_pagamentos": 70,
        "crediario_pendente": 0,
    }

    def requisicao(segundo=False):
        with (
            tenant_context(caso.tenant),
            Session(caso.db.bind, expire_on_commit=False) as db,
        ):
            if segundo:
                assert db.get(Venda, caso.venda.id).status == "aberta"
                segundo_pid.put(db.execute(text("SELECT pg_backend_pid()")).scalar())
            try:
                return executar(
                    caso,
                    [pix(70)],
                    motivo="Autorização inicial sujeita aos valores conferidos",
                    contexto=contexto,
                    db_session=db,
                )
            except HTTPException as erro:
                return erro

    with ThreadPoolExecutor(max_workers=2) as pool:
        primeira = pool.submit(requisicao)
        assert entrou.wait(4)
        segunda = pool.submit(requisicao, True)
        try:
            pid = segundo_pid.get(timeout=4)
            with caso.db.bind.connect() as conn:
                bloqueada = False
                for _ in range(60):
                    bloqueada = conn.execute(
                        text(
                            "SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=:pid"
                        ),
                        {"pid": pid},
                    ).scalar()
                    if bloqueada:
                        break
                    conn.commit()
                    time.sleep(0.025)
                assert bloqueada, (
                    "A segunda requisição deve aguardar o lock da primeira"
                )
        finally:
            liberar.set()
        assert primeira.result(timeout=8)["venda"]["status"] == "baixa_parcial"
        erro = segunda.result(timeout=8)
        assert isinstance(erro, HTTPException)
        assert erro.status_code == 409
        assert erro.detail["code"] == "PAGAMENTO_EXCEDENTE_DESATUALIZADO"
        assert erro.detail["contexto_pagamento_excedente"]["total_ja_pago"] == 70
    caso.db.expire_all()
    assert caso.db.query(VendaPagamento).count() == 1
    assert caso.db.query(VendaPagamento).one().valor == 70
    assert caso.db.query(AuditLog).filter(AuditLog.action == ACAO_EXCESSO).count() == 0
