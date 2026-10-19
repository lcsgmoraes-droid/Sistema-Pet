"""Restituição de pagamentos de benefício na transação da devolução.

O chamador trava a venda. A carteira usa o mesmo lock do cliente que resgates,
expiração e crédito; este módulo nunca faz commit.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import unicodedata

from fastapi import HTTPException

from app.campaigns.cashback_wallet import get_cashback_wallet, lock_cashback_customer
from app.campaigns.cashback_sale_reversal import _revoked_campaign_origins
from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
from app.vendas.status_pagamento import pagamento_valido_para_saldo

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def _erro(
    mensagem, *, codigo="DEVOLUCAO_ORIGEM_INCONSISTENTE", acao="abrir_pagamentos"
):
    raise HTTPException(
        status_code=409,
        detail={"codigo": codigo, "mensagem": mensagem, "acao": acao},
    )


def _moeda(valor):
    try:
        numero = Decimal(str(valor or 0))
        if not numero.is_finite() or numero < 0:
            raise ValueError()
        return numero.quantize(CENT)
    except (InvalidOperation, TypeError, ValueError):
        _erro(
            "O valor do pagamento original não está comprovado. Confira os pagamentos da venda."
        )


def forma_normalizada(pagamento):
    nome = str(getattr(pagamento, "forma_pagamento", "") or "")
    nome = "".join(
        c
        for c in unicodedata.normalize("NFKD", nome.lower())
        if not unicodedata.combining(c)
    )
    return nome.strip().replace(" ", "_").replace("-", "_")


def _valor_pagamento(pagamento):
    valor = getattr(pagamento, "valor", None)
    if getattr(pagamento, "baixa_lote_id", None) is not None:
        try:
            numero = Decimal(str(valor or 0))
        except (InvalidOperation, TypeError, ValueError):
            return _moeda(valor)
        if numero.is_finite() and numero < 0:
            # A contrapartida faz parte do histórico: reduz o total restituível
            # sem invalidar uma nova baixa feita depois da correção.
            return -_moeda(-numero)
    return _moeda(valor)


def pagamentos_validos(venda, tenant_id):
    return [
        p
        for p in (getattr(venda, "pagamentos", []) or [])
        if str(getattr(p, "tenant_id", tenant_id)) == str(tenant_id)
        and pagamento_valido_para_saldo(p)
        and (getattr(p, "valor", None) is None or _valor_pagamento(p) != 0)
    ]


def validar_opcao_restituicao(venda, tenant_id, devolver_na_origem=False):
    beneficios = any(
        forma_normalizada(p) in {"cashback", "credito_cliente"}
        for p in pagamentos_validos(venda, tenant_id)
    )
    if beneficios and devolver_na_origem is not True:
        _erro(
            "Esta venda usou cashback ou Crédito Cliente. Devolva essa parte ao saldo original para continuar; o restante pode ser devolvido em dinheiro ou crédito.",
            codigo="DEVOLUCAO_PAGAMENTO_BENEFICIO",
            acao="devolver_na_origem",
        )
    return beneficios


def ratear_restituicao_acumulada(valor, cashback, credito, restante):
    """Rateio cumulativo e monotônico: centavos restantes vão à próxima forma.

    A hierarquia evita que uma parcela de um centavo vire dinheiro numa venda
    só com benefícios, e que o arredondamento diminua uma forma já restituída.
    """
    total = cashback + credito + restante
    if valor < 0 or valor > total or total <= 0:
        _erro("O saldo da devolução não corresponde aos pagamentos originais.")
    cota_cashback = (valor * cashback / total).quantize(CENT, rounding=ROUND_DOWN)
    saldo = valor - cota_cashback
    sem_cashback = credito + restante
    cota_credito = (
        (saldo * credito / sem_cashback).quantize(CENT, rounding=ROUND_DOWN)
        if sem_cashback
        else ZERO
    )
    return {
        "cashback": cota_cashback,
        "credito_cliente": cota_credito,
        "valor_restante": saldo - cota_credito,
    }


@dataclass
class RestituicaoDevolucao:
    cashback: Decimal = ZERO
    credito_cliente: Decimal = ZERO
    valor_restante: Decimal = ZERO
    cashback_expirado: Decimal = ZERO
    lotes: list = field(default_factory=list)

    def resposta(self):
        return {
            campo: float(getattr(self, campo))
            for campo in (
                "cashback",
                "credito_cliente",
                "valor_restante",
                "cashback_expirado",
            )
        }


def _planejar_cashback(
    db, *, tenant_id, venda, valor, original, ja_devolvido, bloquear
):
    if bloquear:
        try:
            lock_cashback_customer(
                db, tenant_id=tenant_id, customer_id=venda.cliente_id
            )
        except LookupError as erro:
            raise HTTPException(
                status_code=404, detail="Cliente não encontrado"
            ) from erro
    carteira = get_cashback_wallet(
        db, tenant_id=tenant_id, customer_id=venda.cliente_id
    )
    transacoes = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == venda.cliente_id,
        )
        .order_by(CashbackTransaction.id)
        .all()
    )
    creditos = {tx.id: tx for tx in transacoes if Decimal(str(tx.amount or 0)) > 0}
    resgates = [
        tx
        for tx in transacoes
        if tx.source_type == CashbackSourceTypeEnum.redemption
        and tx.source_id == venda.id
        and Decimal(str(tx.amount or 0)) < 0
    ]
    resgates_ids = {tx.id for tx in resgates}
    compensacoes = [
        tx
        for tx in transacoes
        if tx.source_type == CashbackSourceTypeEnum.reversal
        and tx.source_id in resgates_ids
        and Decimal(str(tx.amount or 0)) >= 0
    ]
    compensado = sum((Decimal(str(tx.amount or 0)) for tx in compensacoes), ZERO)
    fechados = {
        tx.source_id for tx in compensacoes if getattr(tx, "tx_type", None) == "closed"
    }
    saldo_resgatado = (
        sum(
            (-Decimal(str(tx.amount)) for tx in resgates if tx.id not in fechados), ZERO
        )
        - compensado
    )
    if saldo_resgatado != original - ja_devolvido:
        _erro(
            "O resgate original de cashback não corresponde aos pagamentos. Confira a carteira e os pagamentos da venda.",
            acao="abrir_beneficios",
        )
    origens = {
        getattr(c, "origin_credit_id", None) or c.id: creditos.get(
            getattr(c, "origin_credit_id", None) or c.id, c
        )
        for c in creditos.values()
    }
    revogadas = _revoked_campaign_origins(db, tenant_id=tenant_id, origins=origens)
    planos = []
    a_restituir = valor
    expirado = ZERO
    agora = datetime.now(timezone.utc)
    for resgate in resgates:
        if resgate.id in fechados:
            continue
        restituido_por_origem = {}
        for tx in compensacoes:
            if tx.source_id == resgate.id and Decimal(str(tx.amount or 0)) > 0:
                origem = getattr(tx, "origin_credit_id", None)
                if origem is None:
                    _erro(
                        "O estorno anterior de cashback não registra o lote original. Confira a carteira do cliente.",
                        acao="abrir_beneficios",
                    )
                restituido_por_origem[origem] = restituido_por_origem.get(
                    origem, ZERO
                ) + Decimal(str(tx.amount))
        alocacoes = carteira.allocations_by_debit.get(resgate.id, {})
        if sum(alocacoes.values(), ZERO) != -Decimal(str(resgate.amount)):
            _erro(
                "Os lotes usados no pagamento com cashback não estão comprovados. Confira a carteira do cliente.",
                acao="abrir_beneficios",
            )
        for credito_id, consumido in alocacoes.items():
            credito = creditos.get(credito_id)
            if credito is None:
                _erro(
                    "Lote original de cashback indisponível. Confira a carteira do cliente.",
                    acao="abrir_beneficios",
                )
            origem = getattr(credito, "origin_credit_id", None) or credito.id
            abatido = min(consumido, restituido_por_origem.get(origem, ZERO))
            restituido_por_origem[origem] = (
                restituido_por_origem.get(origem, ZERO) - abatido
            )
            parcela = min(consumido - abatido, a_restituir)
            if parcela <= 0:
                continue
            if origem not in creditos:
                _erro(
                    "O lote restaurado de cashback não tem origem comprovada. Confira a carteira do cliente.",
                    acao="abrir_beneficios",
                )
            if origem in revogadas:
                _erro(
                    "O cashback usado nesta venda veio de um benefício revogado. Confira a carteira do cliente antes de continuar.",
                    acao="abrir_beneficios",
                )
            validade = getattr(credito, "expires_at", None)
            validade_utc = (
                validade.replace(tzinfo=timezone.utc)
                if validade and validade.tzinfo is None
                else validade
            )
            if validade_utc and validade_utc <= agora:
                expirado += parcela
            planos.append(
                {
                    "resgate_id": resgate.id,
                    "origem_id": origem,
                    "valor": parcela,
                    "expires_at": validade,
                }
            )
            a_restituir -= parcela
        if any(saldo > 0 for saldo in restituido_por_origem.values()):
            _erro(
                "O cashback já estornado excede os lotes originais. Confira a carteira do cliente.",
                acao="abrir_beneficios",
            )
    if a_restituir:
        _erro(
            "Não há cashback original suficiente para esta restituição.",
            acao="abrir_beneficios",
        )
    return planos, expirado


def cotar_restituicao(
    db,
    *,
    tenant_id,
    venda,
    cotacao,
    eventos_anteriores,
    devolver_na_origem=False,
    bloquear=False,
):
    if not validar_opcao_restituicao(venda, tenant_id, devolver_na_origem):
        return RestituicaoDevolucao(valor_restante=cotacao.valor_total)
    if not venda.cliente_id:
        _erro(
            "Vincule o cliente original à venda para restituir cashback ou crédito.",
            acao="vincular_cliente",
        )
    totais = {"cashback": ZERO, "credito_cliente": ZERO, "valor_restante": ZERO}
    for pagamento in pagamentos_validos(venda, tenant_id):
        forma = forma_normalizada(pagamento)
        chave = forma if forma in {"cashback", "credito_cliente"} else "valor_restante"
        totais[chave] += _valor_pagamento(pagamento)
    if sum(totais.values(), ZERO) != _moeda(venda.total):
        _erro(
            "Os pagamentos não correspondem ao total da venda. Confira os pagamentos antes de devolver."
        )
    anteriores = {campo: ZERO for campo in totais}
    for evento in eventos_anteriores:
        restituicao = (getattr(evento, "resposta", None) or {}).get("restituicao")
        if not isinstance(restituicao, dict) or any(
            campo not in restituicao for campo in totais
        ):
            _erro(
                "A devolução anterior não registra a restituição dos pagamentos. Confira o histórico da venda."
            )
        valores = {campo: _moeda(restituicao[campo]) for campo in totais}
        if sum(valores.values(), ZERO) != _moeda(evento.valor_devolvido):
            _erro(
                "Os valores da restituição anterior não correspondem à devolução. Confira o histórico da venda."
            )
        for campo in totais:
            anteriores[campo] += valores[campo]
    acumulados = ratear_restituicao_acumulada(
        cotacao.valor_acumulado,
        totais["cashback"],
        totais["credito_cliente"],
        totais["valor_restante"],
    )
    atuais = {campo: acumulados[campo] - anteriores[campo] for campo in totais}
    if (
        any(valor < 0 for valor in atuais.values())
        or sum(atuais.values(), ZERO) != cotacao.valor_total
    ):
        _erro(
            "O rateio anterior da devolução não corresponde aos pagamentos. Confira o histórico da venda."
        )
    resultado = RestituicaoDevolucao(**atuais)
    if totais["cashback"]:
        resultado.lotes, resultado.cashback_expirado = _planejar_cashback(
            db,
            tenant_id=tenant_id,
            venda=venda,
            valor=resultado.cashback,
            original=totais["cashback"],
            ja_devolvido=anteriores["cashback"],
            bloquear=bloquear,
        )
    return resultado


def registrar_restituicao_cashback(
    db, *, tenant_id, venda, evento_devolucao, restituicao
):
    for lote in restituicao.lotes:
        db.add(
            CashbackTransaction(
                tenant_id=tenant_id,
                customer_id=venda.cliente_id,
                amount=lote["valor"],
                source_type=CashbackSourceTypeEnum.reversal,
                source_id=lote["resgate_id"],
                origin_credit_id=lote["origem_id"],
                expires_at=lote["expires_at"],
                tx_type="credit",
                description=f"Restituição do resgate da venda #{venda.id} pela devolução #{evento_devolucao.id}",
            )
        )
    db.flush()


def validar_restituicao_prevista(restituicao, prevista, *, exigir=False):
    """A divisão e a validade confirmadas também fazem parte da prévia."""
    if prevista is None and not exigir:
        return
    campos = ("cashback", "credito_cliente", "valor_restante", "cashback_expirado")
    if not isinstance(prevista, dict) or any(campo not in prevista for campo in campos):
        _erro(
            "Confira a prévia da restituição antes de confirmar a devolução.",
            codigo="DEVOLUCAO_PREVIA_ALTERADA",
            acao="atualizar_previa",
        )
    for campo in campos:
        try:
            valor = Decimal(str(prevista[campo]))
            valido = (
                valor.is_finite()
                and valor >= 0
                and valor.quantize(CENT) == getattr(restituicao, campo)
            )
        except (InvalidOperation, TypeError, ValueError):
            valido = False
        if not valido:
            _erro(
                "A divisão da devolução mudou. Confira a nova prévia antes de confirmar.",
                codigo="DEVOLUCAO_PREVIA_ALTERADA",
                acao="atualizar_previa",
            )
