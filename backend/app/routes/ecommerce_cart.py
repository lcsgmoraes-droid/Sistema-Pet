from uuid import UUID, uuid4
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.pedido_models import Pedido, PedidoItem
from app.produtos_models import Produto


router = APIRouter(prefix="/carrinho", tags=["ecommerce-cart"])
security = HTTPBearer()

RESERVA_EXPIRACAO_CARRINHO_MINUTOS = 30
RESERVA_EXPIRACAO_PENDENTE_MINUTOS = 60
STATUS_RESERVA_ATIVA = ("carrinho", "pendente")


class CarrinhoAdicionarRequest(BaseModel):
    produto_id: int
    quantidade: int = Field(default=1, ge=1)


class CarrinhoAtualizarRequest(BaseModel):
    quantidade: int = Field(ge=1)


class CarrinhoCupomRequest(BaseModel):
    codigo: str = Field(min_length=1)


class EcommerceIdentity(BaseModel):
    user_id: int
    tenant_id: str


def _current_identity(credentials: HTTPAuthorizationCredentials = Depends(security)) -> EcommerceIdentity:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        token_type = payload.get("token_type")
        tenant_id = str(UUID(str(payload.get("tenant_id"))))
        if token_type != "ecommerce_customer":
            raise credentials_exception
    except (JWTError, TypeError, ValueError):
        raise credentials_exception

    return EcommerceIdentity(user_id=user_id, tenant_id=tenant_id)


def _find_or_create_carrinho(db: Session, identity: EcommerceIdentity) -> Pedido:
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    carrinho = (
        db.query(Pedido)
        .filter(
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
            Pedido.status == "carrinho",
        )
        .order_by(Pedido.id.desc())
        .first()
    )

    if carrinho:
        return carrinho

    carrinho = Pedido(
        pedido_id=str(uuid4()),
        cliente_id=identity.user_id,
        tenant_id=identity.tenant_id,
        total=0.0,
        origem="web",
        status="carrinho",
    )
    db.add(carrinho)
    db.flush()
    return carrinho


def _expirar_reservas_automaticamente(db: Session, tenant_id: str) -> None:
    agora = datetime.utcnow()
    limite_carrinho = agora - timedelta(minutes=RESERVA_EXPIRACAO_CARRINHO_MINUTOS)
    limite_pendente = agora - timedelta(minutes=RESERVA_EXPIRACAO_PENDENTE_MINUTOS)

    carrinhos_expirados = (
        db.query(Pedido)
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.status == "carrinho",
            Pedido.created_at < limite_carrinho,
        )
        .all()
    )
    for pedido in carrinhos_expirados:
        pedido.status = "expirado"

    pendentes_expirados = (
        db.query(Pedido)
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.status == "pendente",
            Pedido.created_at < limite_pendente,
        )
        .all()
    )
    for pedido in pendentes_expirados:
        pedido.status = "cancelado"

    if carrinhos_expirados or pendentes_expirados:
        db.flush()


def _quantidade_reservada_produto(
    db: Session,
    *,
    tenant_id: str,
    produto_id: int,
    excluir_pedido_id: str | None = None,
) -> float:
    query = (
        db.query(func.coalesce(func.sum(PedidoItem.quantidade), 0.0))
        .join(Pedido, Pedido.pedido_id == PedidoItem.pedido_id)
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.status.in_(STATUS_RESERVA_ATIVA),
            PedidoItem.produto_id == produto_id,
        )
    )

    if excluir_pedido_id:
        query = query.filter(Pedido.pedido_id != excluir_pedido_id)

    return float(query.scalar() or 0.0)


def _recalcular_total(db: Session, carrinho: Pedido) -> float:
    itens = db.query(PedidoItem).filter(PedidoItem.pedido_id == carrinho.pedido_id).all()
    total = round(sum((item.subtotal or 0.0) for item in itens), 2)
    carrinho.total = total
    return total


def _serialize_carrinho(db: Session, carrinho: Pedido) -> dict:
    itens = (
        db.query(PedidoItem)
        .filter(PedidoItem.pedido_id == carrinho.pedido_id)
        .order_by(PedidoItem.id.asc())
        .all()
    )

    subtotal = round(sum((item.subtotal or 0.0) for item in itens), 2)
    return {
        "pedido_id": carrinho.pedido_id,
        "itens": [
            {
                "item_id": item.id,
                "produto_id": item.produto_id,
                "nome": item.nome,
                "quantidade": item.quantidade,
                "preco_unitario": item.preco_unitario,
                "subtotal": item.subtotal,
            }
            for item in itens
        ],
        "subtotal": subtotal,
        "total": subtotal,
    }


def _resolver_preco_unitario(produto: Produto) -> float:
    if produto.promocao_ativa and produto.preco_promocional is not None:
        return float(produto.preco_promocional)
    return float(produto.preco_venda or 0.0)


