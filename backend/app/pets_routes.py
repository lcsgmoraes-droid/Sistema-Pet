"""
Módulo dedicado para gestão de PETS
Separado do cadastro de clientes para permitir evolução veterinária
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime as dt
import secrets

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .models import Cliente, Pet, Tenant
from .pet_clinical_utils import normalize_clinical_list, normalize_pet_clinical_payload
from .services import pet_registros_clinicos_service as registros_service
from .security.permissions_decorator import require_permission
from sqlalchemy.orm import object_session
from app.partner_utils import get_all_accessible_tenant_ids

from pydantic import BaseModel, Field


# ============================================================
# SCHEMAS
# ============================================================


class PetBase(BaseModel):
    """Dados base do pet"""

    nome: str = Field(..., min_length=1, max_length=255)
    especie: str = Field(..., min_length=1, max_length=50)
    raca: Optional[str] = Field(None, max_length=100)
    sexo: Optional[str] = Field(None, max_length=10)
    castrado: bool = False

    # Características
    data_nascimento: Optional[dt] = None
    idade_aproximada: Optional[int] = None  # em meses
    peso: Optional[float] = None
    cor: Optional[str] = Field(None, max_length=100)
    porte: Optional[str] = Field(None, max_length=20)

    # Saúde
    microchip: Optional[str] = Field(None, max_length=50)
    alergias: Optional[str] = None
    alergias_lista: List[str] = Field(default_factory=list)
    doencas_cronicas: Optional[str] = None
    condicoes_cronicas_lista: List[str] = Field(default_factory=list)
    medicamentos_continuos: Optional[str] = None
    medicamentos_continuos_lista: List[str] = Field(default_factory=list)
    restricoes_alimentares_lista: List[str] = Field(default_factory=list)
    historico_clinico: Optional[str] = None
    tipo_sanguineo: Optional[str] = Field(None, max_length=20)
    pedigree_registro: Optional[str] = Field(None, max_length=100)
    castrado_data: Optional[date] = None

    # Outros
    observacoes: Optional[str] = None
    foto_url: Optional[str] = Field(None, max_length=500)
    ativo: bool = True


class PetCreate(PetBase):
    """Schema para criação de pet"""

    cliente_id: int = Field(..., gt=0)


class PetUpdate(PetBase):
    """Schema para atualização de pet (todos os campos opcionais)"""

    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    especie: Optional[str] = Field(None, min_length=1, max_length=50)
    cliente_id: Optional[int] = Field(None, gt=0)


class PetResponse(PetBase):
    """Schema de resposta do pet"""

    id: int
    codigo: str
    cliente_id: int
    user_id: int
    # A base inicial permitia timestamps nulos. Mantemos a resposta compatível
    # com esses registros antigos para que um único pet legado não derrube toda
    # a listagem.
    created_at: Optional[dt] = None
    updated_at: Optional[dt] = None

    # Dados do cliente (tutor)
    cliente_nome: Optional[str] = None
    cliente_telefone: Optional[str] = None
    cliente_celular: Optional[str] = None
    # Campo de parceria (True = pertence ao tenant parceiro)
    de_parceiro: bool = False

    class Config:
        from_attributes = True


class PetListItem(BaseModel):
    """Item simplificado para listagem"""

    id: int
    codigo: str
    nome: str
    especie: str
    raca: Optional[str]
    sexo: Optional[str]
    ativo: bool
    cliente_id: int
    cliente_nome: str
    created_at: dt

    class Config:
        from_attributes = True


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(prefix="/pets", tags=["pets"])


# ============================================================
# HELPERS
# ============================================================


def gerar_codigo_pet(db: Session, user_id: int) -> str:
    """Gera código único para o pet"""
    while True:
        codigo = f"PET-{secrets.token_hex(4).upper()}"
        existe = (
            db.query(Pet).filter(Pet.codigo == codigo, Pet.user_id == user_id).first()
        )
        if not existe:
            return codigo


def enriquecer_pet_response(pet: Pet, de_parceiro: bool = False) -> dict:
    """Adiciona dados do cliente ao response"""
    pet_dict = {
        "id": pet.id,
        "codigo": pet.codigo,
        "cliente_id": pet.cliente_id,
        "user_id": pet.user_id,
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        # Registros antigos podem ter NULL mesmo com o campo atual sendo booleano.
        # A listagem deve entregar um valor previsivel ao frontend.
        "castrado": bool(pet.castrado),
        "data_nascimento": pet.data_nascimento,
        "idade_aproximada": pet.idade_aproximada,
        "peso": _ultimo_peso_do_pet(pet),
        "cor": pet.cor,
        "porte": pet.porte,
        "microchip": pet.microchip,
        "alergias": pet.alergias,
        "alergias_lista": normalize_clinical_list(pet.alergias_lista),
        "doencas_cronicas": pet.doencas_cronicas,
        "condicoes_cronicas_lista": normalize_clinical_list(
            pet.condicoes_cronicas_lista
        ),
        "medicamentos_continuos": pet.medicamentos_continuos,
        "medicamentos_continuos_lista": normalize_clinical_list(
            pet.medicamentos_continuos_lista
        ),
        "restricoes_alimentares_lista": normalize_clinical_list(
            pet.restricoes_alimentares_lista
        ),
        "historico_clinico": _ultimo_historico_do_pet(pet),
        "tipo_sanguineo": pet.tipo_sanguineo,
        "pedigree_registro": pet.pedigree_registro,
        "castrado_data": pet.castrado_data,
        "observacoes": pet.observacoes,
        "foto_url": pet.foto_url,
        "ativo": pet.ativo,
        "created_at": pet.created_at,
        "updated_at": pet.updated_at,
        "cliente_nome": pet.cliente.nome if pet.cliente else None,
        "cliente_telefone": pet.cliente.telefone if pet.cliente else None,
        "cliente_celular": pet.cliente.celular if pet.cliente else None,
        "de_parceiro": de_parceiro,
    }
    return pet_dict


# ============================================================
# ENDPOINTS
# ============================================================


def _ultimo_peso_do_pet(pet):
    # object_session() so aceita instancia ORM de verdade; pet "legado" vindo de
    # um fake/SimpleNamespace (ex.: dados de demonstracao) levanta
    # UnmappedInstanceError em vez de retornar None.
    try:
        sessao = object_session(pet)
    except Exception:
        sessao = None
    if sessao is None:
        return getattr(pet, "peso", None)
    registro = registros_service.ultimo_registro(sessao, pet.id, "peso")
    return registro.valor if registro else getattr(pet, "peso", None)


def _ultimo_historico_do_pet(pet):
    try:
        sessao = object_session(pet)
    except Exception:
        sessao = None
    if sessao is None:
        return getattr(pet, "historico_clinico", None)
    registro = registros_service.ultimo_registro(sessao, pet.id, "historico")
    return registro.texto if registro else getattr(pet, "historico_clinico", None)


@router.get("", response_model=List[PetResponse])
def listar_pets(
    busca: Optional[str] = Query(
        None, description="Busca por nome do pet, raça, microchip ou nome do tutor"
    ),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    especie: Optional[str] = Query(None, description="Filtrar por espécie"),
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todos os pets do tenant com filtros
    """
    current_user, tenant_id = user_and_tenant

    # Incluir pets de tenants parceiros (ex.: pet shop parceiro da clínica)
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)

    # Filtrar por tenant_id (multi-tenant)
    query = db.query(Pet).join(Cliente).filter(Cliente.tenant_id.in_(access_ids))
    query = query.options(joinedload(Pet.cliente))

    # Filtros
    if cliente_id:
        query = query.filter(Pet.cliente_id == cliente_id)

    if especie:
        query = query.filter(Pet.especie.ilike(f"%{especie}%"))

    if ativo is not None:
        query = query.filter(Pet.ativo == ativo)

    if busca:
        busca_term = f"%{busca}%"
        # A query base ja faz join com Cliente para filtrar por tenant.
        query = query.filter(
            or_(
                Pet.nome.ilike(busca_term),
                Pet.raca.ilike(busca_term),
                Pet.microchip.ilike(busca_term),
                Pet.codigo.ilike(busca_term),
                Cliente.nome.ilike(busca_term),  # Busca pelo nome do tutor
            )
        )

    # Ordenação: pets ativos primeiro, depois por nome
    query = query.order_by(Pet.ativo.desc(), Pet.nome.asc())

    pets = query.offset(skip).limit(limit).all()

    tenant_id_str = str(tenant_id)
    return [
        enriquecer_pet_response(
            pet,
            de_parceiro=(
                str(pet.cliente.tenant_id) != tenant_id_str if pet.cliente else False
            ),
        )
        for pet in pets
    ]


