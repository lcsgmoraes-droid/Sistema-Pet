# ruff: noqa: F401
"""
Rotas exclusivas do App Mobile (clientes).

Prefixo : /app
Auth    : token JWT "ecommerce_customer" (mesmo fluxo do e-commerce)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Cliente, User, UserPushDevice
from app.produtos_models import Produto
from app.routes.ecommerce_auth import (
    _activate_user_tenant_context,
    _get_current_ecommerce_user,
    _get_or_create_cliente_for_user,
)
from app.routes.app_mobile_funcionario_pdv_routes import (
    FuncionarioPdvBeneficioCupomResponse as FuncionarioPdvBeneficioCupomResponse,
    FuncionarioPdvBeneficiosPreviewRequest as FuncionarioPdvBeneficiosPreviewRequest,
    FuncionarioPdvBeneficiosPreviewResponse as FuncionarioPdvBeneficiosPreviewResponse,
    FuncionarioPdvCaixaResponse as FuncionarioPdvCaixaResponse,
    FuncionarioPdvClienteResponse as FuncionarioPdvClienteResponse,
    FuncionarioPdvFinalizarRequest as FuncionarioPdvFinalizarRequest,
    FuncionarioPdvFinalizarResponse as FuncionarioPdvFinalizarResponse,
    FuncionarioPdvFormaPagamentoResponse as FuncionarioPdvFormaPagamentoResponse,
    FuncionarioPdvItemRequest as FuncionarioPdvItemRequest,
    FuncionarioPdvPagamentoRequest as FuncionarioPdvPagamentoRequest,
    FuncionarioPdvProdutoResponse as FuncionarioPdvProdutoResponse,
    FuncionarioPdvSalvarRequest as FuncionarioPdvSalvarRequest,
    FuncionarioPdvSalvarResponse as FuncionarioPdvSalvarResponse,
    _aplicar_desconto_cupom_nos_itens_funcionario_pdv as _aplicar_desconto_cupom_nos_itens_funcionario_pdv,
    _barcode_filters_for_produto as _barcode_filters_for_produto,
    _buscar_cliente_pdv_funcionario as _buscar_cliente_pdv_funcionario,
    _calcular_beneficios_funcionario_pdv as _calcular_beneficios_funcionario_pdv,
    _calcular_beneficios_gerados_funcionario_pdv as _calcular_beneficios_gerados_funcionario_pdv,
    _cashback_bonus_param_key_funcionario_pdv as _cashback_bonus_param_key_funcionario_pdv,
    _forma_pagamento_key_funcionario_pdv as _forma_pagamento_key_funcionario_pdv,
    _get_funcionario_operacional_or_403 as _get_funcionario_operacional_or_403,
    _listar_cupons_disponiveis_funcionario_pdv as _listar_cupons_disponiveis_funcionario_pdv,
    _normalizar_forma_pagamento_pdv as _normalizar_forma_pagamento_pdv,
    _obter_caixa_aberto_funcionario_pdv as _obter_caixa_aberto_funcionario_pdv,
    _param_float_funcionario_pdv as _param_float_funcionario_pdv,
    _param_int_funcionario_pdv as _param_int_funcionario_pdv,
    _produto_busca_filtros_funcionario as _produto_busca_filtros_funcionario,
    _produto_busca_rank_funcionario as _produto_busca_rank_funcionario,
    _produto_busca_texto_funcionario as _produto_busca_texto_funcionario,
    _resolver_forma_pagamento_cartao_funcionario_pdv as _resolver_forma_pagamento_cartao_funcionario_pdv,
    _round_money_funcionario_pdv as _round_money_funcionario_pdv,
    _serialize_funcionario_pdv_cliente as _serialize_funcionario_pdv_cliente,
    _serialize_funcionario_pdv_produto as _serialize_funcionario_pdv_produto,
    _somente_digitos_funcionario_pdv as _somente_digitos_funcionario_pdv,
    _termo_parece_codigo_produto_funcionario as _termo_parece_codigo_produto_funcionario,
    _tokens_busca_produto_funcionario as _tokens_busca_produto_funcionario,
    buscar_clientes_funcionario_pdv as buscar_clientes_funcionario_pdv,
    buscar_produto_funcionario_pdv_barcode as buscar_produto_funcionario_pdv_barcode,
    buscar_produtos_funcionario_pdv as buscar_produtos_funcionario_pdv,
    finalizar_venda_funcionario_pdv as finalizar_venda_funcionario_pdv,
    listar_formas_pagamento_funcionario_pdv as listar_formas_pagamento_funcionario_pdv,
    obter_caixa_aberto_funcionario_pdv as obter_caixa_aberto_funcionario_pdv,
    preview_beneficios_funcionario_pdv as preview_beneficios_funcionario_pdv,
    router as funcionario_pdv_router,
    salvar_venda_funcionario_pdv as salvar_venda_funcionario_pdv,
)
from app.routes.app_mobile_funcionario_estoque_routes import (
    FuncionarioBalancoRequest as FuncionarioBalancoRequest,
    FuncionarioBalancoResponse as FuncionarioBalancoResponse,
    FuncionarioProdutoEstoqueResponse as FuncionarioProdutoEstoqueResponse,
    _consumir_lotes_balanco_funcionario as _consumir_lotes_balanco_funcionario,
    _parse_data_validade_funcionario as _parse_data_validade_funcionario,
    _produto_permite_balanco_funcionario as _produto_permite_balanco_funcionario,
    _registrar_lote_balanco_funcionario as _registrar_lote_balanco_funcionario,
    _serialize_funcionario_produto_estoque as _serialize_funcionario_produto_estoque,
    buscar_produto_funcionario_barcode as buscar_produto_funcionario_barcode,
    buscar_produtos_funcionario_estoque as buscar_produtos_funcionario_estoque,
    registrar_balanco_funcionario_estoque as registrar_balanco_funcionario_estoque,
    router as funcionario_estoque_router,
)
from app.routes.app_mobile_funcionario_contagem_routes import (
    FuncionarioContagemArquivoResponse as FuncionarioContagemArquivoResponse,
    FuncionarioContagemFornecedorResponse as FuncionarioContagemFornecedorResponse,
    FuncionarioContagemItemRequest as FuncionarioContagemItemRequest,
    FuncionarioContagemItemResponse as FuncionarioContagemItemResponse,
    FuncionarioContagemRequest as FuncionarioContagemRequest,
    FuncionarioContagemResponse as FuncionarioContagemResponse,
    FuncionarioContagemResumoResponse as FuncionarioContagemResumoResponse,
    _colunas_exportacao_contagem as _colunas_exportacao_contagem,
    buscar_fornecedores_contagem_funcionario as buscar_fornecedores_contagem_funcionario,
    criar_contagem_funcionario as criar_contagem_funcionario,
    exportar_contagem_funcionario as exportar_contagem_funcionario,
    exportar_contagem_funcionario_mobile as exportar_contagem_funcionario_mobile,
    listar_contagens_funcionario as listar_contagens_funcionario,
    obter_contagem_funcionario as obter_contagem_funcionario,
    router as funcionario_contagem_router,
)
from app.services.validade_campanha_service import (
    mapear_ofertas_validade_por_produto,
    resolver_preco_publico_produto,
)
from app.routes.app_mobile_pets_routes import (
    PET_UPLOAD_DIR as PET_UPLOAD_DIR,
    PetCarteirinhaResponse as PetCarteirinhaResponse,
    PetCreate as PetCreate,
    PetResponse as PetResponse,
    PetUpdate as PetUpdate,
    _gerar_codigo_pet as _gerar_codigo_pet,
    _get_pet_owned_or_404 as _get_pet_owned_or_404,
    _serialize_pet as _serialize_pet,
    atualizar_pet as atualizar_pet,
    criar_pet as criar_pet,
    deletar_pet as deletar_pet,
    listar_pets as listar_pets,
    obter_carteirinha_pet_app as obter_carteirinha_pet_app,
    router as pets_router,
    upload_foto_pet as upload_foto_pet,
)
from app.veterinario_models import AgendamentoVet

from app.routes.app_mobile_rastreio_routes import (
    _rastreio_mensagem_parada,
    _rastreio_mensagem_status,
    rastreio_entrega,
    router as rastreio_router,
)

router = APIRouter(prefix="/app", tags=["App Mobile"])
router.include_router(pets_router)
router.include_router(funcionario_pdv_router)
router.include_router(funcionario_estoque_router)
router.include_router(funcionario_contagem_router)
router.include_router(rastreio_router)


# ─────────────────────────────────────────
# Schemas de RESPOSTA (response_model)
# Definem exatamente o que a API devolve ao app.
# Importante: evita vazar campos internos do banco.
# ─────────────────────────────────────────


class ProdutoBarcodeResponse(BaseModel):
    id: int
    nome: str
    preco: float
    preco_original: float
    preco_promocional: Optional[float] = None
    foto_url: Optional[str]
    codigo_barras: Optional[str]
    unidade: str
    estoque: float
    promocao_ativa: Optional[bool] = False
    promocao_origem: Optional[str] = None
    promocao_validade: Optional[dict] = None


class PushTokenPayload(BaseModel):
    token: str
    plataforma: Optional[str] = None  # "android" | "ios"
    platform: Optional[str] = None
    device_name: Optional[str] = None
    device_brand: Optional[str] = None
    device_model: Optional[str] = None
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None


def _get_cliente_or_404(db: Session, user: User) -> Cliente:
    """Retorna o Cliente ligado a este usuário ecommerce ou lança 404."""
    cliente = _get_or_create_cliente_for_user(db, user)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de cliente não encontrado. Contate a loja.",
        )
    return cliente


def _serialize_push_device(device: UserPushDevice) -> dict:
    return {
        "id": device.id,
        "platform": device.platform,
        "device_name": device.device_name,
        "device_brand": device.device_brand,
        "device_model": device.device_model,
        "os_name": device.os_name,
        "os_version": device.os_version,
        "app_version": device.app_version,
        "enabled": bool(device.enabled),
        "last_seen_at": device.last_seen_at.isoformat()
        if device.last_seen_at
        else None,
        "last_success_at": device.last_success_at.isoformat()
        if device.last_success_at
        else None,
        "last_ticket_id": device.last_ticket_id,
        "last_error": device.last_error,
        "last_error_at": device.last_error_at.isoformat()
        if device.last_error_at
        else None,
        "token_preview": f"{device.expo_push_token[:18]}..."
        if device.expo_push_token
        else None,
    }


def _disable_same_push_token_for_other_users(
    db: Session, current_user: User, token: str
) -> None:
    other_devices = (
        db.query(UserPushDevice)
        .filter(
            UserPushDevice.tenant_id == current_user.tenant_id,
            UserPushDevice.expo_push_token == token,
            UserPushDevice.user_id != current_user.id,
            UserPushDevice.enabled.is_(True),
        )
        .all()
    )
    if not other_devices:
        return

    other_user_ids = {other_device.user_id for other_device in other_devices}
    for other_device in other_devices:
        other_device.enabled = False

    other_users = (
        db.query(User)
        .filter(
            User.tenant_id == current_user.tenant_id,
            User.id.in_(other_user_ids),
            User.push_token == token,
        )
        .all()
    )
    for other_user in other_users:
        other_user.push_token = None


@router.get("/push-status")
def obter_status_push(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    from app.campaigns.models import NotificationQueue, NotificationStatusEnum

    cliente = _get_cliente_or_404(db, current_user)
    pendentes = (
        db.query(NotificationQueue)
        .filter(
            NotificationQueue.tenant_id == str(current_user.tenant_id),
            NotificationQueue.customer_id == cliente.id,
            NotificationQueue.status == NotificationStatusEnum.pending,
        )
        .order_by(
            NotificationQueue.scheduled_at.asc(), NotificationQueue.created_at.desc()
        )
        .limit(10)
        .all()
    )

    proximos_agendamentos = (
        db.query(AgendamentoVet)
        .filter(
            AgendamentoVet.tenant_id == str(current_user.tenant_id),
            AgendamentoVet.cliente_id == cliente.id,
            AgendamentoVet.status.in_(["agendado", "confirmado", "em_atendimento"]),
            AgendamentoVet.data_hora >= datetime.now(),
        )
        .order_by(AgendamentoVet.data_hora.asc())
        .limit(5)
        .all()
    )

    push_token = getattr(current_user, "push_token", None)
    devices = (
        db.query(UserPushDevice)
        .filter(
            UserPushDevice.tenant_id == current_user.tenant_id,
            UserPushDevice.user_id == current_user.id,
        )
        .order_by(UserPushDevice.enabled.desc(), UserPushDevice.last_seen_at.desc())
        .all()
    )
    return {
        "token_registrado": bool(push_token or devices),
        "push_token_preview": f"{push_token[:18]}..." if push_token else None,
        "devices": [_serialize_push_device(device) for device in devices],
        "pendencias": [
            {
                "id": item.id,
                "assunto": item.subject,
                "mensagem": item.body,
                "scheduled_at": item.scheduled_at.isoformat()
                if item.scheduled_at
                else None,
            }
            for item in pendentes
        ],
        "proximos_agendamentos": [
            {
                "id": ag.id,
                "pet_id": ag.pet_id,
                "data_hora": ag.data_hora.isoformat() if ag.data_hora else None,
                "tipo": ag.tipo,
                "status": ag.status,
            }
            for ag in proximos_agendamentos
        ],
        "observacao": "Push remoto não funciona no Expo Go nas versões atuais. Para homologação real, use build dev client ou APK/IPA.",
    }


# ─────────────────────────────────────────
# PRODUTO POR CÓDIGO DE BARRAS
# ─────────────────────────────────────────


@router.get("/produto-barcode/{barcode}", response_model=ProdutoBarcodeResponse)
def buscar_produto_barcode(
    barcode: str,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Busca produto pelo código de barras (EAN/GTIN).
    Tenta `codigo_barras` e depois `gtin_ean`.
    Retorna apenas produtos ativos, vendaveis e disponiveis para o app.
    Se houver cadastros duplicados para o mesmo codigo, prioriza item com estoque.
    """
    tenant_id = _activate_user_tenant_context(current_user)
    barcode = (barcode or "").strip()
    filtros_codigo = _barcode_filters_for_produto(barcode)

    prioridade_estoque = case((func.coalesce(Produto.estoque_atual, 0) > 0, 0), else_=1)

    produto = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            Produto.is_sellable.is_(True),
            Produto.anunciar_app.is_(True),
            or_(*filtros_codigo),
        )
        .order_by(prioridade_estoque.asc(), Produto.is_parent.asc(), Produto.id.asc())
        .first()
    )

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado para este código de barras.",
        )

    oferta_validade = mapear_ofertas_validade_por_produto(db, [produto], "app").get(
        produto.id
    )
    pricing = resolver_preco_publico_produto(
        produto,
        "app",
        validity_offer=oferta_validade,
    )
    preco = float(
        pricing.promotional_price
        if pricing.promotional_price is not None
        else pricing.regular_price or 0
    )
    preco_original = float(pricing.regular_price or 0)

    return {
        "id": produto.id,
        "nome": produto.nome,
        "preco": preco,
        "preco_original": preco_original,
        "preco_promocional": preco if pricing.promotion_active else None,
        "foto_url": produto.imagem_principal,
        "codigo_barras": produto.codigo_barras,
        "unidade": produto.unidade or "UN",
        "estoque": float(produto.estoque_atual or 0),
        "promocao_ativa": pricing.promotion_active,
        "promocao_origem": pricing.promotion_origin,
        "promocao_validade": {
            "ativa": bool(oferta_validade and oferta_validade.active),
            "lote_id": oferta_validade.lote_id if oferta_validade else None,
            "nome_lote": oferta_validade.lote_nome if oferta_validade else None,
            "dias_para_vencer": oferta_validade.dias_para_vencer
            if oferta_validade
            else None,
            "quantidade_promocional": oferta_validade.quantity_available
            if oferta_validade
            else None,
            "percentual_desconto": oferta_validade.percentual_desconto
            if oferta_validade
            else None,
            "preco_promocional": oferta_validade.promotional_price
            if oferta_validade
            else None,
            "mensagem": oferta_validade.message if oferta_validade else None,
        }
        if oferta_validade
        else None,
    }


