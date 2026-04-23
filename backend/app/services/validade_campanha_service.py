from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.produtos_models import (
    CampanhaValidadeAutomatica,
    CampanhaValidadeExclusao,
    Produto,
    ProdutoLote,
)


CANAIS_VALIDOS = {"app", "ecommerce"}

DEFAULT_CAMPANHA_VALIDADE = {
    "ativo": False,
    "aplicar_app": True,
    "aplicar_ecommerce": True,
    "desconto_60_dias": 10.0,
    "desconto_30_dias": 20.0,
    "desconto_7_dias": 35.0,
    "rotulo_publico": "Validade proxima",
    "mensagem_publica": "Oferta por lote com quantidade limitada.",
}


@dataclass
class ValidityPromotionResult:
    active: bool = False
    config_active: bool = False
    channel_enabled: bool = False
    faixa: Optional[str] = None
    percentual_desconto: Optional[float] = None
    regular_price: float = 0.0
    promotional_price: Optional[float] = None
    quantity_available: float = 0.0
    dias_para_vencer: Optional[int] = None
    excluded: bool = False
    exclusion_id: Optional[int] = None
    lote_id: Optional[int] = None
    lote_nome: Optional[str] = None
    label: Optional[str] = None
    message: Optional[str] = None


@dataclass
class CatalogPricingResult:
    regular_price: float
    promotional_price: Optional[float]
    promotion_active: bool
    promotion_origin: Optional[str]
    manual_promotional_price: Optional[float]
    validity_offer: Optional[ValidityPromotionResult]


def _tenant_key(value) -> str:
    return str(value)


def _normalizar_canal(canal: Optional[str]) -> str:
    value = str(canal or "ecommerce").strip().lower()
    return value if value in CANAIS_VALIDOS else "ecommerce"


def _janela_ativa(inicio, fim, agora: datetime) -> bool:
    if inicio and inicio > agora:
        return False
    if fim and fim < agora:
        return False
    return True


def _formatar_quantidade(valor: float) -> str:
    numero = float(valor or 0)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:.2f}".replace(".", ",")


def _faixa_e_desconto(
    config: CampanhaValidadeAutomatica | None,
    dias_para_vencer: Optional[int],
) -> tuple[Optional[str], Optional[float], Optional[str]]:
    if not config or dias_para_vencer is None or dias_para_vencer < 0:
        return None, None, None
    if dias_para_vencer <= 7 and float(config.desconto_7_dias or 0) > 0:
        return "7_dias", float(config.desconto_7_dias or 0), "7 dias"
    if dias_para_vencer <= 30 and float(config.desconto_30_dias or 0) > 0:
        return "30_dias", float(config.desconto_30_dias or 0), "30 dias"
    if dias_para_vencer <= 60 and float(config.desconto_60_dias or 0) > 0:
        return "60_dias", float(config.desconto_60_dias or 0), "60 dias"
    return None, None, None


def _canal_habilitado(config: CampanhaValidadeAutomatica | None, canal: str) -> bool:
    if not config or not bool(config.ativo):
        return False
    canal_normalizado = _normalizar_canal(canal)
    if canal_normalizado == "app":
        return bool(config.aplicar_app)
    return bool(config.aplicar_ecommerce)


def serializar_campanha_validade_config(
    config: CampanhaValidadeAutomatica | None,
    *,
    total_exclusoes: int = 0,
) -> dict:
    origem = config or type("DefaultConfig", (), DEFAULT_CAMPANHA_VALIDADE)()
    return {
        "id": getattr(config, "id", None),
        "ativo": bool(getattr(origem, "ativo", DEFAULT_CAMPANHA_VALIDADE["ativo"])),
        "aplicar_app": bool(
            getattr(origem, "aplicar_app", DEFAULT_CAMPANHA_VALIDADE["aplicar_app"])
        ),
        "aplicar_ecommerce": bool(
            getattr(
                origem,
                "aplicar_ecommerce",
                DEFAULT_CAMPANHA_VALIDADE["aplicar_ecommerce"],
            )
        ),
        "desconto_60_dias": float(
            getattr(
                origem,
                "desconto_60_dias",
                DEFAULT_CAMPANHA_VALIDADE["desconto_60_dias"],
            )
            or 0
        ),
        "desconto_30_dias": float(
            getattr(
                origem,
                "desconto_30_dias",
                DEFAULT_CAMPANHA_VALIDADE["desconto_30_dias"],
            )
            or 0
        ),
        "desconto_7_dias": float(
            getattr(
                origem,
                "desconto_7_dias",
                DEFAULT_CAMPANHA_VALIDADE["desconto_7_dias"],
            )
            or 0
        ),
        "rotulo_publico": (
            getattr(
                origem,
                "rotulo_publico",
                DEFAULT_CAMPANHA_VALIDADE["rotulo_publico"],
            )
            or DEFAULT_CAMPANHA_VALIDADE["rotulo_publico"]
        ),
        "mensagem_publica": (
            getattr(
                origem,
                "mensagem_publica",
                DEFAULT_CAMPANHA_VALIDADE["mensagem_publica"],
            )
            or DEFAULT_CAMPANHA_VALIDADE["mensagem_publica"]
        ),
        "total_exclusoes": int(total_exclusoes or 0),
    }


