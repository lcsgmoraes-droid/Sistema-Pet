"""Catalogo inicial seguro de operadoras de cartao para cada tenant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.operadoras_models import OperadoraCartao


DEFAULT_CARD_OPERATOR_PRESETS: tuple[dict[str, Any], ...] = (
    {"nome": "Stone", "codigo": "STONE", "cor": "#00A868"},
    {"nome": "Cielo", "codigo": "CIELO", "cor": "#006CB7"},
    {"nome": "Rede", "codigo": "REDE", "cor": "#EC7000"},
    {"nome": "Getnet", "codigo": "GETNET", "cor": "#E30613"},
    {"nome": "PagBank", "codigo": "PAGBANK", "cor": "#00A868"},
    {"nome": "Mercado Pago", "codigo": "MERCADO_PAGO", "cor": "#009EE3"},
    {"nome": "SafraPay", "codigo": "SAFRAPAY", "cor": "#B08D2F"},
    {"nome": "SumUp", "codigo": "SUMUP", "cor": "#111827"},
    {"nome": "Ton", "codigo": "TON", "cor": "#00D17A"},
)


def _normalize_operator_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def operator_matches_preset(
    operator: "OperadoraCartao", preset: dict[str, Any]
) -> bool:
    """Evita duplicar presets quando o tenant ja cadastrou a mesma operadora."""

    existing_code = _normalize_operator_text(getattr(operator, "codigo", None))
    preset_code = _normalize_operator_text(preset["codigo"])
    if existing_code and existing_code == preset_code:
        return True

    existing_name = _normalize_operator_text(getattr(operator, "nome", None))
    preset_name = _normalize_operator_text(preset["nome"])
    return existing_name == preset_name or existing_name.startswith(f"{preset_name} ")


def ensure_card_operator_presets(
    db: Session,
    *,
    tenant_id: Any,
    user_id: int,
    result: Any = None,
) -> dict[str, int]:
    """Cria sugestoes inativas; nunca presume taxa nem habilita uso no PDV."""

    from app.operadoras_models import OperadoraCartao

    existing = (
        db.query(OperadoraCartao).filter(OperadoraCartao.tenant_id == tenant_id).all()
    )
    created = 0
    skipped = 0

    for preset in DEFAULT_CARD_OPERATOR_PRESETS:
        if any(operator_matches_preset(operator, preset) for operator in existing):
            skipped += 1
            if result is not None:
                result.bump("skipped", "card_operators")
            continue

        operator = OperadoraCartao(
            tenant_id=tenant_id,
            user_id=user_id,
            nome=preset["nome"],
            codigo=preset["codigo"],
            cor=preset["cor"],
            icone="💳",
            max_parcelas=12,
            padrao=False,
            ativo=False,
            api_enabled=False,
        )
        db.add(operator)
        existing.append(operator)
        created += 1
        if result is not None:
            result.bump("created", "card_operators")

    return {"created": created, "skipped": skipped}
