"""
Rotas exclusivas do App Mobile (clientes).

Prefixo : /app
Auth    : token JWT "ecommerce_customer" (mesmo fluxo do e-commerce)
"""

import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, or_, text
from sqlalchemy.orm import Session

from app.caixa_models import Caixa
from app.campaigns.channel_scope import campaign_allows_sale_channel, normalize_benefit_channel
from app.campaigns.coupon_service import preview_coupon_redemption
from app.campaigns.models import (
    Campaign,
    CampaignStatusEnum,
    CampaignTypeEnum,
    CashbackTransaction,
    Coupon,
    CouponChannelEnum,
    CouponStatusEnum,
)
from app.db import get_session
from app.financeiro_models import FormaPagamento
from app.models import Cliente, Pet, User
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.routes.ecommerce_auth import (
    _activate_user_tenant_context,
    _cashback_disponivel_clause,
    _get_current_ecommerce_user,
    _get_or_create_cliente_for_user,
)
from app.bling_estoque_sync import sincronizar_bling_background
from app.services.validade_campanha_service import (
    mapear_ofertas_validade_por_produto,
    resolver_preco_publico_produto,
)
from app.veterinario_models import AgendamentoVet, ConsultaVet, ExameVet

router = APIRouter(prefix="/app", tags=["App Mobile"])

PET_UPLOAD_DIR = Path("uploads/pets")


# ─────────────────────────────────────────
# Schemas de RESPOSTA (response_model)
# Definem exatamente o que a API devolve ao app.
# Importante: evita vazar campos internos do banco.
# ─────────────────────────────────────────

class PetResponse(BaseModel):
    id: int
    codigo: str
    nome: str
    especie: str
    raca: Optional[str]
    sexo: Optional[str]
    castrado: bool
    data_nascimento: Optional[str]   # ISO 8601 string
    idade_aproximada: Optional[int] = None
    peso: Optional[float]
    porte: Optional[str]
    cor: Optional[str]
    alergias: Optional[str]
    alergias_lista: list[str] = []
    observacoes: Optional[str]
    restricoes_alimentares_lista: list[str] = []
    condicoes_cronicas_lista: list[str] = []
    medicamentos_continuos_lista: list[str] = []
    tipo_sanguineo: Optional[str] = None
    foto_url: Optional[str]

    class Config:
        from_attributes = True


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


class FuncionarioPdvProdutoResponse(BaseModel):
    id: int
    nome: str
    codigo: Optional[str] = None
    codigo_barras: Optional[str] = None
    unidade: str = "UN"
    preco_venda: float = 0
    estoque_atual: float = 0
    imagem_url: Optional[str] = None
    tipo_produto: Optional[str] = None
    tipo_kit: Optional[str] = None
    vendavel: bool = True
    aviso: Optional[str] = None


class FuncionarioPdvClienteResponse(BaseModel):
    id: int
    codigo: Optional[str] = None
    nome: str
    telefone: Optional[str] = None
    celular: Optional[str] = None
    documento: Optional[str] = None
    tipo_cadastro: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    credito: float = 0
    fidelidade: Optional[dict] = None
    cupons_disponiveis: list[dict] = Field(default_factory=list)


class FuncionarioPdvCaixaResponse(BaseModel):
    aberto: bool
    caixa_id: Optional[int] = None
    numero_caixa: Optional[int] = None
    mensagem: str


class FuncionarioPdvItemRequest(BaseModel):
    produto_id: int
    quantidade: float = Field(gt=0)
    preco_unitario: float = Field(ge=0)


class FuncionarioPdvPagamentoRequest(BaseModel):
    forma_pagamento: str
    valor: float = Field(ge=0)
    valor_recebido: Optional[float] = None
    troco: Optional[float] = None
    numero_parcelas: int = Field(default=1, ge=1)
    forma_pagamento_id: Optional[int] = None
    bandeira: Optional[str] = None
    operadora: Optional[str] = None
    nsu_cartao: Optional[str] = None


class FuncionarioPdvFinalizarRequest(BaseModel):
    cliente_id: Optional[int] = None
    itens: list[FuncionarioPdvItemRequest]
    pagamento: FuncionarioPdvPagamentoRequest
    observacoes: Optional[str] = None
    cupom_codigo: Optional[str] = None
    desconto_cupom: Optional[float] = Field(default=0, ge=0)
    cashback_valor: Optional[float] = Field(default=0, ge=0)


class FuncionarioPdvSalvarRequest(BaseModel):
    cliente_id: Optional[int] = None
    itens: list[FuncionarioPdvItemRequest]
    observacoes: Optional[str] = None
    cupom_codigo: Optional[str] = None
    desconto_cupom: Optional[float] = Field(default=0, ge=0)
    cashback_valor: Optional[float] = Field(default=0, ge=0)


class FuncionarioPdvFormaPagamentoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    key: str
    taxa_percentual: float = 0
    permite_parcelamento: bool = False
    numero_parcelas: int = 1
    max_parcelas: int = 1
    parcelas_maximas: int = 1
    operadora: Optional[str] = None
    requer_nsu: bool = False
    tipo_cartao: Optional[str] = None
    bandeira: Optional[str] = None
    split_parcelas: bool = False


class FuncionarioPdvBeneficioCupomResponse(BaseModel):
    code: str
    coupon_type: str
    discount_value: Optional[float] = None
    discount_percent: Optional[float] = None
    discount_applied: float = 0
    min_purchase_value: Optional[float] = None
    valid_until: Optional[str] = None


class FuncionarioPdvBeneficiosPreviewRequest(BaseModel):
    cliente_id: Optional[int] = None
    itens: list[FuncionarioPdvItemRequest]
    cupom_codigo: Optional[str] = None
    cashback_valor: Optional[float] = Field(default=0, ge=0)


class FuncionarioPdvBeneficiosPreviewResponse(BaseModel):
    subtotal: float
    desconto_cupom: float
    cupom_code: Optional[str] = None
    cashback_disponivel: float
    cashback_valor: float
    total_venda: float
    valor_pagamento: float
    cupons_disponiveis: list[FuncionarioPdvBeneficioCupomResponse] = Field(default_factory=list)
    beneficios_gerados: list[dict] = Field(default_factory=list)
    mensagens: list[str] = Field(default_factory=list)


class FuncionarioPdvFinalizarResponse(BaseModel):
    status: str
    venda_id: int
    numero_venda: str
    total: float
    total_pago: float
    forma_pagamento: str
    mensagem: str


class FuncionarioPdvSalvarResponse(BaseModel):
    status: str
    venda_id: int
    numero_venda: str
    total: float
    mensagem: str


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _get_cliente_or_404(db: Session, user: User) -> Cliente:
    """Retorna o Cliente ligado a este usuário ecommerce ou lança 404."""
    cliente = _get_or_create_cliente_for_user(db, user)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de cliente não encontrado. Contate a loja.",
        )
    return cliente


def _get_funcionario_operacional_or_403(db: Session, user: User) -> tuple[Cliente, str]:
    tenant_id = _activate_user_tenant_context(user)
    funcionario = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.user_id == user.id,
            Cliente.tipo_cadastro == "funcionario",
            Cliente.ativo == True,
        )
        .first()
    )
    if not funcionario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso exclusivo para funcionario operacional.",
        )
    return funcionario, tenant_id


