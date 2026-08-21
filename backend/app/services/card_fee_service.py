"""Fonte unica para resolver taxas de cartao no PDV e no financeiro."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.financeiro_models import FormaPagamento
from app.operadoras_models import OperadoraCartao, OperadoraCartaoTaxa
from app.utils.timezone import now_brasilia


BRAND_ALIASES = {
    "visa": "visa",
    "master": "mastercard",
    "master card": "mastercard",
    "mastercard": "mastercard",
    "elo": "elo",
    "amex": "amex",
    "american express": "amex",
    "hipercard": "hipercard",
    "hiper": "hiper",
    "cabal": "cabal",
    "diners": "diners",
    "diners club": "diners",
    "discover": "discover",
    "union pay": "unionpay",
    "unionpay": "unionpay",
    "outro": "outros",
    "outros": "outros",
}

MODALITY_ALIASES = {
    "credito": "credito",
    "crédito": "credito",
    "cartao_credito": "credito",
    "cartão_credito": "credito",
    "cartao de credito": "credito",
    "cartão de crédito": "credito",
    "debito": "debito",
    "débito": "debito",
    "cartao_debito": "debito",
    "cartão_debito": "debito",
    "cartao de debito": "debito",
    "cartão de débito": "debito",
    "voucher": "voucher",
}


class CardFeeConfigurationError(ValueError):
    """A combinacao escolhida nao possui uma taxa confiavel."""


def normalize_card_brand(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return BRAND_ALIASES.get(normalized, normalized)


def normalize_card_modality(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return MODALITY_ALIASES.get(normalized, normalized)


def modality_from_payment_form(
    forma: Optional[FormaPagamento], fallback: Any = None
) -> str:
    candidates = [
        fallback,
        getattr(forma, "tipo_cartao", None),
        getattr(forma, "tipo", None),
        getattr(forma, "nome", None),
    ]
    combined = " ".join(str(candidate or "").lower() for candidate in candidates)
    if (
        "credito_cliente" in combined
        or "crédito cliente" in combined
        or "cashback" in combined
    ):
        return ""
    for candidate in candidates:
        text = str(candidate or "").strip().lower()
        normalized = normalize_card_modality(text)
        if normalized in {"credito", "debito", "voucher"}:
            return normalized
        if "credit" in text or "crédit" in text:
            return "credito"
        if "debit" in text or "débit" in text:
            return "debito"
        if "voucher" in text:
            return "voucher"
    return ""


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _money(value: Any) -> Decimal:
    return _decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _legacy_installment_values(
    forma: FormaPagamento, parcelas: int
) -> tuple[Decimal, Decimal]:
    percentual = _decimal(getattr(forma, "taxa_percentual", 0))
    fixa = _decimal(getattr(forma, "taxa_fixa", 0))
    raw = getattr(forma, "taxas_por_parcela", None)
    if not raw:
        return percentual, fixa

    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        return percentual, fixa

    configured = parsed.get(str(parcelas)) if isinstance(parsed, dict) else None
    if configured is None:
        return percentual, fixa
    if isinstance(configured, dict):
        return (
            _decimal(configured.get("taxa_percentual", percentual)),
            _decimal(configured.get("taxa_fixa", fixa)),
        )
    return _decimal(configured), fixa


@dataclass(frozen=True)
class CardFeeResolution:
    regra_id: Optional[int]
    operadora_id: Optional[int]
    bandeira: str
    modalidade: str
    parcelas: int
    taxa_percentual: Decimal
    taxa_fixa: Decimal
    prazo_recebimento_dias: int
    valor_taxa: Decimal
    valor_liquido: Decimal
    data_recebimento_prevista: date
    fonte: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "regra_id": self.regra_id,
            "operadora_id": self.operadora_id,
            "bandeira": self.bandeira,
            "modalidade": self.modalidade,
            "parcelas": self.parcelas,
            "taxa_percentual": float(self.taxa_percentual),
            "taxa_fixa": float(self.taxa_fixa),
            "prazo_recebimento_dias": self.prazo_recebimento_dias,
            "valor_taxa": float(self.valor_taxa),
            "valor_liquido": float(self.valor_liquido),
            "data_recebimento_prevista": self.data_recebimento_prevista.isoformat(),
            "fonte": self.fonte,
        }


def _build_resolution(
    *,
    valor: Any,
    operadora_id: Optional[int],
    bandeira: str,
    modalidade: str,
    parcelas: int,
    taxa_percentual: Any,
    taxa_fixa: Any,
    prazo_recebimento_dias: Any,
    regra_id: Optional[int],
    fonte: str,
) -> CardFeeResolution:
    gross = _money(valor)
    percentual = _decimal(taxa_percentual)
    fixa = _money(taxa_fixa)
    fee = _money((gross * percentual / Decimal("100")) + fixa)
    prazo = max(0, int(prazo_recebimento_dias or 0))
    return CardFeeResolution(
        regra_id=regra_id,
        operadora_id=operadora_id,
        bandeira=bandeira,
        modalidade=modalidade,
        parcelas=parcelas,
        taxa_percentual=percentual,
        taxa_fixa=fixa,
        prazo_recebimento_dias=prazo,
        valor_taxa=fee,
        valor_liquido=_money(gross - fee),
        data_recebimento_prevista=now_brasilia().date() + timedelta(days=prazo),
        fonte=fonte,
    )


def resolve_card_fee(
    db: Session,
    *,
    tenant_id: Any,
    valor: Any,
    forma_pagamento_id: Optional[int],
    operadora_id: Optional[int],
    bandeira: Any,
    modalidade: Any,
    parcelas: Any,
    strict: bool = True,
) -> CardFeeResolution:
    """Resolve a regra exata; usa o cadastro legado somente durante a transicao."""

    parcelas_int = max(1, int(parcelas or 1))
    brand = normalize_card_brand(bandeira)
    forma = None
    if forma_pagamento_id:
        forma = (
            db.query(FormaPagamento)
            .filter(
                FormaPagamento.id == forma_pagamento_id,
                FormaPagamento.tenant_id == tenant_id,
            )
            .first()
        )
    modality = modality_from_payment_form(forma, modalidade)

    operadora = None
    if operadora_id:
        operadora = (
            db.query(OperadoraCartao)
            .filter(
                OperadoraCartao.id == operadora_id,
                OperadoraCartao.tenant_id == tenant_id,
                OperadoraCartao.ativo.is_(True),
            )
            .first()
        )
        if not operadora:
            raise CardFeeConfigurationError(
                "Operadora de cartao inexistente ou inativa."
            )
        if parcelas_int > int(operadora.max_parcelas or 1):
            raise CardFeeConfigurationError(
                f"A operadora {operadora.nome} permite no maximo {operadora.max_parcelas}x."
            )

    if operadora_id and brand and modality:
        rules_query = db.query(OperadoraCartaoTaxa).filter(
            OperadoraCartaoTaxa.tenant_id == tenant_id,
            OperadoraCartaoTaxa.operadora_id == operadora_id,
            OperadoraCartaoTaxa.ativo.is_(True),
        )
        rule = (
            rules_query.filter(
                OperadoraCartaoTaxa.bandeira == brand,
                OperadoraCartaoTaxa.modalidade == modality,
                OperadoraCartaoTaxa.parcelas == parcelas_int,
            ).first()
            or rules_query.filter(
                OperadoraCartaoTaxa.bandeira == "outros",
                OperadoraCartaoTaxa.modalidade == modality,
                OperadoraCartaoTaxa.parcelas == parcelas_int,
            ).first()
        )
        if rule:
            return _build_resolution(
                valor=valor,
                operadora_id=operadora_id,
                bandeira=brand,
                modalidade=modality,
                parcelas=parcelas_int,
                taxa_percentual=rule.taxa_percentual,
                taxa_fixa=rule.taxa_fixa,
                prazo_recebimento_dias=rule.prazo_recebimento_dias,
                regra_id=rule.id,
                fonte="regra_operadora",
            )

        if rules_query.first() and strict:
            raise CardFeeConfigurationError(
                "Taxa nao cadastrada para "
                f"{operadora.nome} / {brand.title()} / {modality.title()} / {parcelas_int}x."
            )

    if forma:
        configured_operator = getattr(forma, "operadora_id", None)
        configured_brand = normalize_card_brand(getattr(forma, "bandeira", None))
        if configured_operator and operadora_id and configured_operator != operadora_id:
            if strict:
                raise CardFeeConfigurationError(
                    "A forma de pagamento escolhida pertence a outra operadora."
                )
        elif configured_brand and brand and configured_brand not in {brand, "outros"}:
            if strict:
                raise CardFeeConfigurationError(
                    "A forma de pagamento escolhida pertence a outra bandeira."
                )
        else:
            percentual, fixa = _legacy_installment_values(forma, parcelas_int)
            return _build_resolution(
                valor=valor,
                operadora_id=operadora_id or configured_operator,
                bandeira=brand or configured_brand,
                modalidade=modality,
                parcelas=parcelas_int,
                taxa_percentual=percentual,
                taxa_fixa=fixa,
                prazo_recebimento_dias=getattr(forma, "prazo_dias", 0),
                regra_id=None,
                fonte="forma_pagamento_legada",
            )

    if operadora:
        if modality == "debito" and operadora.taxa_debito is not None:
            legacy_rate = operadora.taxa_debito
        elif parcelas_int == 1 and operadora.taxa_credito_vista is not None:
            legacy_rate = operadora.taxa_credito_vista
        else:
            legacy_rate = operadora.taxa_credito_parcelado
        if legacy_rate is not None:
            return _build_resolution(
                valor=valor,
                operadora_id=operadora.id,
                bandeira=brand,
                modalidade=modality,
                parcelas=parcelas_int,
                taxa_percentual=legacy_rate,
                taxa_fixa=0,
                prazo_recebimento_dias=0,
                regra_id=None,
                fonte="operadora_legada",
            )

    if strict:
        raise CardFeeConfigurationError(
            "Nao existe taxa de cartao cadastrada para a combinacao escolhida."
        )

    return _build_resolution(
        valor=valor,
        operadora_id=operadora_id,
        bandeira=brand,
        modalidade=modality,
        parcelas=parcelas_int,
        taxa_percentual=0,
        taxa_fixa=0,
        prazo_recebimento_dias=0,
        regra_id=None,
        fonte="sem_configuracao",
    )


def applied_fee_fields(resolution: CardFeeResolution) -> dict[str, Any]:
    return {
        "modalidade_cartao": resolution.modalidade,
        "taxa_cartao_regra_id": resolution.regra_id,
        "taxa_percentual_aplicada": resolution.taxa_percentual,
        "taxa_fixa_aplicada": resolution.taxa_fixa,
        "valor_taxa_prevista": resolution.valor_taxa,
        "valor_liquido_previsto": resolution.valor_liquido,
        "prazo_recebimento_dias": resolution.prazo_recebimento_dias,
        "data_recebimento_prevista": resolution.data_recebimento_prevista,
    }
