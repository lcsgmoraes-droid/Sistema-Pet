"""
Rotas para integração com Stone
Endpoints para processar pagamentos PIX e Cartão via Stone
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
import logging
import uuid

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .stone_api_client import StoneAPIClient
from .stone_conciliation_client import StoneConciliationClient
from .stone_models import StoneTransaction, StoneTransactionLog, StoneConfig
from .financeiro_models import ContaReceber, FormaPagamento
from .vendas_models import Venda, VendaPagamento
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, func as sa_func


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stone", tags=["Stone Payments"])

_MSG_TRANSACAO_NAO_ENCONTRADA = "Transação não encontrada"


# ==========================================
# SCHEMAS PYDANTIC
# ==========================================

class StoneConfigSchema(BaseModel):
    """Schema para configuração Stone"""
    client_id: str
    client_secret: Optional[str] = ""
    merchant_id: Optional[str] = None
    webhook_secret: Optional[str] = None
    sandbox: bool = False
    enable_pix: bool = True
    enable_credit_card: bool = True
    enable_debit_card: bool = False
    max_installments: int = 12
    webhook_url: Optional[str] = None
    pos_serial_number: Optional[str] = None


class CreatePixPaymentSchema(BaseModel):
    """Schema para criar pagamento PIX"""
    amount: Decimal = Field(..., gt=0, description="Valor em reais")
    description: str = Field(..., min_length=1, max_length=500)
    external_id: str = Field(..., description="ID único do seu sistema")
    customer_name: Optional[str] = None
    customer_document: Optional[str] = None
    customer_email: Optional[str] = None
    expiration_minutes: int = Field(default=30, ge=5, le=1440)
    venda_id: Optional[int] = None
    conta_receber_id: Optional[int] = None


class CreateCardPaymentSchema(BaseModel):
    """Schema para criar pagamento com cartão"""
    amount: Decimal = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    external_id: str
    card_number: str = Field(..., min_length=13, max_length=19)
    card_holder_name: str
    card_expiration_date: str = Field(..., pattern=r"^\d{2}/\d{2}$")  # MM/YY
    card_cvv: str = Field(..., min_length=3, max_length=4)
    installments: int = Field(default=1, ge=1, le=12)
    customer_name: Optional[str] = None
    customer_document: Optional[str] = None
    customer_email: Optional[str] = None
    venda_id: Optional[int] = None
    conta_receber_id: Optional[int] = None


class CancelPaymentSchema(BaseModel):
    """Schema para cancelar pagamento"""
    reason: Optional[str] = None


class RefundPaymentSchema(BaseModel):
    """Schema para estornar pagamento"""
    amount: Optional[Decimal] = Field(None, gt=0, description="Valor a estornar (null = total)")
    reason: Optional[str] = None


class CriarPedidoPosSchema(BaseModel):
    """Schema para criar pedido na maquininha (POS)"""
    serial_number: Optional[str] = Field(None, description="Número de série da maquininha Stone (usa padrão da config se omitido)")
    items: List[Dict] = Field(..., description="Itens: [{amount (centavos), description, quantity, code}]")
    customer_name: str = Field(default="Cliente")
    customer_email: Optional[str] = None
    customer_document: Optional[str] = None
    payment_type: Optional[str] = Field(None, description="debit | credit | pix | None (cliente escolhe)")
    installments: int = Field(default=1, ge=1, le=12)
    venda_id: Optional[int] = None
    external_id: Optional[str] = None


class CriarPedidoPosVendaSchema(BaseModel):
    """Schema para enviar uma venda ja criada para a maquininha Stone."""
    serial_number: Optional[str] = Field(None, description="Numero de serie da maquininha Stone")
    payment_type: Optional[str] = Field(None, description="credit | debit | pix | cartao_credito | cartao_debito")
    installments: int = Field(default=1, ge=1, le=12)


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def get_stone_client(db: Session, tenant_id) -> StoneAPIClient:
    """Obtém cliente Stone configurado para o tenant"""
    config = db.query(StoneConfig).filter(
        StoneConfig.tenant_id == tenant_id,
        StoneConfig.active == True
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuração Stone não encontrada. Configure primeiro em /api/stone/config"
        )

    return StoneAPIClient(secret_key=config.client_id)


def get_stone_client_and_config(db: Session, tenant_id):
    """Obtém cliente Stone e o registro de config para o tenant"""
    config = db.query(StoneConfig).filter(
        StoneConfig.tenant_id == tenant_id,
        StoneConfig.active == True
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuração Stone não encontrada. Configure primeiro em /api/stone/config"
        )

    return StoneAPIClient(secret_key=config.client_id), config


def _somente_digitos(valor: Any) -> str:
    return "".join(c for c in str(valor or "") if c.isdigit())


def _decimal_monetario(valor: Any) -> Decimal:
    try:
        return Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _moeda_para_centavos(valor: Any) -> int:
    return int((_decimal_monetario(valor) * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))


def _formatar_quantidade_pos(valor: Any) -> str:
    try:
        quantidade = Decimal(str(valor or 1))
        if quantidade == quantidade.to_integral_value():
            return str(int(quantidade))
        return format(quantidade.normalize(), "f").rstrip("0").rstrip(".")
    except Exception:
        return "1"


def _montar_payment_setup_pos(payment_type: Optional[str], installments: int = 1) -> Optional[Dict[str, Any]]:
    if not payment_type:
        return None

    tipo = str(payment_type).strip().lower()
    mapa = {
        "credit": "credit",
        "credito": "credit",
        "cartao_credito": "credit",
        "cartao-credito": "credit",
        "debit": "debit",
        "debito": "debit",
        "cartao_debito": "debit",
        "cartao-debito": "debit",
        "pix": "pix",
    }
    tipo_stone = mapa.get(tipo)
    if not tipo_stone:
        raise ValueError("Tipo de pagamento Stone POS invalido")

    payment_setup = {"type": tipo_stone}
    if tipo_stone == "credit":
        parcelas = max(1, int(installments or 1))
        payment_setup.update({
            "installments": parcelas,
            "installment_type": "merchant",
        })
    return payment_setup


def _total_itens_pos_reais(items: List[Dict]) -> Decimal:
    total_centavos = Decimal("0")
    for item in items or []:
        amount = Decimal(str(item.get("amount") or 0))
        quantidade = Decimal(str(item.get("quantity") or 1))
        total_centavos += amount * quantidade
    return (total_centavos / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _montar_pedido_pos_da_venda(
    venda: Venda,
    *,
    payment_type: Optional[str] = None,
    installments: int = 1,
) -> Dict[str, Any]:
    items = []
    for item in venda.itens or []:
        quantidade_txt = _formatar_quantidade_pos(getattr(item, "quantidade", 1))
        produto = getattr(item, "produto", None)
        nome = (
            getattr(produto, "nome", None)
            or getattr(item, "servico_descricao", None)
            or f"Item {getattr(item, 'id', '')}".strip()
        )
        subtotal = getattr(item, "subtotal", None)
        if subtotal is None:
            subtotal = _decimal_monetario(getattr(item, "preco_unitario", 0)) * Decimal(str(getattr(item, "quantidade", 1) or 1))

        amount = _moeda_para_centavos(subtotal)
        if amount <= 0:
            continue

        codigo = (
            getattr(produto, "codigo", None)
            or getattr(item, "produto_id", None)
            or getattr(item, "id", None)
            or len(items) + 1
        )
        items.append({
            "amount": amount,
            "description": f"{str(nome)[:80]} x{quantidade_txt}",
            "quantity": 1,
            "code": str(codigo),
        })

    if not items:
        raise ValueError("A venda nao possui itens com valor para enviar ao POS")

    cliente = getattr(venda, "cliente", None)
    documento = _somente_digitos(getattr(cliente, "cnpj", None) or getattr(cliente, "cpf", None))
    customer = {
        "name": getattr(cliente, "nome", None) or "Cliente",
        "type": "company" if len(documento) == 14 else "individual",
    }
    email = getattr(cliente, "email", None)
    if email:
        customer["email"] = email
    if documento:
        customer["document"] = documento

    return {
        "items": items,
        "customer": customer,
        "amount": _total_itens_pos_reais(items),
        "display_name": f"Venda {getattr(venda, 'numero_venda', None) or venda.id}",
        "payment_setup": _montar_payment_setup_pos(payment_type, installments),
    }


# ==========================================
# PEDIDO POS (MAQUININHA)
# ==========================================

@router.post("/pedido-pos")
async def criar_pedido_pos(
    pedido: CriarPedidoPosSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Cria um pedido na maquininha Stone (POS).

    O pedido aparece na tela da maquininha para o cliente pagar.
    Após o pagamento, a Stone envia webhook charge.paid e o pedido é fechado automaticamente.

    - payment_type = None → cliente escolhe na maquininha (fluxo Listagem)
    - payment_type = debit/credit/pix → tipo definido pelo sistema (fluxo Direto)
    """
    user, tenant_id = auth
    tenant_id_str = str(tenant_id)

    stone_client, stone_config = get_stone_client_and_config(db, tenant_id_str)

    # Serial number: usa o do pedido, ou o salvo na config como padrão
    serial_number = pedido.serial_number or (stone_config.pos_serial_number or "")
    if not serial_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o número de série da maquininha (serial_number) ou configure-o em /api/stone/config"
        )

    external_id = pedido.external_id or f"VENDA-{pedido.venda_id or uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:6]}"

    customer = {
        "name": pedido.customer_name,
        "type": "individual",
    }
    if pedido.customer_email:
        customer["email"] = pedido.customer_email
    if pedido.customer_document:
        customer["document"] = pedido.customer_document.replace(".", "").replace("-", "").replace("/", "")

    try:
        payment_setup = _montar_payment_setup_pos(pedido.payment_type, pedido.installments)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        stone_response = await stone_client.criar_pedido_pos(
            items=pedido.items,
            customer=customer,
            serial_number=serial_number,
            payment_setup=payment_setup,
            metadata={"external_id": external_id, "venda_id": pedido.venda_id, "display_name": f"Pedido #{pedido.venda_id or external_id[:8]}"},
        )

        amount_reais = _total_itens_pos_reais(pedido.items)

        transaction = StoneTransaction(
            stone_payment_id=stone_response["id"],
            external_id=external_id,
            venda_id=pedido.venda_id,
            payment_method=pedido.payment_type or "pos",
            amount=amount_reais,
            description=f"Pedido POS - {len(pedido.items)} item(ns)",
            installments=pedido.installments,
            status="pending",
            stone_status=stone_response.get("status"),
            customer_name=pedido.customer_name,
            customer_document=pedido.customer_document,
            customer_email=pedido.customer_email,
            stone_response=stone_response,
            tenant_id=tenant_id_str,
            user_id=user.id,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type="pedido_pos_criado",
            event_source="sistema",
            description="Pedido POS criado na maquininha configurada",
            new_status="pending",
            user_id=user.id,
            tenant_id=tenant_id_str,
        )

        logger.info("Pedido POS criado: order_id=%s", stone_response["id"])

        return {
            "success": True,
            "message": "Pedido enviado para a maquininha",
            "order_id": stone_response["id"],
            "transaction_id": transaction.id,
            "status": stone_response.get("status"),
        }

    except Exception as e:
        logger.error(f"Erro ao criar pedido POS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar pedido POS: {str(e)}")