def _produto_permite_balanco_funcionario(produto: Produto) -> tuple[bool, Optional[str]]:
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


def _barcode_filters_for_produto(barcode: str) -> list:
    barcode = (barcode or "").strip()
    barcode_digits = "".join(ch for ch in barcode if ch.isdigit())
    codigo_barras_digits = func.regexp_replace(func.coalesce(Produto.codigo_barras, ""), r"\D", "", "g")
    gtin_digits = func.regexp_replace(func.coalesce(Produto.gtin_ean, ""), r"\D", "", "g")
    gtin_tributario_digits = func.regexp_replace(func.coalesce(Produto.gtin_ean_tributario, ""), r"\D", "", "g")
    filtros_codigo = [
        Produto.codigo_barras == barcode,
        Produto.gtin_ean == barcode,
        Produto.gtin_ean_tributario == barcode,
        Produto.codigo == barcode,
        Produto.codigos_barras_alternativos.ilike(f"%{barcode}%"),
    ]
    if barcode_digits:
        filtros_codigo.extend([
            codigo_barras_digits == barcode_digits,
            gtin_digits == barcode_digits,
            gtin_tributario_digits == barcode_digits,
            Produto.codigo == barcode_digits,
            Produto.codigos_barras_alternativos.ilike(f"%{barcode_digits}%"),
        ])
    return filtros_codigo


def _tokens_busca_produto_funcionario(termo: str) -> list[str]:
    texto = (termo or "").strip()
    for separador in ["/", "\\", "-", "_", ".", ",", ";", ":", "|", "(", ")"]:
        texto = texto.replace(separador, " ")
    return [token for token in texto.split() if len(token.strip()) >= 2]


def _termo_parece_codigo_produto_funcionario(termo: str) -> bool:
    texto = (termo or "").strip()
    if not texto or any(ch.isspace() for ch in texto):
        return False
    return any(ch.isdigit() for ch in texto)


def _produto_busca_texto_funcionario(termo: str):
    return or_(
        Produto.nome.ilike(f"%{termo}%"),
        Produto.codigo.ilike(f"%{termo}%"),
        Produto.codigo_barras.ilike(f"%{termo}%"),
        Produto.gtin_ean.ilike(f"%{termo}%"),
        Produto.gtin_ean_tributario.ilike(f"%{termo}%"),
        Produto.codigos_barras_alternativos.ilike(f"%{termo}%"),
    )


def _produto_busca_filtros_funcionario(termo: str) -> list:
    termo = (termo or "").strip()
    tokens = _tokens_busca_produto_funcionario(termo)
    filtros = [_produto_busca_texto_funcionario(termo)]

    if len(tokens) > 1:
        filtros.append(and_(*[_produto_busca_texto_funcionario(token) for token in tokens]))

    if _termo_parece_codigo_produto_funcionario(termo):
        filtros.extend(_barcode_filters_for_produto(termo))

    return filtros


def _produto_busca_rank_funcionario(termo: str):
    termo = (termo or "").strip()
    tokens = _tokens_busca_produto_funcionario(termo)
    condicoes = []

    if _termo_parece_codigo_produto_funcionario(termo):
        condicoes.extend([
            (Produto.codigo == termo, 0),
            (Produto.codigo_barras == termo, 0),
            (Produto.gtin_ean == termo, 0),
            (Produto.gtin_ean_tributario == termo, 0),
        ])

    condicoes.append((Produto.nome.ilike(f"%{termo}%"), 1))
    if len(tokens) > 1:
        condicoes.append((and_(*[Produto.nome.ilike(f"%{token}%") for token in tokens]), 2))
        condicoes.append((and_(*[_produto_busca_texto_funcionario(token) for token in tokens]), 3))

    condicoes.extend([
        (Produto.codigo.ilike(f"%{termo}%"), 4),
        (Produto.codigo_barras.ilike(f"%{termo}%"), 5),
        (Produto.gtin_ean.ilike(f"%{termo}%"), 5),
        (Produto.codigos_barras_alternativos.ilike(f"%{termo}%"), 6),
    ])
    return case(*condicoes, else_=9)


def _somente_digitos_funcionario_pdv(valor: Optional[str]) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _serialize_funcionario_pdv_produto(produto: Produto) -> dict:
    vendavel = (
        bool(produto.ativo)
        and produto.situacao is not False
        and produto.tipo_produto in ["SIMPLES", "VARIACAO", "KIT"]
    )
    return {
        "id": produto.id,
        "nome": produto.nome,
        "codigo": produto.codigo,
        "codigo_barras": produto.codigo_barras,
        "unidade": produto.unidade or "UN",
        "preco_venda": float(produto.preco_venda or 0),
        "estoque_atual": float(produto.estoque_atual or 0),
        "imagem_url": produto.imagem_principal,
        "tipo_produto": produto.tipo_produto,
        "tipo_kit": produto.tipo_kit,
        "vendavel": vendavel,
        "aviso": None if vendavel else "Produto nao vendavel no PDV.",
    }


def _serialize_funcionario_pdv_cliente(cliente: Cliente) -> dict:
    documento = cliente.cpf or cliente.cnpj
    partes_endereco = [
        getattr(cliente, "endereco", None),
        getattr(cliente, "numero", None),
        getattr(cliente, "bairro", None),
        getattr(cliente, "cidade", None),
        getattr(cliente, "estado", None),
    ]
    endereco = ", ".join(str(parte).strip() for parte in partes_endereco if str(parte or "").strip()) or None
    credito = (
        getattr(cliente, "credito", None)
        or getattr(cliente, "saldo_credito", None)
        or getattr(cliente, "credito_cliente", None)
        or 0
    )
    fidelidade = {
        "pontos": int(getattr(cliente, "pontos_fidelidade", None) or getattr(cliente, "pontos", None) or 0),
        "carimbos": int(getattr(cliente, "carimbos_fidelidade", None) or getattr(cliente, "carimbos", None) or 0),
    }
    return {
        "id": cliente.id,
        "codigo": cliente.codigo,
        "nome": cliente.nome or cliente.nome_fantasia or cliente.razao_social or f"Cliente #{cliente.id}",
        "telefone": cliente.telefone,
        "celular": cliente.celular,
        "documento": documento,
        "tipo_cadastro": cliente.tipo_cadastro,
        "email": cliente.email,
        "endereco": endereco,
        "credito": float(credito or 0),
        "fidelidade": fidelidade,
        "cupons_disponiveis": [],
    }


def _obter_caixa_aberto_funcionario_pdv(db: Session, tenant_id: str, current_user: User) -> Optional[Caixa]:
    prioridade_usuario_atual = case((Caixa.usuario_id == current_user.id, 0), else_=1)
    return (
        db.query(Caixa)
        .filter(
            Caixa.tenant_id == tenant_id,
            Caixa.status == "aberto",
        )
        .order_by(prioridade_usuario_atual.asc(), Caixa.id.desc())
        .first()
    )