@router.post("/adicionar")
def adicionar_item_carrinho(
    payload: CarrinhoAdicionarRequest,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == payload.produto_id,
            Produto.tenant_id == identity.tenant_id,
            Produto.situacao.is_not(False),  # aceita True e NULL (produtos importados)
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")

    if getattr(produto, "is_sellable", True) is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Produto não vendável")

    estoque_ecommerce = float(produto.estoque_ecommerce or 0.0)
    if estoque_ecommerce > 0 and payload.quantidade > estoque_ecommerce:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantidade indisponível em estoque")

    carrinho = _find_or_create_carrinho(db, identity)

    item = (
        db.query(PedidoItem)
        .filter(
            PedidoItem.pedido_id == carrinho.pedido_id,
            PedidoItem.produto_id == payload.produto_id,
            PedidoItem.tenant_id == identity.tenant_id,
        )
        .first()
    )

    preco_unitario = _resolver_preco_unitario(produto)

    nova_quantidade = payload.quantidade
    if item:
        nova_quantidade = item.quantidade + payload.quantidade

    reservado_outros = _quantidade_reservada_produto(
        db,
        tenant_id=identity.tenant_id,
        produto_id=produto.id,
        excluir_pedido_id=carrinho.pedido_id,
    )
    disponivel_para_carrinho = max(estoque_ecommerce - reservado_outros, 0.0)

    if estoque_ecommerce > 0 and float(nova_quantidade) > disponivel_para_carrinho:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantidade indisponível em estoque (reserva ativa)",
        )

    if item:
        item.quantidade = nova_quantidade
        item.subtotal = round(item.quantidade * item.preco_unitario, 2)
    else:
        item = PedidoItem(
            pedido_id=carrinho.pedido_id,
            produto_id=produto.id,
            nome=produto.nome,
            quantidade=payload.quantidade,
            preco_unitario=preco_unitario,
            subtotal=round(payload.quantidade * preco_unitario, 2),
            tenant_id=identity.tenant_id,
        )
        db.add(item)

    _recalcular_total(db, carrinho)
    db.commit()

    return _serialize_carrinho(db, carrinho)


@router.put("/atualizar/{item_id}")
def atualizar_item_carrinho(
    item_id: int,
    payload: CarrinhoAtualizarRequest,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    carrinho = _find_or_create_carrinho(db, identity)

    item = (
        db.query(PedidoItem)
        .filter(
            PedidoItem.id == item_id,
            PedidoItem.pedido_id == carrinho.pedido_id,
            PedidoItem.tenant_id == identity.tenant_id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item do carrinho não encontrado")

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == item.produto_id,
            Produto.tenant_id == identity.tenant_id,
            Produto.situacao.is_(True),
        )
        .first()
    )
    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")

    estoque_ecommerce = float(produto.estoque_ecommerce or 0.0)
    reservado_outros = _quantidade_reservada_produto(
        db,
        tenant_id=identity.tenant_id,
        produto_id=item.produto_id,
        excluir_pedido_id=carrinho.pedido_id,
    )
    disponivel_para_carrinho = max(estoque_ecommerce - reservado_outros, 0.0)

    if estoque_ecommerce > 0 and float(payload.quantidade) > disponivel_para_carrinho:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantidade indisponível em estoque (reserva ativa)",
        )

    item.quantidade = payload.quantidade
    item.subtotal = round(item.quantidade * item.preco_unitario, 2)

    _recalcular_total(db, carrinho)
    db.commit()

    return _serialize_carrinho(db, carrinho)


@router.delete("/remover/{item_id}")
def remover_item_carrinho(
    item_id: int,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    carrinho = _find_or_create_carrinho(db, identity)

    item = (
        db.query(PedidoItem)
        .filter(
            PedidoItem.id == item_id,
            PedidoItem.pedido_id == carrinho.pedido_id,
            PedidoItem.tenant_id == identity.tenant_id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item do carrinho não encontrado")

    db.delete(item)
    _recalcular_total(db, carrinho)
    db.commit()

    return _serialize_carrinho(db, carrinho)


@router.get("")
def obter_carrinho(
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    carrinho = (
        db.query(Pedido)
        .filter(
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
            Pedido.status == "carrinho",
        )
        .order_by(Pedido.id.desc())
        .first()
    )

    if not carrinho:
        return {
            "pedido_id": None,
            "itens": [],
            "subtotal": 0.0,
            "total": 0.0,
        }

    return _serialize_carrinho(db, carrinho)


@router.post("/aplicar-cupom")
def aplicar_cupom(
    payload: CarrinhoCupomRequest,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    carrinho = (
        db.query(Pedido)
        .filter(
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
            Pedido.status == "carrinho",
        )
        .order_by(Pedido.id.desc())
        .first()
    )

    if not carrinho:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    itens_count = db.query(PedidoItem).filter(PedidoItem.pedido_id == carrinho.pedido_id).count()
    if itens_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    cupom = payload.codigo.strip().upper()
    descontos = {
        "MVP5": 5,
        "MVP10": 10,
    }

    percentual = descontos.get(cupom)
    if not percentual:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cupom inválido")

    subtotal = round(float(carrinho.total or 0.0), 2)
    desconto = round((subtotal * percentual) / 100.0, 2)
    total_com_desconto = round(max(subtotal - desconto, 0.0), 2)

    return {
        "codigo": cupom,
        "percentual": percentual,
        "subtotal": subtotal,
        "desconto": desconto,
        "total": total_com_desconto,
        "message": "Cupom aplicado para este cálculo do carrinho",
    }