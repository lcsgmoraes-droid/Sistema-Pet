# âš ï¸ ARQUIVO CRÃTICO DE PRODUÃ‡ÃƒO
# Este arquivo impacta diretamente operaÃ§Ãµes reais (PDV / Financeiro / Estoque).
# NÃƒO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenÃ¡rio real
# 3. Validar impacto financeiro

"""
Routes para gerenciamento de Clientes e Pets
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import case, or_, func, cast, String
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime as dt, date, timedelta
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, validator
import logging

from app.db import get_session
from app.models import User, Cliente, Pet, Raca
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.audit_log import log_create, log_update, log_delete
from app.pet_clinical_utils import normalize_pet_clinical_payload
from app.security.permissions_decorator import require_permission
from app.partner_utils import get_all_accessible_tenant_ids

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clientes", tags=["clientes"])


def _somente_digitos_coluna(coluna):
    """Normaliza telefone/celular removendo caracteres de máscara para busca numérica."""
    return func.replace(
        func.replace(
            func.replace(
                func.replace(
                    func.replace(
                        func.replace(func.coalesce(coluna, ""), "(", ""),
                        ")",
                        "",
                    ),
                    "-",
                    "",
                ),
                " ",
                "",
            ),
            "+",
            "",
        ),
        ".",
        "",
    )


# ========== HELPERS INTERNOS ==========

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant (padrÃ£o repetido 21x)"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    """Busca cliente com validaÃ§Ã£o de tenant e retorna 404 se nÃ£o encontrado"""
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nÃ£o encontrado"
        )
    
    return cliente


# ========== UTILITÃRIOS ==========

def gerar_codigo_cliente(db: Session, tipo_cadastro: str, tipo_pessoa: str, tenant_id: int) -> str:
    """
    Gera código único e crescente para o cliente neste tenant.
    Pega o maior código numérico existente (ativo ou inativo) e soma 1.
    Código nunca é reutilizado mesmo se o cliente for inativado.
    """
    from sqlalchemy import func as sqlfunc, cast as sqcast, String as SqString
    from sqlalchemy.dialects.postgresql import BIGINT

    resultado = db.query(sqlfunc.max(sqcast(Cliente.codigo, BIGINT))).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.codigo.op('~')('^[0-9]+$'),  # apenas codigos numericos
    ).scalar()

    proximo = (resultado or 10000) + 1
    return str(proximo)


# Schemas
class PetCreate(BaseModel):
    nome: str
    especie: str
    raca: Optional[str] = None
    sexo: Optional[str] = None
    data_nascimento: Optional[date] = None
    idade_aproximada: Optional[int] = None
    castrado: Optional[bool] = False
    cor: Optional[str] = None
    porte: Optional[str] = None
    peso: Optional[float] = None
    microchip: Optional[str] = None
    alergias: Optional[str] = None
    alergias_lista: List[str] = Field(default_factory=list)
    doencas_cronicas: Optional[str] = None
    condicoes_cronicas_lista: List[str] = Field(default_factory=list)
    medicamentos_continuos: Optional[str] = None
    medicamentos_continuos_lista: List[str] = Field(default_factory=list)
    restricoes_alimentares_lista: List[str] = Field(default_factory=list)
    historico_clinico: Optional[str] = None
    tipo_sanguineo: Optional[str] = None
    pedigree_registro: Optional[str] = None
    castrado_data: Optional[date] = None
    observacoes: Optional[str] = None
    foto_url: Optional[str] = None
    ativo: Optional[bool] = True

    model_config = {"from_attributes": True}


class PetUpdate(BaseModel):
    nome: Optional[str] = None
    especie: Optional[str] = None
    raca: Optional[str] = None
    sexo: Optional[str] = None
    data_nascimento: Optional[dt] = None
    idade_aproximada: Optional[int] = None
    castrado: Optional[bool] = None
    cor: Optional[str] = None
    porte: Optional[str] = None
    peso: Optional[float] = None
    microchip: Optional[str] = None
    alergias: Optional[str] = None
    alergias_lista: Optional[List[str]] = None
    doencas_cronicas: Optional[str] = None
    condicoes_cronicas_lista: Optional[List[str]] = None
    medicamentos_continuos: Optional[str] = None
    medicamentos_continuos_lista: Optional[List[str]] = None
    restricoes_alimentares_lista: Optional[List[str]] = None
    historico_clinico: Optional[str] = None
    tipo_sanguineo: Optional[str] = None
    pedigree_registro: Optional[str] = None
    castrado_data: Optional[date] = None
    observacoes: Optional[str] = None
    foto_url: Optional[str] = None
    ativo: Optional[bool] = None

    model_config = {"from_attributes": True}


class PetResponse(BaseModel):
    id: int
    codigo: str
    nome: str
    especie: str
    raca: Optional[str]
    sexo: Optional[str]
    data_nascimento: Optional[dt]
    idade_aproximada: Optional[int] = None
    castrado: Optional[bool] = None
    castrado_data: Optional[date] = None
    cor: Optional[str]
    porte: Optional[str] = None
    peso: Optional[float]
    peso_kg: Optional[float] = None  # Alias para compatibilidade
    idade_meses: Optional[int] = None  # Calculado a partir da data_nascimento
    microchip: Optional[str] = None
    alergias: Optional[str] = None
    alergias_lista: List[str] = Field(default_factory=list)
    doencas_cronicas: Optional[str] = None
    condicoes_cronicas_lista: List[str] = Field(default_factory=list)
    medicamentos_continuos: Optional[str] = None
    medicamentos_continuos_lista: List[str] = Field(default_factory=list)
    restricoes_alimentares_lista: List[str] = Field(default_factory=list)
    historico_clinico: Optional[str] = None
    tipo_sanguineo: Optional[str] = None
    pedigree_registro: Optional[str] = None
    observacoes: Optional[str]
    foto_url: Optional[str] = None
    ativo: bool
    created_at: dt
    updated_at: dt

    @validator(
        "alergias_lista",
        "condicoes_cronicas_lista",
        "medicamentos_continuos_lista",
        "restricoes_alimentares_lista",
        pre=True,
    )
    def normalize_list_fields(cls, v):
        # Compatibilidade com registros antigos que possuem null no banco.
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []

    model_config = {"from_attributes": True}


class ClienteCreate(BaseModel):
    # Tipo de cadastro
    tipo_cadastro: str = "cliente"  # cliente, fornecedor, veterinario, funcionario
    tipo_pessoa: str = "PF"  # PF ou PJ
    
    # Dados comuns
    nome: str  # Nome completo (PF) ou Nome Fantasia (PJ)
    data_nascimento: Optional[date] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    
    # Pessoa FÃ­sica
    cpf: Optional[str] = None
    
    # Pessoa JurÃ­dica
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    responsavel: Optional[str] = None
    
    # VeterinÃ¡rio
    crmv: Optional[str] = None
    
    # Sistema de parceiros (comissÃµes)
    parceiro_ativo: Optional[bool] = False
    parceiro_desde: Optional[str] = None
    parceiro_observacoes: Optional[str] = None
    
    # EndereÃ§o
    cep: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    
    # EndereÃ§os de entrega
    endereco_entrega: Optional[str] = None
    endereco_entrega_2: Optional[str] = None
    enderecos_adicionais: Optional[list] = None  # Array de endereÃ§os com tipo, apelido, etc.
    
    # ðŸšš ENTREGADOR (SPRINT 1)
    is_entregador: bool = False
    entregador_padrao: bool = False
    is_terceirizado: bool = False
    recebe_repasse: bool = False
    gera_conta_pagar: bool = False
    tipo_vinculo_entrega: Optional[str] = None  # funcionario | terceirizado | eventual
    valor_padrao_entrega: Optional[Decimal] = None
    valor_por_km: Optional[Decimal] = None
    recebe_comissao_entrega: bool = False
    
    # ðŸ“† ACERTO FINANCEIRO (ETAPA 4)
    tipo_acerto_entrega: Optional[str] = None  # semanal | quinzenal | mensal
    dia_semana_acerto: Optional[int] = None  # 1=segunda ... 7=domingo
    dia_mes_acerto: Optional[int] = None  # 1 a 28
    data_ultimo_acerto: Optional[str] = None  # Data do Ãºltimo acerto (YYYY-MM-DD)
    
    observacoes: Optional[str] = None

    model_config = {"from_attributes": True}
    
    @validator('email', 'cpf', 'telefone', 'celular', 'cep', 'endereco', 'numero', 
               'complemento', 'bairro', 'cidade', 'estado', 'observacoes',
               'cnpj', 'inscricao_estadual', 'razao_social', 'nome_fantasia', 'responsavel', 'crmv',
               'endereco_entrega', 'endereco_entrega_2', 'parceiro_desde', 'parceiro_observacoes',
               'tipo_vinculo_entrega', pre=True)
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v
    
    @validator('tipo_pessoa')
    def validate_tipo_pessoa(cls, v):
        if v not in ['PF', 'PJ']:
            raise ValueError('tipo_pessoa deve ser PF ou PJ')
        return v
    
    @validator('tipo_cadastro')
    def validate_tipo_cadastro(cls, v):
        if v not in ['cliente', 'fornecedor', 'veterinario', 'funcionario']:
            raise ValueError('tipo_cadastro deve ser cliente, fornecedor, veterinario ou funcionario')
        return v


class ClienteUpdate(BaseModel):
    tipo_cadastro: Optional[str] = None
    tipo_pessoa: Optional[str] = None
    nome: Optional[str] = None
    data_nascimento: Optional[date] = None
    cpf: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    
    # Campos PJ
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    responsavel: Optional[str] = None
    
    # VeterinÃ¡rio
    crmv: Optional[str] = None
    
    # Sistema de parceiros (comissÃµes)
    parceiro_ativo: Optional[bool] = None
    parceiro_desde: Optional[str] = None
    parceiro_observacoes: Optional[str] = None
    data_fechamento_comissao: Optional[int] = None
    
    cep: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    
    # EndereÃ§os de entrega
    endereco_entrega: Optional[str] = None
    endereco_entrega_2: Optional[str] = None
    enderecos_adicionais: Optional[list] = None  # Array de endereÃ§os com tipo, apelido, etc.
    
    # ðŸšš ENTREGADOR (SPRINT 1)
    is_entregador: Optional[bool] = None
    is_terceirizado: Optional[bool] = None
    recebe_repasse: Optional[bool] = None
    gera_conta_pagar: Optional[bool] = None
    tipo_vinculo_entrega: Optional[str] = None
    valor_padrao_entrega: Optional[Decimal] = None
    valor_por_km: Optional[Decimal] = None
    recebe_comissao_entrega: Optional[bool] = None
    
    # ðŸšš ENTREGADOR - SISTEMA COMPLETO (FASE 2)
    entregador_ativo: Optional[bool] = None
    entregador_padrao: Optional[bool] = None
    controla_rh: Optional[bool] = None
    gera_conta_pagar_custo_entrega: Optional[bool] = None
    media_entregas_configurada: Optional[int] = None
    media_entregas_real: Optional[int] = None
    custo_rh_ajustado: Optional[Decimal] = None
    modelo_custo_entrega: Optional[str] = None
    taxa_fixa_entrega: Optional[Decimal] = None
    valor_por_km_entrega: Optional[Decimal] = None
    moto_propria: Optional[bool] = None
    
    # ðŸ“† ACERTO FINANCEIRO (ETAPA 4)
    tipo_acerto_entrega: Optional[str] = None  # semanal | quinzenal | mensal
    dia_semana_acerto: Optional[int] = None  # 1=segunda ... 7=domingo
    dia_mes_acerto: Optional[int] = None  # 1 a 28
    data_ultimo_acerto: Optional[str] = None  # Data do Ãºltimo acerto (YYYY-MM-DD)
    
    # ðŸ“Š DRE - CONTROLE DE CLASSIFICAÃ‡ÃƒO
    controla_dre: Optional[bool] = None  # True = vai para DRE, False = nÃ£o classifica (produtos p/ revenda)
    
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None

    model_config = {"from_attributes": True}
    
    @validator('email', 'cpf', 'telefone', 'celular', 'cep', 'endereco', 'numero', 
               'complemento', 'bairro', 'cidade', 'estado', 'observacoes',
               'cnpj', 'inscricao_estadual', 'razao_social', 'nome_fantasia', 'responsavel', 'crmv',
               'parceiro_desde', 'parceiro_observacoes', 'tipo_vinculo_entrega', pre=True)
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v


class ClienteResponse(BaseModel):
    id: int
    codigo: Optional[str] = None
    tipo_cadastro: str
    tipo_pessoa: str
    nome: str
    data_nascimento: Optional[dt] = None
    cpf: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    
    # Campos PJ
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    responsavel: Optional[str] = None
    
    # VeterinÃ¡rio
    crmv: Optional[str] = None
    
    # Sistema de parceiros (comissÃµes)
    parceiro_ativo: bool = False
    parceiro_desde: Optional[dt] = None
    parceiro_observacoes: Optional[str] = None
    data_fechamento_comissao: Optional[int] = None
    
    cep: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    
    # EndereÃ§os adicionais
    endereco_entrega: Optional[str] = None
    endereco_entrega_2: Optional[str] = None
    enderecos_adicionais: Optional[list] = None
    
    # ðŸšš ENTREGADOR (SPRINT 1)
    is_entregador: bool = False
    is_terceirizado: bool = False
    recebe_repasse: bool = False
    gera_conta_pagar: bool = False
    tipo_vinculo_entrega: Optional[str] = None
    valor_padrao_entrega: Optional[Decimal] = None
    valor_por_km: Optional[Decimal] = None
    recebe_comissao_entrega: bool = False
    
    # ðŸšš ENTREGADOR - SISTEMA COMPLETO (FASE 2)
    entregador_ativo: bool = True
    entregador_padrao: bool = False
    controla_rh: bool = False
    gera_conta_pagar_custo_entrega: bool = False
    media_entregas_configurada: Optional[int] = None
    media_entregas_real: Optional[int] = None
    custo_rh_ajustado: Optional[Decimal] = None
    modelo_custo_entrega: Optional[str] = None
    taxa_fixa_entrega: Optional[Decimal] = None
    valor_por_km_entrega: Optional[Decimal] = None
    moto_propria: bool = True
    
    # ðŸ“† ACERTO FINANCEIRO (ETAPA 4)
    tipo_acerto_entrega: Optional[str] = None  # semanal | quinzenal | mensal
    dia_semana_acerto: Optional[int] = None  # 1=segunda ... 7=domingo
    dia_mes_acerto: Optional[int] = None  # 1 a 28
    data_ultimo_acerto: Optional[str] = None  # Data do Ãºltimo acerto (YYYY-MM-DD)
    
    # ðŸ“Š DRE - CONTROLE DE CLASSIFICAÃ‡ÃƒO
    controla_dre: bool = True  # True = vai para DRE, False = nÃ£o classifica (produtos p/ revenda)
    
    observacoes: Optional[str] = None
    ativo: bool = True
    credito: Optional[Decimal] = Decimal('0.00')
    created_at: dt
    updated_at: dt
    pets: List[PetResponse] = []
    
    @validator('parceiro_ativo', pre=True)
    def ensure_parceiro_ativo(cls, v):
        """Garantir que parceiro_ativo seja sempre bool"""
        if v is None:
            return False
        return bool(v)
    
    @validator('enderecos_adicionais', pre=True)
    def deserialize_enderecos(cls, v):
        """Desserializar JSON string para lista"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return None
        return v

    @validator('pets', pre=True)
    def filter_active_pets(cls, v):
        """Filtrar apenas pets ativos"""
        if isinstance(v, list):
            result = []
            for pet in v:
                try:
                    # Pet pode ser objeto ou dict
                    ativo = pet.ativo if hasattr(pet, 'ativo') else pet.get('ativo', True)
                    if ativo:
                        result.append(pet)
                except:
                    # Em caso de erro, incluir o pet
                    result.append(pet)
            return result
        return v if v else []

    # Campo de parceria (True = pertence ao tenant parceiro, False = próprio)
    de_parceiro: bool = False

    model_config = {"from_attributes": True}