def _normalizar_forma_pagamento_pdv(forma_pagamento: str) -> str:
    forma = (forma_pagamento or "").strip().lower()
    mapa = {
        "dinheiro": "Dinheiro",
        "pix": "PIX",
        "credito": "cartao_credito",
        "cartao_credito": "cartao_credito",
        "cartao de credito": "cartao_credito",
        "debito": "cartao_debito",
        "cartao_debito": "cartao_debito",
        "cartao de debito": "cartao_debito",
        "cashback": "Cashback",
    }
    if forma not in mapa:
        raise HTTPException(status_code=400, detail="Forma de pagamento invalida para o PDV mobile.")
    return mapa[forma]


def _forma_pagamento_key_funcionario_pdv(forma_pagamento: FormaPagamento) -> Optional[str]:
    texto = f"{forma_pagamento.tipo or ''} {forma_pagamento.nome or ''} {forma_pagamento.tipo_cartao or ''}".lower()
    if "credito" in texto or "crédito" in texto:
        return "credito"
    if "debito" in texto or "débito" in texto:
        return "debito"
    if "pix" in texto:
        return "pix"
    if "dinheiro" in texto:
        return "dinheiro"
    return None


def _resolver_forma_pagamento_cartao_funcionario_pdv(
    db: Session,
    tenant_id: str,
    pagamento: FuncionarioPdvPagamentoRequest,
) -> Optional[FormaPagamento]:
    forma_key = (pagamento.forma_pagamento or "").strip().lower()
    if forma_key not in {"credito", "debito", "cartao_credito", "cartao_debito"}:
        return None

    forma_normalizada = "credito" if "credito" in forma_key else "debito"
    query = db.query(FormaPagamento).filter(
        FormaPagamento.tenant_id == tenant_id,
        FormaPagamento.ativo == True,
    )

    if pagamento.forma_pagamento_id:
        forma = query.filter(FormaPagamento.id == pagamento.forma_pagamento_id).first()
        if not forma:
            raise HTTPException(status_code=400, detail="Forma de pagamento do cartao nao encontrada.")
        if _forma_pagamento_key_funcionario_pdv(forma) != forma_normalizada:
            raise HTTPException(status_code=400, detail="Forma de pagamento nao corresponde ao tipo de cartao selecionado.")
    else:
        formas_cartao = [
            forma
            for forma in query.order_by(FormaPagamento.nome.asc()).all()
            if _forma_pagamento_key_funcionario_pdv(forma) == forma_normalizada
        ]
        if len(formas_cartao) != 1:
            raise HTTPException(status_code=400, detail="Selecione a bandeira/operadora do cartao.")
        forma = formas_cartao[0]

    max_parcelas = max(1, int(forma.parcelas_maximas or forma.max_parcelas or 1))
    numero_parcelas = max(1, int(pagamento.numero_parcelas or 1))
    pode_parcelar = forma_normalizada == "credito" and (bool(forma.permite_parcelamento) or bool(forma.split_parcelas))

    if forma_normalizada == "debito" and numero_parcelas != 1:
        raise HTTPException(status_code=400, detail="Cartao de debito deve ser registrado em 1 parcela.")
    if forma_normalizada == "credito" and numero_parcelas > 1 and not pode_parcelar:
        raise HTTPException(status_code=400, detail="Esta forma de credito nao permite parcelamento.")
    if forma_normalizada == "credito" and numero_parcelas > max_parcelas:
        raise HTTPException(status_code=400, detail=f"Esta forma de credito permite no maximo {max_parcelas}x.")

    return forma


def _round_money_funcionario_pdv(valor) -> float:
    return round(float(valor or 0), 2)


def _buscar_cliente_pdv_funcionario(db: Session, tenant_id: str, cliente_id: Optional[int]) -> Optional[Cliente]:
    if not cliente_id:
        return None
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id,
            Cliente.ativo == True,
        )
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada.")
    return cliente


def _listar_cupons_disponiveis_funcionario_pdv(
    db: Session,
    *,
    tenant_id: str,
    cliente_id: Optional[int],
    subtotal: float,
) -> list[dict]:
    filtros_cliente = [Coupon.customer_id.is_(None)]
    if cliente_id:
        filtros_cliente.append(Coupon.customer_id == cliente_id)

    cupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.status == CouponStatusEnum.active,
            Coupon.channel.in_([CouponChannelEnum.pdv, CouponChannelEnum.all]),
            or_(*filtros_cliente),
        )
        .order_by(Coupon.created_at.desc())
        .limit(20)
        .all()
    )

    disponiveis = []
    for cupom in cupons:
        try:
            preview = preview_coupon_redemption(
                db,
                tenant_id=tenant_id,
                code=cupom.code,
                venda_total=subtotal,
                customer_id=cliente_id,
            )
        except HTTPException:
            continue

        disponiveis.append(
            {
                "code": preview["code"],
                "coupon_type": preview["coupon_type"],
                "discount_value": preview.get("discount_value"),
                "discount_percent": preview.get("discount_percent"),
                "discount_applied": _round_money_funcionario_pdv(preview.get("discount_applied")),
                "min_purchase_value": (
                    float(cupom.min_purchase_value) if cupom.min_purchase_value else None
                ),
                "valid_until": cupom.valid_until.isoformat() if cupom.valid_until else None,
            }
        )
    return disponiveis


def _saldo_cashback_funcionario_pdv(
    db: Session,
    *,
    tenant_id: str,
    cliente_id: Optional[int],
) -> float:
    if not cliente_id:
        return 0.0
    saldo_raw = (
        db.query(func.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente_id,
            _cashback_disponivel_clause(CashbackTransaction, datetime.now(timezone.utc)),
        )
        .scalar()
    )
    return max(0.0, _round_money_funcionario_pdv(saldo_raw))


def _cashback_bonus_param_key_funcionario_pdv(sale_channel: str) -> str:
    channel = normalize_benefit_channel(sale_channel)
    if channel == "app":
        return "app_bonus_percent"
    if channel == "ecommerce":
        return "ecommerce_bonus_percent"
    return "pdv_bonus_percent"


def _param_float_funcionario_pdv(params: dict, *keys: str, default: float = 0) -> float:
    for key in keys:
        valor = params.get(key)
        if valor is None or valor == "":
            continue
        try:
            return float(valor)
        except (TypeError, ValueError):
            continue
    return default


def _param_int_funcionario_pdv(params: dict, *keys: str, default: int = 0) -> int:
    for key in keys:
        valor = params.get(key)
        if valor is None or valor == "":
            continue
        try:
            return int(float(valor))
        except (TypeError, ValueError):
            continue
    return default


