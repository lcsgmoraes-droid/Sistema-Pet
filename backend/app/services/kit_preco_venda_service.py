"""Sugestoes autorizadas de preco de venda para produtos compostos."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from sqlalchemy.orm import Session

from ..produtos_models import Produto, ProdutoKitComponente
from .kit_custo_service import KitCustoService


CENTAVO = Decimal("0.01")


def _moeda(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


class KitPrecoVendaService:
    """Calcula e aplica sugestoes sem alterar precos sem autorizacao."""

    @staticmethod
    def _montar_sugestoes(
        db: Session,
        produto_componente: Produto,
        novo_preco_venda: float,
        tenant_id,
        preco_venda_atual=None,
    ) -> list[tuple[Produto, dict]]:
        valor_atual = (
            produto_componente.preco_venda
            if preco_venda_atual is None
            else preco_venda_atual
        )
        preco_unitario_atual = _moeda(valor_atual)
        preco_unitario_novo = _moeda(novo_preco_venda)
        diferenca_unitaria = preco_unitario_novo - preco_unitario_atual

        if diferenca_unitaria == 0:
            return []

        relacoes = (
            db.query(ProdutoKitComponente)
            .filter(
                ProdutoKitComponente.produto_componente_id == produto_componente.id,
                ProdutoKitComponente.tenant_id == tenant_id,
            )
            .all()
        )

        sugestoes: list[tuple[Produto, dict]] = []
        for relacao in relacoes:
            produto_composto = (
                db.query(Produto)
                .filter(
                    Produto.id == relacao.kit_id,
                    Produto.tenant_id == tenant_id,
                )
                .first()
            )
            if not KitCustoService.produto_usa_custo_por_componentes(produto_composto):
                continue

            quantidade = Decimal(str(relacao.quantidade or 0))
            if quantidade <= 0:
                continue

            preco_atual = _moeda(produto_composto.preco_venda)
            preco_sugerido = max(
                Decimal("0"), preco_atual + (diferenca_unitaria * quantidade)
            ).quantize(CENTAVO, rounding=ROUND_HALF_UP)

            if preco_sugerido == preco_atual:
                continue

            sugestoes.append(
                (
                    produto_composto,
                    {
                        "produto_id": produto_composto.id,
                        "sku": produto_composto.codigo,
                        "nome": produto_composto.nome,
                        "ativo": bool(produto_composto.ativo),
                        "quantidade_componente": float(quantidade),
                        "preco_venda_atual": float(preco_atual),
                        "preco_venda_sugerido": float(preco_sugerido),
                    },
                )
            )

        return sugestoes

    @staticmethod
    def listar_sugestoes(
        db: Session,
        produto_componente: Produto,
        novo_preco_venda: float,
        tenant_id,
    ) -> list[dict]:
        """Lista os compostos afetados, sem modificar o banco."""

        return [
            sugestao
            for _, sugestao in KitPrecoVendaService._montar_sugestoes(
                db, produto_componente, novo_preco_venda, tenant_id
            )
        ]

    @staticmethod
    def aplicar_sugestoes(
        db: Session,
        produto_componente: Produto,
        novo_preco_venda: float,
        produtos_compostos_ids: Iterable[int],
        tenant_id,
        preco_venda_atual=None,
    ) -> dict[int, Decimal]:
        """Aplica apenas os precos dos produtos compostos autorizados."""

        ids_selecionados = {int(produto_id) for produto_id in produtos_compostos_ids}
        if not ids_selecionados:
            return {}

        atualizados: dict[int, Decimal] = {}
        sugestoes = KitPrecoVendaService._montar_sugestoes(
            db,
            produto_componente,
            novo_preco_venda,
            tenant_id,
            preco_venda_atual=preco_venda_atual,
        )
        for produto_composto, sugestao in sugestoes:
            if produto_composto.id not in ids_selecionados:
                continue

            preco_sugerido = _moeda(sugestao["preco_venda_sugerido"])
            produto_composto.preco_venda = float(preco_sugerido)
            produto_composto.updated_at = datetime.utcnow()
            atualizados[produto_composto.id] = preco_sugerido

        return atualizados
