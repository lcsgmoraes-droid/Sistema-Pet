"""Desfaz um pagamento e seus espelhos na mesma transacao da venda.

Referencias novas usam campos existentes. Registros antigos so sao associados
quando valor, forma e data produzem uma unica correspondencia; divergencias
historicas exigem conferencia, nunca a exclusao de todos os recebiveis da venda.
"""

import json
import unicodedata
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.audit_log import log_action
from app.caixa.service import CaixaService
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.financeiro_models import (
    ContaPagar,
    ContaReceber,
    LancamentoManual,
    Recebimento,
)
from app.models import AuditLog, Cliente, CreditoLog
from app.services.venda_rentabilidade_snapshot_service import (
    invalidate_venda_rentabilidade_snapshot,
)
from app.utils.pagamento_vinculos import pagamento_da_observacao, referencia_pagamento
from app.vendas_models import Venda, VendaPagamento


def _valor(valor):
    return Decimal(str(valor or 0)).quantize(Decimal("0.01"))


def _forma(valor):
    texto = "".join(
        c
        for c in unicodedata.normalize("NFKD", str(valor or "").lower())
        if not unicodedata.combining(c)
    )
    return texto.replace(" ", "_").replace("-", "_")


def _data(valor):
    return valor.date() if hasattr(valor, "date") else valor


def _conferir(pagamento, venda, motivo):
    raise HTTPException(
        409,
        (
            f"Nao foi possivel excluir o pagamento #{pagamento.id} da venda "
            f"{venda.numero_venda}: {motivo}. Confira os recebimentos e o extrato "
            "do caixa antes de corrigir esse registro. Nenhum valor foi alterado."
        ),
    )


