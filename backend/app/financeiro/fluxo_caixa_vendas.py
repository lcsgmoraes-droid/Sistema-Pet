"""Entradas de vendas no fluxo de caixa, inclusive baixas com crédito do cliente."""

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import re
import unicodedata

from app.financeiro_models import LancamentoManual
from app.vendas_models import Venda, VendaPagamento
from app.vendas_devolucoes_models import VendaDevolucao


_DOCUMENTO_VENDA = re.compile(r"VENDA-(\d+)(-REALIZADO)?$")
_STATUS_DEVOLVIDO = {
    "finalizada_devolucao",
    "finalizada_devolucao_parcial",
    "devolvida_total",
}


def _id_venda_documento(documento: str | None) -> tuple[int, bool] | None:
    encontrado = _DOCUMENTO_VENDA.fullmatch(str(documento or ""))
    if not encontrado:
        return None
    return int(encontrado.group(1)), bool(encontrado.group(2))


def _forma_normalizada(forma: str | None) -> str:
    texto = "".join(
        letra
        for letra in unicodedata.normalize("NFKD", str(forma or "").lower())
        if not unicodedata.combining(letra)
    )
    return texto.replace(" ", "_").replace("-", "_")


def _eh_pagamento_nao_monetario(forma: str | None) -> bool:
    return _forma_normalizada(forma) in {"credito_cliente", "cashback"}


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    return valor if isinstance(valor, date) else None


def valores_nao_monetarios_por_venda(db, tenant_id, venda_ids) -> dict[int, Decimal]:
    ids = set(venda_ids)
    if not ids:
        return {}
    totais = defaultdict(Decimal)
    for pagamento in (
        db.query(VendaPagamento)
        .filter(VendaPagamento.tenant_id == tenant_id, VendaPagamento.venda_id.in_(ids))
        .all()
    ):
        if _eh_pagamento_nao_monetario(pagamento.forma_pagamento):
            totais[pagamento.venda_id] += Decimal(str(pagamento.valor or 0))
    return dict(totais)


def vendas_devolvidas_com_entrada_integral(db, tenant_id, vendas) -> set[int]:
    """Exige prova de que a entrada integral existia antes da devolução."""
    devolvidas = {
        venda.id: venda
        for venda in vendas
        if str(venda.status or "").lower() in _STATUS_DEVOLVIDO
    }
    if not devolvidas:
        return set()
    origens = {}
    for venda_id, status_original in (
        db.query(VendaDevolucao.venda_id, VendaDevolucao.status_original_venda)
        .filter(
            VendaDevolucao.tenant_id == tenant_id,
            VendaDevolucao.venda_id.in_(devolvidas),
        )
        .order_by(VendaDevolucao.id)
        .all()
    ):
        origens.setdefault(venda_id, str(status_original or "").lower())

    pagamentos = defaultdict(Decimal)
    for venda_id, valor in (
        db.query(VendaPagamento.venda_id, VendaPagamento.valor)
        .filter(
            VendaPagamento.tenant_id == tenant_id,
            VendaPagamento.venda_id.in_(devolvidas),
        )
        .all()
    ):
        pagamentos[venda_id] += Decimal(str(valor or 0))
    entrada_integral = set()
    for venda_id, venda in devolvidas.items():
        status_original = origens.get(venda_id)
        if status_original == "baixa_parcial":
            continue
        if status_original == "finalizada" or pagamentos[venda_id] >= Decimal(
            str(venda.total or 0)
        ):
            entrada_integral.add(venda_id)
    return entrada_integral


def vendas_com_lancamento(db, tenant_id, venda_ids) -> set[int]:
    ids = set(venda_ids)
    if not ids:
        return set()
    documentos = [
        documento
        for venda_id in ids
        for documento in (f"VENDA-{venda_id}", f"VENDA-{venda_id}-REALIZADO")
    ]
    linhas = (
        db.query(LancamentoManual.documento)
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.tipo == "entrada",
            LancamentoManual.documento.in_(documentos),
        )
        .all()
    )
    return {
        identificador[0]
        for (documento,) in linhas
        if (identificador := _id_venda_documento(documento)) is not None
    }


