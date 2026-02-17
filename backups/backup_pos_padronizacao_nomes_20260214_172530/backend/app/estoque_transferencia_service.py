
from sqlalchemy.orm import Session
from datetime import datetime

from app.estoque_local_models import EstoqueLocal
from app.local_estoque_models import LocalEstoque

class EstoqueTransferenciaService:
    """
    Serviço de transferência de estoque entre locais.
    """

    @staticmethod
    def transferir(
        db: Session,
        sku: str,
        local_origem_id: str,
        local_destino_id: str,
        quantidade: int,
        documento: str = None,
        observacao: str = None
    ):
        if quantidade <= 0:
            raise ValueError("Quantidade inválida")

        if local_origem_id == local_destino_id:
            raise ValueError("Origem e destino não podem ser iguais")

        origem = db.query(EstoqueLocal).filter(
            EstoqueLocal.sku == sku,
            EstoqueLocal.local_estoque_id == local_origem_id
        ).first()

        if not origem or origem.quantidade < quantidade:
            raise ValueError("Estoque insuficiente no local de origem")

        destino = db.query(EstoqueLocal).filter(
            EstoqueLocal.sku == sku,
            EstoqueLocal.local_estoque_id == local_destino_id
        ).first()

        # Debita origem
        origem.quantidade -= quantidade
        db.add(origem)

        # Credita destino
        if destino:
            destino.quantidade += quantidade
        else:
            destino = EstoqueLocal(
                sku=sku,
                local_estoque_id=local_destino_id,
                quantidade=quantidade
            )
        db.add(destino)

        db.commit()

        return {
            "sku": sku,
            "quantidade": quantidade,
            "origem": local_origem_id,
            "destino": local_destino_id,
            "documento": documento,
            "observacao": observacao,
            "data": datetime.utcnow()
        }
