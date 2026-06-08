from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Cliente, FornecedorGrupo
from app.partner_utils import is_partner_owned
from app.produtos_models import Produto, ProdutoFornecedor
from app.services.kit_estoque_service import KitEstoqueService


logger = logging.getLogger(__name__)


def _palavras_busca_produto(termo: Optional[str]) -> list[str]:
    if not termo:
        return []
    return [palavra.strip() for palavra in termo.split() if palavra.strip()]


def _tipos_base_listagem(include_variations: bool, termo_busca: Optional[str]) -> list[str]:
    if not include_variations:
        return ["SIMPLES"]
    if (termo_busca or "").strip():
        return ["SIMPLES", "PAI", "KIT", "VARIACAO"]
    return ["SIMPLES", "PAI", "KIT"]


def _normalizar_paginacao_produtos(
    page: int,
    page_size: int,
    *,
    max_page_size: int,
) -> tuple[int, int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), max_page_size)
    offset = (page - 1) * page_size
    return page, page_size, offset


def _resolver_fornecedor_ids_filtro_produto(
    db: Session,
    *,
    tenant_id: str,
    fornecedor_id: Optional[int],
    fornecedor_grupo_id: Optional[int],
    tenant_ids_fornecedores: Optional[List[str]] = None,
) -> tuple[list[int], bool]:
    if fornecedor_grupo_id:
        grupo = db.query(FornecedorGrupo).filter(
            FornecedorGrupo.id == fornecedor_grupo_id,
            FornecedorGrupo.tenant_id == tenant_id,
            FornecedorGrupo.ativo.is_(True),
        ).first()
        if not grupo:
            raise HTTPException(status_code=404, detail="Grupo de fornecedor nao encontrado")

        tenant_refs = [
            str(tenant_ref)
            for tenant_ref in (tenant_ids_fornecedores or [tenant_id])
            if tenant_ref is not None
        ] or [tenant_id]

        fornecedor_ids = [
            fornecedor_id_grupo
            for (fornecedor_id_grupo,) in db.query(Cliente.id).filter(
                Cliente.tenant_id.in_(tenant_refs),
                Cliente.tipo_cadastro == "fornecedor",
                Cliente.fornecedor_grupo_id == grupo.id,
                Cliente.ativo.is_(True),
            ).all()
        ]
        return fornecedor_ids, True

    if fornecedor_id:
        return [fornecedor_id], False

    return [], False


def _aplicar_filtro_fornecedor_produto(
    query: Any,
    *,
    fornecedor_ids: list[int],
    filtro_por_grupo: bool,
) -> Any:
    if filtro_por_grupo and not fornecedor_ids:
        return query.filter(Produto.id == -1)

    if not fornecedor_ids:
        return query

    return query.filter(
        or_(
            Produto.fornecedor_id.in_(fornecedor_ids),
            Produto.fornecedores_alternativos.any(
                and_(
                    ProdutoFornecedor.fornecedor_id.in_(fornecedor_ids),
                    ProdutoFornecedor.ativo == True,
                )
            ),
        )
    )


def _as_float_optional(valor: Any) -> Optional[float]:
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _datetime_naive(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None) if valor.tzinfo else valor
    return None


def _janela_promocao_ativa(
    inicio: Any,
    fim: Any,
    referencia: Optional[datetime] = None,
) -> bool:
    agora = _datetime_naive(referencia) or datetime.now()
    inicio_dt = _datetime_naive(inicio)
    fim_dt = _datetime_naive(fim)

    if inicio_dt and agora < inicio_dt:
        return False
    if fim_dt and agora > fim_dt:
        return False
    return True


def _resolver_promocao_erp_produto(
    produto: Produto,
    referencia: Optional[datetime] = None,
) -> dict[str, Any]:
    preco_regular = _as_float_optional(getattr(produto, "preco_venda", None)) or 0.0
    preco_promocional = _as_float_optional(getattr(produto, "preco_promocional", None))

    promocao_ativa = (
        preco_promocional is not None
        and preco_promocional > 0
        and (preco_regular <= 0 or preco_promocional < preco_regular)
        and _janela_promocao_ativa(
            getattr(produto, "promocao_inicio", None),
            getattr(produto, "promocao_fim", None),
            referencia,
        )
    )

    preco_pdv = preco_promocional if promocao_ativa else preco_regular
    desconto = (
        max(preco_regular - (preco_promocional or preco_regular), 0.0)
        if promocao_ativa
        else 0.0
    )

    return {
        "promocao_ativa": bool(promocao_ativa),
        "preco_pdv": round(float(preco_pdv or 0), 2),
        "preco_regular": round(float(preco_regular or 0), 2),
        "preco_promocional": round(float(preco_promocional), 2)
        if preco_promocional is not None
        else None,
        "desconto": round(float(desconto or 0), 2),
    }


def _enriquecer_preco_pdv(produto: Produto, referencia: Optional[datetime] = None) -> Produto:
    promocao = _resolver_promocao_erp_produto(produto, referencia)
    produto.preco_venda_original = promocao["preco_regular"]
    produto.preco_venda_pdv = promocao["preco_pdv"]
    produto.preco_venda_efetivo = promocao["preco_pdv"]
    produto.promocao_pdv_ativa = promocao["promocao_ativa"]
    produto.promocao_origem_pdv = "Promocao ERP" if promocao["promocao_ativa"] else None
    produto.desconto_promocional_pdv = promocao["desconto"]
    return produto