# ==================== CLIENTES ====================

@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def create_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Criar novo cliente/fornecedor"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Validar documento conforme tipo de pessoa (CPF nÃ£o Ã© obrigatÃ³rio)
    if cliente_data.tipo_pessoa == "PF":
        # Verificar se CPF jÃ¡ existe (se fornecido)
        if cliente_data.cpf:
            existing = db.query(Cliente).filter(
                Cliente.tenant_id == tenant_id,
                Cliente.cpf == cliente_data.cpf,
                Cliente.ativo == True
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"JÃ¡ existe um {cliente_data.tipo_cadastro} cadastrado com este CPF"
                )
    
    elif cliente_data.tipo_pessoa == "PJ":
        if not cliente_data.cnpj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNPJ Ã© obrigatÃ³rio para Pessoa JurÃ­dica"
            )
        # Verificar se CNPJ jÃ¡ existe
        existing = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cnpj == cliente_data.cnpj,
            Cliente.ativo == True
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"JÃ¡ existe um {cliente_data.tipo_cadastro} cadastrado com este CNPJ"
            )
    
    # Verificar se CRMV jÃ¡ existe (se fornecido e for veterinÃ¡rio)
    if cliente_data.crmv and cliente_data.tipo_cadastro == "veterinario":
        existing_crmv = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.crmv == cliente_data.crmv,
            Cliente.ativo == True
        ).first()
        if existing_crmv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um veterinÃ¡rio cadastrado com este CRMV"
            )
    
    # Verificar se celular jÃ¡ existe (se fornecido)
    if cliente_data.celular:
        existing_cel = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.celular == cliente_data.celular,
            Cliente.ativo == True
        ).first()
        if existing_cel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cadastro com este celular"
            )
    
    # Verificar se telefone jÃ¡ existe (se fornecido)
    if cliente_data.telefone:
        existing_tel = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.telefone == cliente_data.telefone,
            Cliente.ativo == True
        ).first()
        if existing_tel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cliente cadastrado com este telefone"
            )
    
    # Gerar cÃ³digo usando a nova funÃ§Ã£o
    codigo = gerar_codigo_cliente(db, cliente_data.tipo_cadastro, cliente_data.tipo_pessoa, tenant_id)
    
    # Preparar dados do cliente
    dados_cliente = cliente_data.model_dump()
    
    # ðŸšš VALIDAÃ‡ÃƒO: Apenas 1 entregador padrÃ£o por vez
    if dados_cliente.get('entregador_padrao') is True:
        # Verificar se jÃ¡ existe outro entregador padrÃ£o
        entregador_padrao_atual = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.entregador_padrao == True,
            Cliente.ativo == True
        ).first()
        
        if entregador_padrao_atual:
            # Desmarcar o antigo como padrÃ£o
            entregador_padrao_atual.entregador_padrao = False
            entregador_padrao_atual.updated_at = dt.utcnow()
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"ðŸšš Entregador padrÃ£o removido de: {entregador_padrao_atual.nome} (ID: {entregador_padrao_atual.id})")
    
    # Serializar enderecos_adicionais para JSON (SQLite armazena como TEXT)
    if dados_cliente.get('enderecos_adicionais'):
        import json
        dados_cliente['enderecos_adicionais'] = json.dumps(dados_cliente['enderecos_adicionais'])
    
    # Criar cliente
    novo_cliente = Cliente(
        user_id=current_user.id,
        tenant_id=tenant_id,
        codigo=codigo,
        **dados_cliente
    )
    
    db.add(novo_cliente)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Código de cliente já em uso. Tente cadastrar novamente."
        )
    db.refresh(novo_cliente)
    
    # Log de auditoria
    log_create(db, current_user.id, "cliente", novo_cliente.id, cliente_data.model_dump())
    
    return novo_cliente


class ClientesListResponse(BaseModel):
    items: List[ClienteResponse]
    total: int
    skip: int
    limit: int