@router.post("", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
def criar_pet(
    pet_data: PetCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria um novo pet
    """
    current_user, tenant_id = user_and_tenant

    # Validar se cliente existe e pertence ao tenant
    cliente = registros_service.cliente_visivel(db, pet_data.cliente_id, tenant_id)

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    # Gerar código único
    codigo = gerar_codigo_pet(db, current_user.id)

    pet_payload = normalize_pet_clinical_payload(pet_data.model_dump())
    pet_payload.pop("cliente_id", None)
    peso_inicial = pet_payload.pop("peso", None)
    historico_inicial = pet_payload.pop("historico_clinico", None)

    # Criar pet
    novo_pet = Pet(
        user_id=current_user.id,
        tenant_id=tenant_id,
        origem_tenant_id=tenant_id,
        cliente_id=pet_data.cliente_id,
        codigo=codigo,
        **pet_payload,
    )

    db.add(novo_pet)
    db.flush()
    registros_service.registrar_se_mudou(
        db, pet_id=novo_pet.id, tenant_id=tenant_id, user_id=current_user.id, tipo="peso", novo=peso_inicial
    )
    registros_service.registrar_se_mudou(
        db, pet_id=novo_pet.id, tenant_id=tenant_id, user_id=current_user.id, tipo="historico", novo=historico_inicial
    )
    db.commit()
    db.refresh(novo_pet)

    # Carregar relacionamento
    db.refresh(novo_pet)
    pet_com_cliente = (
        db.query(Pet)
        .options(joinedload(Pet.cliente))
        .filter(Pet.id == novo_pet.id)
        .first()
    )

    return enriquecer_pet_response(pet_com_cliente)


@router.get("/{pet_id}", response_model=PetResponse)
def obter_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Obtém detalhes de um pet específico
    """
    current_user, tenant_id = user_and_tenant

    pet = registros_service.pet_visivel(db, pet_id, tenant_id)
    if pet is not None:
        pet = (
            db.query(Pet)
            .options(joinedload(Pet.cliente))
            .filter(Pet.id == pet.id)
            .first()
        )

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet não encontrado"
        )

    return enriquecer_pet_response(pet)


@router.put("/{pet_id}", response_model=PetResponse)
def atualizar_pet(
    pet_id: int,
    pet_data: PetUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza dados de um pet
    """
    current_user, tenant_id = user_and_tenant

    pet = registros_service.pet_visivel(db, pet_id, tenant_id)

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet não encontrado"
        )

    # Se mudou o cliente, validar
    if pet_data.cliente_id and pet_data.cliente_id != pet.cliente_id:
        novo_cliente = registros_service.cliente_visivel(db, pet_data.cliente_id, tenant_id)

        if not novo_cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Novo cliente não encontrado",
            )

    # Atualizar campos fornecidos
    update_data = normalize_pet_clinical_payload(
        pet_data.model_dump(exclude_unset=True)
    )
    peso_informado = update_data.pop("peso", None) if "peso" in update_data else None
    historico_informado = (
        update_data.pop("historico_clinico", None)
        if "historico_clinico" in update_data
        else None
    )
    registrar_peso = "peso" in pet_data.model_fields_set
    registrar_historico = "historico_clinico" in pet_data.model_fields_set

    # Se idade_aproximada foi fornecida, converter para data_nascimento
    if (
        "idade_aproximada" in update_data
        and update_data["idade_aproximada"] is not None
    ):
        idade_meses = update_data["idade_aproximada"]
        hoje = dt.now()
        # Calcular data de nascimento subtraindo os meses
        anos = idade_meses // 12
        meses = idade_meses % 12
        ano_nascimento = hoje.year - anos
        mes_nascimento = hoje.month - meses

        # Ajustar se o mês ficar negativo
        if mes_nascimento <= 0:
            mes_nascimento += 12
            ano_nascimento -= 1

        # Usar dia 1 como padrão
        pet.data_nascimento = dt(ano_nascimento, mes_nascimento, 1)
        # Remover idade_aproximada do update_data pois já foi processada
        del update_data["idade_aproximada"]

    for field, value in update_data.items():
        setattr(pet, field, value)

    pet.updated_at = dt.now()

    if registrar_peso:
        registros_service.registrar_se_mudou(
            db, pet_id=pet.id, tenant_id=tenant_id, user_id=current_user.id, tipo="peso", novo=peso_informado
        )
    if registrar_historico:
        registros_service.registrar_se_mudou(
            db, pet_id=pet.id, tenant_id=tenant_id, user_id=current_user.id, tipo="historico", novo=historico_informado
        )

    db.commit()
    db.refresh(pet)

    # Carregar com relacionamento
    pet_com_cliente = (
        db.query(Pet).options(joinedload(Pet.cliente)).filter(Pet.id == pet.id).first()
    )

    return enriquecer_pet_response(pet_com_cliente)


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_pet(
    pet_id: int,
    soft_delete: bool = Query(
        True, description="Se True, apenas desativa. Se False, exclui permanentemente"
    ),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Exclui ou desativa um pet (soft delete por padrão)
    """
    current_user, tenant_id = user_and_tenant

    pet = (
        db.query(Pet)
        .join(Cliente)
        .filter(Pet.id == pet_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet não encontrado"
        )

    if soft_delete:
        # Soft delete: apenas marca como inativo
        pet.ativo = False
        pet.updated_at = dt.now()
        db.commit()
    else:
        # Hard delete: remove permanentemente
        db.delete(pet)
        db.commit()

    return None


@router.post("/{pet_id}/ativar", response_model=PetResponse)
def ativar_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Reativa um pet desativado
    """
    current_user, tenant_id = user_and_tenant

    pet = (
        db.query(Pet)
        .join(Cliente)
        .filter(Pet.id == pet_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet não encontrado"
        )

    pet.ativo = True
    pet.updated_at = dt.now()
    db.commit()
    db.refresh(pet)

    pet_com_cliente = (
        db.query(Pet).options(joinedload(Pet.cliente)).filter(Pet.id == pet.id).first()
    )

    return enriquecer_pet_response(pet_com_cliente)


@router.get("/cliente/{cliente_id}", response_model=List[PetResponse])
def listar_pets_por_cliente(
    cliente_id: int,
    incluir_inativos: bool = Query(False, description="Incluir pets inativos"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todos os pets de um cliente específico
    """
    current_user, tenant_id = user_and_tenant

    # Validar cliente
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    query = (
        db.query(Pet)
        .options(joinedload(Pet.cliente))
        .join(Cliente)
        .filter(Pet.cliente_id == cliente_id, Cliente.tenant_id == tenant_id)
    )

    if not incluir_inativos:
        query = query.filter(Pet.ativo)

    pets = query.order_by(Pet.ativo.desc(), Pet.nome.asc()).all()

    return [enriquecer_pet_response(pet) for pet in pets]


class RegistroClinicoCreate(BaseModel):
    tipo: str
    texto: Optional[str] = None
    valor: Optional[float] = None
    registrado_em: Optional[dt] = None


class RegistroClinicoUpdate(BaseModel):
    texto: Optional[str] = None
    valor: Optional[float] = None
    registrado_em: Optional[dt] = None


def _serializar_registros(db: Session, registros, tenant_id):
    ids_lojas = {str(r.tenant_id) for r in registros}
    nomes = {
        str(t.id): t.name
        for t in db.query(Tenant).filter(Tenant.id.in_(ids_lojas)).all()
    } if ids_lojas else {}
    return [
        {
            "id": r.id,
            "tipo": r.tipo,
            "texto": r.texto,
            "valor": r.valor,
            "registrado_em": r.registrado_em.isoformat() if r.registrado_em else None,
            "loja_id": str(r.tenant_id),
            "loja_nome": nomes.get(str(r.tenant_id)),
            "pode_editar": str(r.tenant_id) == str(tenant_id),
        }
        for r in registros
    ]


@router.get("/{pet_id}/registros-clinicos")
def listar_registros_clinicos(
    pet_id: int,
    tipo: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    if registros_service.pet_visivel(db, pet_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Pet não encontrado")
    registros = registros_service.listar_registros(db, pet_id, tipo)
    return {"items": _serializar_registros(db, registros, tenant_id)}


@router.post("/{pet_id}/registros-clinicos", status_code=status.HTTP_201_CREATED)
@require_permission("clientes.editar")
def criar_registro_clinico(
    pet_id: int,
    payload: RegistroClinicoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    if registros_service.pet_visivel(db, pet_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Pet não encontrado")
    registro = registros_service.criar_registro(
        db,
        pet_id=pet_id,
        tenant_id=tenant_id,
        user_id=current_user.id,
        tipo=payload.tipo,
        texto=payload.texto,
        valor=payload.valor,
        registrado_em=payload.registrado_em,
    )
    db.commit()
    return _serializar_registros(db, [registro], tenant_id)[0]


@router.patch("/{pet_id}/registros-clinicos/{registro_id}")
@require_permission("clientes.editar")
def atualizar_registro_clinico(
    pet_id: int,
    registro_id: int,
    payload: RegistroClinicoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    try:
        registro = registros_service.atualizar_registro(
            db,
            registro_id=registro_id,
            pet_id=pet_id,
            tenant_id=tenant_id,
            texto=payload.texto,
            valor=payload.valor,
            registrado_em=payload.registrado_em,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    return _serializar_registros(db, [registro], tenant_id)[0]


@router.delete("/{pet_id}/registros-clinicos/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("clientes.editar")
def excluir_registro_clinico(
    pet_id: int,
    registro_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    try:
        registros_service.excluir_registro(db, registro_id=registro_id, pet_id=pet_id, tenant_id=tenant_id)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    return None
