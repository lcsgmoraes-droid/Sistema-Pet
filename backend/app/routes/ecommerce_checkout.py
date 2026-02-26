from uuid import UUID
from datetime import datetime, timedelta
import hashlib
import json
import random

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.idempotency_models import IdempotencyKey
from app.pedido_models import Pedido, PedidoItem


router = APIRouter(prefix="/checkout", tags=["ecommerce-checkout"])
security = HTTPBearer()

RESERVA_EXPIRACAO_CARRINHO_MINUTOS = 30
RESERVA_EXPIRACAO_PENDENTE_MINUTOS = 60

# Palavras do mundo pet para código de retirada por terceiro
_PALAVRAS_PET = [
    "patinha", "focinho", "coleira", "bigodinho", "rabinho", "pelagem",
    "latido", "miado", "ronronar", "arranhado", "mordisco", "felpudo",
    "manchado", "listrado", "tigrao", "leaozinho", "pompom", "bolota",
    "amendoim", "biscoito", "caramelo", "chocolate", "baunilha", "canela",
    "malhado", "pintado", "bolinha", "fralda", "petisco", "ossinhos",
    "aquario", "gaiola", "gambito", "pinscher", "vira-lata", "siames",
    "labrador", "poodle", "bulldog", "dachshund", "beagle", "shih-tzu",
    "periquito", "calopsita", "hamster", "coelho", "porquinho", "tartaruga",
]


def _gerar_palavra_chave_retirada() -> str:
    """Gera código de retirada com 2 palavras do mundo pet, ex: 'patinha-bolota'"""
    return "-".join(random.sample(_PALAVRAS_PET, 2))


class EcommerceIdentity(BaseModel):
    user_id: int
    tenant_id: str


class CheckoutCalcularFreteRequest(BaseModel):
    cidade_destino: str = Field(min_length=2)


class CheckoutFinalizarRequest(BaseModel):
    cidade_destino: str = Field(min_length=2)
    endereco_entrega: str | None = None
    cupom: str | None = None
    tipo_retirada: str | None = None  # proprio, terceiro (usado quando delivery_mode=retirada)


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


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _frete_local_por_cidade(db: Session, tenant_id: str, cidade_destino: str) -> dict:
    cidade_loja_raw = None
    try:
        result = db.execute(
            text("""
                SELECT cidade
                FROM configuracoes_entrega
                WHERE tenant_id = :tenant_id
                LIMIT 1
            """),
            {"tenant_id": tenant_id},
        ).fetchone()
        if result:
            cidade_loja_raw = result[0]
    except Exception:
        cidade_loja_raw = None

    cidade_loja = _normalize_text(cidade_loja_raw)
    destino = _normalize_text(cidade_destino)

    if not destino:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cidade de destino obrigatória")

    if not cidade_loja:
        return {
            "disponivel": True,
            "valor_frete": 0.0,
            "prazo_estimado": "mesmo_dia",
            "tipo": "entrega_local",
            "cidade_loja": None,
            "cidade_destino": cidade_destino,
            "observacao": "Cidade da loja não configurada; aplicado frete local padrão",
        }

    if destino != cidade_loja:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entrega disponível apenas na cidade da loja",
        )

    return {
        "disponivel": True,
        "valor_frete": 0.0,
        "prazo_estimado": "mesmo_dia",
        "tipo": "entrega_local",
        "cidade_loja": cidade_loja_raw,
        "cidade_destino": cidade_destino,
        "observacao": "Entrega local da loja (sem integração logística)",
    }


def _buscar_carrinho(db: Session, identity: EcommerceIdentity) -> Pedido | None:
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    return (
        db.query(Pedido)
        .filter(
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
            Pedido.status == "carrinho",
        )
        .order_by(Pedido.id.desc())
        .first()
    )


def _buscar_itens(db: Session, pedido_id: str) -> list[PedidoItem]:
    return (
        db.query(PedidoItem)
        .filter(PedidoItem.pedido_id == pedido_id)
        .order_by(PedidoItem.id.asc())
        .all()
    )


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