def _exclusao_anterior(db, tenant_id, pagamento_id):
    auditoria = (
        db.query(AuditLog)
        .filter_by(
            tenant_id=tenant_id,
            action="delete",
            entity_type="venda_pagamentos",
            entity_id=pagamento_id,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    if auditoria and auditoria.new_value:
        dados = json.loads(auditoria.new_value)
        if dados.get("pagamento_excluido") is True:
            return dados["resultado"]
    raise HTTPException(404, "Pagamento nao encontrado")


def _conferir_taxas(db, venda, pagamento, tenant_id, forma):
    from sqlalchemy import or_

    taxa_prevista = _valor(pagamento.valor_taxa_prevista) > 0
    taxa_historica = None
    if (
        not CaixaService.eh_forma_dinheiro(pagamento.forma_pagamento)
        and forma != "credito_cliente"
    ):
        referencia = f"Taxa de pagamento ref. venda {venda.numero_venda}"
        taxa_historica = (
            db.query(ContaPagar.id)
            .filter(
                ContaPagar.tenant_id == tenant_id,
                or_(
                    ContaPagar.status.is_(None),
                    ContaPagar.status.notin_(("cancelado", "cancelada")),
                ),
                or_(
                    ContaPagar.observacoes == referencia,
                    ContaPagar.observacoes.startswith(
                        referencia + " - ", autoescape=True
                    ),
                ),
            )
            .first()
        )
    if taxa_prevista or taxa_historica:
        _conferir(
            pagamento,
            venda,
            "ha taxa de pagamento prevista ou registrada; confira e estorne a taxa no financeiro",
        )


def _movimento_do_pagamento(db, venda, pagamento, pagamentos, tenant_id):
    if not CaixaService.eh_forma_dinheiro(pagamento.forma_pagamento):
        return None
    movimentos = (
        db.query(MovimentacaoCaixa)
        .filter_by(tenant_id=tenant_id, venda_id=venda.id, tipo="venda")
        .order_by(MovimentacaoCaixa.id)
        .all()
    )
    dinheiro = [
        p for p in pagamentos if CaixaService.eh_forma_dinheiro(p.forma_pagamento)
    ]
    if sum((_valor(m.valor) for m in movimentos), Decimal("0")) != sum(
        (_valor(p.valor) for p in dinheiro), Decimal("0")
    ):
        _conferir(
            pagamento, venda, "as entradas em dinheiro divergem dos pagamentos atuais"
        )
    ligados = [
        m for m in movimentos if m.documento == referencia_pagamento(pagamento.id)
    ]
    if len(ligados) == 1 and _valor(ligados[0].valor) == _valor(pagamento.valor):
        return ligados[0]
    if ligados:
        _conferir(pagamento, venda, "ha mais de uma entrada vinculada ao pagamento")
    # O valor isolado nao basta quando houve recebimentos repetidos ou parciais.
    candidatos = [
        m
        for m in movimentos
        if not m.documento
        and _valor(m.valor) == _valor(pagamento.valor)
        and _data(m.data_movimento) == _data(pagamento.data_pagamento)
    ]
    iguais = [
        p
        for p in dinheiro
        if _valor(p.valor) == _valor(pagamento.valor)
        and _data(p.data_pagamento) == _data(pagamento.data_pagamento)
    ]
    if len(candidatos) != 1 or len(iguais) != 1:
        _conferir(
            pagamento,
            venda,
            "a entrada antiga nao tem um vinculo unico com o pagamento",
        )
    return candidatos[0]


def _efeitos_recebiveis(db, venda, pagamento, pagamentos, tenant_id):
    contas = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.venda_id == venda.id,
            ContaReceber.status.notin_(("cancelado", "cancelada")),
        )
        .populate_existing()
        .with_for_update()
        .all()
    )
    recebimentos = (
        db.query(Recebimento)
        .filter(
            Recebimento.tenant_id == tenant_id,
            Recebimento.conta_receber_id.in_([c.id for c in contas]),
        )
        .populate_existing()
        .with_for_update()
        .all()
    )
    proprias = [
        c for c in contas if pagamento_da_observacao(c.observacoes) == pagamento.id
    ]
    baixas = [
        r
        for r in recebimentos
        if pagamento_da_observacao(r.observacoes) == pagamento.id
    ]
    if not proprias and not baixas:
        # Legado: uma conta/um conjunto de parcelas de mesmo valor, data e forma.
        iguais = [
            p
            for p in pagamentos
            if p.forma_pagamento_id == pagamento.forma_pagamento_id
            and _valor(p.valor) == _valor(pagamento.valor)
            and _data(p.data_pagamento) == _data(pagamento.data_pagamento)
        ]
        candidatas = [
            c
            for c in contas
            if not pagamento_da_observacao(c.observacoes)
            and c.forma_pagamento_id == pagamento.forma_pagamento_id
            and c.data_emissao == _data(pagamento.data_pagamento)
        ]
        simples = [
            c
            for c in candidatas
            if _valor(c.valor_original) == _valor(pagamento.valor)
            and (c.total_parcelas or 1) == 1
        ]
        parcelas = [
            c
            for c in candidatas
            if (c.total_parcelas or 1) > 1
            and c.total_parcelas == pagamento.numero_parcelas
        ]
        if len(iguais) == 1 and len(simples) == 1:
            proprias = simples
        elif (
            len(iguais) == 1
            and len(parcelas) == (pagamento.numero_parcelas or 1)
            and {c.numero_parcela for c in parcelas}
            == set(range(1, (pagamento.numero_parcelas or 1) + 1))
            and sum((_valor(c.valor_original) for c in parcelas), Decimal("0"))
            == _valor(pagamento.valor)
        ):
            proprias = parcelas
        if proprias:
            ids = {c.id for c in proprias}
            baixas = [
                r
                for r in recebimentos
                if r.conta_receber_id in ids
                and pagamento_da_observacao(r.observacoes) is None
                and r.data_recebimento == _data(pagamento.data_pagamento)
                and r.forma_pagamento_id == pagamento.forma_pagamento_id
            ]
        else:
            # Baixa parcial em conta preexistente, sem criar conta do pagamento.
            baixas = [
                r
                for r in recebimentos
                if pagamento_da_observacao(r.observacoes) is None
                and r.data_recebimento == _data(pagamento.data_pagamento)
                and r.forma_pagamento_id == pagamento.forma_pagamento_id
            ]
            if len(iguais) != 1 or sum(
                (_valor(r.valor_recebido) for r in baixas), Decimal("0")
            ) != _valor(pagamento.valor):
                _conferir(
                    pagamento,
                    venda,
                    "os recebiveis antigos nao identificam esse pagamento com seguranca",
                )
    ids_proprias = {c.id for c in proprias}
    ids_baixas = {r.id for r in baixas}
    afetadas = [
        c
        for c in contas
        if c.id in ids_proprias or c.id in {r.conta_receber_id for r in baixas}
    ]
    if not afetadas:
        _conferir(pagamento, venda, "nao foram encontrados os recebiveis do pagamento")
    for conta in afetadas:
        if (
            conta.conciliado
            or conta.conciliacao_recebimento_id
            or conta.conciliacao_lote_id
            or conta.validacao_id
            or conta.data_liquidacao
            or conta.status_conciliacao not in (None, "prevista")
        ):
            _conferir(
                pagamento, venda, "o recebivel ja participou de conciliacao financeira"
            )
        registros = [r for r in recebimentos if r.conta_receber_id == conta.id]
        if sum((_valor(r.valor_recebido) for r in registros), Decimal("0")) != _valor(
            conta.valor_recebido
        ):
            _conferir(
                pagamento, venda, "o saldo da conta difere de suas baixas registradas"
            )
        if conta.id in ids_proprias and any(r.id not in ids_baixas for r in registros):
            _conferir(pagamento, venda, "a conta desse pagamento recebeu outras baixas")
    contabilizado = sum((_valor(c.valor_original) for c in proprias), Decimal("0"))
    contabilizado += sum(
        (
            _valor(r.valor_recebido)
            for r in baixas
            if r.conta_receber_id not in ids_proprias
        ),
        Decimal("0"),
    )
    if contabilizado != _valor(pagamento.valor):
        _conferir(
            pagamento,
            venda,
            "os valores vinculados aos recebiveis nao fecham com o pagamento",
        )
    return proprias, baixas, afetadas