def _mapa_reservas_ativas_multitenant(db: Session, tenant_ids: List[str]) -> dict[int, float]:
    """Consolida reservas ativas por produto para os tenants acessiveis."""
    try:
        from app.estoque_reserva_service import EstoqueReservaService

        reservas_consolidadas: dict[int, float] = {}
        for tenant_ref in {str(tenant) for tenant in tenant_ids if tenant is not None}:
            reservas_tenant = EstoqueReservaService.mapa_reservas_ativas_por_produto(
                db,
                tenant_ref,
            )
            for produto_id, quantidade in (reservas_tenant or {}).items():
                reservas_consolidadas[int(produto_id)] = (
                    float(reservas_consolidadas.get(int(produto_id), 0.0) or 0.0)
                    + float(quantidade or 0.0)
                )
        return reservas_consolidadas
    except Exception as exc:
        logger.warning("Nao foi possivel consolidar reservas ativas: %s", exc)
        db.rollback()
        return {}


def _enriquecer_produto_listagem(
    db: Session,
    produto: Produto,
    tenant_id,
    reservas_por_produto: dict[int, float] | None = None,
    incluir_detalhes_composto: bool = True,
    validade_por_produto: dict[int, dict[str, Any]] | None = None,
):
    """Padroniza dados de listagem para produtos simples, kits e variacoes-kit."""
    reservas_por_produto = reservas_por_produto or {}
    validade_por_produto = validade_por_produto or {}
    tenant_produto = getattr(produto, "tenant_id", tenant_id)
    reservas_mesmo_tenant = str(tenant_produto) == str(tenant_id)
    estoque_reservado = (
        float(reservas_por_produto.get(produto.id, 0.0) or 0.0)
        if reservas_mesmo_tenant
        else 0.0
    )

    if produto.categoria:
        produto.categoria_nome = produto.categoria.nome

    produto_composto = produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit

    if produto_composto and incluir_detalhes_composto:
        try:
            from app.services.kit_custo_service import KitCustoService

            composicao = KitEstoqueService.obter_detalhes_composicao(
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
                    KitEstoqueService.calcular_estoque_virtual_kit(
                        db,
                        produto.id,
                        tenant_id=tenant_produto,
                        reservas_por_produto=reservas_por_produto if reservas_mesmo_tenant else None,
                    )
                )
            else:
                produto.estoque_virtual = int(produto.estoque_atual or 0)
        except Exception as e:
            logger.warning(f"Erro ao processar produto composto {produto.id}: {e}")
            produto.composicao_kit = []
            produto.estoque_virtual = int(produto.estoque_atual or 0)
    elif produto_composto and produto.tipo_kit == "VIRTUAL":
        produto.composicao_kit = []
        try:
            produto.estoque_virtual = int(
                KitEstoqueService.calcular_estoque_virtual_kit(
                    db,
                    produto.id,
                    tenant_id=tenant_produto,
                    reservas_por_produto=reservas_por_produto if reservas_mesmo_tenant else None,
                )
            )
        except Exception as e:
            logger.warning(f"Erro ao calcular estoque virtual do produto composto {produto.id}: {e}")
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
    _enriquecer_preco_pdv(produto)
    return produto


def _nome_area_produto(produto: Produto) -> str:
    if getattr(produto, "departamento", None):
        return produto.departamento.nome
    if getattr(produto, "categoria", None) and getattr(produto.categoria, "departamento", None):
        return produto.categoria.departamento.nome
    return "Sem setor"


def _departamento_id_produto(produto: Produto) -> Optional[int]:
    if getattr(produto, "departamento_id", None):
        return produto.departamento_id
    if getattr(produto, "categoria", None):
        return getattr(produto.categoria, "departamento_id", None)
    return None


def _fornecedor_nome_produto(produto: Produto) -> Optional[str]:
    fornecedor = produto.fornecedor
    if not fornecedor and getattr(produto, "fornecedores_alternativos", None):
        vinculo_principal = next(
            (
                vinculo
                for vinculo in produto.fornecedores_alternativos
                if vinculo.ativo and vinculo.e_principal and vinculo.fornecedor
            ),
            None,
        )
        vinculo_secundario = next(
            (
                vinculo
                for vinculo in produto.fornecedores_alternativos
                if vinculo.ativo and vinculo.fornecedor
            ),
            None,
        )
        fornecedor = (
            vinculo_principal.fornecedor
            if vinculo_principal
            else vinculo_secundario.fornecedor if vinculo_secundario else None
        )
    return fornecedor.nome if fornecedor else None


def _resolver_metricas_valorizacao_produto(
    db: Session,
    produto: Produto,
    reservas_por_produto: dict[int, float] | None = None,
) -> dict:
    reservas_por_produto = reservas_por_produto or {}
    estoque_reservado = float(reservas_por_produto.get(produto.id, 0.0) or 0.0)
    estoque_atual = float(produto.estoque_atual or 0)
    preco_custo = float(produto.preco_custo or 0)

    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit == "VIRTUAL":
        try:
            from app.services.kit_custo_service import KitCustoService

            estoque_atual = float(
                KitEstoqueService.calcular_estoque_virtual_kit(
                    db,
                    produto.id,
                    tenant_id=getattr(produto, "tenant_id", None),
                    reservas_por_produto=reservas_por_produto,
                )
            )
            preco_custo = float(KitCustoService.calcular_custo_kit(produto.id, db))
            estoque_reservado = 0.0
        except Exception as exc:
            logger.warning(
                "Erro ao calcular valorizacao do kit virtual %s: %s",
                produto.id,
                exc,
            )

    estoque_disponivel = max(estoque_atual - estoque_reservado, 0.0)
    preco_venda = float(produto.preco_venda or 0)

    return {
        "estoque_atual": estoque_atual,
        "estoque_reservado": estoque_reservado,
        "estoque_disponivel": estoque_disponivel,
        "preco_custo": preco_custo,
        "preco_venda": preco_venda,
        "valor_custo_total": estoque_atual * preco_custo,
        "valor_venda_total": estoque_atual * preco_venda,
    }