def _request_hash(data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _calcular_desconto(subtotal: float, cupom: str | None) -> tuple[str | None, int, float]:
    if not cupom:
        return None, 0, 0.0

    codigo = cupom.strip().upper()
    descontos = {
        "MVP5": 5,
        "MVP10": 10,
    }
    percentual = descontos.get(codigo, 0)
    if percentual == 0:
        return codigo, 0, 0.0

    valor = round((subtotal * percentual) / 100.0, 2)
    return codigo, percentual, valor


@router.post("/calcular-frete")
def calcular_frete_local(
    payload: CheckoutCalcularFreteRequest,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    return _frete_local_por_cidade(db, identity.tenant_id, payload.cidade_destino)


@router.get("/resumo")
def resumo_checkout(
    cidade_destino: str = Query(..., min_length=2),
    cupom: str | None = Query(default=None),
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    carrinho = _buscar_carrinho(db, identity)
    if not carrinho:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    itens = _buscar_itens(db, carrinho.pedido_id)
    if not itens:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    subtotal = round(sum(float(item.subtotal or 0.0) for item in itens), 2)
    frete = _frete_local_por_cidade(db, identity.tenant_id, cidade_destino)
    cupom_codigo, cupom_percentual, desconto = _calcular_desconto(subtotal, cupom)
    total = round(max(subtotal - desconto, 0.0) + float(frete["valor_frete"]), 2)

    return {
        "pedido_id": carrinho.pedido_id,
        "itens_count": len(itens),
        "subtotal": subtotal,
        "frete": frete,
        "cupom": {
            "codigo": cupom_codigo,
            "percentual": cupom_percentual,
            "desconto": desconto,
        },
        "total": total,
    }


@router.post("/finalizar")
def finalizar_checkout(
    payload: CheckoutFinalizarRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    endpoint_name = "POST /api/checkout/finalizar"
    idem_key_value = idempotency_key or request.headers.get("Idempotency-Key")
    tenant_uuid = str(UUID(identity.tenant_id))
    request_data = {
        "user_id": identity.user_id,
        "tenant_id": tenant_uuid,
        "cidade_destino": payload.cidade_destino,
        "endereco_entrega": payload.endereco_entrega,
        "cupom": payload.cupom,
    }
    request_hash = _request_hash(request_data)
    idem_row = None

    if idem_key_value:
        idem_row = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.user_id == identity.user_id,
                IdempotencyKey.tenant_id == tenant_uuid,
                IdempotencyKey.endpoint == endpoint_name,
                IdempotencyKey.chave_idempotencia == idem_key_value,
            )
            .first()
        )

        if idem_row:
            if idem_row.request_hash != request_hash:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflito de idempotência")
            if idem_row.status == "completed" and idem_row.response_body:
                return json.loads(idem_row.response_body)
        else:
            idem_row = IdempotencyKey(
                user_id=identity.user_id,
                tenant_id=tenant_uuid,
                endpoint=endpoint_name,
                chave_idempotencia=idem_key_value,
                request_hash=request_hash,
                status="processing",
            )
            db.add(idem_row)
            db.flush()

    carrinho = _buscar_carrinho(db, identity)
    if not carrinho:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    itens = _buscar_itens(db, carrinho.pedido_id)
    if not itens:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    subtotal = round(sum(float(item.subtotal or 0.0) for item in itens), 2)
    frete = _frete_local_por_cidade(db, identity.tenant_id, payload.cidade_destino)
    cupom_codigo, cupom_percentual, desconto = _calcular_desconto(subtotal, payload.cupom)
    total = round(max(subtotal - desconto, 0.0) + float(frete["valor_frete"]), 2)

    carrinho.total = total
    carrinho.status = "pendente"

    # Tipo de retirada e palavra-chave para terceiro retirar
    tipo_retirada = payload.tipo_retirada  # 'proprio' | 'terceiro' | None
    palavra_chave = None
    if tipo_retirada == "terceiro":
        palavra_chave = _gerar_palavra_chave_retirada()
    carrinho.tipo_retirada = tipo_retirada
    carrinho.palavra_chave_retirada = palavra_chave

    response = {
        "status": "pedido_finalizado",
        "pedido_id": carrinho.pedido_id,
        "pedido_status": carrinho.status,
        "subtotal": subtotal,
        "frete": frete,
        "cupom": {
            "codigo": cupom_codigo,
            "percentual": cupom_percentual,
            "desconto": desconto,
        },
        "total": total,
        "endereco_entrega": payload.endereco_entrega,
        "tipo_retirada": tipo_retirada,
        "palavra_chave_retirada": palavra_chave,
    }

    if idem_row:
        idem_row.status = "completed"
        idem_row.response_status_code = 200
        idem_row.response_body = json.dumps(response, ensure_ascii=False)
        idem_row.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(carrinho)

    return response


@router.get("/pedidos")
def listar_pedidos_cliente(
    limit: int = Query(default=20, ge=1, le=100),
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    """Lista todos os pedidos finalizados do cliente logado (exclui carrinho ativo)."""
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
            Pedido.status != "carrinho",
        )
        .order_by(Pedido.id.desc())
        .limit(limit)
        .all()
    )

    resultado = []
    for pedido in pedidos:
        itens = _buscar_itens(db, pedido.pedido_id)
        resultado.append({
            "pedido_id": pedido.pedido_id,
            "status": pedido.status,
            "total": float(pedido.total or 0.0),
            "tipo_retirada": pedido.tipo_retirada,
            "palavra_chave_retirada": pedido.palavra_chave_retirada,
            "created_at": pedido.created_at.isoformat() if pedido.created_at else None,
            "itens": [
                {
                    "produto_id": item.produto_id,
                    "nome": item.nome,
                    "quantidade": item.quantidade,
                    "preco_unitario": float(item.preco_unitario or 0.0),
                    "subtotal": float(item.subtotal or 0.0),
                }
                for item in itens
            ],
        })

    return {"pedidos": resultado}


@router.get("/pedido/{pedido_id}/status")
def consultar_status_pedido(
    pedido_id: str,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    return {
        "pedido_id": pedido.pedido_id,
        "status": pedido.status,
        "total": float(pedido.total or 0.0),
        "created_at": pedido.created_at,
    }


@router.post("/pedido/{pedido_id}/cancelar")
def cancelar_pedido(
    pedido_id: str,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    if pedido.status not in ("carrinho", "pendente"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pedido não pode ser cancelado")

    pedido.status = "cancelado"
    db.commit()

    return {
        "pedido_id": pedido.pedido_id,
        "status": pedido.status,
        "message": "Pedido cancelado com sucesso",
    }