def obter_campanha_validade_config(
    db: Session,
    tenant_id,
) -> CampanhaValidadeAutomatica | None:
    return (
        db.query(CampanhaValidadeAutomatica)
        .filter(CampanhaValidadeAutomatica.tenant_id == tenant_id)
        .first()
    )


def obter_configs_campanha_validade(
    db: Session,
    tenant_ids: Iterable,
) -> dict[str, CampanhaValidadeAutomatica]:
    tenant_values = [tenant_id for tenant_id in tenant_ids if tenant_id]
    if not tenant_values:
        return {}
    rows = (
        db.query(CampanhaValidadeAutomatica)
        .filter(CampanhaValidadeAutomatica.tenant_id.in_(tenant_values))
        .all()
    )
    return {_tenant_key(row.tenant_id): row for row in rows}


def contar_exclusoes_ativas(db: Session, tenant_id) -> int:
    return int(
        db.query(func.count(CampanhaValidadeExclusao.id))
        .filter(
            CampanhaValidadeExclusao.tenant_id == tenant_id,
            CampanhaValidadeExclusao.ativo.is_(True),
        )
        .scalar()
        or 0
    )


def obter_mapas_exclusao_validade(
    db: Session,
    tenant_ids: Iterable,
    *,
    produto_ids: Optional[Iterable[int]] = None,
) -> tuple[dict[tuple[str, int], CampanhaValidadeExclusao], dict[tuple[str, int], CampanhaValidadeExclusao]]:
    tenant_values = [tenant_id for tenant_id in tenant_ids if tenant_id]
    if not tenant_values:
        return {}, {}

    query = db.query(CampanhaValidadeExclusao).filter(
        CampanhaValidadeExclusao.tenant_id.in_(tenant_values),
        CampanhaValidadeExclusao.ativo.is_(True),
    )
    if produto_ids:
        produto_ids = [int(produto_id) for produto_id in produto_ids if produto_id]
        if produto_ids:
            query = query.filter(CampanhaValidadeExclusao.produto_id.in_(produto_ids))

    exclusoes = query.all()
    exclusoes_produto: dict[tuple[str, int], CampanhaValidadeExclusao] = {}
    exclusoes_lote: dict[tuple[str, int], CampanhaValidadeExclusao] = {}
    for exclusao in exclusoes:
        tenant_key = _tenant_key(exclusao.tenant_id)
        if exclusao.lote_id:
            exclusoes_lote[(tenant_key, int(exclusao.lote_id))] = exclusao
        exclusoes_produto[(tenant_key, int(exclusao.produto_id))] = exclusao
    return exclusoes_produto, exclusoes_lote


def resolver_preco_regular_canal(produto: Produto, canal: Optional[str]) -> float:
    canal_normalizado = _normalizar_canal(canal)
    if canal_normalizado == "app":
        base = produto.preco_app if produto.preco_app is not None else produto.preco_venda
    else:
        base = (
            produto.preco_ecommerce
            if produto.preco_ecommerce is not None
            else produto.preco_venda
        )
    return round(float(base or 0), 2)


def resolver_preco_promocional_manual(
    produto: Produto,
    canal: Optional[str],
    *,
    agora: Optional[datetime] = None,
) -> Optional[float]:
    canal_normalizado = _normalizar_canal(canal)
    agora = agora or datetime.now(timezone.utc)
    candidatos: list[float] = []

    if canal_normalizado == "app" and produto.preco_app_promo is not None:
        if _janela_ativa(produto.preco_app_promo_inicio, produto.preco_app_promo_fim, agora):
            candidatos.append(float(produto.preco_app_promo))

    if canal_normalizado == "ecommerce" and produto.preco_ecommerce_promo is not None:
        if _janela_ativa(
            produto.preco_ecommerce_promo_inicio,
            produto.preco_ecommerce_promo_fim,
            agora,
        ):
            candidatos.append(float(produto.preco_ecommerce_promo))

    if produto.promocao_ativa and produto.preco_promocional is not None:
        if _janela_ativa(produto.promocao_inicio, produto.promocao_fim, agora):
            candidatos.append(float(produto.preco_promocional))

    if not candidatos:
        return None
    return round(min(candidatos), 2)


