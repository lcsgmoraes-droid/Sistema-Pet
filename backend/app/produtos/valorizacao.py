import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def nome_area_produto(produto: Any) -> str:
    if getattr(produto, "departamento", None):
        return produto.departamento.nome
    if getattr(produto, "categoria", None) and getattr(produto.categoria, "departamento", None):
        return produto.categoria.departamento.nome
    return "Sem setor"


def departamento_id_produto(produto: Any) -> Optional[int]:
    if getattr(produto, "departamento_id", None):
        return produto.departamento_id
    if getattr(produto, "categoria", None):
        return getattr(produto.categoria, "departamento_id", None)
    return None


def fornecedor_nome_produto(produto: Any) -> Optional[str]:
    fornecedor = getattr(produto, "fornecedor", None)
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


def resolver_metricas_valorizacao_produto(
    db,
    produto: Any,
    reservas_por_produto: dict[int, float] | None = None,
    kit_estoque_service=None,
    kit_custo_service=None,
) -> dict:
    reservas_por_produto = reservas_por_produto or {}
    estoque_reservado = float(reservas_por_produto.get(produto.id, 0.0) or 0.0)
    estoque_atual = float(produto.estoque_atual or 0)
    preco_custo = float(produto.preco_custo or 0)

    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit == "VIRTUAL":
        try:
            if kit_estoque_service is None:
                from app.services.kit_estoque_service import KitEstoqueService

                kit_estoque_service = KitEstoqueService
            if kit_custo_service is None:
                from app.services.kit_custo_service import KitCustoService

                kit_custo_service = KitCustoService

            estoque_atual = float(
                kit_estoque_service.calcular_estoque_virtual_kit(
                    db,
                    produto.id,
                    tenant_id=getattr(produto, "tenant_id", None),
                    reservas_por_produto=reservas_por_produto,
                )
            )
            preco_custo = float(kit_custo_service.calcular_custo_kit(produto.id, db))
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