@router.post("/pedido-pos/venda/{venda_id}")
async def criar_pedido_pos_da_venda(
    venda_id: int,
    pedido: CriarPedidoPosVendaSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Envia uma venda aberta do PDV para a maquininha Stone.

    A venda continua aberta ate o webhook charge.paid confirmar o pagamento.
    """
    user, tenant_id = auth
    tenant_id_str = str(tenant_id)

    venda = db.query(Venda).filter(
        Venda.id == venda_id,
        Venda.tenant_id == tenant_id_str,
    ).first()
    if not venda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venda nao encontrada")

    if venda.status not in ("aberta", "baixa_parcial"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Apenas vendas abertas ou com baixa parcial podem ser enviadas ao POS (status atual: {venda.status})",
        )

    transaction_pendente = db.query(StoneTransaction).filter(
        StoneTransaction.tenant_id == tenant_id_str,
        StoneTransaction.venda_id == venda.id,
        StoneTransaction.status == "pending",
    ).order_by(StoneTransaction.created_at.desc()).first()
    if transaction_pendente:
        return {
            "success": True,
            "message": "Ja existe um pedido Stone aguardando pagamento para esta venda",
            "order_id": transaction_pendente.stone_payment_id,
            "transaction_id": transaction_pendente.id,
            "status": transaction_pendente.status,
            "reused": True,
        }

    stone_client, stone_config = get_stone_client_and_config(db, tenant_id_str)

    serial_number = pedido.serial_number or (stone_config.pos_serial_number or "")
    if not serial_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o numero de serie da maquininha ou configure o POS padrao em Stone Connect",
        )

    try:
        payload_pos = _montar_pedido_pos_da_venda(
            venda,
            payment_type=pedido.payment_type,
            installments=pedido.installments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    external_id = f"VENDA-{venda.numero_venda or venda.id}-{uuid.uuid4().hex[:6]}"
    metadata = {
        "external_id": external_id,
        "venda_id": venda.id,
        "numero_venda": venda.numero_venda,
        "display_name": payload_pos["display_name"],
    }

    try:
        stone_response = await stone_client.criar_pedido_pos(
            items=payload_pos["items"],
            customer=payload_pos["customer"],
            serial_number=serial_number,
            payment_setup=payload_pos["payment_setup"],
            metadata=metadata,
        )

        transaction = StoneTransaction(
            stone_payment_id=stone_response["id"],
            external_id=external_id,
            venda_id=venda.id,
            payment_method=(payload_pos["payment_setup"] or {}).get("type") or "pos",
            amount=payload_pos["amount"],
            description=f"Pedido POS - venda {venda.numero_venda}",
            installments=pedido.installments,
            status="pending",
            stone_status=stone_response.get("status"),
            customer_name=payload_pos["customer"].get("name"),
            customer_document=payload_pos["customer"].get("document"),
            customer_email=payload_pos["customer"].get("email"),
            stone_response=stone_response,
            tenant_id=tenant_id_str,
            user_id=user.id,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type="pedido_pos_criado",
            event_source="pdv",
            description=f"Venda {venda.numero_venda} enviada para POS configurado",
            new_status="pending",
            user_id=user.id,
            tenant_id=tenant_id_str,
        )

        return {
            "success": True,
            "message": "Venda enviada para a maquininha",
            "order_id": stone_response["id"],
            "transaction_id": transaction.id,
            "status": stone_response.get("status") or "pending",
            "reused": False,
        }
    except Exception as e:
        logger.error(f"Erro ao enviar venda {venda.id} para POS Stone: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar venda para Stone POS: {str(e)}")


@router.post("/pedido-pos/{order_id}/fechar")
async def fechar_pedido_pos(
    order_id: str,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Fecha um pedido POS manualmente (normalmente feito automaticamente pelo webhook).
    Necessário quando o webhook não chegou ou para forçar fechamento.
    """
    user, tenant_id = auth
    tenant_id_str = str(tenant_id)

    transaction = db.query(StoneTransaction).filter(
        StoneTransaction.stone_payment_id == order_id,
        StoneTransaction.tenant_id == tenant_id_str,
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    stone_client = get_stone_client(db, tenant_id_str)
    try:
        await stone_client.fechar_pedido(order_id)

        old_status = transaction.status
        transaction.status = "approved"
        transaction.paid_at = transaction.paid_at or datetime.now(timezone.utc)
        transaction.updated_at = datetime.now(timezone.utc)
        db.commit()

        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type="pedido_pos_fechado",
            event_source="manual",
            description="Pedido fechado manualmente",
            old_status=old_status,
            new_status="approved",
            user_id=user.id,
            tenant_id=tenant_id_str,
        )

        return {"success": True, "message": "Pedido fechado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fechar pedido: {str(e)}")


@router.get("/pedidos-abertos")
async def listar_pedidos_abertos_pos(
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Lista pedidos em aberto na Stone (closed=false).
    Útil para diagnosticar o limite de 30 pedidos que bloqueia o POS:
    se a conta tiver >= 30 pedidos abertos, a maquininha para de exibir novos.
    """
    user, tenant_id = auth
    stone_client = get_stone_client(db, str(tenant_id))
    try:
        resultado = await stone_client.listar_pedidos_abertos()
        pedidos = resultado.get("data", [])
        return {
            "total": len(pedidos),
            "alerta_limite": len(pedidos) >= 25,
            "pedidos": [
                {
                    "id": p.get("id"),
                    "code": p.get("code"),
                    "status": p.get("status"),
                    "amount": p.get("amount"),
                    "created_at": p.get("created_at"),
                    "closed": p.get("closed"),
                }
                for p in pedidos
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar pedidos abertos: {str(e)}")


@router.post("/pedidos-abertos/cancelar-todos")
async def cancelar_todos_pedidos_abertos(
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Cancela todos os pedidos abertos na Stone para liberar a fila do POS.
    Use isso quando a maquininha parar de exibir novos pedidos (limite de 30).
    Só cancela pedidos que ainda não foram pagos (status != paid).
    """
    user, tenant_id = auth
    stone_client = get_stone_client(db, str(tenant_id))
    try:
        resultado = await stone_client.listar_pedidos_abertos()
        pedidos = resultado.get("data", [])

        cancelados = []
        erros = []
        for p in pedidos:
            order_id = p.get("id")
            if not order_id:
                continue
            try:
                await stone_client.cancelar_pedido(order_id)
                cancelados.append(order_id)
                # Atualiza registro local se existir
                local = db.query(StoneTransaction).filter(
                    StoneTransaction.stone_payment_id == order_id
                ).first()
                if local:
                    local.status = "cancelled"
                    local.cancelled_at = datetime.now(timezone.utc)
            except Exception as ex:
                erros.append({"order_id": order_id, "erro": str(ex)})

        db.commit()
        return {
            "success": True,
            "cancelados": len(cancelados),
            "erros": len(erros),
            "ids_cancelados": cancelados,
            "detalhes_erros": erros,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao cancelar pedidos: {str(e)}")


def registrar_log(
    db: Session,
    transaction_id: int,
    event_type: str,
    event_source: str,
    description: str,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    webhook_data: Optional[dict] = None,
    error_details: Optional[dict] = None,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None
):
    """Registra um log de evento"""
    log = StoneTransactionLog(
        transaction_id=transaction_id,
        event_type=event_type,
        event_source=event_source,
        description=description,
        old_status=old_status,
        new_status=new_status,
        webhook_data=webhook_data,
        error_details=error_details,
        user_id=user_id,
        tenant_id=tenant_id
    )
    db.add(log)
    db.commit()


# ==========================================
# CONFIGURAÇÃO
# ==========================================

@router.post("/config")
def configurar_stone(
    config_data: StoneConfigSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Configura credenciais Stone para o tenant

    **Importante:** Guarde suas credenciais com segurança!
    """
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    tenant_id = current_user['tenant_id']

    # Verifica se já existe configuração
    existing_config = db.query(StoneConfig).filter(
        StoneConfig.tenant_id == tenant_id
    ).first()

    config_payload = config_data.dict()

    if existing_config:
        # Se o frontend reenviar a chave mascarada, preserva a chave real salva.
        incoming_client_id = config_payload.get("client_id")
        if incoming_client_id and "*" in incoming_client_id:
            config_payload["client_id"] = existing_config.client_id

        # Atualiza configuração existente
        for key, value in config_payload.items():
            setattr(existing_config, key, value)
        existing_config.updated_at = datetime.now(timezone.utc)
        config = existing_config
    else:
        # Cria nova configuração
        config = StoneConfig(
            **config_payload,
            tenant_id=tenant_id,
            user_id=current_user['id']
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    logger.info(f"Configuração Stone criada/atualizada para tenant {tenant_id}")

    return {
        "success": True,
        "message": "Configuração Stone salva com sucesso",
        "config": config.to_dict()
    }


@router.get("/config")
def obter_config_stone(
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Retorna configuração Stone do tenant (sem expor secrets)"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    config = db.query(StoneConfig).filter(
        StoneConfig.tenant_id == current_user['tenant_id']
    ).first()

    if not config:
        # Retorna dados padrao para evitar erro 404 no frontend
        return {
            "client_id": "",
            "merchant_id": None,
            "sandbox": False,
            "enable_pix": True,
            "enable_credit_card": True,
            "enable_debit_card": True,
            "max_installments": 12,
            "webhook_url": None,
            "webhook_enabled": True,
            "active": False,
            "affiliation_code": "",
            "documento": "",
            "conciliacao_username": None,
            "conciliacao_configurado": False,
            "pos_serial_number": None,
        }

    return config.to_dict()


# ==========================================
# PAGAMENTOS PIX
# ==========================================

@router.post("/payments/pix")
async def criar_pagamento_pix(
    payment_data: CreatePixPaymentSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Cria um pagamento via PIX

    Retorna QR Code e código Pix Copia e Cola para o cliente pagar
    """
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    tenant_id = current_user['tenant_id']

    # Verifica se external_id já existe
    existing = db.query(StoneTransaction).filter(
        StoneTransaction.external_id == payment_data.external_id,
        StoneTransaction.tenant_id == tenant_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pagamento com external_id '{payment_data.external_id}' já existe"
        )

    # Obtém cliente Stone
    stone_client = get_stone_client(db, tenant_id)

    try:
        # Cria pagamento na Stone
        stone_response = await stone_client.criar_pagamento_pix(
            amount=payment_data.amount,
            description=payment_data.description,
            external_id=payment_data.external_id,
            customer_name=payment_data.customer_name,
            customer_document=payment_data.customer_document,
            customer_email=payment_data.customer_email,
            expiration_minutes=payment_data.expiration_minutes
        )

        # Salva transação no banco
        transaction = StoneTransaction(
            stone_payment_id=stone_response['id'],
            external_id=payment_data.external_id,
            venda_id=payment_data.venda_id,
            conta_receber_id=payment_data.conta_receber_id,
            payment_method='pix',
            amount=payment_data.amount,
            description=payment_data.description,
            status='pending',
            stone_status=stone_response.get('status'),
            customer_name=payment_data.customer_name,
            customer_document=payment_data.customer_document,
            customer_email=payment_data.customer_email,
            pix_qr_code=stone_response.get('pix', {}).get('qr_code'),
            pix_qr_code_url=stone_response.get('pix', {}).get('qr_code_url'),
            pix_copy_paste=stone_response.get('pix', {}).get('copy_paste'),
            pix_expiration=datetime.now(timezone.utc) + timedelta(minutes=payment_data.expiration_minutes),
            stone_response=stone_response,
            tenant_id=tenant_id,
            user_id=current_user['id']
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        # Registra log
        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type='payment_created',
            event_source='manual',
            description=f'Pagamento PIX criado - R$ {payment_data.amount}',
            new_status='pending',
            user_id=current_user['id'],
            tenant_id=tenant_id
        )

        logger.info(f"Pagamento PIX criado: {transaction.id} - R$ {payment_data.amount}")

        return {
            "success": True,
            "message": "Pagamento PIX criado com sucesso",
            "transaction": transaction.to_dict(),
            "pix": {
                "qr_code": transaction.pix_qr_code,
                "qr_code_url": transaction.pix_qr_code_url,
                "copy_paste": transaction.pix_copy_paste,
                "expiration": transaction.pix_expiration.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Erro ao criar pagamento PIX: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar pagamento PIX: {str(e)}"
        )


# ==========================================
# PAGAMENTOS CARTÃO
# ==========================================

@router.post("/payments/card")
async def criar_pagamento_cartao(
    payment_data: CreateCardPaymentSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Cria um pagamento via cartão de crédito/débito

    **Atenção:** Dados do cartão são sensíveis. Use HTTPS!
    """
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    tenant_id = current_user['tenant_id']

    # Verifica se external_id já existe
    existing = db.query(StoneTransaction).filter(
        StoneTransaction.external_id == payment_data.external_id,
        StoneTransaction.tenant_id == tenant_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pagamento com external_id '{payment_data.external_id}' já existe"
        )

    # Obtém cliente Stone
    stone_client = get_stone_client(db, tenant_id)

    try:
        # Cria pagamento na Stone
        stone_response = await stone_client.criar_pagamento_cartao(
            amount=payment_data.amount,
            description=payment_data.description,
            external_id=payment_data.external_id,
            card_number=payment_data.card_number,
            card_holder_name=payment_data.card_holder_name,
            card_expiration_date=payment_data.card_expiration_date,
            card_cvv=payment_data.card_cvv,
            installments=payment_data.installments,
            customer_name=payment_data.customer_name,
            customer_document=payment_data.customer_document,
            customer_email=payment_data.customer_email
        )

        # Extrai dados do cartão (mascarados)
        card_data = stone_response.get('card', {})

        # Salva transação no banco
        transaction = StoneTransaction(
            stone_payment_id=stone_response['id'],
            external_id=payment_data.external_id,
            venda_id=payment_data.venda_id,
            conta_receber_id=payment_data.conta_receber_id,
            payment_method='credit_card',
            amount=payment_data.amount,
            description=payment_data.description,
            installments=payment_data.installments,
            status=stone_response.get('status', 'pending'),
            stone_status=stone_response.get('status'),
            customer_name=payment_data.customer_name,
            customer_document=payment_data.customer_document,
            customer_email=payment_data.customer_email,
            card_brand=card_data.get('brand'),
            card_last_digits=card_data.get('last_digits'),
            fee_amount=Decimal(stone_response.get('fee_amount', 0)) / 100,
            net_amount=Decimal(stone_response.get('net_amount', 0)) / 100,
            stone_response=stone_response,
            tenant_id=tenant_id,
            user_id=current_user['id']
        )

        # Se aprovado imediatamente, registra data de pagamento
        if stone_response.get('status') == 'approved':
            transaction.paid_at = datetime.now(timezone.utc)

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        # Registra log
        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type='payment_created',
            event_source='manual',
            description=f'Pagamento Cartão criado - R$ {payment_data.amount} - {payment_data.installments}x',
            new_status=transaction.status,
            user_id=current_user['id'],
            tenant_id=tenant_id
        )

        logger.info(f"Pagamento Cartão criado: {transaction.id} - R$ {payment_data.amount}")

        return {
            "success": True,
            "message": "Pagamento processado com sucesso",
            "transaction": transaction.to_dict(),
            "status": transaction.status
        }

    except Exception as e:
        logger.error(f"Erro ao criar pagamento Cartão: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar pagamento: {str(e)}"
        )


# ==========================================
# CONSULTAS
# ==========================================

@router.get("/payments/{transaction_id}")
async def consultar_pagamento(
    transaction_id: int,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Consulta status atualizado de um pagamento"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    transaction = db.query(StoneTransaction).filter(
        StoneTransaction.id == transaction_id,
        StoneTransaction.tenant_id == current_user['tenant_id']
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_MSG_TRANSACAO_NAO_ENCONTRADA
        )

    # Consulta Stone para obter status atualizado
    stone_client = get_stone_client(db, current_user['tenant_id'])

    try:
        stone_response = await stone_client.consultar_pagamento(transaction.stone_payment_id)

        # Atualiza status se mudou
        old_status = transaction.status
        new_status = stone_response.get('status')

        if old_status != new_status:
            transaction.status = new_status
            transaction.stone_status = new_status
            transaction.stone_response = stone_response
            transaction.updated_at = datetime.now(timezone.utc)

            # Atualiza datas específicas
            if new_status == 'approved' and not transaction.paid_at:
                transaction.paid_at = datetime.now(timezone.utc)
            elif new_status == 'cancelled' and not transaction.cancelled_at:
                transaction.cancelled_at = datetime.now(timezone.utc)
            elif new_status == 'refunded' and not transaction.refunded_at:
                transaction.refunded_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(transaction)

            # Registra mudança de status
            registrar_log(
                db=db,
                transaction_id=transaction.id,
                event_type='status_change',
                event_source='api_call',
                description='Status atualizado via API',
                old_status=old_status,
                new_status=new_status,
                user_id=current_user['id'],
                tenant_id=current_user['tenant_id']
            )

        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "stone_data": stone_response
        }

    except Exception as e:
        logger.error(f"Erro ao consultar pagamento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar pagamento: {str(e)}"
        )


@router.get("/payments")
def listar_pagamentos(
    status_filter: Optional[str] = None,
    payment_method: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Lista pagamentos com filtros"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    query = db.query(StoneTransaction).filter(
        StoneTransaction.tenant_id == current_user['tenant_id']
    )

    if status_filter:
        query = query.filter(StoneTransaction.status == status_filter)

    if payment_method:
        query = query.filter(StoneTransaction.payment_method == payment_method)

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(StoneTransaction.created_at >= start)
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(StoneTransaction.created_at <= end)
        except ValueError:
            pass

    total = query.count()
    transactions = query.order_by(StoneTransaction.created_at.desc()).limit(limit).offset(offset).all()

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "transactions": [t.to_dict() for t in transactions]
    }


# ==========================================
# CANCELAMENTOS E ESTORNOS
# ==========================================

@router.post("/payments/{transaction_id}/cancel")
async def cancelar_pagamento(
    transaction_id: int,
    cancel_data: CancelPaymentSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Cancela um pagamento pendente"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    transaction = db.query(StoneTransaction).filter(
        StoneTransaction.id == transaction_id,
        StoneTransaction.tenant_id == current_user['tenant_id']
    ).first()

    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_MSG_TRANSACAO_NAO_ENCONTRADA)

    if transaction.status not in ['pending', 'processing']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível cancelar pagamento com status '{transaction.status}'"
        )

    stone_client = get_stone_client(db, current_user['tenant_id'])

    try:
        await stone_client.cancelar_pagamento(
            payment_id=transaction.stone_payment_id,
            reason=cancel_data.reason
        )

        old_status = transaction.status
        transaction.status = 'cancelled'
        transaction.cancelled_at = datetime.now(timezone.utc)
        transaction.updated_at = datetime.now(timezone.utc)
        db.commit()

        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type='payment_cancelled',
            event_source='manual',
            description=cancel_data.reason or 'Pagamento cancelado',
            old_status=old_status,
            new_status='cancelled',
            user_id=current_user['id'],
            tenant_id=current_user['tenant_id']
        )

        return {"success": True, "message": "Pagamento cancelado com sucesso"}

    except Exception as e:
        logger.error(f"Erro ao cancelar pagamento: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/payments/{transaction_id}/refund")
async def estornar_pagamento(
    transaction_id: int,
    refund_data: RefundPaymentSchema,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Estorna um pagamento aprovado (total ou parcial)"""
    user, tenant_id = auth
    current_user = {'id': user.id, 'tenant_id': str(tenant_id)}
    transaction = db.query(StoneTransaction).filter(
        StoneTransaction.id == transaction_id,
        StoneTransaction.tenant_id == current_user['tenant_id']
    ).first()

    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_MSG_TRANSACAO_NAO_ENCONTRADA)

    if transaction.status != 'approved':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas pagamentos aprovados podem ser estornados"
        )

    stone_client = get_stone_client(db, current_user['tenant_id'])

    try:
        await stone_client.estornar_pagamento(
            payment_id=transaction.stone_payment_id,
            amount=refund_data.amount,
            reason=refund_data.reason
        )

        old_status = transaction.status
        transaction.status = 'refunded'
        transaction.refunded_at = datetime.now(timezone.utc)
        transaction.updated_at = datetime.now(timezone.utc)
        db.commit()

        registrar_log(
            db=db,
            transaction_id=transaction.id,
            event_type='payment_refunded',
            event_source='manual',
            description=refund_data.reason or f'Estorno de R$ {refund_data.amount or transaction.amount}',
            old_status=old_status,
            new_status='refunded',
            user_id=current_user['id'],
            tenant_id=current_user['tenant_id']
        )

        return {"success": True, "message": "Pagamento estornado com sucesso"}

    except Exception as e:
        logger.error(f"Erro ao estornar pagamento: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==========================================
# WEBHOOK (Recebe notificações da Stone)
# ==========================================

@dataclass(frozen=True)
class StonePosPaymentData:
    order_id: str
    charge_id: str
    valor: Decimal
    tipo_forma_pagamento: str
    bandeira: Optional[str]
    nsu: Optional[str]
    numero_autorizacao: Optional[str]
    parcelas: int
    paid_at: Optional[datetime]
    terminal_serial_number: Optional[str]


def _normalizar_chave_metadata(chave: str) -> str:
    return "".join(c for c in str(chave or "").lower() if c.isalnum())


def _metadata_value(metadata: dict, *chaves: str) -> Any:
    if not isinstance(metadata, dict):
        return None

    for chave in chaves:
        valor = metadata.get(chave)
        if valor not in (None, ""):
            return valor

    normalizado = {
        _normalizar_chave_metadata(chave): valor
        for chave, valor in metadata.items()
        if valor not in (None, "")
    }
    for chave in chaves:
        valor = normalizado.get(_normalizar_chave_metadata(chave))
        if valor not in (None, ""):
            return valor
    return None


def _centavos_para_decimal(valor_centavos: Any) -> Decimal:
    try:
        return (Decimal(str(valor_centavos or 0)) / Decimal("100")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _parse_datetime_stone(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    try:
        texto = str(valor).strip()
        if texto.endswith("Z"):
            texto = f"{texto[:-1]}+00:00"
        return datetime.fromisoformat(texto)
    except Exception:
        return None


def _normalizar_tipo_pagamento_pos(account_funding_source: Any, payment_method: Any) -> str:
    origem = str(account_funding_source or "").strip().lower()
    metodo = str(payment_method or "").strip().lower()

    if origem in {"credit", "credito", "crédito"} or metodo in {"credit", "credit_card", "cartao_credito"}:
        return "cartao_credito"
    if origem in {"debit", "debito", "débito", "prepaid"} or metodo in {"debit", "debit_card", "cartao_debito"}:
        return "cartao_debito"
    if metodo == "pix":
        return "pix"

    # Nos exemplos oficiais do POS o payment_method aparece como "cash",
    # enquanto o tipo real vem no metadata.account_funding_source.
    return "cartao_credito"


def _extrair_dados_pagamento_pos(webhook_data: dict) -> StonePosPaymentData:
    data = webhook_data.get("data") or {}
    order = data.get("order") or {}
    last_transaction = data.get("last_transaction") or {}
    metadata = {
        **(order.get("metadata") or {}),
        **(last_transaction.get("metadata") or {}),
        **(data.get("metadata") or {}),
    }

    order_id = order.get("id") or data.get("order_id") or _metadata_value(metadata, "order_id")
    charge_id = data.get("id") or last_transaction.get("id") or ""
    parcelas_raw = (
        _metadata_value(metadata, "installment_quantity", "installmentQuantity")
        or last_transaction.get("installments")
        or 1
    )
    try:
        parcelas = max(1, int(parcelas_raw or 1))
    except (TypeError, ValueError):
        parcelas = 1

    valor_centavos = data.get("paid_amount") or data.get("amount") or last_transaction.get("amount")
    account_funding_source = _metadata_value(metadata, "account_funding_source", "accountFundingSource")
    tipo_forma_pagamento = _normalizar_tipo_pagamento_pos(
        account_funding_source=account_funding_source,
        payment_method=data.get("payment_method") or last_transaction.get("transaction_type"),
    )

    return StonePosPaymentData(
        order_id=str(order_id or ""),
        charge_id=str(charge_id or ""),
        valor=_centavos_para_decimal(valor_centavos),
        tipo_forma_pagamento=tipo_forma_pagamento,
        bandeira=_metadata_value(metadata, "scheme_name", "schemeName"),
        nsu=data.get("code"),
        numero_autorizacao=_metadata_value(metadata, "authorization_code", "authorizationCode"),
        parcelas=parcelas,
        paid_at=_parse_datetime_stone(data.get("paid_at") or _metadata_value(metadata, "transaction_timestamp", "transactionTimestamp")),
        terminal_serial_number=_metadata_value(metadata, "terminal_serial_number", "terminalSerialNumber"),
    )


def _mapear_forma_pagamento_stone(
    db: Session,
    tenant_id: str,
    tipo_forma_pagamento: str,
    parcelas: int,
) -> str:
    query = db.query(FormaPagamento).filter(
        FormaPagamento.tenant_id == tenant_id,
        FormaPagamento.tipo == tipo_forma_pagamento,
        FormaPagamento.ativo == True,
    )

    forma = None
    if tipo_forma_pagamento == "cartao_credito":
        if parcelas > 1:
            forma = query.filter(
                FormaPagamento.permite_parcelamento == True,
                FormaPagamento.parcelas_maximas >= parcelas,
            ).order_by(FormaPagamento.parcelas_maximas.desc()).first()
            if not forma:
                forma = query.filter(sa_func.lower(FormaPagamento.nome).like("%parcel%")).first()
        else:
            forma = query.filter(~sa_func.lower(FormaPagamento.nome).like("%parcel%")).first()

    if not forma:
        forma = query.first()

    if forma:
        return forma.nome

    fallback = {
        "cartao_credito": "Cartão Crédito",
        "cartao_debito": "Cartão Débito",
        "pix": "PIX",
    }
    return fallback.get(tipo_forma_pagamento, "Stone POS")


def _buscar_pagamento_stone_existente(
    db: Session,
    *,
    venda_id: int,
    tenant_id: str,
    dados_pagamento: StonePosPaymentData,
) -> Optional[VendaPagamento]:
    filtros = [
        VendaPagamento.tenant_id == tenant_id,
        VendaPagamento.venda_id == venda_id,
    ]
    identificadores = []
    if dados_pagamento.charge_id:
        identificadores.append(VendaPagamento.numero_transacao == dados_pagamento.charge_id)
    if dados_pagamento.nsu:
        identificadores.append(VendaPagamento.nsu_cartao == dados_pagamento.nsu)

    if not identificadores:
        return None

    return db.query(VendaPagamento).filter(*filtros, or_(*identificadores)).first()


def _registrar_pagamento_venda_stone(
    db: Session,
    *,
    transaction: StoneTransaction,
    dados_pagamento: StonePosPaymentData,
) -> Optional[VendaPagamento]:
    if not transaction.venda_id:
        return None

    tenant_id = str(transaction.tenant_id)
    venda = db.query(Venda).filter(
        Venda.id == transaction.venda_id,
        Venda.tenant_id == tenant_id,
    ).first()
    if not venda:
        logger.warning("Venda %s não encontrada para webhook Stone.", transaction.venda_id)
        return None

    existente = _buscar_pagamento_stone_existente(
        db,
        venda_id=venda.id,
        tenant_id=tenant_id,
        dados_pagamento=dados_pagamento,
    )
    if existente:
        existente.bandeira = existente.bandeira or dados_pagamento.bandeira
        existente.numero_parcelas = existente.numero_parcelas or dados_pagamento.parcelas
        existente.numero_transacao = existente.numero_transacao or dados_pagamento.charge_id
        existente.numero_autorizacao = existente.numero_autorizacao or dados_pagamento.numero_autorizacao
        existente.status = "aprovado"
        db.flush()
        return existente

    forma_pagamento_nome = _mapear_forma_pagamento_stone(
        db,
        tenant_id=tenant_id,
        tipo_forma_pagamento=dados_pagamento.tipo_forma_pagamento,
        parcelas=dados_pagamento.parcelas,
    )

    from app.vendas.service import VendaService

    VendaService.finalizar_venda(
        venda_id=venda.id,
        pagamentos=[
            {
                "forma_pagamento": forma_pagamento_nome,
                "valor": float(dados_pagamento.valor),
                "numero_parcelas": dados_pagamento.parcelas,
                "bandeira": dados_pagamento.bandeira,
                "nsu_cartao": dados_pagamento.nsu,
                "operadora_id": None,
            }
        ],
        user_id=transaction.user_id,
        user_nome="Stone POS",
        tenant_id=tenant_id,
        db=db,
    )

    pagamento = _buscar_pagamento_stone_existente(
        db,
        venda_id=venda.id,
        tenant_id=tenant_id,
        dados_pagamento=dados_pagamento,
    )
    if not pagamento:
        pagamento = db.query(VendaPagamento).filter(
            VendaPagamento.tenant_id == tenant_id,
            VendaPagamento.venda_id == venda.id,
        ).order_by(VendaPagamento.id.desc()).first()

    if pagamento:
        pagamento.numero_transacao = dados_pagamento.charge_id
        pagamento.numero_autorizacao = dados_pagamento.numero_autorizacao
        pagamento.status = "aprovado"
        if dados_pagamento.paid_at:
            pagamento.data_pagamento = dados_pagamento.paid_at
        db.flush()

    return pagamento


_WEBHOOK_STATUS_MAP = {
    "charge.paid": "approved",
    "charge.refunded": "refunded",
    "charge.chargedback": "refunded",
    "charge.payment_failed": "failed",
}


async def _fechar_pedido_stone(db: Session, tenant_id: str, order_id: str) -> None:
    """Fecha um pedido na Stone após pagamento confirmado (obrigatório, limite 30 abertos)."""
    config = db.query(StoneConfig).filter(StoneConfig.tenant_id == tenant_id).first()
    if config:
        try:
            await StoneAPIClient(secret_key=config.client_id).fechar_pedido(order_id)
            logger.info(f"Pedido {order_id} fechado automaticamente após charge.paid")
        except Exception as e:
            logger.error(f"Erro ao fechar pedido {order_id} após webhook: {e}")


# ==========================================
# WEBHOOK (Recebe notificações da Stone)
# ==========================================

@router.post("/webhook")
async def receber_webhook_stone(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session)
):
    """
    Recebe webhooks da Stone Connect (charge.paid, charge.refunded, etc.).

    Formato Stone Connect:
    {
      "type": "charge.paid",
      "data": {
        "id": "ch_...",
        "status": "paid",
        "order": { "id": "or_...", ... }
      }
    }

    Após charge.paid: fecha o pedido automaticamente na Stone.
    """
    webhook_data = await request.json()
    event_type = webhook_data.get("type", "")
    data = webhook_data.get("data", {})

    logger.info(f"Webhook Stone Connect recebido: {event_type}")

    dados_pagamento = _extrair_dados_pagamento_pos(webhook_data)
    order_id = dados_pagamento.order_id

    if not order_id:
        logger.error(f"Webhook Stone sem order_id: {webhook_data}")
        return {"success": False, "error": "order_id não encontrado no payload"}

    transaction = db.query(StoneTransaction).filter(
        StoneTransaction.stone_payment_id == order_id
    ).first()

    if not transaction:
        logger.warning(f"Transação não encontrada para order_id: {order_id}")
        return {"success": True, "message": "Pedido não rastreado por este sistema"}

    old_status = transaction.status
    new_status = _WEBHOOK_STATUS_MAP.get(event_type, old_status)

    if event_type == "charge.paid":
        if not transaction.paid_at:
            transaction.paid_at = dados_pagamento.paid_at or datetime.now(timezone.utc)
        transaction.payment_method = dados_pagamento.tipo_forma_pagamento
        transaction.amount = dados_pagamento.valor
        transaction.card_brand = dados_pagamento.bandeira
        transaction.installments = dados_pagamento.parcelas
        _registrar_pagamento_venda_stone(
            db=db,
            transaction=transaction,
            dados_pagamento=dados_pagamento,
        )
        await _fechar_pedido_stone(db, transaction.tenant_id, order_id)
    elif event_type in ("charge.refunded", "charge.chargedback"):
        if not transaction.refunded_at:
            transaction.refunded_at = datetime.now(timezone.utc)

    transaction.status = new_status
    transaction.stone_status = data.get("status", new_status)
    transaction.last_webhook_at = datetime.now(timezone.utc)
    transaction.webhook_count = (transaction.webhook_count or 0) + 1
    transaction.stone_response = data
    transaction.updated_at = datetime.now(timezone.utc)
    db.commit()

    registrar_log(
        db=db,
        transaction_id=transaction.id,
        event_type="webhook_recebido",
        event_source="stone_webhook",
        description=f"Webhook: {event_type}",
        old_status=old_status,
        new_status=new_status,
        webhook_data=webhook_data,
        tenant_id=transaction.tenant_id,
    )

    logger.info(f"Webhook processado: order={order_id} {old_status} → {new_status}")
    return {"success": True, "message": "Webhook processado"}


# ==========================================
# TESTE DE CONEXÃO (SEM AUTENTICAÇÃO)
# ==========================================

@router.get("/test-connection")
async def test_stone_connection():
    """
    🔧 Endpoint de teste para verificar conexão com API da Stone

    **Não requer autenticação** - Usa credenciais do ambiente

    Testa:
    1. OAuth2 Client Credentials (múltiplos endpoints)
    2. API Key direta (Authorization Bearer)
    """
    import os
    import httpx

    try:
        # Pega credenciais do ambiente
        client_id = os.getenv('STONE_CLIENT_ID', '')
        client_secret = os.getenv('STONE_CLIENT_SECRET', '')
        merchant_id = os.getenv('STONE_MERCHANT_ID', '')
        sandbox = os.getenv('STONE_SANDBOX', 'true').lower() == 'true'

        if not client_id:
            return {
                "success": False,
                "error": "STONE_CLIENT_ID não configurado no ambiente"
            }

        # =====================================
        # TESTE 1: Usar chave como API Key direta
        # =====================================
        api_key_results = []

        base_urls = [
            "https://payments.stone.com.br",
            "https://api.stone.com.br",
            "https://ton.com.br"
        ]

        test_endpoints = [
            "/api/v1/transactions",
            "/v1/transactions",
            "/api/transactions",
            "/transactions"
        ]

        async with httpx.AsyncClient(timeout=10.0) as http_client:
            for base_url in base_urls:
                for endpoint in test_endpoints:
                    url = f"{base_url}{endpoint}"

                    try:
                        response = await http_client.get(
                            url,
                            headers={"Authorization": f"Bearer {client_id}"}
                        )

                        result = {
                            "method": "API_KEY",
                            "url": url,
                            "status": response.status_code,
                            "success": response.status_code in [200, 401]  # 401 = autenticado mas sem acesso
                        }

                        if response.status_code == 200:
                            result["message"] = "✅ API Key funcionou!"
                            api_key_results.append(result)

                            return {
                                "success": True,
                                "message": "✅ Conexão Stone estabelecida com API Key!",
                                "auth_method": "API_KEY",
                                "endpoint": url,
                                "all_tests": api_key_results
                            }
                        elif response.status_code == 401:
                            result["message"] = "🔐 Endpoint existe mas precisa de autenticação diferente"
                        else:
                            result["response"] = response.text[:150]

                        api_key_results.append(result)

                    except Exception as e:
                        api_key_results.append({
                            "method": "API_KEY",
                            "url": url,
                            "status": "error",
                            "success": False,
                            "error": str(e)[:100]
                        })

        # =====================================
        # TESTE 2: OAuth2 (como antes)
        # =====================================
        oauth_results = []

        oauth_base_urls = ["https://payments.stone.com.br", "https://api.stone.com.br"]
        oauth_paths = ["/auth/oauth/token", "/oauth/token", "/api/oauth/token"]

        async with httpx.AsyncClient(timeout=10.0) as http_client:
            for base_url in oauth_base_urls[:2]:  # Limita a 2 URLs principais
                for oauth_path in oauth_paths[:3]:  # Limita a 3 paths principais
                    url = f"{base_url}{oauth_path}"

                    try:
                        response = await http_client.post(
                            url,
                            data={
                                "grant_type": "client_credentials",
                                "client_id": client_id,
                                "client_secret": client_secret
                            },
                            headers={"Content-Type": "application/x-www-form-urlencoded"}
                        )

                        result = {
                            "method": "OAUTH2",
                            "url": url,
                            "status": response.status_code,
                            "success": response.status_code == 200
                        }

                        if response.status_code == 200:
                            result["message"] = "✅ OAuth2 funcionou!"
                            oauth_results.append(result)

                            return {
                                "success": True,
                                "message": "✅ Conexão Stone estabelecida com OAuth2!",
                                "auth_method": "OAUTH2",
                                "endpoint": url,
                                "all_tests": oauth_results
                            }
                        else:
                            result["response"] = response.text[:150]

                        oauth_results.append(result)

                    except Exception as e:
                        oauth_results.append({
                            "method": "OAUTH2",
                            "url": url,
                            "status": "error",
                            "success": False,
                            "error": str(e)[:100]
                        })

        # Nenhum método funcionou
        return {
            "success": False,
            "message": "❌ Nenhum método de autenticação funcionou",
            "tests_performed": {
                "api_key": len(api_key_results),
                "oauth2": len(oauth_results)
            },
            "api_key_results": api_key_results[:10],  # Primeiros 10
            "oauth2_results": oauth_results[:6]  # Primeiros 6
        }

    except Exception as e:
        logger.error(f"Erro ao testar conexão Stone: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "details": {
                "sandbox_mode": sandbox if 'sandbox' in locals() else None,
                "base_url": client.base_url if 'client' in locals() else None
            }
        }


# ==========================================
# API DE CONCILIAÇÃO STONE
# ==========================================

class ConsentRequestSchema(BaseModel):
    """Schema para solicitar consentimento"""
    document: str = Field(..., description="CNPJ do lojista")
    affiliation_code: str = Field(..., description="Stone Code")
    webhook_url: str = Field(..., description="URL para receber webhook")


class ConsentWebhookSchema(BaseModel):
    """Schema do webhook de consentimento"""
    status: str  # pending, accepted, denied
    document: str
    affiliation_code: str
    username: Optional[str] = None
    password: Optional[str] = None


# Armazenamento temporário de credenciais (em produção, use banco de dados)
_stone_credentials = {}


@router.post("/solicitar-consentimento")
async def solicitar_consentimento_stone(
    payload: ConsentRequestSchema,
    auth = Depends(get_current_user_and_tenant)
):
    """
    📝 Solicita consentimento do lojista para acessar dados de conciliação

    **Fluxo:**
    1. Sistema envia solicitação para Stone
    2. Stone envia email para o lojista
    3. Lojista aprova ou nega
    4. Stone envia webhook com credenciais (se aprovado)
    5. Sistema salva credenciais automaticamente

    **Requer:** Permissão de admin
    """
    import os

    _ = auth  # verificado pelo Depends, nao usado diretamente

    try:
        client_id = os.getenv("STONE_CLIENT_ID", "")
        client_secret = os.getenv("STONE_CLIENT_SECRET", "")
        sandbox = os.getenv("STONE_SANDBOX", "true").lower() == "true"

        if not client_id or not client_secret:
            raise HTTPException(400, "Credenciais Stone não configuradas")

        client = StoneConciliationClient(
            client_id=client_id,
            client_secret=client_secret,
            sandbox=sandbox
        )

        result = await client.request_consent(
            document=payload.document,
            affiliation_code=payload.affiliation_code,
            webhook_url=payload.webhook_url
        )

        if result.get("success"):
            return {
                "success": True,
                "message": "✅ Consentimento solicitado! Verifique o email do lojista para aprovar.",
                "details": {
                    "document": payload.document,
                    "affiliation_code": payload.affiliation_code,
                    "next_steps": "O lojista receberá um email da Stone para aprovar o acesso"
                }
            }
        else:
            raise HTTPException(400, result.get("message", "Erro desconhecido"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao solicitar consentimento: {str(e)}")
        raise HTTPException(500, f"Erro ao solicitar consentimento: {str(e)}")


@router.post("/webhook-consentimento")
async def webhook_consentimento_stone(
    payload: ConsentWebhookSchema,
    request: Request
):
    """
    🔔 Webhook para receber notificação de consentimento da Stone

    **Este endpoint é chamado pela Stone quando:**
    - Lojista aprova o consentimento (status=accepted)
    - Lojista nega o consentimento (status=denied)

    **Não requer autenticação** (webhook externo)
    """
    try:
        logger.info(f"Webhook Stone recebido: {payload.dict()}")

        if payload.status == "accepted":
            # Salva credenciais
            key = f"{payload.document}_{payload.affiliation_code}"
            _stone_credentials[key] = {
                "username": payload.username,
                "password": payload.password,
                "approved_at": datetime.now().isoformat(),
                "document": payload.document,
                "affiliation_code": payload.affiliation_code
            }

            logger.info(f"✅ Consentimento aprovado para {payload.document}")

            return {
                "success": True,
                "message": "Consentimento aprovado e credenciais salvas"
            }

        elif payload.status == "denied":
            logger.warning(f"❌ Consentimento negado para {payload.document}")
            return {
                "success": True,
                "message": "Consentimento negado pelo lojista"
            }

        else:  # pending
            logger.info(f"⏳ Consentimento pendente para {payload.document}")
            return {
                "success": True,
                "message": "Consentimento pendente de aprovação"
            }

    except Exception as e:
        logger.error(f"Erro ao processar webhook: {str(e)}")
        # Retorna 200 mesmo com erro para não retentar
        return {"success": False, "error": str(e)}


@router.get("/extrato/{stone_code}")
async def buscar_extrato_stone(
    stone_code: str,
    start_date: str,
    end_date: str,
    auth = Depends(get_current_user_and_tenant)
):
    """
    📊 Busca extrato de transações da Stone

    **Args:**
    - stone_code: Código Stone do estabelecimento
    - start_date: Data inicial (YYYY-MM-DD)
    - end_date: Data final (YYYY-MM-DD)

    **Returns:** Lista de transações do período
    """
    import os

    _ = auth  # verificado pelo Depends, nao usado diretamente

    try:
        # Busca credenciais
        document = os.getenv("STONE_DOCUMENT", "")
        key = f"{document}_{stone_code}"

        if key not in _stone_credentials:
            raise HTTPException(
                400,
                "Consentimento não aprovado. Solicite acesso primeiro."
            )

        creds = _stone_credentials[key]

        client_id = os.getenv("STONE_CLIENT_ID")
        client_secret = os.getenv("STONE_CLIENT_SECRET")
        sandbox = os.getenv("STONE_SANDBOX", "true").lower() == "true"

        client = StoneConciliationClient(
            client_id=client_id,
            client_secret=client_secret,
            sandbox=sandbox
        )

        # Define credenciais
        client.set_credentials(
            username=creds["username"],
            password=creds["password"]
        )

        # Busca transações
        transactions = await client.get_transactions(
            stone_code=stone_code,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "period": {
                "start": start_date,
                "end": end_date
            },
            "total": len(transactions),
            "transactions": transactions
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar extrato: {str(e)}")
        raise HTTPException(500, f"Erro ao buscar extrato: {str(e)}")


@router.post("/conciliar-automatico/{stone_code}")
async def conciliar_automatico_stone(
    stone_code: str,
    start_date: str,
    end_date: str,
    auth = Depends(get_current_user_and_tenant)
):
    """
    🔗 Busca extrato Stone e concilia automaticamente com vendas

    **Processo:**
    1. Busca transações da Stone no período
    2. Para cada transação, tenta match por:
       - NSU exato
       - Valor + data próxima
    3. Atualiza contas_receber como conciliadas

    **Returns:** Resumo da conciliação
    """
    _ = auth  # auth verificado pelo Depends
    session = next(get_session())

    try:
        # Busca extrato
        extrato_result = await buscar_extrato_stone(
            stone_code=stone_code,
            start_date=start_date,
            end_date=end_date,
            auth=auth
        )

        if not extrato_result.get("success"):
            raise HTTPException(400, "Erro ao buscar extrato")

        transactions = extrato_result.get("transactions", [])

        resultado = {
            "total_transacoes": len(transactions),
            "conciliadas_nsu": 0,
            "conciliadas_valor_data": 0,
            "nao_encontradas": 0,
            "detalhes": []
        }

        for trans in transactions:
            try:
                # Tenta match por NSU
                conta = session.query(ContaReceber).filter(
                    and_(
                        ContaReceber.tenant_id == tenant_id,
                        ContaReceber.nsu == trans["nsu"],
                        ContaReceber.conciliado == False
                    )
                ).first()

                match_type = None

                if conta:
                    match_type = "nsu"
                    resultado["conciliadas_nsu"] += 1
                else:
                    # Tenta match por valor + data
                    trans_date = datetime.fromisoformat(trans["date"])
                    data_inicio = trans_date - timedelta(days=1)
                    data_fim = trans_date + timedelta(days=1)

                    conta = session.query(ContaReceber).filter(
                        and_(
                            ContaReceber.tenant_id == tenant_id,
                            ContaReceber.valor == trans["amount"],
                            ContaReceber.data_vencimento >= data_inicio,
                            ContaReceber.data_vencimento <= data_fim,
                            ContaReceber.conciliado == False
                        )
                    ).first()

                    if conta:
                        match_type = "valor_data"
                        resultado["conciliadas_valor_data"] += 1

                if conta:
                    # Atualiza conta
                    conta.conciliado = True
                    conta.data_conciliacao = datetime.now()
                    conta.nsu = trans["nsu"]
                    conta.adquirente = "Stone"

                    venda_numero = None
                    if conta.venda_id:
                        venda = session.query(Venda).get(conta.venda_id)
                        if venda:
                            venda_numero = venda.numero_venda

                    resultado["detalhes"].append({
                        "stone_id": trans["stone_id"],
                        "nsu": trans["nsu"],
                        "valor": float(trans["amount"]),
                        "match": True,
                        "match_type": match_type,
                        "venda": venda_numero
                    })
                else:
                    resultado["nao_encontradas"] += 1
                    resultado["detalhes"].append({
                        "stone_id": trans["stone_id"],
                        "nsu": trans["nsu"],
                        "valor": float(trans["amount"]),
                        "match": False,
                        "motivo": "Nenhuma venda encontrada"
                    })

            except Exception as e:
                logger.error(f"Erro ao processar transação {trans.get('nsu')}: {str(e)}")
                resultado["detalhes"].append({
                    "nsu": trans.get("nsu"),
                    "erro": str(e)
                })

        # Salva alterações
        session.commit()

        return {
            "success": True,
            "message": f"✅ Conciliação concluída: {resultado['conciliadas_nsu'] + resultado['conciliadas_valor_data']} de {resultado['total_transacoes']} transações",
            "resumo": resultado
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erro na conciliação automática: {str(e)}")
        raise HTTPException(500, f"Erro na conciliação: {str(e)}")
    finally:
        session.close()