def construir_oferta_validade(
    produto: Produto,
    lote: ProdutoLote,
    canal: Optional[str],
    *,
    config: CampanhaValidadeAutomatica | None = None,
    exclusao_produto: CampanhaValidadeExclusao | None = None,
    exclusao_lote: CampanhaValidadeExclusao | None = None,
) -> ValidityPromotionResult:
    canal_normalizado = _normalizar_canal(canal)
    config = config
    dias_para_vencer = lote.dias_para_vencer
    regular_price = resolver_preco_regular_canal(produto, canal_normalizado)

    result = ValidityPromotionResult(
        active=False,
        config_active=bool(config and config.ativo),
        channel_enabled=_canal_habilitado(config, canal_normalizado),
        regular_price=regular_price,
        quantity_available=float(lote.quantidade_disponivel or 0),
        dias_para_vencer=dias_para_vencer,
        lote_id=lote.id,
        lote_nome=lote.nome_lote,
        excluded=bool(exclusao_produto or exclusao_lote),
        exclusion_id=(
            int(exclusao_lote.id)
            if exclusao_lote
            else int(exclusao_produto.id) if exclusao_produto else None
        ),
    )

    if not result.config_active or not result.channel_enabled:
        return result
    if result.excluded or result.quantity_available <= 0:
        return result

    faixa, percentual, label = _faixa_e_desconto(config, dias_para_vencer)
    if not faixa or percentual is None:
        return result

    promotional_price = round(max(regular_price * (1 - (percentual / 100.0)), 0), 2)
    if promotional_price >= regular_price:
        return result

    result.active = True
    result.faixa = faixa
    result.percentual_desconto = percentual
    result.promotional_price = promotional_price
    result.label = label
    result.message = (
        f"Ate {_formatar_quantidade(result.quantity_available)} unidade(s) do lote "
        f"{lote.nome_lote} por esse preco."
    )
    return result


def resolver_preco_publico_produto(
    produto: Produto,
    canal: Optional[str],
    *,
    validity_offer: Optional[ValidityPromotionResult] = None,
) -> CatalogPricingResult:
    canal_normalizado = _normalizar_canal(canal)
    regular_price = resolver_preco_regular_canal(produto, canal_normalizado)
    manual_promotional_price = resolver_preco_promocional_manual(produto, canal_normalizado)

    if validity_offer and validity_offer.active and validity_offer.promotional_price is not None:
        if manual_promotional_price is None or validity_offer.promotional_price < manual_promotional_price:
            return CatalogPricingResult(
                regular_price=regular_price,
                promotional_price=validity_offer.promotional_price,
                promotion_active=True,
                promotion_origin="validade",
                manual_promotional_price=manual_promotional_price,
                validity_offer=validity_offer,
            )

    if manual_promotional_price is not None and manual_promotional_price < regular_price:
        return CatalogPricingResult(
            regular_price=regular_price,
            promotional_price=manual_promotional_price,
            promotion_active=True,
            promotion_origin="manual",
            manual_promotional_price=manual_promotional_price,
            validity_offer=validity_offer,
        )

    return CatalogPricingResult(
        regular_price=regular_price,
        promotional_price=None,
        promotion_active=False,
        promotion_origin=None,
        manual_promotional_price=manual_promotional_price,
        validity_offer=validity_offer,
    )


def mapear_ofertas_validade_por_produto(
    db: Session,
    produtos: Iterable[Produto],
    canal: Optional[str],
) -> dict[int, ValidityPromotionResult]:
    produtos = [produto for produto in produtos if produto]
    if not produtos:
        return {}

    tenant_ids = {produto.tenant_id for produto in produtos if produto.tenant_id}
    produto_ids = [int(produto.id) for produto in produtos]
    produtos_por_id = {int(produto.id): produto for produto in produtos}
    configs = obter_configs_campanha_validade(db, tenant_ids)
    exclusoes_produto, exclusoes_lote = obter_mapas_exclusao_validade(
        db,
        tenant_ids,
        produto_ids=produto_ids,
    )

    lotes = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id.in_(produto_ids),
            ProdutoLote.data_validade.isnot(None),
            func.coalesce(ProdutoLote.quantidade_disponivel, 0) > 0,
        )
        .order_by(ProdutoLote.data_validade.asc(), ProdutoLote.id.asc())
        .all()
    )

    offers: dict[int, ValidityPromotionResult] = {}
    for lote in lotes:
        produto = produtos_por_id.get(int(lote.produto_id))
        if not produto:
            continue
        tenant_key = _tenant_key(produto.tenant_id)
        offer = construir_oferta_validade(
            produto,
            lote,
            canal,
            config=configs.get(tenant_key),
            exclusao_produto=exclusoes_produto.get((tenant_key, int(produto.id))),
            exclusao_lote=exclusoes_lote.get((tenant_key, int(lote.id))),
        )
        if offer.active and int(produto.id) not in offers:
            offers[int(produto.id)] = offer
    return offers