def _sincronizar_espelhos(db, venda, pagamentos, tenant_id, user_id):
    documentos = [
        f"VENDA-{venda.id}",
        f"VENDA-{venda.id}-SALDO",
        f"VENDA-{venda.id}-REALIZADO",
    ]
    antigos = (
        db.query(LancamentoManual)
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.documento.in_(documentos),
            LancamentoManual.tipo == "entrada",
            LancamentoManual.status.in_(("realizado", "previsto")),
        )
        .with_for_update()
        .order_by(LancamentoManual.id)
        .all()
    )
    modelo = next(iter(antigos), None)
    data_prevista = next(
        (
            lancamento.data_lancamento
            for lancamento in antigos
            if lancamento.status == "previsto"
        ),
        date.today() + timedelta(days=30),
    )
    for antigo in antigos:
        antigo.status = "cancelado"
    comum = dict(
        tenant_id=tenant_id,
        user_id=user_id,
        tipo="entrada",
        categoria_id=modelo.categoria_id if modelo else None,
        fornecedor_cliente=modelo.fornecedor_cliente if modelo else None,
        gerado_automaticamente=True,
    )
    cumulativo = Decimal("0")
    # Os espelhos parciais sao cumulativos; o leitor converte-os em incrementos
    # e desconta credito/cashback ainda vinculados a esses pagamentos.
    for pagamento in sorted(
        pagamentos, key=lambda p: (_data(p.data_pagamento) or date.min, p.id)
    ):
        cumulativo += _valor(pagamento.valor)
        db.add(
            LancamentoManual(
                **comum,
                valor=cumulativo,
                status="realizado",
                documento=f"VENDA-{venda.id}-REALIZADO",
                descricao=f"Venda {venda.numero_venda} - Recebido (parcial)",
                data_lancamento=_data(pagamento.data_pagamento) or date.today(),
            )
        )
    saldo = max(_valor(venda.total) - cumulativo, Decimal("0"))
    if saldo:
        db.add(
            LancamentoManual(
                **comum,
                valor=saldo,
                status="previsto",
                documento=f"VENDA-{venda.id}",
                descricao=f"Venda {venda.numero_venda} - Saldo restante",
                data_lancamento=data_prevista,
            )
        )


