from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.produtos_models import Produto, ProdutoKitComponente


class EstoqueReservaService:
    """
    Servico central de reserva de estoque.
    Trabalha pela intencao de venda do pedido integrado e projeta a reserva
    no produto correto. Para KIT VIRTUAL, a reserva recai nos componentes.
    """

    @staticmethod
    def _skus_produto(produto: Produto) -> list[str]:
        skus = []
        for valor in (produto.codigo, produto.codigo_barras):
            texto = (valor or "").strip()
            if texto and texto not in skus:
                skus.append(texto)
        return skus

    @staticmethod
    def _usa_composicao_virtual(produto: Produto | None) -> bool:
        return bool(
            produto
            and produto.tipo_kit == "VIRTUAL"
            and produto.tipo_produto in ("KIT", "VARIACAO")
        )

    @staticmethod
    def _itens_reservados_ativos(db: Session, tenant_id):
        return (
            db.query(PedidoIntegradoItem)
            .filter(
                PedidoIntegradoItem.tenant_id == tenant_id,
                PedidoIntegradoItem.liberado_em.is_(None),
                PedidoIntegradoItem.vendido_em.is_(None),
            )
            .all()
        )

    @staticmethod
    def _produtos_por_sku(db: Session, tenant_id, skus: list[str]) -> dict[str, Produto]:
        skus_limpos = [str(sku or "").strip() for sku in skus if str(sku or "").strip()]
        if not skus_limpos:
            return {}

        produtos = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                or_(Produto.codigo.in_(skus_limpos), Produto.codigo_barras.in_(skus_limpos)),
            )
            .all()
        )

        mapa: dict[str, Produto] = {}
        for produto in produtos:
            for sku in EstoqueReservaService._skus_produto(produto):
                mapa.setdefault(sku, produto)
        return mapa

    @staticmethod
    def _componentes_por_kit(db: Session, kit_ids: list[int]) -> dict[int, list[ProdutoKitComponente]]:
        ids = [int(kit_id) for kit_id in kit_ids if kit_id]
        if not ids:
            return {}

        componentes = (
            db.query(ProdutoKitComponente)
            .filter(ProdutoKitComponente.kit_id.in_(ids))
            .all()
        )

        mapa: dict[int, list[ProdutoKitComponente]] = defaultdict(list)
        for componente in componentes:
            mapa[int(componente.kit_id)].append(componente)
        return dict(mapa)

    @staticmethod
    def _quantidade_reservada(db: Session, tenant_id, skus: list[str]):
        if not skus:
            return 0

        return (
            db.query(func.coalesce(func.sum(PedidoIntegradoItem.quantidade), 0))
            .filter(
                PedidoIntegradoItem.tenant_id == tenant_id,
                PedidoIntegradoItem.sku.in_(skus),
                PedidoIntegradoItem.liberado_em.is_(None),
                PedidoIntegradoItem.vendido_em.is_(None),
            )
            .scalar()
        )

    @staticmethod
    def mapa_reservas_ativas_por_produto(db: Session, tenant_id) -> dict[int, float]:
        itens_ativos = EstoqueReservaService._itens_reservados_ativos(db, tenant_id)
        if not itens_ativos:
            return {}

        skus = list(
            dict.fromkeys(
                str(item.sku or "").strip()
                for item in itens_ativos
                if str(item.sku or "").strip()
            )
        )
        produtos_por_sku = EstoqueReservaService._produtos_por_sku(db, tenant_id, skus)
        kit_ids = list(
            dict.fromkeys(
                int(produto.id)
                for produto in produtos_por_sku.values()
                if getattr(produto, "id", None) and EstoqueReservaService._usa_composicao_virtual(produto)
            )
        )
        componentes_por_kit = EstoqueReservaService._componentes_por_kit(db, kit_ids)

        reservas: dict[int, float] = defaultdict(float)

        for item in itens_ativos:
            sku = str(item.sku or "").strip()
            if not sku:
                continue

            produto = produtos_por_sku.get(sku)
            if not produto or not getattr(produto, "id", None):
                continue

            quantidade_item = float(item.quantidade or 0)
            if quantidade_item <= 0:
                continue

            if EstoqueReservaService._usa_composicao_virtual(produto):
                for componente in componentes_por_kit.get(int(produto.id), []):
                    if not componente.produto_componente_id:
                        continue
                    reservas[int(componente.produto_componente_id)] += quantidade_item * float(componente.quantidade or 0)
                continue

            reservas[int(produto.id)] += quantidade_item

        return dict(reservas)

    @staticmethod
    def quantidade_reservada_produto(db: Session, tenant_id, produto: Produto | None) -> float:
        if not produto or not getattr(produto, "id", None):
            return 0.0
        return float(
            EstoqueReservaService.mapa_reservas_ativas_por_produto(db, tenant_id).get(int(produto.id), 0.0)
        )

    @staticmethod
    def reservar(db: Session, item: PedidoIntegradoItem):
        produto = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == item.tenant_id,
                or_(Produto.codigo == item.sku, Produto.codigo_barras == item.sku),
            )
            .first()
        )

        if not produto:
            raise ValueError(f"Produto com SKU {item.sku} nao encontrado")

        reservas_ativas = EstoqueReservaService.mapa_reservas_ativas_por_produto(db, item.tenant_id)

        if EstoqueReservaService._usa_composicao_virtual(produto):
            componentes = EstoqueReservaService._componentes_por_kit(db, [int(produto.id)]).get(int(produto.id), [])
            if not componentes:
                import logging

                logging.getLogger(__name__).warning(
                    f"[RESERVA] Kit virtual {produto.nome} ({item.sku}) sem componentes cadastrados. "
                    f"Item registrado sem cobertura."
                )
                return False

            for componente in componentes:
                produto_componente = (
                    db.query(Produto)
                    .filter(
                        Produto.tenant_id == item.tenant_id,
                        Produto.id == componente.produto_componente_id,
                    )
                    .first()
                )
                if not produto_componente:
                    raise ValueError(
                        f"Componente ID {componente.produto_componente_id} do kit {produto.nome} nao encontrado"
                    )

                reservado = float(reservas_ativas.get(int(produto_componente.id), 0.0))
                necessario = float(item.quantidade or 0) * float(componente.quantidade or 0)
                disponivel = float(produto_componente.estoque_atual or 0) - reservado

                if disponivel < necessario:
                    import logging

                    logging.getLogger(__name__).warning(
                        f"[RESERVA] Estoque insuficiente para componente {produto_componente.codigo or produto_componente.nome} "
                        f"do kit virtual {produto.nome}. Disponivel: {disponivel}, solicitado: {necessario}. "
                        f"Item registrado mesmo assim."
                    )
                    return False

            return True

        reservado = float(reservas_ativas.get(int(produto.id), 0.0))
        disponivel = float(produto.estoque_atual or 0) - reservado

        if disponivel < float(item.quantidade or 0):
            import logging

            logging.getLogger(__name__).warning(
                f"[RESERVA] Estoque insuficiente para SKU {item.sku}. "
                f"Disponivel: {disponivel}, solicitado: {item.quantidade}. "
                f"Item registrado mesmo assim."
            )
            return False

        return True

    @staticmethod
    def liberar(db: Session, item: PedidoIntegradoItem):
        item.liberado_em = datetime.utcnow()
        db.add(item)
        db.commit()

    @staticmethod
    def confirmar_venda(db: Session, item: PedidoIntegradoItem):
        item.vendido_em = datetime.utcnow()
        db.add(item)
        db.commit()