def _calcular_beneficios_gerados_funcionario_pdv(
    db: Session,
    *,
    tenant_id: str,
    cliente_id: Optional[int],
    total_venda: float,
) -> list[dict]:
    if total_venda <= 0:
        return []

    sale_channel = "loja_fisica"
    campanhas = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.status == CampaignStatusEnum.active,
            Campaign.campaign_type.in_([
                CampaignTypeEnum.cashback,
                CampaignTypeEnum.loyalty_stamp,
                CampaignTypeEnum.quick_repurchase,
            ]),
        )
        .order_by(Campaign.priority.asc(), Campaign.id.asc())
        .all()
    )

    beneficios: list[dict] = []
    for campanha in campanhas:
        if not campaign_allows_sale_channel(campanha, sale_channel):
            continue

        params = campanha.params or {}
        min_purchase_value = _param_float_funcionario_pdv(
            params,
            "min_purchase_value",
            "valor_minimo",
            "minimum_purchase",
            default=0,
        )
        if min_purchase_value and total_venda + 0.01 < min_purchase_value:
            continue

        tipo_campanha = campanha.campaign_type
        if tipo_campanha == CampaignTypeEnum.cashback:
            percentual = _param_float_funcionario_pdv(
                params,
                "cashback_percent",
                "percentual_cashback",
                "percentual",
                default=0,
            )
            percentual += _param_float_funcionario_pdv(
                params,
                _cashback_bonus_param_key_funcionario_pdv(sale_channel),
                default=0,
            )
            valor_cashback = _round_money_funcionario_pdv(total_venda * percentual / 100)
            if valor_cashback > 0:
                beneficios.append({
                    "tipo": "cashback",
                    "titulo": campanha.name or "Cashback",
                    "valor": valor_cashback,
                    "descricao": f"{percentual:.2f}% sobre a venda",
                    "cliente_id": cliente_id,
                })
            continue

        if tipo_campanha == CampaignTypeEnum.loyalty_stamp:
            stamps_per_purchase = max(1, _param_int_funcionario_pdv(
                params,
                "stamps_per_purchase",
                "carimbos_por_compra",
                "stamp_count",
                default=1,
            ))
            if min_purchase_value > 0:
                quantidade = max(1, int(total_venda // min_purchase_value)) * stamps_per_purchase
            else:
                quantidade = stamps_per_purchase
            beneficios.append({
                "tipo": "fidelidade",
                "titulo": campanha.name or "Cartao fidelidade",
                "quantidade": quantidade,
                "descricao": f"{quantidade} carimbo(s) previstos",
                "cliente_id": cliente_id,
            })
            continue

        if tipo_campanha == CampaignTypeEnum.quick_repurchase:
            valor_cupom = _param_float_funcionario_pdv(
                params,
                "coupon_value",
                "valor_cupom",
                "discount_value",
                default=0,
            )
            percentual_cupom = _param_float_funcionario_pdv(
                params,
                "coupon_percent",
                "percentual_cupom",
                "discount_percent",
                default=0,
            )
            if valor_cupom > 0 or percentual_cupom > 0:
                beneficios.append({
                    "tipo": "cupom",
                    "titulo": campanha.name or "Cupom de recompra",
                    "valor": valor_cupom,
                    "percentual": percentual_cupom,
                    "descricao": "Cupom previsto apos a venda",
                    "cliente_id": cliente_id,
                })

    return beneficios


def _aplicar_desconto_cupom_nos_itens_funcionario_pdv(
    itens_payload: list[dict],
    desconto_total: float,
) -> list[dict]:
    desconto_total = min(_round_money_funcionario_pdv(desconto_total), sum(item["subtotal"] for item in itens_payload))
    if desconto_total <= 0:
        return itens_payload

    total_bruto = sum(item["subtotal"] for item in itens_payload)
    restante = desconto_total
    itens_com_desconto = []
    for indice, item in enumerate(itens_payload):
        item_ajustado = dict(item)
        if indice == len(itens_payload) - 1:
            desconto_item = restante
        else:
            desconto_item = _round_money_funcionario_pdv(desconto_total * item["subtotal"] / total_bruto)
            desconto_item = min(desconto_item, item["subtotal"], restante)
            restante = _round_money_funcionario_pdv(restante - desconto_item)

        item_ajustado["desconto_item"] = _round_money_funcionario_pdv(
            float(item_ajustado.get("desconto_item") or 0) + desconto_item
        )
        item_ajustado["subtotal"] = _round_money_funcionario_pdv(item_ajustado["subtotal"] - desconto_item)
        itens_com_desconto.append(item_ajustado)

    return itens_com_desconto


def _calcular_beneficios_funcionario_pdv(
    db: Session,
    *,
    tenant_id: str,
    cliente_id: Optional[int],
    itens: list[FuncionarioPdvItemRequest],
    cupom_codigo: Optional[str] = None,
    cashback_valor: Optional[float] = None,
) -> dict:
    if not itens:
        raise HTTPException(status_code=400, detail="Adicione ao menos um item para vender.")

    _buscar_cliente_pdv_funcionario(db, tenant_id, cliente_id)

    itens_payload = []
    subtotal_bruto = 0.0
    for item in itens:
        produto = (
            db.query(Produto)
            .filter(
                Produto.id == item.produto_id,
                Produto.tenant_id == tenant_id,
                Produto.ativo == True,
                Produto.situacao.is_not(False),
                Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            )
            .first()
        )
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto ID {item.produto_id} nao encontrado.")

        preco_unitario = float(produto.preco_venda or item.preco_unitario or 0)
        if preco_unitario <= 0:
            raise HTTPException(status_code=400, detail=f"Produto '{produto.nome}' esta sem preco de venda.")

        quantidade = float(item.quantidade)
        subtotal_item = _round_money_funcionario_pdv(quantidade * preco_unitario)
        subtotal_bruto = _round_money_funcionario_pdv(subtotal_bruto + subtotal_item)
        itens_payload.append(
            {
                "tipo": "produto",
                "produto_id": produto.id,
                "quantidade": quantidade,
                "preco_unitario": preco_unitario,
                "desconto_item": 0,
                "subtotal": subtotal_item,
            }
        )

    cupom_code = None
    desconto_cupom = 0.0
    if cupom_codigo:
        preview_cupom = preview_coupon_redemption(
            db,
            tenant_id=tenant_id,
            code=cupom_codigo,
            venda_total=subtotal_bruto,
            customer_id=cliente_id,
        )
        cupom_code = preview_cupom["code"]
        desconto_cupom = _round_money_funcionario_pdv(preview_cupom.get("discount_applied"))

    itens_payload = _aplicar_desconto_cupom_nos_itens_funcionario_pdv(itens_payload, desconto_cupom)
    total_venda = _round_money_funcionario_pdv(sum(item["subtotal"] for item in itens_payload))

    cashback_disponivel = _saldo_cashback_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=cliente_id,
    )
    cashback_solicitado = _round_money_funcionario_pdv(cashback_valor)
    mensagens: list[str] = []
    if cashback_solicitado > 0 and not cliente_id:
        raise HTTPException(status_code=400, detail="Selecione um cliente para usar cashback.")
    if cashback_solicitado > cashback_disponivel + 0.01:
        raise HTTPException(status_code=400, detail="Cashback solicitado maior que o saldo disponivel.")

    cashback_usado = min(cashback_solicitado, total_venda)
    if cashback_solicitado > total_venda:
        mensagens.append("Cashback limitado ao total da venda apos descontos.")
    cashback_usado = _round_money_funcionario_pdv(cashback_usado)
    valor_pagamento = _round_money_funcionario_pdv(total_venda - cashback_usado)

    cupons_disponiveis = _listar_cupons_disponiveis_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        subtotal=subtotal_bruto,
    )
    beneficios_gerados = _calcular_beneficios_gerados_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        total_venda=total_venda,
    )

    return {
        "itens_payload": itens_payload,
        "subtotal": subtotal_bruto,
        "desconto_cupom": desconto_cupom,
        "cupom_code": cupom_code,
        "cashback_disponivel": cashback_disponivel,
        "cashback_valor": cashback_usado,
        "total_venda": total_venda,
        "valor_pagamento": valor_pagamento,
        "cupons_disponiveis": cupons_disponiveis,
        "beneficios_gerados": beneficios_gerados,
        "mensagens": mensagens,
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

    nome_lote = (numero_lote or f"{produto.codigo}-{datetime.now().strftime('%Y%m%d%H%M%S')}").strip()
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


def _consumir_lotes_balanco_funcionario(db: Session, produto: Produto, quantidade: float) -> str | None:
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


def _gerar_codigo_pet(db: Session, user_id: int) -> str:
    """Gera código único para o pet (ex.: PET-3A7F1C2B)."""
    for _ in range(10):
        codigo = f"PET-{secrets.token_hex(4).upper()}"
        if not db.query(Pet).filter(Pet.codigo == codigo).first():
            return codigo
    raise RuntimeError("Não foi possível gerar código único para o pet.")


# ─────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────

class PetCreate(BaseModel):
    nome: str
    especie: str
    raca: Optional[str] = None
    sexo: Optional[str] = None
    castrado: bool = False
    data_nascimento: Optional[datetime] = None
    idade_aproximada: Optional[int] = None
    peso: Optional[float] = None
    porte: Optional[str] = None
    cor: Optional[str] = None
    alergias: Optional[str] = None
    observacoes: Optional[str] = None
    foto_url: Optional[str] = None


class PetUpdate(BaseModel):
    nome: Optional[str] = None
    especie: Optional[str] = None
    raca: Optional[str] = None
    sexo: Optional[str] = None
    castrado: Optional[bool] = None
    data_nascimento: Optional[datetime] = None
    idade_aproximada: Optional[int] = None
    peso: Optional[float] = None
    porte: Optional[str] = None
    cor: Optional[str] = None
    alergias: Optional[str] = None
    observacoes: Optional[str] = None
    foto_url: Optional[str] = None


class PushTokenPayload(BaseModel):
    token: str
    plataforma: Optional[str] = None  # "android" | "ios"


class PetCarteirinhaResponse(BaseModel):
    pet: dict
    alertas: list[dict]
    status_vacinal: dict
    consultas: list[dict]
    exames: list[dict]


# ─────────────────────────────────────────
# Serialização
# ─────────────────────────────────────────

def _serialize_pet(pet: Pet) -> dict:
    return {
        "id": pet.id,
        "codigo": pet.codigo,
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "castrado": pet.castrado,
        "data_nascimento": pet.data_nascimento.isoformat() if pet.data_nascimento else None,
        "idade_aproximada": pet.idade_aproximada,
        "peso": pet.peso,
        "porte": pet.porte,
        "cor": pet.cor,
        "alergias": pet.alergias,
        "alergias_lista": getattr(pet, "alergias_lista", None) or [],
        "observacoes": pet.observacoes,
        "restricoes_alimentares_lista": getattr(pet, "restricoes_alimentares_lista", None) or [],
        "condicoes_cronicas_lista": getattr(pet, "condicoes_cronicas_lista", None) or [],
        "medicamentos_continuos_lista": getattr(pet, "medicamentos_continuos_lista", None) or [],
        "tipo_sanguineo": getattr(pet, "tipo_sanguineo", None),
        "foto_url": pet.foto_url,
    }


def _get_pet_owned_or_404(db: Session, pet_id: int, current_user: User) -> Pet:
    cliente = _get_cliente_or_404(db, current_user)
    pet = (
        db.query(Pet)
        .filter(
            Pet.id == pet_id,
            Pet.tenant_id == str(current_user.tenant_id),
            Pet.cliente_id == cliente.id,
            Pet.ativo == True,
        )
        .first()
    )
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado.")
    return pet


# ─────────────────────────────────────────
# PETS — CRUD
# ─────────────────────────────────────────

@router.get("/pets", response_model=list[PetResponse])
def listar_pets(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Lista todos os pets do cliente autenticado."""
    cliente = _get_cliente_or_404(db, current_user)
    pets = (
        db.query(Pet)
        .filter(
            Pet.tenant_id == str(current_user.tenant_id),
            Pet.cliente_id == cliente.id,
            Pet.ativo == True,
        )
        .order_by(Pet.nome)
        .all()
    )
    return [_serialize_pet(p) for p in pets]


@router.post("/pets", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
def criar_pet(
    payload: PetCreate,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Cadastra um novo pet para o cliente autenticado."""
    cliente = _get_cliente_or_404(db, current_user)
    codigo = _gerar_codigo_pet(db, current_user.id)

    pet = Pet(
        tenant_id=str(current_user.tenant_id),
        user_id=current_user.id,
        cliente_id=cliente.id,
        codigo=codigo,
        nome=payload.nome,
        especie=payload.especie,
        raca=payload.raca,
        sexo=payload.sexo,
        castrado=payload.castrado,
        data_nascimento=payload.data_nascimento,
        idade_aproximada=payload.idade_aproximada,
        peso=payload.peso,
        porte=payload.porte,
        cor=payload.cor,
        alergias=payload.alergias,
        observacoes=payload.observacoes,
        foto_url=payload.foto_url,
        ativo=True,
    )
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return _serialize_pet(pet)


@router.put("/pets/{pet_id}", response_model=PetResponse)
def atualizar_pet(
    pet_id: int,
    payload: PetUpdate,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Atualiza dados de um pet do cliente autenticado."""
    pet = _get_pet_owned_or_404(db, pet_id, current_user)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(pet, field, value)

    db.commit()
    db.refresh(pet)
    return _serialize_pet(pet)


@router.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_pet(
    pet_id: int,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Remove (soft-delete) um pet do cliente autenticado."""
    pet = _get_pet_owned_or_404(db, pet_id, current_user)

    pet.ativo = False
    db.commit()


@router.post("/pets/{pet_id}/foto", response_model=PetResponse)
async def upload_foto_pet(
    pet_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """Faz upload da foto do pet e salva em /uploads/pets/{tenant_id}/."""
    pet = _get_pet_owned_or_404(db, pet_id, current_user)

    # Valida tipo de arquivo
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não suportado. Use JPG, PNG ou WebP.")

    # Salva o arquivo em uploads/pets/{tenant_id}/
    ext = Path(file.filename or "foto.jpg").suffix or ".jpg"
    tenant_dir = PET_UPLOAD_DIR / str(current_user.tenant_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    filename = f"pet-{pet_id}-{uuid.uuid4().hex[:8]}{ext}"
    dest = tenant_dir / filename

    content = await file.read()
    dest.write_bytes(content)

    # Remove foto anterior se era um upload local
    if pet.foto_url and pet.foto_url.startswith("/uploads/pets/"):
        old_path = Path(pet.foto_url.lstrip("/"))
        if old_path.exists():
            old_path.unlink(missing_ok=True)

    pet.foto_url = f"/uploads/pets/{current_user.tenant_id}/{filename}"
    db.commit()
    db.refresh(pet)
    return _serialize_pet(pet)


@router.get("/pets/{pet_id}/carteirinha", response_model=PetCarteirinhaResponse)
def obter_carteirinha_pet_app(
    pet_id: int,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    pet = _get_pet_owned_or_404(db, pet_id, current_user)
    from app.veterinario_clinico import _montar_alertas_pet, _status_vacinal_pet

    tenant_id = str(current_user.tenant_id)
    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    consultas = db.query(ConsultaVet).filter(
        ConsultaVet.pet_id == pet.id,
        ConsultaVet.tenant_id == tenant_id,
    ).order_by(ConsultaVet.created_at.desc()).limit(10).all()
    exames = db.query(ExameVet).filter(
        ExameVet.pet_id == pet.id,
        ExameVet.tenant_id == tenant_id,
    ).order_by(ExameVet.created_at.desc()).limit(10).all()

    return {
        "pet": _serialize_pet(pet),
        "alertas": _montar_alertas_pet(db, pet, tenant_id),
        "status_vacinal": status_vacinal,
        "consultas": [
            {
                "id": consulta.id,
                "data": consulta.created_at.isoformat() if consulta.created_at else None,
                "tipo": consulta.tipo,
                "status": consulta.status,
                "diagnostico": consulta.diagnostico,
                "observacoes_tutor": consulta.observacoes_tutor,
            }
            for consulta in consultas
        ],
        "exames": [
            {
                "id": exame.id,
                "nome": exame.nome,
                "tipo": exame.tipo,
                "status": exame.status,
                "data_resultado": exame.data_resultado.isoformat() if exame.data_resultado else None,
                "interpretacao_ia_resumo": exame.interpretacao_ia_resumo,
                "arquivo_url": exame.arquivo_url,
            }
            for exame in exames
        ],
    }


@router.get("/push-status")
def obter_status_push(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    from app.campaigns.models import NotificationQueue, NotificationStatusEnum

    cliente = _get_cliente_or_404(db, current_user)
    pendentes = db.query(NotificationQueue).filter(
        NotificationQueue.tenant_id == str(current_user.tenant_id),
        NotificationQueue.customer_id == cliente.id,
        NotificationQueue.status == NotificationStatusEnum.pending,
    ).order_by(NotificationQueue.scheduled_at.asc(), NotificationQueue.created_at.desc()).limit(10).all()

    proximos_agendamentos = db.query(AgendamentoVet).filter(
        AgendamentoVet.tenant_id == str(current_user.tenant_id),
        AgendamentoVet.cliente_id == cliente.id,
        AgendamentoVet.status.in_(["agendado", "confirmado", "em_atendimento"]),
        AgendamentoVet.data_hora >= datetime.now(),
    ).order_by(AgendamentoVet.data_hora.asc()).limit(5).all()

    push_token = getattr(current_user, "push_token", None)
    return {
        "token_registrado": bool(push_token),
        "push_token_preview": f"{push_token[:18]}..." if push_token else None,
        "pendencias": [
            {
                "id": item.id,
                "assunto": item.subject,
                "mensagem": item.body,
                "scheduled_at": item.scheduled_at.isoformat() if item.scheduled_at else None,
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

@router.get("/funcionario/estoque/produtos/buscar", response_model=list[FuncionarioProdutoEstoqueResponse])
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
            Produto.ativo == True,
            Produto.situacao.is_not(False),
            or_(*filtros_busca),
        )
        .order_by(rank_busca.asc(), prioridade_estoque.asc(), Produto.is_parent.asc(), Produto.nome.asc())
        .limit(20)
        .all()
    )
    return [_serialize_funcionario_produto_estoque(produto) for produto in produtos]


@router.get("/funcionario/estoque/produtos/barcode/{barcode}", response_model=FuncionarioProdutoEstoqueResponse)
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
            Produto.ativo == True,
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
            Produto.ativo == True,
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
    observacao = observacao_base if not payload.observacao else f"{observacao_base}: {payload.observacao.strip()}"

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
        lotes_consumidos = _consumir_lotes_balanco_funcionario(db, produto, quantidade_movimentada)

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


@router.get("/funcionario/pdv/produtos/buscar", response_model=list[FuncionarioPdvProdutoResponse])
def buscar_produtos_funcionario_pdv(
    q: str = "",
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    termo = (q or "").strip()
    if len(termo) < 2:
        return []

    filtros = _produto_busca_filtros_funcionario(termo)
    rank_busca = _produto_busca_rank_funcionario(termo)
    prioridade_estoque = case((func.coalesce(Produto.estoque_atual, 0) > 0, 0), else_=1)
    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo == True,
            Produto.situacao.is_not(False),
            Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            or_(*filtros),
        )
        .order_by(rank_busca.asc(), prioridade_estoque.asc(), Produto.nome.asc())
        .limit(20)
        .all()
    )
    return [_serialize_funcionario_pdv_produto(produto) for produto in produtos]


@router.get("/funcionario/pdv/produtos/barcode/{barcode}", response_model=FuncionarioPdvProdutoResponse)
def buscar_produto_funcionario_pdv_barcode(
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
            Produto.ativo == True,
            Produto.situacao.is_not(False),
            Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            or_(*_barcode_filters_for_produto(barcode)),
        )
        .order_by(prioridade_estoque.asc(), Produto.nome.asc(), Produto.id.asc())
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto ERP nao encontrado para este codigo.")
    return _serialize_funcionario_pdv_produto(produto)


@router.get("/funcionario/pdv/clientes/buscar", response_model=list[FuncionarioPdvClienteResponse])
def buscar_clientes_funcionario_pdv(
    q: str = "",
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    termo = (q or "").strip()
    if len(termo) < 2:
        return []

    termo_digits = _somente_digitos_funcionario_pdv(termo)
    cpf_digits = func.regexp_replace(func.coalesce(Cliente.cpf, ""), r"\D", "", "g")
    cnpj_digits = func.regexp_replace(func.coalesce(Cliente.cnpj, ""), r"\D", "", "g")
    telefone_digits = func.regexp_replace(func.coalesce(Cliente.telefone, ""), r"\D", "", "g")
    celular_digits = func.regexp_replace(func.coalesce(Cliente.celular, ""), r"\D", "", "g")
    filtros = [
        Cliente.codigo.ilike(f"%{termo}%"),
        Cliente.nome.ilike(f"%{termo}%"),
        Cliente.nome_fantasia.ilike(f"%{termo}%"),
        Cliente.razao_social.ilike(f"%{termo}%"),
        Cliente.cpf.ilike(f"%{termo}%"),
        Cliente.cnpj.ilike(f"%{termo}%"),
        Cliente.telefone.ilike(f"%{termo}%"),
        Cliente.celular.ilike(f"%{termo}%"),
    ]
    if termo_digits:
        filtros.extend(
            [
                cpf_digits.ilike(f"%{termo_digits}%"),
                cnpj_digits.ilike(f"%{termo_digits}%"),
                telefone_digits.ilike(f"%{termo_digits}%"),
                celular_digits.ilike(f"%{termo_digits}%"),
            ]
        )

    clientes = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.ativo == True,
            or_(*filtros),
        )
        .order_by(Cliente.nome.asc(), Cliente.id.asc())
        .limit(20)
        .all()
    )
    return [_serialize_funcionario_pdv_cliente(cliente) for cliente in clientes]


@router.get("/funcionario/pdv/caixa/aberto", response_model=FuncionarioPdvCaixaResponse)
def obter_caixa_aberto_funcionario_pdv(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    caixa = _obter_caixa_aberto_funcionario_pdv(db, tenant_id, current_user)
    if not caixa:
        return {
            "aberto": False,
            "caixa_id": None,
            "numero_caixa": None,
            "mensagem": "Abra um caixa no ERP web antes de vender pelo app.",
        }
    return {
        "aberto": True,
        "caixa_id": caixa.id,
        "numero_caixa": caixa.numero_caixa,
        "mensagem": "Caixa aberto.",
    }


@router.get("/funcionario/pdv/formas-pagamento", response_model=list[FuncionarioPdvFormaPagamentoResponse])
def listar_formas_pagamento_funcionario_pdv(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    formas = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.ativo == True,
        )
        .order_by(FormaPagamento.nome.asc())
        .all()
    )

    resposta = []
    for forma in formas:
        key = _forma_pagamento_key_funcionario_pdv(forma)
        if not key:
            continue
        parcelas_maximas = int(forma.parcelas_maximas or forma.max_parcelas or 1)
        max_parcelas = int(forma.max_parcelas or parcelas_maximas or 1)
        numero_parcelas = max(1, parcelas_maximas, max_parcelas)
        permite_parcelamento = key == "credito" and (bool(forma.permite_parcelamento) or bool(forma.split_parcelas))
        resposta.append({
            "id": forma.id,
            "nome": forma.nome,
            "tipo": forma.tipo,
            "key": key,
            "taxa_percentual": float(forma.taxa_percentual or 0),
            "permite_parcelamento": permite_parcelamento,
            "numero_parcelas": numero_parcelas if permite_parcelamento else 1,
            "max_parcelas": numero_parcelas if permite_parcelamento else 1,
            "parcelas_maximas": numero_parcelas if permite_parcelamento else 1,
            "operadora": forma.operadora,
            "requer_nsu": bool(forma.requer_nsu),
            "tipo_cartao": forma.tipo_cartao,
            "bandeira": forma.bandeira,
            "split_parcelas": bool(forma.split_parcelas),
        })
    return resposta


@router.post("/funcionario/pdv/beneficios/preview", response_model=FuncionarioPdvBeneficiosPreviewResponse)
def preview_beneficios_funcionario_pdv(
    dados: FuncionarioPdvBeneficiosPreviewRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    beneficios = _calcular_beneficios_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=dados.cliente_id,
        itens=dados.itens,
        cupom_codigo=dados.cupom_codigo,
        cashback_valor=dados.cashback_valor,
    )
    return {
        "subtotal": beneficios["subtotal"],
        "desconto_cupom": beneficios["desconto_cupom"],
        "cupom_code": beneficios["cupom_code"],
        "cashback_disponivel": beneficios["cashback_disponivel"],
        "cashback_valor": beneficios["cashback_valor"],
        "total_venda": beneficios["total_venda"],
        "valor_pagamento": beneficios["valor_pagamento"],
        "cupons_disponiveis": beneficios["cupons_disponiveis"],
        "beneficios_gerados": beneficios["beneficios_gerados"],
        "mensagens": beneficios["mensagens"],
    }


@router.post("/funcionario/pdv/vendas/salvar", response_model=FuncionarioPdvSalvarResponse)
def salvar_venda_funcionario_pdv(
    dados: FuncionarioPdvSalvarRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    from app.vendas import VendaService

    funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    if not dados.itens:
        raise HTTPException(status_code=400, detail="Adicione ao menos um item para vender.")

    caixa = _obter_caixa_aberto_funcionario_pdv(db, tenant_id, current_user)
    if not caixa:
        raise HTTPException(status_code=400, detail="Abra um caixa no ERP web antes de salvar pelo app.")

    beneficios = _calcular_beneficios_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=dados.cliente_id,
        itens=dados.itens,
        cupom_codigo=dados.cupom_codigo,
        cashback_valor=0,
    )

    criar_payload = {
        "cliente_id": dados.cliente_id,
        "vendedor_id": current_user.id,
        "funcionario_id": funcionario.id,
        "itens": beneficios["itens_payload"],
        "desconto_valor": beneficios["desconto_cupom"],
        "desconto_percentual": 0,
        "cupom_code": beneficios["cupom_code"],
        "cupom_discount_applied": beneficios["desconto_cupom"],
        "tenant_id": tenant_id,
        "observacoes": dados.observacoes,
        "tem_entrega": False,
        "taxa_entrega": 0,
        "percentual_taxa_loja": 0,
        "percentual_taxa_entregador": 0,
        "canal": "app_funcionario",
    }
    venda_criada = VendaService.criar_venda(payload=criar_payload, user_id=current_user.id, db=db)
    return {
        "status": "aberta",
        "venda_id": venda_criada["id"],
        "numero_venda": venda_criada.get("numero_venda") or str(venda_criada["id"]),
        "total": float(venda_criada.get("total") or beneficios["total_venda"]),
        "mensagem": "Venda salva em aberto para recebimento no caixa.",
    }


@router.post("/funcionario/pdv/vendas/finalizar", response_model=FuncionarioPdvFinalizarResponse)
def finalizar_venda_funcionario_pdv(
    dados: FuncionarioPdvFinalizarRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    from app.vendas import VendaService
    from app.vendas.service import processar_comissoes_venda

    funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    if not dados.itens:
        raise HTTPException(status_code=400, detail="Adicione ao menos um item para vender.")

    caixa = _obter_caixa_aberto_funcionario_pdv(db, tenant_id, current_user)
    if not caixa:
        raise HTTPException(status_code=400, detail="Abra um caixa no ERP web antes de vender pelo app.")

    beneficios = _calcular_beneficios_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=dados.cliente_id,
        itens=dados.itens,
        cupom_codigo=dados.cupom_codigo,
        cashback_valor=dados.cashback_valor,
    )

    valor_pagamento = round(float(dados.pagamento.valor), 2)
    if abs(valor_pagamento - beneficios["valor_pagamento"]) > 0.01:
        raise HTTPException(status_code=400, detail="Valor do pagamento deve fechar o total da venda.")

    forma_pagamento = _normalizar_forma_pagamento_pdv(dados.pagamento.forma_pagamento)
    numero_parcelas = max(1, int(dados.pagamento.numero_parcelas or 1))
    forma_pagamento_selecionada = _resolver_forma_pagamento_cartao_funcionario_pdv(db, tenant_id, dados.pagamento)
    if forma_pagamento != "cartao_credito":
        numero_parcelas = max(1, min(numero_parcelas, 1))
    criar_payload = {
        "cliente_id": dados.cliente_id,
        "vendedor_id": current_user.id,
        "funcionario_id": funcionario.id,
        "itens": beneficios["itens_payload"],
        "desconto_valor": beneficios["desconto_cupom"],
        "desconto_percentual": 0,
        "cupom_code": beneficios["cupom_code"],
        "cupom_discount_applied": beneficios["desconto_cupom"],
        "tenant_id": tenant_id,
        "observacoes": dados.observacoes,
        "tem_entrega": False,
        "taxa_entrega": 0,
        "percentual_taxa_loja": 0,
        "percentual_taxa_entregador": 0,
        "canal": "app_funcionario",
    }
    venda_criada = VendaService.criar_venda(payload=criar_payload, user_id=current_user.id, db=db)

    pagamentos_payload = []
    if valor_pagamento > 0:
        pagamento_payload = {
            "forma_pagamento": forma_pagamento,
            "valor": valor_pagamento,
            "numero_parcelas": numero_parcelas,
            "forma_pagamento_id": dados.pagamento.forma_pagamento_id,
            "bandeira": dados.pagamento.bandeira or (forma_pagamento_selecionada.bandeira if forma_pagamento_selecionada else None),
            "operadora": dados.pagamento.operadora or (forma_pagamento_selecionada.operadora if forma_pagamento_selecionada else None),
            "nsu_cartao": dados.pagamento.nsu_cartao,
        }
        if dados.pagamento.valor_recebido is not None:
            pagamento_payload["valor_recebido"] = float(dados.pagamento.valor_recebido)
        if dados.pagamento.troco is not None:
            pagamento_payload["troco"] = float(dados.pagamento.troco)
        pagamentos_payload.append(pagamento_payload)

    if beneficios["cashback_valor"] > 0:
        parcelas_cashback = max(1, 1)
        pagamentos_payload.append(
            {
                "forma_pagamento": "Cashback",
                "valor": beneficios["cashback_valor"],
                "numero_parcelas": parcelas_cashback,
            }
        )

    if not pagamentos_payload:
        raise HTTPException(status_code=400, detail="Informe uma forma de pagamento valida.")

    resultado = VendaService.finalizar_venda(
        venda_id=venda_criada["id"],
        pagamentos=pagamentos_payload,
        user_id=current_user.id,
        user_nome=current_user.nome or current_user.email or "Funcionario",
        tenant_id=tenant_id,
        db=db,
        cupom_code=beneficios["cupom_code"],
        cupom_discount_applied=beneficios["desconto_cupom"],
        caixa_id=caixa.id,
        permitir_caixa_tenant=True,
    )
    processar_comissoes_venda(
        venda_id=venda_criada["id"],
        funcionario_id=funcionario.id,
        valor_pago=beneficios["total_venda"],
        user_id=current_user.id,
        db=db,
    )
    venda_resultado = resultado.get("venda", {})
    return {
        "status": venda_resultado.get("status", "finalizada"),
        "venda_id": venda_criada["id"],
        "numero_venda": venda_resultado.get("numero_venda") or venda_criada.get("numero_venda"),
        "total": float(venda_resultado.get("total") or beneficios["total_venda"]),
        "total_pago": float(venda_resultado.get("total_pago") or beneficios["total_venda"]),
        "forma_pagamento": " + ".join(p["forma_pagamento"] for p in pagamentos_payload),
        "mensagem": "Venda registrada pelo app.",
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
    barcode_digits = "".join(ch for ch in barcode if ch.isdigit())
    codigo_barras_digits = func.regexp_replace(func.coalesce(Produto.codigo_barras, ""), r"\D", "", "g")
    gtin_digits = func.regexp_replace(func.coalesce(Produto.gtin_ean, ""), r"\D", "", "g")
    gtin_tributario_digits = func.regexp_replace(func.coalesce(Produto.gtin_ean_tributario, ""), r"\D", "", "g")
    filtros_codigo = [
        Produto.codigo_barras == barcode,
        Produto.gtin_ean == barcode,
        Produto.gtin_ean_tributario == barcode,
        Produto.codigo == barcode,
        Produto.codigos_barras_alternativos.ilike(f"%{barcode}%"),
    ]
    if barcode_digits:
        filtros_codigo.extend([
            codigo_barras_digits == barcode_digits,
            gtin_digits == barcode_digits,
            gtin_tributario_digits == barcode_digits,
            Produto.codigo == barcode_digits,
            Produto.codigos_barras_alternativos.ilike(f"%{barcode_digits}%"),
        ])

    prioridade_estoque = case((func.coalesce(Produto.estoque_atual, 0) > 0, 0), else_=1)

    produto = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo == True,
            Produto.situacao.is_not(False),
            Produto.is_sellable == True,
            Produto.anunciar_app == True,
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

    oferta_validade = mapear_ofertas_validade_por_produto(db, [produto], "app").get(produto.id)
    pricing = resolver_preco_publico_produto(
        produto,
        "app",
        validity_offer=oferta_validade,
    )
    preco = float(pricing.promotional_price if pricing.promotional_price is not None else pricing.regular_price or 0)
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
            "dias_para_vencer": oferta_validade.dias_para_vencer if oferta_validade else None,
            "quantidade_promocional": oferta_validade.quantity_available if oferta_validade else None,
            "percentual_desconto": oferta_validade.percentual_desconto if oferta_validade else None,
            "preco_promocional": oferta_validade.promotional_price if oferta_validade else None,
            "mensagem": oferta_validade.message if oferta_validade else None,
        } if oferta_validade else None,
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
        return {"status": "ignored", "motivo": "Migration pendente: coluna push_token não existe."}

    current_user.push_token = payload.token
    db.commit()
    return {"status": "ok"}


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
        .filter(RotaEntregaParada.venda_id == venda.id)
        .first()
    )

    if not parada:
        return {
            "status_pedido": pedido.status,
            "tem_entrega": True,
            "mensagem": "Entrega em preparação — em breve será despachada.",
            "rota": None,
        }

    rota = db.query(RotaEntrega).filter(RotaEntrega.id == parada.rota_id).first()
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
        .filter(RotaEntregaParada.rota_id == rota.id)
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
                WHERE id = :rid
                """
            ),
            {"rid": rota.id},
        ).fetchone()

        if rota_posicao and rota_posicao[0] is not None and rota_posicao[1] is not None:
            ultima_posicao = {
                "lat": float(rota_posicao[0]),
                "lon": float(rota_posicao[1]),
                "atualizada_em": rota_posicao[2].isoformat() if rota_posicao[2] else None,
                "fonte": "rota_atual",
            }
        else:
            for p in reversed(todas_paradas):
                result = db.execute(
                    text("SELECT lat_entrega, lon_entrega FROM rotas_entrega_paradas WHERE id = :pid"),
                    {"pid": p.id}
                ).fetchone()
                if result and result[0] is not None and result[1] is not None:
                    ultima_posicao = {
                        "lat": float(result[0]),
                        "lon": float(result[1]),
                        "atualizada_em": p.data_entrega.isoformat() if p.data_entrega else None,
                        "fonte": "ultima_parada",
                    }
                    break
    except Exception:
        pass

    entregador_nome = None
    if rota.entregador_id:
        entregador = db.query(Cliente).filter(Cliente.id == rota.entregador_id).first()
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
            "data_entrega": parada.data_entrega.isoformat() if parada.data_entrega else None,
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