def excluir_pagamento_atomico(*, db, pagamento_id, tenant_id, current_user):
    """Nao comita. A rota confirma auditoria, caixa, credito e baixas juntos."""
    inicial = (
        db.query(VendaPagamento.venda_id, VendaPagamento.caixa_id)
        .filter_by(
            id=pagamento_id,
            tenant_id=tenant_id,
        )
        .first()
    )
    if not inicial:
        return _exclusao_anterior(db, tenant_id, pagamento_id)
    # Mesma ordem de locks do recebimento/fechamento: Caixa -> Venda -> Cliente.
    caixa_ids = {
        c
        for (c,) in db.query(MovimentacaoCaixa.caixa_id)
        .filter_by(venda_id=inicial.venda_id, tenant_id=tenant_id, tipo="venda")
        .all()
    }
    if inicial.caixa_id:
        caixa_ids.add(inicial.caixa_id)
    caixas = (
        db.query(Caixa)
        .filter(Caixa.tenant_id == tenant_id, Caixa.id.in_(caixa_ids))
        .order_by(Caixa.id)
        .populate_existing()
        .with_for_update()
        .all()
    )
    venda = (
        db.query(Venda)
        .filter_by(id=inicial.venda_id, tenant_id=tenant_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if not venda:
        raise HTTPException(404, "Venda nao encontrada")
    pagamentos = (
        db.query(VendaPagamento)
        .filter_by(venda_id=venda.id, tenant_id=tenant_id)
        .populate_existing()
        .order_by(VendaPagamento.id)
        .all()
    )
    pagamento = next((p for p in pagamentos if p.id == pagamento_id), None)
    if not pagamento:
        return _exclusao_anterior(db, tenant_id, pagamento_id)
    if venda.status == "pago_nf":
        raise HTTPException(400, "Cancele a nota fiscal antes de excluir pagamentos.")
    if venda.status != "aberta":
        raise HTTPException(
            400,
            'Reabra a venda pelo botao "Reabrir Venda" antes de excluir pagamentos.',
        )
    caixas_por_id = {caixa.id: caixa for caixa in caixas}
    if inicial.caixa_id and (
        inicial.caixa_id not in caixas_por_id
        or caixas_por_id[inicial.caixa_id].status != "aberto"
    ):
        _conferir(
            pagamento, venda, "o pagamento pertence a um caixa fechado ou indisponivel"
        )
    forma = _forma(pagamento.forma_pagamento)
    _conferir_taxas(db, venda, pagamento, tenant_id, forma)
    if (
        forma == "cashback"
        or pagamento.gateway_payment_id
        or pagamento.gateway_provider
        or pagamento.status_conciliacao == "conciliado"
    ):
        _conferir(
            pagamento,
            venda,
            "esse pagamento exige estorno pela conciliacao ou carteira",
        )
    cliente = None
    if forma == "credito_cliente":
        cliente = (
            db.query(Cliente)
            .filter_by(id=venda.cliente_id, tenant_id=tenant_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not cliente:
            _conferir(pagamento, venda, "o cliente do credito nao esta disponivel")
    movimento = _movimento_do_pagamento(db, venda, pagamento, pagamentos, tenant_id)
    if movimento and (
        movimento.caixa_id not in caixas_por_id
        or caixas_por_id[movimento.caixa_id].status != "aberto"
    ):
        _conferir(
            pagamento, venda, "a entrada pertence a um caixa fechado ou indisponivel"
        )
    proprias, baixas, afetadas = _efeitos_recebiveis(
        db, venda, pagamento, pagamentos, tenant_id
    )
    from app.financeiro_models import MovimentacaoFinanceira
    from app.ia.aba5_models import FluxoCaixa
    from sqlalchemy import or_, and_

    conta_ids = [c.id for c in afetadas]
    bancaria = (
        db.query(MovimentacaoFinanceira.id)
        .filter(
            MovimentacaoFinanceira.tenant_id == tenant_id,
            MovimentacaoFinanceira.status != "cancelado",
            or_(
                and_(
                    MovimentacaoFinanceira.origem_tipo == "venda",
                    MovimentacaoFinanceira.origem_id == venda.id,
                ),
                and_(
                    MovimentacaoFinanceira.origem_tipo == "conta_receber",
                    MovimentacaoFinanceira.origem_id.in_(conta_ids),
                ),
            ),
        )
        .first()
    )
    fluxo = (
        db.query(FluxoCaixa.id)
        .filter(
            FluxoCaixa.tenant_id == tenant_id,
            FluxoCaixa.status != "cancelado",
            or_(
                and_(
                    FluxoCaixa.origem_tipo == "venda", FluxoCaixa.origem_id == venda.id
                ),
                and_(
                    FluxoCaixa.origem_tipo == "conta_receber",
                    FluxoCaixa.origem_id.in_(conta_ids),
                ),
            ),
        )
        .first()
    )
    if bancaria or fluxo:
        _conferir(
            pagamento,
            venda,
            "ha movimentacao financeira vinculada que precisa ser conciliada",
        )
    if cliente:
        anterior = _valor(cliente.credito)
        cliente.credito = anterior + _valor(pagamento.valor)
        db.add(
            CreditoLog(
                tenant_id=tenant_id,
                cliente_id=cliente.id,
                tipo="estorno_venda",
                valor=_valor(pagamento.valor),
                saldo_anterior=anterior,
                saldo_atual=cliente.credito,
                referencia_id=venda.id,
                usuario_nome=current_user.nome or "Usuario",
                motivo=f"Exclusao do pagamento #{pagamento.id} da venda {venda.numero_venda}",
            )
        )
    if movimento:
        db.delete(movimento)
    for recebimento in baixas:
        db.delete(recebimento)
    ids_proprias = {c.id for c in proprias}
    for conta in afetadas:
        excluido = sum(
            (
                _valor(r.valor_recebido)
                for r in baixas
                if r.conta_receber_id == conta.id
            ),
            Decimal("0"),
        )
        conta.valor_recebido = _valor(conta.valor_recebido) - excluido
        conta.data_recebimento = None
        if conta.id in ids_proprias:
            conta.status = "cancelado"
        else:
            conta.status = "parcial" if conta.valor_recebido > 0 else "pendente"
    restantes = [p for p in pagamentos if p.id != pagamento.id]
    _sincronizar_espelhos(db, venda, restantes, tenant_id, current_user.id)
    resultado = {
        "message": "Pagamento excluido com sucesso",
        "venda_id": venda.id,
        "novo_status": "aberta",
        "total_pago": float(sum((_valor(p.valor) for p in restantes), Decimal("0"))),
    }
    resultado["valor_restante"] = max(0, float(venda.total) - resultado["total_pago"])
    log_action(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="delete",
        entity_type="venda_pagamentos",
        entity_id=pagamento.id,
        commit=False,
        old_value={
            "venda_id": venda.id,
            "valor": str(pagamento.valor),
            "forma_pagamento": pagamento.forma_pagamento,
            "movimentacao_caixa_id": movimento.id if movimento else None,
            "contas_canceladas": [c.id for c in proprias],
            "recebimentos_excluidos": [r.id for r in baixas],
        },
        new_value={"pagamento_excluido": True, "resultado": resultado},
        details=f"Excluido pagamento de R$ {pagamento.valor} ({pagamento.forma_pagamento}) da venda #{venda.id}",
    )
    db.delete(pagamento)
    venda.status = "aberta"
    invalidate_venda_rentabilidade_snapshot(venda)
    db.flush()
    return resultado