def lancamentos_cashback_sem_saida_caixa(
    db, tenant_id, lancamentos_periodo
) -> set[int]:
    """Suprime só o espelho automático cuja soma coincide com o resgate salvo."""
    documentos = {
        lancamento.documento
        for lancamento in lancamentos_periodo
        if lancamento.tipo == "saida"
        and lancamento.gerado_automaticamente
        and str(lancamento.documento or "").startswith("CASHBACK-")
    }
    if not documentos:
        return set()
    numeros = {documento[len("CASHBACK-") :] for documento in documentos}
    vendas = (
        db.query(Venda.id, Venda.numero_venda)
        .filter(Venda.tenant_id == tenant_id, Venda.numero_venda.in_(numeros))
        .all()
    )
    numeros_por_venda = dict(vendas)
    if not numeros_por_venda:
        return set()
    valores_resgatados = defaultdict(Decimal)
    for pagamento in (
        db.query(VendaPagamento)
        .filter(
            VendaPagamento.tenant_id == tenant_id,
            VendaPagamento.venda_id.in_(numeros_por_venda),
        )
        .all()
    ):
        if _forma_normalizada(pagamento.forma_pagamento) == "cashback":
            valores_resgatados[numeros_por_venda[pagamento.venda_id]] += Decimal(
                str(pagamento.valor or 0)
            )
    espelhos = (
        db.query(LancamentoManual)
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.tipo == "saida",
            LancamentoManual.status == "realizado",
            LancamentoManual.gerado_automaticamente.is_(True),
            LancamentoManual.documento.in_(documentos),
        )
        .all()
    )
    por_documento = defaultdict(list)
    for espelho in espelhos:
        por_documento[espelho.documento].append(espelho)
    return {
        espelho.id
        for documento, linhas in por_documento.items()
        if valores_resgatados[documento[len("CASHBACK-") :]] > 0
        and sum((Decimal(str(linha.valor or 0)) for linha in linhas), Decimal("0"))
        == valores_resgatados[documento[len("CASHBACK-") :]]
        for espelho in linhas
    }


def valores_entradas_venda_realizadas(
    db, tenant_id, lancamentos_periodo, data_fim: date
) -> dict[int, Decimal]:
    """Converte baixas cumulativas em incrementos e retira crédito/cashback.

    ``VENDA-ID-REALIZADO`` guarda o total pago até a baixa parcial. O
    ``VENDA-ID`` final guarda o saldo do previsto, portanto é incremental.
    Consultar a sequência anterior evita repetir a baixa em meses diferentes.
    """
    venda_ids = {
        identificado[0]
        for lancamento in lancamentos_periodo
        if lancamento.tipo == "entrada"
        and (identificado := _id_venda_documento(lancamento.documento)) is not None
    }
    if not venda_ids:
        return {}
    documentos = [
        documento
        for venda_id in venda_ids
        for documento in (f"VENDA-{venda_id}", f"VENDA-{venda_id}-REALIZADO")
    ]
    historico = (
        db.query(LancamentoManual)
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.tipo == "entrada",
            LancamentoManual.status == "realizado",
            LancamentoManual.documento.in_(documentos),
            LancamentoManual.data_lancamento <= data_fim,
        )
        .order_by(LancamentoManual.data_lancamento, LancamentoManual.id)
        .all()
    )
    pagamentos = (
        db.query(VendaPagamento)
        .filter(
            VendaPagamento.tenant_id == tenant_id,
            VendaPagamento.venda_id.in_(venda_ids),
        )
        .all()
    )
    pagamentos_nao_monetarios = defaultdict(list)
    for pagamento in pagamentos:
        if _eh_pagamento_nao_monetario(pagamento.forma_pagamento):
            pagamentos_nao_monetarios[pagamento.venda_id].append(
                (_data(pagamento.data_pagamento), Decimal(str(pagamento.valor or 0)))
            )

    por_venda = defaultdict(list)
    for lancamento in historico:
        venda_id, parcial = _id_venda_documento(lancamento.documento)
        por_venda[venda_id].append((lancamento, parcial))

    valores = {}
    for venda_id, linhas in por_venda.items():
        parcial_anterior = Decimal("0")
        credito_alocado = Decimal("0")
        for lancamento, parcial in linhas:
            bruto = Decimal(str(lancamento.valor or 0))
            if parcial:
                incremento = max(bruto - parcial_anterior, Decimal("0"))
                parcial_anterior = max(parcial_anterior, bruto)
            else:
                incremento = bruto
            data_lancamento = _data(lancamento.data_lancamento)
            credito_disponivel = (
                sum(
                    (
                        valor
                        for data_pagamento, valor in pagamentos_nao_monetarios[venda_id]
                        if data_pagamento is None
                        or (
                            data_lancamento is not None
                            and data_pagamento <= data_lancamento
                        )
                    ),
                    Decimal("0"),
                )
                - credito_alocado
            )
            credito_usado = min(incremento, max(credito_disponivel, Decimal("0")))
            credito_alocado += credito_usado
            valores[lancamento.id] = incremento - credito_usado
    return valores
