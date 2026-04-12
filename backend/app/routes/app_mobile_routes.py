"""
Rotas exclusivas do App Mobile (clientes).

Prefixo : /app
Auth    : token JWT "ecommerce_customer" (mesmo fluxo do e-commerce)
"""

import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Cliente, Pet, User
from app.produtos_models import Produto
from app.routes.ecommerce_auth import _get_current_ecommerce_user
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
    foto_url: Optional[str]
    codigo_barras: Optional[str]
    unidade: str
    estoque: float


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _get_cliente_or_404(db: Session, user: User) -> Cliente:
    """Retorna o Cliente ligado a este usuário ecommerce ou lança 404."""
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == str(user.tenant_id),
            Cliente.user_id == user.id,
        )
        .first()
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de cliente não encontrado. Contate a loja.",
        )
    return cliente


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
    from app.veterinario_routes import _montar_alertas_pet, _status_vacinal_pet

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

@router.get("/produto-barcode/{barcode}", response_model=ProdutoBarcodeResponse)
def buscar_produto_barcode(
    barcode: str,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Busca produto pelo código de barras (EAN/GTIN).
    Tenta `codigo_barras` e depois `gtin_ean`.
    Retorna apenas produtos ativos do tenant.
    """
    produto = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == str(current_user.tenant_id),
            Produto.situacao == True,
            Produto.codigo_barras == barcode,
        )
        .first()
    )

    if not produto:
        produto = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == str(current_user.tenant_id),
                Produto.situacao == True,
                Produto.gtin_ean == barcode,
            )
            .first()
        )

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado para este código de barras.",
        )

    preco = float(produto.preco_venda or 0)
    preco_original = float(produto.preco_promocional or produto.preco_venda or 0) if produto.preco_promocional else preco

    return {
        "id": produto.id,
        "nome": produto.nome,
        "preco": preco,
        "preco_original": preco_original,
        "foto_url": produto.imagem_principal,
        "codigo_barras": produto.codigo_barras,
        "unidade": produto.unidade or "UN",
        "estoque": float(produto.estoque_atual or 0),
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

    # Verificar se o pedido pertence ao cliente
    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.tenant_id == str(current_user.tenant_id),
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
            Venda.tenant_id == str(current_user.tenant_id),
            Venda.canal.in_(["ecommerce", "aplicativo"]),
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
