import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.partner_utils import is_partner_owned
from app.produtos_models import Produto
from app.services.kit_estoque_service import KitEstoqueService

logger = logging.getLogger(__name__)


def as_float_optional(valor: Any) -> Optional[float]:
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def datetime_naive(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None) if valor.tzinfo else valor
    return None


def janela_promocao_ativa(inicio: Any, fim: Any, referencia: Optional[datetime] = None) -> bool:
    agora = datetime_naive(referencia) or datetime.now()
    inicio_dt = datetime_naive(inicio)
    fim_dt = datetime_naive(fim)

    if inicio_dt and agora < inicio_dt:
        return False
    if fim_dt and agora > fim_dt:
        return False
    return True


def resolver_promocao_erp_produto(produto: Produto, referencia: Optional[datetime] = None) -> dict[str, Any]:
    preco_regular = as_float_optional(getattr(produto, "preco_venda", None)) or 0.0
    preco_promocional = as_float_optional(getattr(produto, "preco_promocional", None))

    promocao_ativa = (
        preco_promocional is not None
        and preco_promocional > 0
        and (preco_regular <= 0 or preco_promocional < preco_regular)
        and janela_promocao_ativa(
            getattr(produto, "promocao_inicio", None),
            getattr(produto, "promocao_fim", None),
            referencia,
        )
    )

    preco_pdv = preco_promocional if promocao_ativa else preco_regular
    desconto = max(preco_regular - (preco_promocional or preco_regular), 0.0) if promocao_ativa else 0.0

    return {
        "promocao_ativa": bool(promocao_ativa),
        "preco_pdv": round(float(preco_pdv or 0), 2),
        "preco_regular": round(float(preco_regular or 0), 2),
        "preco_promocional": round(float(preco_promocional), 2) if preco_promocional is not None else None,
        "desconto": round(float(desconto or 0), 2),
    }


def enriquecer_preco_pdv(produto: Produto, referencia: Optional[datetime] = None) -> Produto:
    promocao = resolver_promocao_erp_produto(produto, referencia)
    produto.preco_venda_original = promocao["preco_regular"]
    produto.preco_venda_pdv = promocao["preco_pdv"]
    produto.preco_venda_efetivo = promocao["preco_pdv"]
    produto.promocao_pdv_ativa = promocao["promocao_ativa"]
    produto.promocao_origem_pdv = "Promocao ERP" if promocao["promocao_ativa"] else None
    produto.desconto_promocional_pdv = promocao["desconto"]
    return produto


def enriquecer_produto_listagem(
    db: Session,
    produto: Produto,
    tenant_id,
    reservas_por_produto: dict[int, float] | None = None,
    incluir_detalhes_composto: bool = True,
    validade_por_produto: dict[int, dict[str, Any]] | None = None,
    kit_estoque_service=KitEstoqueService,
):
    """Padroniza dados de listagem para produtos simples, kits e variacoes-kit."""
    reservas_por_produto = reservas_por_produto or {}
    validade_por_produto = validade_por_produto or {}
    tenant_produto = getattr(produto, "tenant_id", tenant_id)
    reservas_mesmo_tenant = str(tenant_produto) == str(tenant_id)
    estoque_reservado = float(
        reservas_por_produto.get(produto.id, 0.0) or 0.0
    ) if reservas_mesmo_tenant else 0.0

    if produto.categoria:
        produto.categoria_nome = produto.categoria.nome

    produto_composto = produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit

    if produto_composto and incluir_detalhes_composto:
        try:
            from app.services.kit_custo_service import KitCustoService

            composicao = kit_estoque_service.obter_detalhes_composicao(
                db,
                produto.id,
                tenant_id=tenant_produto,
                reservas_por_produto=reservas_por_produto if reservas_mesmo_tenant else None,
            )
            produto.composicao_kit = [
                {
                    "id": comp["id"],
                    "produto_id": comp["produto_id"],
                    "produto_nome": comp["produto_nome"],
                    "produto_sku": comp["produto_sku"],
                    "produto_tipo": comp["produto_tipo"],
                    "quantidade": comp["quantidade"],
                    "estoque_componente": comp["estoque_componente"],
                    "estoque_reservado": comp.get("estoque_reservado", 0),
                    "estoque_disponivel": comp.get("estoque_disponivel", 0),
                    "kits_possiveis": comp["kits_possiveis"],
                    "ordem": comp["ordem"],
                    "opcional": comp["opcional"],
                }
                for comp in composicao
            ]
            produto.preco_custo = float(KitCustoService.calcular_custo_kit(produto.id, db))

            if produto.tipo_kit == "VIRTUAL":
                produto.estoque_virtual = int(
                    kit_estoque_service.calcular_estoque_virtual_kit(
                        db,
                        produto.id,
                        tenant_id=tenant_produto,
                        reservas_por_produto=reservas_por_produto if reservas_mesmo_tenant else None,
                    )
                )
            else:
                produto.estoque_virtual = int(produto.estoque_atual or 0)
        except Exception as e:
            logger.warning("Erro ao processar produto composto %s: %s", produto.id, e)
            produto.composicao_kit = []
            produto.estoque_virtual = int(produto.estoque_atual or 0)
    elif produto_composto and produto.tipo_kit == "VIRTUAL":
        produto.composicao_kit = []
        try:
            produto.estoque_virtual = int(
                kit_estoque_service.calcular_estoque_virtual_kit(
                    db,
                    produto.id,
                    tenant_id=tenant_produto,
                    reservas_por_produto=reservas_por_produto if reservas_mesmo_tenant else None,
                )
            )
        except Exception as e:
            logger.warning("Erro ao calcular estoque virtual do produto composto %s: %s", produto.id, e)
            produto.estoque_virtual = int(produto.estoque_atual or 0)
    elif produto_composto:
        produto.composicao_kit = []
        produto.estoque_virtual = int(produto.estoque_atual or 0)
    else:
        produto.composicao_kit = []
        produto.estoque_virtual = int(produto.estoque_atual or 0)

    validade_info = validade_por_produto.get(produto.id, {})
    produto.validade_proxima_listagem = validade_info.get("validade_proxima_listagem")
    produto.lote_validade_proxima = validade_info.get("lote_validade_proxima")
    produto.lotes_validade_resumo = validade_info.get("lotes_validade_resumo", [])
    produto.estoque_reservado = estoque_reservado
    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit == "VIRTUAL":
        produto.estoque_disponivel = float(produto.estoque_virtual or 0)
    else:
        produto.estoque_disponivel = max(
            float(produto.estoque_atual or 0) - produto.estoque_reservado,
            0.0,
        )
    produto.de_parceiro = is_partner_owned(tenant_id, produto.tenant_id)
    enriquecer_preco_pdv(produto)
    return produto