@router.get("/", response_model=ClientesListResponse)
@require_permission("clientes.visualizar")
def list_clientes(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    ativo: Optional[bool] = None,
    tipo_cadastro: Optional[List[str]] = Query(None),  # Aceita lista de tipos
    is_entregador: Optional[bool] = None,  # Filtro para entregadores
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Listar clientes/fornecedores do usuÃ¡rio"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    try:
        # Incluir clientes de tenants parceiros (ex.: pet shop parceiro da clínica)
        access_ids = get_all_accessible_tenant_ids(db, tenant_id)
        query = db.query(Cliente).filter(Cliente.tenant_id.in_(access_ids))
        
        # Filtro por tipo de cadastro (aceita lista ou string)
        if tipo_cadastro:
            if isinstance(tipo_cadastro, list):
                query = query.filter(Cliente.tipo_cadastro.in_(tipo_cadastro))
            else:
                query = query.filter(Cliente.tipo_cadastro == tipo_cadastro)
        
        # Filtro por entregador
        if is_entregador is not None:
            query = query.filter(Cliente.is_entregador == is_entregador)
        
        termo_busca = (search or "").strip()

        termo_digitos = "".join(ch for ch in termo_busca if ch.isdigit())
        termo_numerico = bool(termo_digitos)
        telefone_digitos = _somente_digitos_coluna(Cliente.telefone)
        celular_digitos = _somente_digitos_coluna(Cliente.celular)

        # Filtro de busca por múltiplas palavras (qualquer ordem)
        # Cada palavra precisa existir em pelo menos um dos campos pesquisáveis.
        if termo_busca:
            palavras = [p.strip() for p in termo_busca.split() if p.strip()]
            for palavra in palavras:
                like = f"%{palavra}%"
                palavra_digitos = "".join(ch for ch in palavra if ch.isdigit())
                filtros = [
                    Cliente.codigo.ilike(like),
                    Cliente.nome.ilike(like),
                    Cliente.nome_fantasia.ilike(like),
                    Cliente.razao_social.ilike(like),
                    Cliente.cpf.ilike(like),
                    Cliente.cnpj.ilike(like),
                    Cliente.email.ilike(like),
                    Cliente.telefone.ilike(like),
                    Cliente.celular.ilike(like),
                ]
                if palavra_digitos:
                    like_digitos = f"%{palavra_digitos}%"
                    filtros.extend([
                        telefone_digitos.ilike(like_digitos),
                        celular_digitos.ilike(like_digitos),
                    ])
                query = query.filter(
                    or_(*filtros)
                )
        
        # Filtro de ativo (padrÃ£o True - mostrar apenas ativos)
        if ativo is None:
            ativo = True
        if ativo:
            query = query.filter(or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)))
        else:
            query = query.filter(Cliente.ativo.is_(False))
        
        # Contar total (ANTES do offset/limit)
        total = query.count()
        
        # Ordenação inteligente por campos visíveis ao usuário (id interno ignorado).
        if termo_busca:
            termo_lower = termo_busca.lower()
            if termo_numerico:
                query = query.order_by(
                    case(
                        (func.lower(Cliente.codigo) == termo_lower, 1),   # codigo exato
                        (telefone_digitos == termo_digitos, 2),            # telefone exato
                        (celular_digitos == termo_digitos, 3),             # celular exato
                        (Cliente.codigo.ilike(f"{termo_digitos}%"), 4),   # codigo começa com
                        (telefone_digitos.ilike(f"{termo_digitos}%"), 5),
                        (celular_digitos.ilike(f"{termo_digitos}%"), 6),
                        (func.lower(Cliente.nome) == termo_lower, 7),
                        (Cliente.nome.ilike(f"{termo_busca}%"), 8),
                        (Cliente.nome_fantasia.ilike(f"{termo_busca}%"), 9),
                        (Cliente.razao_social.ilike(f"{termo_busca}%"), 10),
                        else_=11,
                    ),
                    Cliente.nome
                )
            else:
                query = query.order_by(
                    case(
                        (func.lower(Cliente.codigo) == termo_lower, 1),
                        (func.lower(Cliente.nome) == termo_lower, 2),
                        (func.lower(Cliente.nome_fantasia) == termo_lower, 3),
                        (func.lower(Cliente.razao_social) == termo_lower, 4),
                        (Cliente.codigo.ilike(f"{termo_busca}%"), 5),
                        (Cliente.nome.ilike(f"{termo_busca}%"), 6),
                        (Cliente.nome_fantasia.ilike(f"{termo_busca}%"), 7),
                        (Cliente.razao_social.ilike(f"{termo_busca}%"), 8),
                        else_=9,
                    ),
                    Cliente.nome
                )
        else:
            query = query.order_by(Cliente.nome)
        
        # Buscar registros paginados
        clientes = query.offset(skip).limit(limit).all()

        # Marcar clientes que pertencem ao tenant parceiro
        tenant_id_str = str(tenant_id)
        for c in clientes:
            if str(c.tenant_id) != tenant_id_str:
                c.de_parceiro = True

        return ClientesListResponse(
            items=clientes,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao listar clientes: {e}")
        logger.error(f"Tipo do erro: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar clientes: {str(e)}"
        )


@router.get("/verificar-duplicata/campo", response_model=dict)
def verificar_duplicata(
    cpf: Optional[str] = None,
    cnpj: Optional[str] = None,
    telefone: Optional[str] = None,
    celular: Optional[str] = None,
    crmv: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Verificar se existe cliente com CPF, CNPJ, telefone, celular ou CRMV duplicado"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    resultado = {
        "duplicado": False,
        "cliente": None,
        "campo": None
    }
    
    # Verificar CPF
    if cpf:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cpf == cpf,
            Cliente.ativo == True
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)
        
        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "cpf"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "tipo_cadastro": cliente.tipo_cadastro,
                "tipo_pessoa": cliente.tipo_pessoa,
                "cpf": cliente.cpf,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email
            }
            return resultado
    
    # Verificar CNPJ
    if cnpj:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cnpj == cnpj,
            Cliente.ativo == True
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)
        
        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "cnpj"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "tipo_cadastro": cliente.tipo_cadastro,
                "tipo_pessoa": cliente.tipo_pessoa,
                "cnpj": cliente.cnpj,
                "razao_social": cliente.razao_social,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email
            }
            return resultado
    
    # Verificar celular
    if celular:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.celular == celular,
            Cliente.ativo == True
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)
        
        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "celular"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "cpf": cliente.cpf,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email
            }
            return resultado
    
    # Verificar telefone
    if telefone:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.telefone == telefone,
            Cliente.ativo == True
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)
        
        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "telefone"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "cpf": cliente.cpf,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email
            }
            return resultado
    
    # Verificar CRMV
    if crmv:
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.crmv == crmv,
            Cliente.ativo == True
        )
        if cliente_id:
            query = query.filter(Cliente.id != cliente_id)
        
        cliente = query.first()
        if cliente:
            resultado["duplicado"] = True
            resultado["campo"] = "crmv"
            resultado["cliente"] = {
                "id": cliente.id,
                "codigo": cliente.codigo,
                "nome": cliente.nome,
                "tipo_cadastro": cliente.tipo_cadastro,
                "crmv": cliente.crmv,
                "telefone": cliente.telefone,
                "celular": cliente.celular,
                "email": cliente.email
            }
            return resultado
    
    return resultado


# ==================== RAÃ‡AS ====================

@router.get("/racas-teste")
def list_racas_teste(especie: str = ""):
    """Teste simples sem dependÃªncias"""
    return [
        {"id": 1, "nome": "Labrador", "especie": "CÃ£o"},
        {"id": 2, "nome": "SiamÃªs", "especie": "Gato"}
    ]

@router.get("/racas")
def list_racas(
    especie: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Listar raÃ§as cadastradas (filtro por espÃ©cie)"""
    
    query = db.query(Raca).filter(Raca.ativo == True)
    
    if especie:
        query = query.filter(Raca.especie == especie)
    
    if search:
        query = query.filter(Raca.nome.ilike(f"%{search}%"))
    
    racas = query.order_by(Raca.nome).all()
    
    return [{"id": r.id, "nome": r.nome, "especie": r.especie} for r in racas]


# ==================== CLIENTES - GET/UPDATE/DELETE ====================

@router.get("/{cliente_id}", response_model=ClienteResponse)
def get_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Obter cliente por ID"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    return cliente


@router.put("/{cliente_id}")
def update_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualizar cliente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DEBUG update_cliente] ID={cliente_id}, tenant_id={tenant_id}, data_fechamento_comissao={cliente_data.data_fechamento_comissao}")
    logger.info(f"[DEBUG] entregador_padrao={cliente_data.entregador_padrao}, gera_conta_pagar_custo_entrega={cliente_data.gera_conta_pagar_custo_entrega}")
    
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Verificar CPF duplicado (se alterado)
    if cliente_data.cpf and cliente_data.cpf != cliente.cpf:
        existing = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cpf == cliente_data.cpf,
            Cliente.id != cliente_id,
            Cliente.ativo == True
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cliente cadastrado com este CPF"
            )
    
    # Verificar CNPJ duplicado (se alterado)
    if cliente_data.cnpj and cliente_data.cnpj != cliente.cnpj:
        existing = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cnpj == cliente_data.cnpj,
            Cliente.id != cliente_id,
            Cliente.ativo == True
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cadastro com este CNPJ"
            )
    
    # Verificar CRMV duplicado (se alterado)
    if cliente_data.crmv and cliente_data.crmv != cliente.crmv:
        existing = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.crmv == cliente_data.crmv,
            Cliente.id != cliente_id,
            Cliente.ativo == True
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um veterinÃ¡rio cadastrado com este CRMV"
            )
    
    # Verificar celular duplicado (se alterado)
    if cliente_data.celular and cliente_data.celular != cliente.celular:
        existing_cel = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.celular == cliente_data.celular,
            Cliente.id != cliente_id,
            Cliente.ativo == True
        ).first()
        if existing_cel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cliente cadastrado com este celular"
            )
    
    # Verificar telefone duplicado (se alterado)
    if cliente_data.telefone and cliente_data.telefone != cliente.telefone:
        existing_tel = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.telefone == cliente_data.telefone,
            Cliente.id != cliente_id,
            Cliente.ativo == True
        ).first()
        if existing_tel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cliente cadastrado com este telefone"
            )
    
    # Atualizar campos
    update_data = cliente_data.model_dump(exclude_unset=True)
    
    # ðŸšš VALIDAÃ‡ÃƒO: Apenas 1 entregador padrÃ£o por vez
    if 'entregador_padrao' in update_data and update_data['entregador_padrao'] is True:
        # Verificar se jÃ¡ existe outro entregador padrÃ£o
        entregador_padrao_atual = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.entregador_padrao == True,
            Cliente.id != cliente_id,
            Cliente.ativo == True
        ).first()
        
        if entregador_padrao_atual:
            # Desmarcar o antigo como padrÃ£o
            entregador_padrao_atual.entregador_padrao = False
            entregador_padrao_atual.updated_at = dt.utcnow()
            logger.info(f"ðŸšš Entregador padrÃ£o removido de: {entregador_padrao_atual.nome} (ID: {entregador_padrao_atual.id})")
    
    # Serializar enderecos_adicionais para JSON (SQLite armazena como TEXT)
    if 'enderecos_adicionais' in update_data and update_data['enderecos_adicionais'] is not None:
        import json
        update_data['enderecos_adicionais'] = json.dumps(update_data['enderecos_adicionais'])
    
    # ðŸ”’ DETECTAR TRANSIÃ‡ÃƒO DE PARCEIRO_ATIVO (TRUE â†’ FALSE)
    parceiro_desativado = False
    comissoes_desativadas_count = 0
    
    if 'parceiro_ativo' in update_data:
        # Cliente era parceiro e estÃ¡ sendo desmarcado
        if hasattr(cliente, 'parceiro_ativo') and cliente.parceiro_ativo and not update_data['parceiro_ativo']:
            parceiro_desativado = True
            
            # Desativar todas as comissÃµes ativas dessa pessoa
            from sqlalchemy import text
            
            # Contar comissÃµes ativas antes de desativar
            result = db.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM comissoes_configuracao 
                    WHERE funcionario_id = :funcionario_id 
                    AND (ativo = 1 OR ativo IS NULL)
                """),
                {"funcionario_id": cliente_id}
            )
            comissoes_desativadas_count = result.fetchone()[0]
            
            # Desativar comissÃµes (preservando histÃ³rico)
            if comissoes_desativadas_count > 0:
                db.execute(
                    text("""
                        UPDATE comissoes_configuracao 
                        SET ativo = 0,
                            data_atualizacao = CURRENT_TIMESTAMP,
                            usuario_atualizacao = :usuario_id
                        WHERE funcionario_id = :funcionario_id 
                        AND (ativo = 1 OR ativo IS NULL)
                    """),
                    {"funcionario_id": cliente_id, "usuario_id": current_user.id}
                )
    
    # Salvar estado antigo para auditoria
    old_data = {field: getattr(cliente, field) for field in update_data.keys()}
    
    for field, value in update_data.items():
        setattr(cliente, field, value)
    
    # Se estiver reativando e nÃ£o tiver cÃ³digo, gerar um
    if cliente.ativo and not cliente.codigo:
        cliente.codigo = gerar_codigo_cliente(db, cliente.tipo_cadastro, cliente.tipo_pessoa, tenant_id)
    
    cliente.updated_at = dt.utcnow()
    db.commit()
    db.refresh(cliente)
    
    # Log de auditoria
    log_update(db, current_user.id, "cliente", cliente.id, old_data, update_data)
    
    # ðŸ“¢ PREPARAR RESPOSTA COM AVISO SOBRE COMISSÃ•ES
    response = {
        "id": cliente.id,
        "codigo": cliente.codigo,
        "nome": cliente.nome,
        "tipo_cadastro": cliente.tipo_cadastro,
        "tipo_pessoa": cliente.tipo_pessoa,
        "cpf": cliente.cpf,
        "cnpj": cliente.cnpj,
        "email": cliente.email,
        "telefone": cliente.telefone,
        "celular": cliente.celular,
        "parceiro_ativo": cliente.parceiro_ativo if hasattr(cliente, 'parceiro_ativo') else False,
        "data_fechamento_comissao": cliente.data_fechamento_comissao,
        "ativo": cliente.ativo,
        "created_at": cliente.created_at,
        "updated_at": cliente.updated_at
    }
    
    # Adicionar aviso se comissÃµes foram desativadas
    if parceiro_desativado and comissoes_desativadas_count > 0:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"ðŸ”’ {comissoes_desativadas_count} comissÃ£o(Ãµes) desativada(s) automaticamente "
            f"para {cliente.nome} (ID: {cliente_id}) porque deixou de ser parceiro."
        )
        
        response["aviso"] = (
            f"ComissÃµes desativadas automaticamente porque o cliente deixou de ser parceiro. "
            f"Total desativado: {comissoes_desativadas_count}"
        )
    
    return response


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Desativar cliente (soft delete)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Soft delete
    cliente.ativo = False
    cliente.updated_at = dt.utcnow()
    
    # Desativar pets tambÃ©m
    for pet in cliente.pets:
        pet.ativo = False
        pet.updated_at = dt.utcnow()
    
    db.commit()
    
    # Log de auditoria
    log_delete(db, current_user.id, "cliente", cliente.id, {
        "codigo": cliente.codigo,
        "nome": cliente.nome,
        "cpf": cliente.cpf
    })
    
    return None