# ─────────────────────────────────────────
# PUSH TOKEN
# ─────────────────────────────────────────


@router.post("/push-token")
def registrar_push_token(
    payload: PushTokenPayload,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Salva o token de notificação push (Expo Push Token ou FCM)
    no campo `push_token` do usuário.

    Requer migration para adicionar a coluna `push_token` a `users`.
    Execute: `alembic revision --autogenerate -m "add push_token to users"`
    seguido de `alembic upgrade head` em produção.
    """
    if not hasattr(current_user, "push_token"):
        # Coluna ainda não existe (migration pendente)
        return {
            "status": "ignored",
            "motivo": "Migration pendente: coluna push_token não existe.",
        }

    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token de push obrigatorio.")
    current_user.push_token = token
    _disable_same_push_token_for_other_users(db, current_user, token)

    device = (
        db.query(UserPushDevice)
        .filter(
            UserPushDevice.tenant_id == current_user.tenant_id,
            UserPushDevice.user_id == current_user.id,
            UserPushDevice.expo_push_token == token,
        )
        .first()
    )
    if not device:
        device = UserPushDevice(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            expo_push_token=token,
        )
        db.add(device)

    device.platform = (payload.platform or payload.plataforma or "").strip() or None
    device.device_name = (payload.device_name or "").strip() or None
    device.device_brand = (payload.device_brand or "").strip() or None
    device.device_model = (payload.device_model or "").strip() or None
    device.os_name = (payload.os_name or "").strip() or None
    device.os_version = (payload.os_version or "").strip() or None
    device.app_version = (payload.app_version or "").strip() or None
    device.enabled = True
    device.last_seen_at = func.now()
    device.last_error = None
    device.last_error_at = None
    db.commit()
    db.refresh(device)
    return {
        "status": "ok",
        "device_id": device.id,
        "token_preview": f"{token[:18]}...",
    }


# ─────────────────────────────────────────
# RASTREIO DE ENTREGA
# ─────────────────────────────────────────
