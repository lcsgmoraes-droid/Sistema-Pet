"""
Rotas exclusivas do App Mobile (clientes).

Prefixo : /app
Auth    : token JWT "ecommerce_customer" (mesmo fluxo do e-commerce)
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, text
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Cliente, User, UserPushDevice
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
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
from app.bling_estoque_sync import sincronizar_bling_background
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

router = APIRouter(prefix="/app", tags=["App Mobile"])
router.include_router(pets_router)
router.include_router(funcionario_pdv_router)


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


class FuncionarioProdutoEstoqueResponse(BaseModel):
    id: int
    nome: str
    codigo: Optional[str] = None
    codigo_barras: Optional[str] = None
    gtin_ean: Optional[str] = None
    unidade: str = "UN"
    preco_venda: float = 0
    preco_custo: float = 0
    estoque_atual: float = 0
    imagem_url: Optional[str] = None
    is_parent: bool = False
    tipo_produto: Optional[str] = None
    tipo_kit: Optional[str] = None
    permite_balanco: bool = True
    aviso: Optional[str] = None


class FuncionarioBalancoRequest(BaseModel):
    produto_id: int
    saldo_final: float = Field(ge=0)
    numero_lote: Optional[str] = None
    data_validade: Optional[str] = None
    observacao: Optional[str] = None


class FuncionarioBalancoResponse(BaseModel):
    status: str
    produto: FuncionarioProdutoEstoqueResponse
    estoque_anterior: float
    estoque_novo: float
    diferenca: float
    tipo_movimentacao: Optional[str] = None
    quantidade_movimentada: float = 0
    movimentacao_id: Optional[int] = None
    mensagem: str


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


def _produto_permite_balanco_funcionario(
    produto: Produto,
) -> tuple[bool, Optional[str]]:
    if getattr(produto, "is_parent", False):
        return False, "Produto pai: ajuste o estoque nas variacoes individuais."
    if produto.tipo_produto == "KIT" and produto.tipo_kit == "VIRTUAL":
        return False, "Kit virtual: ajuste os componentes que formam este kit."
    return True, None


def _serialize_funcionario_produto_estoque(produto: Produto) -> dict:
    permite_balanco, aviso = _produto_permite_balanco_funcionario(produto)
    return {
        "id": produto.id,
        "nome": produto.nome,
        "codigo": produto.codigo,
        "codigo_barras": produto.codigo_barras,
        "gtin_ean": produto.gtin_ean,
        "unidade": produto.unidade or "UN",
        "preco_venda": float(produto.preco_venda or 0),
        "preco_custo": float(produto.preco_custo or 0),
        "estoque_atual": float(produto.estoque_atual or 0),
        "imagem_url": produto.imagem_principal,
        "is_parent": bool(produto.is_parent),
        "tipo_produto": produto.tipo_produto,
        "tipo_kit": produto.tipo_kit,
        "permite_balanco": permite_balanco,
        "aviso": aviso,
    }


def _parse_data_validade_funcionario(valor: Optional[str]) -> Optional[datetime]:
    texto = str(valor or "").strip()
    if not texto:
        return None
    candidatos = [
        texto,
        texto.replace("Z", "+00:00"),
        texto.replace(" ", "T"),
        texto.split("T")[0],
    ]
    for candidato in candidatos:
        try:
            data = datetime.fromisoformat(candidato)
            return data.replace(tzinfo=None) if data.tzinfo else data
        except ValueError:
            continue
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:10], formato)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail="Data de validade invalida.")


def _registrar_lote_balanco_funcionario(
    db: Session,
    produto: Produto,
    quantidade: float,
    numero_lote: Optional[str],
    data_validade: Optional[str],
) -> int | None:
    if quantidade <= 0 or not (numero_lote or data_validade):
        return None

    nome_lote = (
        numero_lote or f"{produto.codigo}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    ).strip()
    data_val = _parse_data_validade_funcionario(data_validade)
    produto.controle_lote = True

    lote = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto.id,
            ProdutoLote.nome_lote == nome_lote,
        )
        .first()
    )
    if lote:
        lote.quantidade_inicial = float(lote.quantidade_inicial or 0) + quantidade
        lote.quantidade_disponivel = float(lote.quantidade_disponivel or 0) + quantidade
        lote.data_validade = data_val or lote.data_validade
        lote.custo_unitario = lote.custo_unitario or produto.preco_custo
        lote.status = "ativo"
    else:
        lote = ProdutoLote(
            produto_id=produto.id,
            nome_lote=nome_lote,
            quantidade_inicial=quantidade,
            quantidade_disponivel=quantidade,
            quantidade_reservada=0,
            data_validade=data_val,
            custo_unitario=produto.preco_custo,
            ordem_entrada=int(datetime.now().timestamp()),
            status="ativo",
        )
        db.add(lote)
        db.flush()
    return lote.id


def _consumir_lotes_balanco_funcionario(
    db: Session, produto: Produto, quantidade: float
) -> str | None:
    lotes_consumidos = []
    quantidade_restante = quantidade
    lotes_ativos = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto.id,
            ProdutoLote.quantidade_disponivel > 0,
            ProdutoLote.status == "ativo",
        )
        .order_by(ProdutoLote.ordem_entrada)
        .all()
    )
    for lote in lotes_ativos:
        if quantidade_restante <= 0:
            break
        saldo_anterior = float(lote.quantidade_disponivel or 0)
        quantidade_consumida = min(saldo_anterior, quantidade_restante)
        lote.quantidade_disponivel = saldo_anterior - quantidade_consumida
        quantidade_restante -= quantidade_consumida
        if lote.quantidade_disponivel <= 0:
            lote.status = "esgotado"
        lotes_consumidos.append(
            {
                "lote_id": lote.id,
                "nome_lote": lote.nome_lote,
                "quantidade": quantidade_consumida,
                "saldo_anterior": saldo_anterior,
            }
        )
    return json.dumps(lotes_consumidos) if lotes_consumidos else None


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


@router.get(
    "/funcionario/estoque/produtos/buscar",
    response_model=list[FuncionarioProdutoEstoqueResponse],
)
def buscar_produtos_funcionario_estoque(
    q: str = "",
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    termo = (q or "").strip()
    if len(termo) < 2:
        return []

    filtros_busca = _produto_busca_filtros_funcionario(termo)
    rank_busca = _produto_busca_rank_funcionario(termo)
    prioridade_estoque = case((func.coalesce(Produto.estoque_atual, 0) > 0, 0), else_=1)
    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            or_(*filtros_busca),
        )
        .order_by(
            rank_busca.asc(),
            prioridade_estoque.asc(),
            Produto.is_parent.asc(),
            Produto.nome.asc(),
        )
        .limit(20)
        .all()
    )
    return [_serialize_funcionario_produto_estoque(produto) for produto in produtos]


@router.get(
    "/funcionario/estoque/produtos/barcode/{barcode}",
    response_model=FuncionarioProdutoEstoqueResponse,
)
def buscar_produto_funcionario_barcode(
    barcode: str,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    barcode = (barcode or "").strip()
    if not barcode:
        raise HTTPException(status_code=400, detail="Codigo de barras obrigatorio.")

    prioridade_estoque = case((func.coalesce(Produto.estoque_atual, 0) > 0, 0), else_=1)
    produto = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            or_(*_barcode_filters_for_produto(barcode)),
        )
        .order_by(prioridade_estoque.asc(), Produto.is_parent.asc(), Produto.id.asc())
        .first()
    )
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto ERP nao encontrado para este codigo.",
        )
    return _serialize_funcionario_produto_estoque(produto)


@router.post("/funcionario/estoque/balanco", response_model=FuncionarioBalancoResponse)
def registrar_balanco_funcionario_estoque(
    payload: FuncionarioBalancoRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == payload.produto_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
        )
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado.")

    permite_balanco, aviso = _produto_permite_balanco_funcionario(produto)
    if not permite_balanco:
        raise HTTPException(status_code=400, detail=aviso)

    estoque_atual = float(produto.estoque_atual or 0)
    saldo_final = float(payload.saldo_final)
    diferenca = round(saldo_final - estoque_atual, 6)
    documento = f"APP-FUNC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    observacao_base = "App funcionario - balanco por camera"
    observacao = (
        observacao_base
        if not payload.observacao
        else f"{observacao_base}: {payload.observacao.strip()}"
    )

    if abs(diferenca) < 0.000001:
        return {
            "status": "sem_alteracao",
            "produto": _serialize_funcionario_produto_estoque(produto),
            "estoque_anterior": estoque_atual,
            "estoque_novo": saldo_final,
            "diferenca": 0,
            "tipo_movimentacao": None,
            "quantidade_movimentada": 0,
            "movimentacao_id": None,
            "mensagem": "Saldo final igual ao estoque atual. Nenhuma movimentacao registrada.",
        }

    tipo_movimentacao = "entrada" if diferenca > 0 else "saida"
    quantidade_movimentada = abs(diferenca)
    lote_id = None
    lotes_consumidos = None
    if tipo_movimentacao == "entrada":
        lote_id = _registrar_lote_balanco_funcionario(
            db,
            produto,
            quantidade_movimentada,
            payload.numero_lote,
            payload.data_validade,
        )
    else:
        lotes_consumidos = _consumir_lotes_balanco_funcionario(
            db, produto, quantidade_movimentada
        )

    produto.estoque_atual = saldo_final
    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo=tipo_movimentacao,
        motivo="balanco",
        quantidade=quantidade_movimentada,
        quantidade_anterior=estoque_atual,
        quantidade_nova=saldo_final,
        custo_unitario=produto.preco_custo,
        valor_total=quantidade_movimentada * float(produto.preco_custo or 0),
        lote_id=lote_id,
        lotes_consumidos=lotes_consumidos,
        documento=documento,
        observacao=observacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    db.refresh(produto)

    try:
        sincronizar_bling_background(produto.id, saldo_final, "balanco_app_funcionario")
    except Exception:
        pass

    return {
        "status": "registrado",
        "produto": _serialize_funcionario_produto_estoque(produto),
        "estoque_anterior": estoque_atual,
        "estoque_novo": saldo_final,
        "diferenca": diferenca,
        "tipo_movimentacao": tipo_movimentacao,
        "quantidade_movimentada": quantidade_movimentada,
        "movimentacao_id": movimentacao.id,
        "mensagem": f"Balanco registrado por {funcionario.nome or current_user.nome or current_user.email}.",
    }


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


@router.get("/pedidos/{pedido_id}/rastreio")
def rastreio_entrega(
    pedido_id: str,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna o status de rastreio de entrega de um pedido do cliente.
    Busca a rota de entrega associada à venda gerada pelo pedido.
    """
    from app.pedido_models import Pedido
    from app.vendas_models import Venda
    from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada

    tenant_id = _activate_user_tenant_context(current_user)

    # Verificar se o pedido pertence ao cliente
    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.tenant_id == tenant_id,
            Pedido.cliente_id == current_user.id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    # Buscar venda associada ao pedido (via observações ou canal+cliente)
    venda = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.canal.in_(["ecommerce", "app", "aplicativo"]),
            Venda.observacoes.contains(pedido_id),
        )
        .first()
    )

    if not venda:
        # Pedido ainda não gerou venda (aguardando pagamento)
        return {
            "status_pedido": pedido.status,
            "tem_entrega": False,
            "mensagem": _rastreio_mensagem_status(pedido.status),
            "rota": None,
        }

    if not venda.tem_entrega:
        return {
            "status_pedido": pedido.status,
            "tem_entrega": False,
            "mensagem": "Seu pedido é para retirada na loja.",
            "tipo_retirada": venda.tipo_retirada,
            "palavra_chave_retirada": venda.palavra_chave_retirada,
            "rota": None,
        }

    # Buscar parada de entrega associada a esta venda
    parada = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.venda_id == venda.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .first()
    )

    if not parada:
        return {
            "status_pedido": pedido.status,
            "tem_entrega": True,
            "mensagem": "Entrega em preparação — em breve será despachada.",
            "rota": None,
        }

    rota = (
        db.query(RotaEntrega)
        .filter(
            RotaEntrega.id == parada.rota_id,
            RotaEntrega.tenant_id == tenant_id,
        )
        .first()
    )
    if not rota:
        return {
            "status_pedido": pedido.status,
            "tem_entrega": True,
            "mensagem": "Entrega em preparação.",
            "rota": None,
        }

    # Buscar todas as paradas da rota para calcular progresso
    todas_paradas = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .order_by(RotaEntregaParada.ordem)
        .all()
    )
    entregues = sum(1 for p in todas_paradas if p.status == "entregue")
    posicao_cliente = None
    for i, p in enumerate(todas_paradas):
        if p.id == parada.id:
            posicao_cliente = i + 1
            break

    # Última posição GPS do entregador.
    # Prioridade:
    # 1) posição atual contínua da rota (lat_atual/lon_atual)
    # 2) fallback para última parada entregue com GPS
    ultima_posicao = None
    try:
        rota_posicao = db.execute(
            text(
                """
                SELECT lat_atual, lon_atual, localizacao_atualizada_em
                FROM rotas_entrega
                WHERE id = :rid AND tenant_id = :tenant
                """
            ),
            {"rid": rota.id, "tenant": tenant_id},
        ).fetchone()

        if rota_posicao and rota_posicao[0] is not None and rota_posicao[1] is not None:
            ultima_posicao = {
                "lat": float(rota_posicao[0]),
                "lon": float(rota_posicao[1]),
                "atualizada_em": rota_posicao[2].isoformat()
                if rota_posicao[2]
                else None,
                "fonte": "rota_atual",
            }
        else:
            for p in reversed(todas_paradas):
                result = db.execute(
                    text(
                        "SELECT lat_entrega, lon_entrega "
                        "FROM rotas_entrega_paradas "
                        "WHERE id = :pid AND tenant_id = :tenant"
                    ),
                    {"pid": p.id, "tenant": tenant_id},
                ).fetchone()
                if result and result[0] is not None and result[1] is not None:
                    ultima_posicao = {
                        "lat": float(result[0]),
                        "lon": float(result[1]),
                        "atualizada_em": p.data_entrega.isoformat()
                        if p.data_entrega
                        else None,
                        "fonte": "ultima_parada",
                    }
                    break
    except Exception:
        pass

    entregador_nome = None
    if rota.entregador_id:
        entregador = (
            db.query(Cliente)
            .filter(
                Cliente.id == rota.entregador_id,
                Cliente.tenant_id == tenant_id,
            )
            .first()
        )
        if entregador:
            entregador_nome = entregador.nome

    return {
        "status_pedido": pedido.status,
        "tem_entrega": True,
        "rota": {
            "numero": rota.numero,
            "status": rota.status,
            "token_rastreio": rota.token_rastreio,
            "entregador_nome": entregador_nome or "Entregador",
            "total_paradas": len(todas_paradas),
            "entregues": entregues,
            "posicao_cliente": posicao_cliente,
            "paradas_antes": max(0, (posicao_cliente or 1) - 1 - entregues),
            "status_parada": parada.status,
            "endereco_entrega": parada.endereco or venda.endereco_entrega,
            "data_entrega": parada.data_entrega.isoformat()
            if parada.data_entrega
            else None,
            "ultima_posicao_gps": ultima_posicao,
        },
        "mensagem": _rastreio_mensagem_parada(parada.status, rota.status),
    }


def _rastreio_mensagem_status(status: str) -> str:
    mapa = {
        "carrinho": "Carrinho ainda ativo.",
        "pendente": "Aguardando confirmação de pagamento.",
        "aprovado": "Pagamento confirmado! Preparando seu pedido.",
        "recusado": "Pagamento recusado. Entre em contato com a loja.",
        "cancelado": "Pedido cancelado.",
        "criado": "Pedido recebido, em preparação.",
    }
    return mapa.get(status, "Pedido em processamento.")


def _rastreio_mensagem_parada(status_parada: str, status_rota: str) -> str:
    if status_parada == "entregue":
        return "✅ Entregue! Aproveite seu pedido."
    if status_rota in ("em_rota", "em_andamento"):
        return "🛵 Entregador saiu para entrega!"
    if status_parada == "pendente":
        return "📦 Pedido separado, aguardando saída para entrega."
    return "Entrega em preparação."