# ==================== PARCEIROS ====================

class ToggleParceiroRequest(BaseModel):
    """Request para ativar/desativar parceiro"""
    parceiro_ativo: bool
    parceiro_observacoes: Optional[str] = None


@router.patch("/{cliente_id}/parceiro")
def toggle_parceiro(
    cliente_id: int,
    request: ToggleParceiroRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Ativar ou desativar um cliente como parceiro para receber comissÃµes.
    
    Permite que QUALQUER pessoa (cliente, veterinÃ¡rio, funcionÃ¡rio, fornecedor)
    seja ativada como parceiro, independente do tipo_cadastro.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Salvar estado anterior para auditoria e lÃ³gica
    old_status = cliente.parceiro_ativo
    old_parceiro_desde = cliente.parceiro_desde
    
    # ========================================================================
    # LÃ“GICA DE ATIVAÃ‡ÃƒO/DESATIVAÃ‡ÃƒO COM PRESERVAÃ‡ÃƒO DE HISTÃ“RICO
    # ========================================================================
    
    # CenÃ¡rio 1: Ativando parceiro (false â†’ true ou None â†’ true)
    if request.parceiro_ativo and not old_status:
        cliente.parceiro_ativo = True
        
        # Se Ã© primeira ativaÃ§Ã£o (nunca foi parceiro antes)
        if not old_parceiro_desde:
            cliente.parceiro_desde = dt.utcnow()
            acao = "primeira_ativacao"
        # Se Ã© reativaÃ§Ã£o (jÃ¡ foi parceiro antes)
        else:
            # Manter data original de parceiro_desde
            # Adicionar registro de reativaÃ§Ã£o nas observaÃ§Ãµes
            data_reativacao = dt.utcnow().strftime('%d/%m/%Y')
            observacao_reativacao = f"\n[Reativado como parceiro em {data_reativacao}]"
            
            if cliente.parceiro_observacoes:
                cliente.parceiro_observacoes += observacao_reativacao
            else:
                cliente.parceiro_observacoes = f"Reativado como parceiro em {data_reativacao}"
            
            acao = "reativacao"
    
    # CenÃ¡rio 2: Desativando parceiro (true â†’ false)
    elif not request.parceiro_ativo and old_status:
        cliente.parceiro_ativo = False
        # NÃƒO limpar parceiro_desde - preservar histÃ³rico
        # Adicionar registro de desativaÃ§Ã£o nas observaÃ§Ãµes
        data_desativacao = dt.utcnow().strftime('%d/%m/%Y')
        observacao_desativacao = f"\n[Desativado como parceiro em {data_desativacao}]"
        
        if cliente.parceiro_observacoes:
            cliente.parceiro_observacoes += observacao_desativacao
        else:
            cliente.parceiro_observacoes = f"Desativado como parceiro em {data_desativacao}"
        
        acao = "desativacao"
    
    # CenÃ¡rio 3: Status nÃ£o mudou (idempotÃªncia)
    else:
        acao = "sem_alteracao"
    
    # Atualizar observaÃ§Ãµes adicionais se fornecidas pelo usuÃ¡rio
    # (concatena com as automÃ¡ticas)
    if request.parceiro_observacoes is not None and request.parceiro_observacoes.strip():
        if cliente.parceiro_observacoes:
            cliente.parceiro_observacoes = f"{request.parceiro_observacoes}\n{cliente.parceiro_observacoes}"
        else:
            cliente.parceiro_observacoes = request.parceiro_observacoes
    
    cliente.updated_at = dt.utcnow()
    db.commit()
    db.refresh(cliente)
    
    # Log de auditoria detalhado
    log_update(db, current_user.id, "cliente_parceiro", cliente.id, 
        {
            "parceiro_ativo": old_status,
            "parceiro_desde": old_parceiro_desde.isoformat() if old_parceiro_desde else None
        }, 
        {
            "parceiro_ativo": cliente.parceiro_ativo,
            "parceiro_desde": cliente.parceiro_desde.isoformat() if cliente.parceiro_desde else None,
            "acao": acao
        }
    )
    
    # Mensagens especÃ­ficas por aÃ§Ã£o
    mensagens = {
        "primeira_ativacao": f"Parceiro ativado pela primeira vez em {cliente.parceiro_desde.strftime('%d/%m/%Y')}",
        "reativacao": f"Parceiro reativado com sucesso (parceiro desde {cliente.parceiro_desde.strftime('%d/%m/%Y')})",
        "desativacao": f"Parceiro desativado (histÃ³rico preservado desde {cliente.parceiro_desde.strftime('%d/%m/%Y') if cliente.parceiro_desde else 'N/A'})",
        "sem_alteracao": f"Status de parceiro jÃ¡ estava como {'ativo' if cliente.parceiro_ativo else 'inativo'}"
    }
    
    return {
        "success": True,
        "message": mensagens.get(acao, "Status atualizado"),
        "acao": acao,
        "data": {
            "id": cliente.id,
            "nome": cliente.nome,
            "tipo_cadastro": cliente.tipo_cadastro,
            "parceiro_ativo": cliente.parceiro_ativo,
            "parceiro_desde": cliente.parceiro_desde.isoformat() if cliente.parceiro_desde else None,
            "parceiro_observacoes": cliente.parceiro_observacoes,
            "foi_reativacao": acao == "reativacao",
            "historico_preservado": cliente.parceiro_desde is not None
        }
    }


@router.patch("/{cliente_id}/controla-dre")
def atualizar_controla_dre(
    cliente_id: int,
    controla_dre: bool,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualizar o controle DRE de um cliente/fornecedor.
    
    - controla_dre=True: LanÃ§amentos deste fornecedor/cliente VÃƒO para DRE (padrÃ£o)
    - controla_dre=False: LanÃ§amentos NÃƒO vÃ£o para DRE (ex: fornecedor de produtos para revenda como Buendia)
    
    Quando controla_dre=False, os lanÃ§amentos deste fornecedor/cliente:
    - NÃƒO aparecem na lista de pendentes de classificaÃ§Ã£o
    - NÃƒO geram sugestÃµes de classificaÃ§Ã£o DRE
    - SÃ£o automaticamente ignorados no processo de classificaÃ§Ã£o
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Atualizar campo
    old_value = cliente.controla_dre
    cliente.controla_dre = controla_dre
    cliente.updated_at = dt.utcnow()
    
    db.commit()
    db.refresh(cliente)
    
    # Log de auditoria
    log_update(db, current_user.id, "cliente_controla_dre", cliente.id, 
        {"controla_dre": old_value}, 
        {"controla_dre": controla_dre}
    )
    
    return {
        "success": True,
        "message": f"{'Ativado' if controla_dre else 'Desativado'} controle DRE para {cliente.nome}",
        "data": {
            "id": cliente.id,
            "nome": cliente.nome,
            "tipo_cadastro": cliente.tipo_cadastro,
            "controla_dre": cliente.controla_dre
        }
    }


# ==================== PETS ====================

@router.post("/{cliente_id}/pets", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
def create_pet(
    cliente_id: int,
    pet_data: PetCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Criar novo pet para um cliente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Gerar cÃ³digo Ãºnico para o pet baseado no cÃ³digo do cliente
    codigo_pet = f"{cliente.codigo}-PET-{db.query(Pet).filter(Pet.cliente_id == cliente_id).count() + 1:04d}"
    pet_payload = normalize_pet_clinical_payload(pet_data.model_dump())
    
    # Criar pet
    novo_pet = Pet(
        cliente_id=cliente_id,
        user_id=current_user.id,
        tenant_id=tenant_id,
        codigo=codigo_pet,
        **pet_payload
    )
    
    db.add(novo_pet)
    db.commit()
    db.refresh(novo_pet)
    
    # Log de auditoria
    log_create(db, current_user.id, "pet", novo_pet.id, {
        "cliente_id": cliente_id,
        **pet_payload
    })
    
    return novo_pet


@router.get("/pets/todos", response_model=List[PetResponse])
def listar_todos_pets(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Listar todos os pets do usuÃ¡rio (de todos os clientes)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    pets = db.query(Pet).join(Cliente).filter(
        Cliente.tenant_id == tenant_id
    ).order_by(Pet.nome).all()
    
    return pets


@router.get("/{cliente_id}/pets", response_model=List[PetResponse])
def list_pets_by_cliente(
    cliente_id: int,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Listar pets de um cliente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    query = db.query(Pet).filter(Pet.cliente_id == cliente_id)
    
    if ativo is not None:
        query = query.filter(Pet.ativo == ativo)
    
    pets = query.order_by(Pet.nome).all()
    return pets


@router.get("/pets/{pet_id}", response_model=PetResponse)
def get_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Obter pet por ID"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    pet = db.query(Pet).join(Cliente).filter(
        Pet.id == pet_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet nÃ£o encontrado"
        )
    
    # Calcular idade em meses se tiver data de nascimento
    idade_meses = None
    if pet.data_nascimento:
        from datetime import datetime
        hoje = dt.now()
        idade_meses = (hoje.year - pet.data_nascimento.year) * 12 + (hoje.month - pet.data_nascimento.month)
    
    # Criar resposta completa com todos os campos do PetResponse
    pet_dict = {
        "id": pet.id,
        "codigo": pet.codigo,
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "data_nascimento": pet.data_nascimento,
        "idade_aproximada": pet.idade_aproximada,
        "castrado": pet.castrado,
        "castrado_data": pet.castrado_data,
        "cor": pet.cor,
        "porte": pet.porte,
        "peso": pet.peso,
        "peso_kg": pet.peso,  # Alias para compatibilidade
        "idade_meses": idade_meses,  # Calculado
        "microchip": pet.microchip,
        "alergias": pet.alergias,
        "alergias_lista": pet.alergias_lista or [],
        "doencas_cronicas": pet.doencas_cronicas,
        "condicoes_cronicas_lista": pet.condicoes_cronicas_lista or [],
        "medicamentos_continuos": pet.medicamentos_continuos,
        "medicamentos_continuos_lista": pet.medicamentos_continuos_lista or [],
        "restricoes_alimentares_lista": pet.restricoes_alimentares_lista or [],
        "historico_clinico": pet.historico_clinico,
        "tipo_sanguineo": pet.tipo_sanguineo,
        "pedigree_registro": pet.pedigree_registro,
        "observacoes": pet.observacoes,
        "foto_url": pet.foto_url,
        "ativo": pet.ativo,
        "created_at": pet.created_at,
        "updated_at": pet.updated_at
    }
    
    return pet_dict


@router.put("/pets/{pet_id}", response_model=PetResponse)
def update_pet(
    pet_id: int,
    pet_data: PetUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualizar pet"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    pet = db.query(Pet).join(Cliente).filter(
        Pet.id == pet_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet nÃ£o encontrado"
        )
    
    # Capturar dados antigos para auditoria
    old_data = {
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "data_nascimento": pet.data_nascimento.isoformat() if pet.data_nascimento else None,
        "cor": pet.cor,
        "peso": pet.peso,
        "observacoes": pet.observacoes
    }
    
    # Atualizar campos
    update_data = normalize_pet_clinical_payload(pet_data.model_dump(exclude_unset=True))
    
    # Se idade_aproximada foi fornecida, converter para data_nascimento
    if 'idade_aproximada' in update_data and update_data['idade_aproximada'] is not None:
        idade_meses = update_data['idade_aproximada']
        hoje = dt.utcnow()
        # Calcular data de nascimento subtraindo os meses
        anos = idade_meses // 12
        meses = idade_meses % 12
        ano_nascimento = hoje.year - anos
        mes_nascimento = hoje.month - meses
        
        # Ajustar se o mÃªs ficar negativo
        if mes_nascimento <= 0:
            mes_nascimento += 12
            ano_nascimento -= 1
        
        # Usar dia 1 como padrÃ£o
        pet.data_nascimento = dt(ano_nascimento, mes_nascimento, 1)
        # Remover idade_aproximada do update_data pois jÃ¡ foi processada
        del update_data['idade_aproximada']
    
    for field, value in update_data.items():
        setattr(pet, field, value)
    
    pet.updated_at = dt.utcnow()
    db.commit()
    db.refresh(pet)
    
    # Log de auditoria com old_data e new_data
    log_update(db, current_user, "pet", pet.id, old_data, update_data)
    
    # Calcular idade em meses se tiver data de nascimento
    idade_meses = None
    if pet.data_nascimento:
        from datetime import datetime
        hoje = dt.now()
        idade_meses = (hoje.year - pet.data_nascimento.year) * 12 + (hoje.month - pet.data_nascimento.month)
    
    # Criar resposta com campos calculados
    pet_dict = {
        "id": pet.id,
        "codigo": pet.codigo,
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "data_nascimento": pet.data_nascimento,
        "idade_aproximada": pet.idade_aproximada,
        "castrado": pet.castrado,
        "castrado_data": pet.castrado_data,
        "cor": pet.cor,
        "porte": pet.porte,
        "peso": pet.peso,
        "peso_kg": pet.peso,  # Alias
        "idade_meses": idade_meses,
        "microchip": pet.microchip,
        "alergias": pet.alergias,
        "alergias_lista": pet.alergias_lista or [],
        "doencas_cronicas": pet.doencas_cronicas,
        "condicoes_cronicas_lista": pet.condicoes_cronicas_lista or [],
        "medicamentos_continuos": pet.medicamentos_continuos,
        "medicamentos_continuos_lista": pet.medicamentos_continuos_lista or [],
        "restricoes_alimentares_lista": pet.restricoes_alimentares_lista or [],
        "historico_clinico": pet.historico_clinico,
        "tipo_sanguineo": pet.tipo_sanguineo,
        "pedigree_registro": pet.pedigree_registro,
        "observacoes": pet.observacoes,
        "foto_url": pet.foto_url,
        "ativo": pet.ativo,
        "created_at": pet.created_at,
        "updated_at": pet.updated_at
    }
    
    return pet_dict


@router.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Desativar pet (soft delete)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    pet = db.query(Pet).join(Cliente).filter(
        Pet.id == pet_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet nÃ£o encontrado"
        )
    
    # Soft delete
    pet.ativo = False
    pet.updated_at = dt.utcnow()
    db.commit()
    
    # Log de auditoria
    log_delete(db, current_user.id, "pet", pet.id, {
        "nome": pet.nome,
        "especie": pet.especie,
        "cliente_id": pet.cliente_id
    })
    
    return None


# ==================== REMOVER CAMPO DUPLICADO ====================

@router.put("/{cliente_id}/remover-campo")
def remover_campo_duplicado(
    cliente_id: int,
    campo: str,
    novo_cliente_codigo: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Remove campo duplicado (telefone/celular/CPF) de um cliente antigo
    e adiciona observaÃ§Ã£o sobre a remoÃ§Ã£o.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Validar campo
    if campo not in ["telefone", "celular", "cpf", "cnpj"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo invÃ¡lido. Use: telefone, celular, cpf ou cnpj"
        )
    
    # Buscar cliente antigo
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Validar que estÃ¡ ativo
    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nÃ£o encontrado"
        )
    
    # Guardar valor antigo para log
    valor_antigo = getattr(cliente, campo)
    
    # Remover o campo
    setattr(cliente, campo, None)
    
    # Adicionar observaÃ§Ã£o
    observacao_atual = cliente.observacoes or ""
    nova_observacao = f"[SISTEMA] {campo.capitalize()} removido (valor anterior: {valor_antigo}) - Transferido para cadastro do cliente cÃ³digo {novo_cliente_codigo}"
    
    if observacao_atual:
        cliente.observacoes = f"{observacao_atual}\n\n{nova_observacao}"
    else:
        cliente.observacoes = nova_observacao
    
    cliente.updated_at = dt.utcnow()
    db.commit()
    
    # Log de auditoria
    log_update(db, current_user.id, "cliente", cliente.id, 
        {campo: valor_antigo},
        {campo: None, "observacoes": cliente.observacoes}
    )
    
    return {
        "message": f"{campo.capitalize()} removido com sucesso",
        "cliente_id": cliente.id,
        "campo_removido": campo,
        "valor_anterior": valor_antigo
    }


# ============================================================================
# GERENCIAMENTO DE CRÃ‰DITO
# ============================================================================

class AjustarCreditoRequest(BaseModel):
    valor: float
    motivo: str

@router.post("/{cliente_id}/credito/adicionar")
def adicionar_credito(
    cliente_id: int,
    dados: AjustarCreditoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Adiciona crÃ©dito ao saldo do cliente"""
    from decimal import Decimal
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nÃ£o encontrado"
        )
    
    if dados.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor deve ser maior que zero"
        )
    
    from app.models import CreditoLog

    # Adicionar crédito
    credito_anterior = float(cliente.credito or 0)
    cliente.credito = Decimal(str(credito_anterior + dados.valor))
    cliente.updated_at = dt.utcnow()

    # Log estruturado de crédito
    log_credito = CreditoLog(
        tenant_id=tenant_id,
        cliente_id=cliente.id,
        tipo='adicao_manual',
        valor=Decimal(str(dados.valor)),
        saldo_anterior=Decimal(str(credito_anterior)),
        saldo_atual=Decimal(str(float(cliente.credito))),
        motivo=dados.motivo,
        usuario_nome=current_user.nome or current_user.email,
    )
    db.add(log_credito)
    
    db.commit()
    
    # Log de auditoria
    log_update(db, current_user.id, "cliente", cliente.id,
        {"credito": credito_anterior},
        {"credito": float(cliente.credito)}
    )
    
    return {
        "message": "CrÃ©dito adicionado com sucesso",
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        "credito_anterior": credito_anterior,
        "valor_adicionado": dados.valor,
        "credito_atual": float(cliente.credito),
        "motivo": dados.motivo
    }


@router.post("/{cliente_id}/credito/remover")
def remover_credito(
    cliente_id: int,
    dados: AjustarCreditoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Remove crÃ©dito do saldo do cliente"""
    from decimal import Decimal
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nÃ£o encontrado"
        )
    
    if dados.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor deve ser maior que zero"
        )
    
    credito_atual = float(cliente.credito or 0)
    
    if dados.valor > credito_atual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valor a remover (R$ {dados.valor:.2f}) excede o crÃ©dito disponÃ­vel (R$ {credito_atual:.2f})"
        )
    
    from app.models import CreditoLog

    # Remover crédito
    novo_saldo = Decimal(str(credito_atual - dados.valor))
    cliente.credito = novo_saldo
    cliente.updated_at = dt.utcnow()

    # Log estruturado de crédito
    log_credito = CreditoLog(
        tenant_id=tenant_id,
        cliente_id=cliente.id,
        tipo='remocao_manual',
        valor=Decimal(str(dados.valor)),
        saldo_anterior=Decimal(str(credito_atual)),
        saldo_atual=novo_saldo,
        motivo=dados.motivo,
        usuario_nome=current_user.nome or current_user.email,
    )
    db.add(log_credito)

    db.commit()
    
    # Log de auditoria
    log_update(db, current_user.id, "cliente", cliente.id,
        {"credito": credito_atual},
        {"credito": float(cliente.credito)}
    )
    
    return {
        "message": "CrÃ©dito removido com sucesso",
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        "credito_anterior": credito_atual,
        "valor_removido": dados.valor,
        "credito_atual": float(cliente.credito),
        "motivo": dados.motivo
    }


# ============================================================================
# HISTÃ“RICO DE COMPRAS
# ============================================================================


# ============================================================================
# EXTRATO DE CRÉDITO
# ============================================================================

@router.get("/{cliente_id}/credito/extrato")
def get_extrato_credito(
    cliente_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Retorna o histórico de movimentações de crédito do cliente."""
    from app.models import CreditoLog
    from sqlalchemy import desc

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    _obter_cliente_ou_404(db, cliente_id, tenant_id)

    logs = (
        db.query(CreditoLog)
        .filter(CreditoLog.cliente_id == cliente_id, CreditoLog.tenant_id == tenant_id)
        .order_by(desc(CreditoLog.created_at))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "tipo": log.tipo,
            "valor": float(log.valor),
            "saldo_anterior": float(log.saldo_anterior),
            "saldo_atual": float(log.saldo_atual),
            "motivo": log.motivo,
            "referencia_id": log.referencia_id,
            "usuario_nome": log.usuario_nome,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/{cliente_id}/historico-compras")
async def get_historico_compras(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Retorna o histÃ³rico de compras do cliente"""
    from .vendas_models import Venda
    from sqlalchemy import func, desc
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Buscar vendas do cliente
    vendas = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id
    ).order_by(desc(Venda.data_venda)).all()
    
    # EstatÃ­sticas
    total_compras = len(vendas)
    total_gasto = sum(float(v.total or 0) for v in vendas if v.status == 'finalizada')
    ticket_medio = total_gasto / total_compras if total_compras > 0 else 0
    
    # Ãšltima compra
    ultima_compra = vendas[0].data_venda if vendas else None
    
    return {
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        # Campos no nÃ­vel raiz para compatibilidade com frontend
        "total_compras": total_compras,
        "valor_total_gasto": round(total_gasto, 2),
        "ticket_medio": round(ticket_medio, 2),
        "ultima_compra": ultima_compra.isoformat() if ultima_compra else None,
        # Mantendo estatisticas tambÃ©m para compatibilidade
        "estatisticas": {
            "total_compras": total_compras,
            "total_gasto": round(total_gasto, 2),
            "ticket_medio": round(ticket_medio, 2),
            "ultima_compra": ultima_compra.isoformat() if ultima_compra else None
        },
        "vendas": [
            {
                "id": v.id,
                "numero_venda": v.numero_venda if hasattr(v, 'numero_venda') and v.numero_venda else v.id,
                "data_venda": v.data_venda.isoformat() if hasattr(v.data_venda, 'isoformat') else str(v.data_venda),
                "total": float(v.total or 0),
                "subtotal": float(v.subtotal or 0) if hasattr(v, 'subtotal') else float(v.total or 0),
                "desconto_valor": float(v.desconto_valor or 0) if hasattr(v, 'desconto_valor') else 0,
                "taxa_entrega": float(v.taxa_entrega or 0) if hasattr(v, 'taxa_entrega') else 0,
                "saldo_devedor": float(v.total or 0) - (sum(float(pag.valor or 0) for pag in v.pagamentos) if hasattr(v, 'pagamentos') and v.pagamentos else 0),
                "status": v.status,
                "total_itens": len(v.itens) if v.itens else 0,
                "vendedor_nome": v.vendedor_nome if hasattr(v, 'vendedor_nome') else None,
                "observacoes": v.observacoes if hasattr(v, 'observacoes') else None,
                # Lista completa de formas de pagamento
                "pagamentos": [
                    {
                        "forma": (
                            pag.forma_pagamento.nome if (pag.forma_pagamento and hasattr(pag.forma_pagamento, 'nome'))
                            else str(pag.forma_pagamento) if pag.forma_pagamento
                            else "Não informado"
                        ),
                        "valor": float(pag.valor or 0)
                    }
                    for pag in (v.pagamentos or [])
                ],
                # Itens da venda
                "itens": [
                    {
                        "nome": (item.produto.nome if item.produto else item.servico_descricao) or "Item",
                        "quantidade": float(item.quantidade or 0),
                        "preco_unitario": float(item.preco_unitario or 0),
                        "subtotal": float(item.subtotal or 0),
                        "tipo": item.tipo or "produto",
                    }
                    for item in (v.itens or [])
                ]
            }
            for v in vendas
        ]
    }


@router.get("/{cliente_id}/vendas-em-aberto")
async def get_vendas_em_aberto(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Retorna vendas em aberto (pendentes) do cliente"""
    from .vendas_models import Venda
    from sqlalchemy import desc
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Buscar vendas em aberto do cliente (status: aberta ou baixa_parcial)
    # Ordenar da mais ANTIGA para a mais RECENTE (ordem ascendente)
    vendas_aberto = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id,
        Venda.status.in_(['aberta', 'baixa_parcial'])
    ).order_by(Venda.data_venda.asc()).all()
    
    # DEBUG: Log para verificar quantas vendas foram encontradas
    logger.info(f"ðŸ” DEBUG vendas-em-aberto: cliente_id={cliente_id}, user_id={current_user.id}")
    logger.info(f"ðŸ“Š Total vendas encontradas: {len(vendas_aberto)}")
    
    # Filtrar apenas vendas com saldo devedor maior que zero
    vendas_com_saldo = []
    for v in vendas_aberto:
        valor_pago = sum(float(pag.valor or 0) for pag in v.pagamentos) if hasattr(v, 'pagamentos') and v.pagamentos else 0
        saldo = float(v.total or 0) - valor_pago
        
        if saldo > 0.01:  # Apenas vendas com saldo maior que 1 centavo
            vendas_com_saldo.append(v)
            logger.info(f"  âœ… ID: {v.id} | Status: {v.status} | Total: R$ {v.total} | Pago: R$ {valor_pago} | Saldo: R$ {saldo}")
        else:
            logger.info(f"  âŒ ID: {v.id} | Status: {v.status} | Saldo zerado - EXCLUÃDA")
    
    # Usar apenas vendas com saldo
    vendas_aberto = vendas_com_saldo
    
    # Calcular valores
    total_vendas = len(vendas_aberto)
    valor_total = sum(float(v.total or 0) for v in vendas_aberto)
    
    # Calcular valor pago somando os pagamentos
    valor_pago = 0
    for v in vendas_aberto:
        if hasattr(v, 'pagamentos') and v.pagamentos:
            valor_pago += sum(float(pag.valor or 0) for pag in v.pagamentos)
    
    saldo_pendente = valor_total - valor_pago
    
    return {
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        "tem_vendas_aberto": total_vendas > 0,
        "resumo": {
            "total_vendas": total_vendas,
            "valor_total": round(valor_total, 2),
            "valor_pago": round(valor_pago, 2),
            "saldo_pendente": round(saldo_pendente, 2),
            "total_em_aberto": round(saldo_pendente, 2)  # Compatibilidade com frontend
        },
        "vendas": [
            {
                "id": v.id,
                "numero_venda": v.numero_venda,  # NÃºmero formatado da venda (ex: 202601190004)
                "data_venda": v.data_venda.isoformat() if hasattr(v.data_venda, 'isoformat') else str(v.data_venda),
                "total": float(v.total or 0),
                "total_pago": sum(float(pag.valor or 0) for pag in v.pagamentos) if hasattr(v, 'pagamentos') and v.pagamentos else 0,
                "saldo_devedor": float(v.total or 0) - (sum(float(pag.valor or 0) for pag in v.pagamentos) if hasattr(v, 'pagamentos') and v.pagamentos else 0),
                "status": v.status
            }
            for v in vendas_aberto
        ]
    }


@router.post("/{cliente_id}/baixar-vendas-lote")
async def baixar_vendas_lote(
    cliente_id: int,
    dados: dict,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """DÃ¡ baixa em mÃºltiplas vendas de uma vez, gerando movimentaÃ§Ãµes no caixa e contas a receber"""
    try:
        current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
        
        logger.info(f"\n=== BAIXAR VENDAS LOTE ===")
        logger.info(f"Cliente ID: {cliente_id}")
        logger.info(f"Dados recebidos: {dados}")
        
        from .vendas_models import Venda, VendaPagamento
        from .caixa_models import Caixa, MovimentacaoCaixa
        from .financeiro_models import ContaReceber, Recebimento
        from .ia.aba5_models import FluxoCaixa
        
        # Extrair dados do body
        vendas_ids = dados.get('vendas_ids', [])
        valor_total = float(dados.get('valor_total', 0))
        forma_pagamento = dados.get('forma_pagamento', '')
        numero_transacao = dados.get('numero_transacao')
        observacoes = dados.get('observacoes')
        
        logger.info(f"Vendas IDs: {vendas_ids}")
        logger.info(f"Valor total: {valor_total}")
        logger.info(f"Forma pagamento: {forma_pagamento}")
        
        # Validar se hÃ¡ caixa aberto
        caixa_aberto = db.query(Caixa).filter(
            Caixa.usuario_id == current_user.id,
            Caixa.tenant_id == tenant_id,
            Caixa.status == 'aberto'
        ).first()
        
        logger.info(f"Caixa aberto: {caixa_aberto}")
        
        if not caixa_aberto:
            raise HTTPException(
                status_code=400,
                detail='NÃ£o hÃ¡ caixa aberto. Abra o caixa antes de dar baixa nas vendas.'
            )
        
        # Buscar vendas ordenadas da mais antiga para a mais nova
        vendas = db.query(Venda).filter(
            Venda.id.in_(vendas_ids),
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(['aberta', 'baixa_parcial'])
        ).order_by(Venda.data_venda.asc()).all()  # Ordenar das mais antigas para as mais novas
        
        logger.info(f"Vendas encontradas: {len(vendas)}")
        
        if not vendas:
            raise HTTPException(status_code=404, detail='Nenhuma venda encontrada')
        
        if len(vendas) != len(vendas_ids):
            raise HTTPException(status_code=400, detail='Algumas vendas nÃ£o foram encontradas ou nÃ£o estÃ£o em aberto')
        
        # Calcular saldo devedor de cada venda
        vendas_com_saldo = []
        total_saldo_devedor = 0
        
        for venda in vendas:
            valor_ja_pago = sum(float(p.valor or 0) for p in venda.pagamentos) if venda.pagamentos else 0
            saldo_devedor = float(venda.total or 0) - valor_ja_pago
            
            logger.info(f"Venda {venda.id}: Total={venda.total}, Pago={valor_ja_pago}, Saldo={saldo_devedor}")
            
            if saldo_devedor > 0.01:  # TolerÃ¢ncia de 1 centavo
                vendas_com_saldo.append({
                    'venda': venda,
                    'saldo_devedor': saldo_devedor,
                    'valor_ja_pago': valor_ja_pago
                })
                total_saldo_devedor += saldo_devedor
        
        logger.info(f"Vendas com saldo: {len(vendas_com_saldo)}, Total saldo: {total_saldo_devedor}")
        
        if not vendas_com_saldo:
            raise HTTPException(status_code=400, detail='Todas as vendas jÃ¡ estÃ£o quitadas')
        
        if valor_total > total_saldo_devedor + 0.01:
            raise HTTPException(
                status_code=400,
                detail=f'Valor do pagamento (R$ {valor_total:.2f}) excede o saldo devedor total (R$ {total_saldo_devedor:.2f})'
            )
        
        # Distribuir o valor proporcionalmente entre as vendas
        valor_restante = valor_total
        vendas_quitadas = []
        vendas_parciais = []
        
        for item in vendas_com_saldo:
            venda = item['venda']
            saldo_devedor = item['saldo_devedor']
            
            # Calcular quanto aplicar nesta venda (proporcional ao saldo)
            if valor_restante <= 0:
                break
                
            valor_aplicar = min(valor_restante, saldo_devedor)
            
            logger.info(f"Aplicando {valor_aplicar} na venda {venda.id}")
            
            # Criar pagamento
            # ðŸ”’ ISOLAMENTO MULTI-TENANT: tenant_id obrigatÃ³rio
            pagamento = VendaPagamento(
                venda_id=venda.id,
                tenant_id=tenant_id,  # âœ… Garantir isolamento entre empresas
                forma_pagamento=forma_pagamento,
                valor=valor_aplicar,
                numero_transacao=numero_transacao,
                status='confirmado',
                data_pagamento=dt.now()
            )
            db.add(pagamento)
            
            # Atualizar status da venda
            novo_valor_pago = item['valor_ja_pago'] + valor_aplicar
            novo_saldo = float(venda.total) - novo_valor_pago
            
            if abs(novo_saldo) < 0.01:  # Quitada
                venda.status = 'finalizada'
                vendas_quitadas.append({
                    'id': venda.id,
                    'numero_venda': venda.id,
                    'valor_baixado': valor_aplicar,
                    'saldo_anterior': saldo_devedor
                })
            else:  # Baixa parcial
                venda.status = 'baixa_parcial'
                vendas_parciais.append({
                    'id': venda.id,
                    'numero_venda': venda.id,
                    'valor_baixado': valor_aplicar,
                    'saldo_restante': novo_saldo,
                    'saldo_anterior': saldo_devedor
                })
            
            # Registrar movimentaÃ§Ã£o no caixa (apenas para formas que movimentam caixa)
            formas_que_movimentam_caixa = ['dinheiro', 'Dinheiro', 'pix', 'PIX', 'cartao_debito', 'CartÃ£o de DÃ©bito']
            if forma_pagamento in formas_que_movimentam_caixa:
                # ðŸ”’ ISOLAMENTO MULTI-TENANT: tenant_id obrigatÃ³rio
                movimentacao = MovimentacaoCaixa(
                    caixa_id=caixa_aberto.id,
                    tipo='venda',
                    categoria='venda',
                    valor=valor_aplicar,
                    forma_pagamento=forma_pagamento,
                    descricao=f'Baixa venda #{venda.id} - {venda.cliente.nome if venda.cliente else "Cliente avulso"}',
                    venda_id=venda.id,
                    usuario_id=current_user.id,
                    usuario_nome=current_user.nome or current_user.email,
                    data_movimento=dt.now(),
                    tenant_id=tenant_id  # âœ… Garantir isolamento entre empresas
                )
                db.add(movimentacao)
            
            # Dar baixa no contas a receber (se existir)
            conta_receber = db.query(ContaReceber).filter(
                ContaReceber.venda_id == venda.id,
                ContaReceber.status.in_(['pendente', 'baixa_parcial', 'parcial'])
            ).first()
            
            if conta_receber:
                valor_ja_recebido = float(conta_receber.valor_recebido or 0)
                novo_valor_recebido = valor_ja_recebido + valor_aplicar
                
                conta_receber.valor_recebido = novo_valor_recebido
                conta_receber.data_recebimento = dt.now()
                
                if abs(float(conta_receber.valor_final) - novo_valor_recebido) < 0.01:
                    conta_receber.status = 'pago'
                else:
                    conta_receber.status = 'baixa_parcial'
                
                # ðŸ†• Criar registro de recebimento
                recebimento = Recebimento(
                    conta_receber_id=conta_receber.id,
                    valor_recebido=valor_aplicar,
                    data_recebimento=dt.now().date(),
                    observacoes=f'Baixa em lote - {forma_pagamento}',
                    user_id=current_user.id,
                    tenant_id=tenant_id  # âœ… Garantir isolamento multi-tenant
                )
                db.add(recebimento)
                
                # ðŸ†• CRIAR LANÃ‡AMENTO REALIZADO NO FLUXO DE CAIXA
                fluxo_realizado = FluxoCaixa(
                    usuario_id=current_user.id,
                    tipo='entrada',
                    categoria='Recebimento de Venda',
                    descricao=f'Baixa venda #{venda.numero_venda} - {venda.cliente.nome if venda.cliente else "Cliente avulso"}',
                    valor=valor_aplicar,
                    data_movimentacao=dt.now(),
                    data_prevista=None,
                    status='realizado',
                    origem_tipo='conta_receber',
                    origem_id=conta_receber.id
                )
                db.add(fluxo_realizado)
                
                logger.info(f"âœ… Fluxo de caixa REALIZADO criado: R$ {valor_aplicar:.2f}")
                
                # ðŸ†• CRIAR LANÃ‡AMENTO PREVISTO NO FLUXO DE CAIXA (se houver saldo restante)
                saldo_conta = float(conta_receber.valor_final) - novo_valor_recebido
                if saldo_conta > 0.01:  # Se ainda tem saldo
                    data_previsao = dt.now() + timedelta(days=30)  # +30 dias
                    
                    fluxo_previsto = FluxoCaixa(
                        usuario_id=current_user.id,
                        tipo='entrada',
                        categoria='Recebimento de Venda',
                        descricao=f'Saldo previsto venda #{venda.numero_venda} - {venda.cliente.nome if venda.cliente else "Cliente avulso"}',
                        valor=saldo_conta,
                        data_movimentacao=None,
                        data_prevista=data_previsao,
                        status='previsto',
                        origem_tipo='conta_receber',
                        origem_id=conta_receber.id
                    )
                    db.add(fluxo_previsto)
                    
                    logger.info(f"âœ… Fluxo de caixa PREVISTO criado: R$ {saldo_conta:.2f} para {data_previsao.strftime('%d/%m/%Y')}")
            
            valor_restante -= valor_aplicar
        
        db.commit()
        
        logger.info(f"Commit realizado com sucesso!")
        
        return {
            "success": True,
            "total_vendas_afetadas": len(vendas_quitadas) + len(vendas_parciais),
            "vendas_quitadas": vendas_quitadas,
            "vendas_parciais": vendas_parciais,
            "valor_total_baixado": valor_total,
            "valor_restante": valor_restante,
            "message": f"Baixa realizada com sucesso! {len(vendas_quitadas)} vendas quitadas, {len(vendas_parciais)} com baixa parcial."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"ERRO NO PROCESSAMENTO: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar baixa: {str(e)}")


@router.get("/{cliente_id}/historico")
async def get_cliente_historico(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    âš ï¸ **DEPRECATED** - Esta rota serÃ¡ removida em versÃ£o futura
    
    **Problemas desta rota:**
    - âŒ Carrega TODAS as transaÃ§Ãµes em memÃ³ria (sem paginaÃ§Ã£o)
    - âŒ Performance ruim com histÃ³rico grande (>500 transaÃ§Ãµes)
    - âŒ Alto consumo de memÃ³ria
    - âŒ Ordena tudo em Python (deveria ser no banco)
    
    **Migre para as novas rotas:**
    
    1. **Para histÃ³rico completo paginado:**
       ```
       GET /financeiro/cliente/{cliente_id}?page=1&per_page=20
       ```
       - PaginaÃ§Ã£o obrigatÃ³ria
       - Filtros: data_inicio, data_fim, tipo, status
       - Performance otimizada
    
    2. **Para resumo leve (uso no cadastro):**
       ```
       GET /financeiro/cliente/{cliente_id}/resumo
       ```
       - Apenas dados agregados (COUNT, SUM)
       - Muito mais rÃ¡pido (~10-50ms vs 500-2000ms)
       - Ideal para Step 6 do wizard
    
    **Data de remoÃ§Ã£o planejada:** Junho/2026
    
    ---
    
    Retorna o histÃ³rico completo de transaÃ§Ãµes do cliente:
    - Vendas realizadas
    - DevoluÃ§Ãµes
    - Contas a receber (em aberto e pagas)
    - Recebimentos
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    user = current_user  # Definir variÃ¡vel user para uso posterior
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Importar modelos necessÃ¡rios
    from app.vendas_models import Venda
    from app.financeiro_models import ContaReceber, Recebimento
    
    historico = []
    
    # 1. Buscar vendas do cliente (excluir canceladas/devolvidas do histÃ³rico principal)
    vendas = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.status.notin_(['cancelada', 'devolvida'])
    ).order_by(Venda.data_venda.desc()).all()
    
    for venda in vendas:
        historico.append({
            "tipo": "venda",
            "data": venda.data_venda.isoformat() if venda.data_venda else None,
            "descricao": f"Venda #{venda.numero_venda}",
            "valor": float(venda.total),
            "status": venda.status,
            "detalhes": {
                "venda_id": venda.id,
                "numero_venda": venda.numero_venda,
                "subtotal": float(venda.subtotal),
                "desconto": float(venda.desconto_valor) if venda.desconto_valor else 0,
                "total": float(venda.total),
                "status": venda.status,
                "canal": venda.canal,
                "observacoes": venda.observacoes
            }
        })
    
    # 2. Buscar devoluÃ§Ãµes (vendas canceladas/devolvidas)
    devolucoes = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.status.in_(['cancelada', 'devolvida'])
    ).order_by(Venda.data_venda.desc()).all()
    
    for devolucao in devolucoes:
        historico.append({
            "tipo": "devolucao",
            "data": devolucao.data_venda.isoformat() if devolucao.data_venda else None,
            "descricao": f"DevoluÃ§Ã£o - Venda #{devolucao.numero_venda}",
            "valor": -float(devolucao.total),
            "status": devolucao.status,
            "detalhes": {
                "numero_venda": devolucao.numero_venda,
                "total": float(devolucao.total),
                "motivo": devolucao.observacoes
            }
        })
    
    # 3. Buscar contas a receber
    contas_receber = db.query(ContaReceber).filter(
        ContaReceber.cliente_id == cliente_id
    ).order_by(ContaReceber.data_vencimento.desc()).all()
    
    for conta in contas_receber:
        valor_recebido = float(conta.valor_recebido) if conta.valor_recebido else 0
        valor_pendente = float(conta.valor_original) - valor_recebido
        
        historico.append({
            "tipo": "conta_receber",
            "data": conta.data_emissao.isoformat() if conta.data_emissao else None,
            "descricao": conta.descricao,
            "valor": float(conta.valor_original),
            "status": conta.status,
            "detalhes": {
                "vencimento": conta.data_vencimento.isoformat() if conta.data_vencimento else None,
                "valor_original": float(conta.valor_original),
                "valor_recebido": valor_recebido,
                "valor_pendente": valor_pendente,
                "status": conta.status,
                "numero_parcela": conta.numero_parcela,
                "total_parcelas": conta.total_parcelas
            }
        })
    
    # 4. Buscar recebimentos
    recebimentos = db.query(Recebimento).join(ContaReceber).filter(
        ContaReceber.cliente_id == cliente_id
    ).order_by(Recebimento.data_recebimento.desc()).all()
    
    for rec in recebimentos:
        historico.append({
            "tipo": "recebimento",
            "data": rec.data_recebimento.isoformat() if rec.data_recebimento else None,
            "descricao": f"Recebimento - {rec.conta.descricao if rec.conta else 'Conta'}",
            "valor": float(rec.valor_recebido),
            "status": "efetivado",
            "detalhes": {
                "valor": float(rec.valor_recebido),
                "forma_pagamento": rec.forma_pagamento.nome if rec.forma_pagamento else None,
                "observacoes": rec.observacoes
            }
        })
    
    # Ordenar histÃ³rico por data (mais recente primeiro)
    historico.sort(key=lambda x: x['data'] if x['data'] else '', reverse=True)
    
    # Calcular totais
    total_vendas = sum(float(v.total) for v in vendas)
    total_em_aberto = sum(float(c.valor_original) - float(c.valor_recebido or 0) for c in contas_receber if c.status == 'pendente')
    total_recebido = sum(float(r.valor_recebido) for r in recebimentos)
    
    return {
        "cliente": {
            "id": cliente.id,
            "codigo": cliente.codigo,
            "nome": cliente.nome,
            "credito_atual": float(cliente.credito) if cliente.credito else 0
        },
        "resumo": {
            "total_vendas": total_vendas,
            "total_em_aberto": total_em_aberto,
            "total_recebido": total_recebido,
            "total_transacoes": len(historico)
        },
        "historico": historico
    }


# ============================================================
# TIMELINE UNIFICADA DO CLIENTE
# ============================================================

class TimelineEvento(BaseModel):
    """Evento da timeline do cliente"""
    tipo_evento: str
    evento_id: int
    cliente_id: int
    pet_id: Optional[int] = None
    data_evento: dt
    titulo: str
    descricao: str
    status: str
    cor_badge: str
    
    class Config:
        from_attributes = True


@router.get("/{cliente_id}/timeline", response_model=List[TimelineEvento])
def obter_timeline_cliente(
    cliente_id: int,
    tipo_evento: Optional[str] = Query(None, description="Filtrar por tipo de evento"),
    pet_id: Optional[int] = Query(None, description="Filtrar eventos de um pet especÃ­fico"),
    limit: int = Query(20, ge=1, le=100, description="Limite de eventos"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna a timeline consolidada do cliente com eventos de:
    - Vendas
    - Contas a receber
    - Pets (cadastro e atualizaÃ§Ãµes)
    
    OrdenaÃ§Ã£o: mais recente â†’ mais antigo
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Validar se cliente existe e pertence ao usuÃ¡rio
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nÃ£o encontrado"
        )
    
    return _obter_timeline(db, "cliente_timeline", cliente_id, tipo_evento, pet_id, limit)


def _obter_timeline(db: Session, view_name: str, entity_id: int, tipo_evento: Optional[str], pet_id: Optional[int], limit: int):
    """Função auxiliar para buscar timeline de qualquer entidade — consulta tabelas diretamente."""
    from .vendas_models import Venda
    from .financeiro_models import ContaReceber
    
    is_cliente = "cliente" in view_name
    eventos: list[TimelineEvento] = []

    # ─── 1. VENDAS ───────────────────────────────────────────────────────────
    if is_cliente and (not tipo_evento or tipo_evento == "venda"):
        filtro = [Venda.cliente_id == entity_id]
        vendas_q = db.query(Venda).filter(*filtro).order_by(Venda.data_venda.desc()).limit(limit).all()
        for v in vendas_q:
            cor = {"finalizada": "green", "pendente": "yellow", "cancelada": "red"}.get(v.status or "", "gray")
            eventos.append(TimelineEvento(
                tipo_evento="venda",
                evento_id=v.id,
                cliente_id=entity_id,
                pet_id=None,
                data_evento=v.data_venda or v.created_at,
                titulo=f"Venda #{v.numero_venda or v.id}",
                descricao=f"R$ {float(v.total or 0):.2f} - {v.status or ''}",
                status=v.status or "",
                cor_badge=cor,
            ))

    # ─── 2. CONTAS A RECEBER ─────────────────────────────────────────────────
    if is_cliente and (not tipo_evento or tipo_evento == "conta_receber"):
        contas_q = (
            db.query(ContaReceber)
            .filter(ContaReceber.cliente_id == entity_id)
            .order_by(ContaReceber.data_vencimento.desc())
            .limit(limit)
            .all()
        )
        for cr in contas_q:
            cor = {"recebido": "green", "pendente": "yellow", "vencido": "red", "cancelado": "gray"}.get(cr.status or "", "blue")
            eventos.append(TimelineEvento(
                tipo_evento="conta_receber",
                evento_id=cr.id,
                cliente_id=entity_id,
                pet_id=None,
                data_evento=cr.data_vencimento or cr.data_emissao or cr.created_at,
                titulo="Conta a Receber",
                descricao=f"R$ {float(cr.valor_original or 0):.2f} - {cr.descricao or ''}",
                status=cr.status or "",
                cor_badge=cor,
            ))

    # ─── 3. PETS ─────────────────────────────────────────────────────────────
    if is_cliente and (not tipo_evento or tipo_evento in ("pet_cadastro", "pet_atualizacao")):
        filtro_pet = [Pet.cliente_id == entity_id]
        if pet_id:
            filtro_pet.append(Pet.id == pet_id)
        pets_q = db.query(Pet).filter(*filtro_pet).all()
        for p in pets_q:
            cor = "blue" if p.ativo else "gray"
            st = "ativo" if p.ativo else "inativo"
            if not tipo_evento or tipo_evento == "pet_cadastro":
                eventos.append(TimelineEvento(
                    tipo_evento="pet_cadastro",
                    evento_id=p.id,
                    cliente_id=entity_id,
                    pet_id=p.id,
                    data_evento=p.created_at,
                    titulo=f"🐾 Pet cadastrado: {p.nome}",
                    descricao=f"{p.especie or ''}{(' - ' + p.raca) if p.raca else ''}",
                    status=st,
                    cor_badge=cor,
                ))
            _upd = p.updated_at.replace(tzinfo=None) if p.updated_at else None
            _crt = p.created_at.replace(tzinfo=None) if p.created_at else None
            if (not tipo_evento or tipo_evento == "pet_atualizacao") and p.updated_at and _upd != _crt:
                eventos.append(TimelineEvento(
                    tipo_evento="pet_atualizacao",
                    evento_id=p.id,
                    cliente_id=entity_id,
                    pet_id=p.id,
                    data_evento=p.updated_at,
                    titulo=f"✏️ Pet atualizado: {p.nome}",
                    descricao="Informações atualizadas",
                    status=st,
                    cor_badge="purple",
                ))

    # Ordenar por data decrescente e aplicar limite
    # Normaliza timezone para evitar TypeError ao comparar naive vs aware
    def _to_aware(d):
        if d is None:
            from datetime import timezone as _tz
            return dt.min.replace(tzinfo=_tz.utc)
        if d.tzinfo is None:
            from datetime import timezone as _tz
            return d.replace(tzinfo=_tz.utc)
        return d

    eventos.sort(key=lambda e: _to_aware(e.data_evento), reverse=True)
    return eventos[:limit]


# ============================================================
# TIMELINE DE FORNECEDORES
# ============================================================

@router.get("/fornecedor/{fornecedor_id}/timeline", response_model=List[TimelineEvento])
def obter_timeline_fornecedor(
    fornecedor_id: int,
    tipo_evento: Optional[str] = Query(None, description="Filtrar por tipo de evento"),
    limit: int = Query(20, ge=1, le=100, description="Limite de eventos"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna a timeline consolidada do fornecedor com eventos de:
    - Pedidos de compra
    - Contas a pagar
    - Recebimentos de mercadorias
    
    OrdenaÃ§Ã£o: mais recente â†’ mais antigo
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Validar se fornecedor existe e pertence ao usuÃ¡rio
    fornecedor = db.query(Cliente).filter(
        Cliente.id == fornecedor_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == 'fornecedor'
    ).first()
    
    if not fornecedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fornecedor nÃ£o encontrado"
        )
    
    return _obter_timeline(db, "fornecedor_timeline", fornecedor_id, tipo_evento, None, limit)


# ============================================================
# ðŸšš ENTREGADORES - Custo Operacional
# ============================================================

@router.get("/entregadores/{entregador_id}/custo-operacional")
def obter_custo_operacional_entregador(
    entregador_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna o custo operacional calculado para o entregador.
    
    Para modelo 'rateio_rh':
    - Calcula custo_por_entrega = custo_rh_ajustado / media_entregas_real (se disponÃ­vel)
    - SenÃ£o usa media_entregas_configurada como fallback
    
    Para modelo 'taxa_fixa':
    - Retorna taxa_fixa_entrega
    
    Para modelo 'por_km':
    - Retorna valor_por_km_entrega (frontend precisa multiplicar pela distÃ¢ncia)
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar entregador
    entregador = db.query(Cliente).filter(
        Cliente.id == entregador_id,
        Cliente.tenant_id == tenant_id,
        Cliente.is_entregador == True
    ).first()
    
    if not entregador:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entregador nÃ£o encontrado"
        )
    
    custo_por_entrega = 0
    modelo = entregador.modelo_custo_entrega
    detalhes = {}
    
    if modelo == 'rateio_rh' and entregador.controla_rh:
        # Usar custo_rh_ajustado se disponÃ­vel
        if entregador.custo_rh_ajustado:
            custo_rh = float(entregador.custo_rh_ajustado)
            # Usar mÃ©dia real se disponÃ­vel, senÃ£o configurada
            media_entregas = entregador.media_entregas_real or entregador.media_entregas_configurada or 1
            custo_por_entrega = custo_rh / media_entregas if media_entregas > 0 else 0
            
            detalhes = {
                "custo_rh": custo_rh,
                "media_entregas": media_entregas,
                "tipo_media": "real" if entregador.media_entregas_real else "configurada"
            }
        else:
            # Sem custo RH configurado
            custo_por_entrega = 0
            detalhes = {"aviso": "Custo RH nÃ£o configurado"}
    
    elif modelo == 'taxa_fixa':
        custo_por_entrega = float(entregador.taxa_fixa_entrega or 0)
        detalhes = {"taxa_fixa": custo_por_entrega}
    
    elif modelo == 'por_km':
        custo_por_entrega = float(entregador.valor_por_km_entrega or 0)
        detalhes = {
            "valor_por_km": custo_por_entrega,
            "observacao": "Requer cÃ¡lculo de distÃ¢ncia no frontend"
        }
    
    else:
        # Sem modelo configurado
        detalhes = {"aviso": "Modelo de custo nÃ£o configurado"}
    
    return {
        "entregador_id": entregador_id,
        "nome": entregador.nome_fantasia or entregador.nome,
        "modelo_custo": modelo,
        "custo_por_entrega": round(custo_por_entrega, 2),
        "detalhes": detalhes
    }

