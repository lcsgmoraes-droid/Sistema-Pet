# ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
# Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
# NÃO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenário real
# 3. Validar impacto financeiro

"""
Routes para gerenciamento de Clientes e Pets
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime as dt, date, timedelta
from decimal import Decimal
from pydantic import BaseModel, EmailStr, validator
import logging

from app.db import get_session
from app.models import User, Cliente, Pet, Raca
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.audit_log import log_create, log_update, log_delete
from app.security.permissions_decorator import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clientes", tags=["clientes"])


# ========== HELPERS INTERNOS ==========

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant (padrão repetido 21x)"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    """Busca cliente com validação de tenant e retorna 404 se não encontrado"""
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return cliente


# ========== UTILITÁRIOS ==========

def gerar_codigo_cliente(db: Session, tipo_cadastro: str, tipo_pessoa: str, tenant_id: int) -> str:
    """
    Gera código único para cliente seguindo o padrão:
    - Cliente PF: 1XXX (inicia em 1001)
    - Cliente PJ: 2XXX (inicia em 2001)
    - Fornecedor: 3XXX (inicia em 3001)
    - Veterinário: 4XXX (inicia em 4001)
    - Funcionário: 5XXX (inicia em 5001)
    """
    # Definir prefixo baseado no tipo
    if tipo_cadastro == 'cliente':
        prefixo = 1 if tipo_pessoa == 'PF' else 2
        base = prefixo * 1000 + 1  # 1001 ou 2001
    elif tipo_cadastro == 'fornecedor':
        prefixo = 3
        base = 3001
    elif tipo_cadastro == 'veterinario':
        prefixo = 4
        base = 4001
    elif tipo_cadastro == 'funcionario':
        prefixo = 5
        base = 5001
    else:
        # Fallback para tipos não mapeados
        prefixo = 9
        base = 9001
    
    # Buscar códigos existentes com este prefixo APENAS DESTE TENANT
    codigos_usados = db.query(Cliente.codigo).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.codigo.like(f'{prefixo}%'),
        Cliente.ativo == True
    ).all()
    
    codigos_usados_set = {int(c[0]) for c in codigos_usados if c[0] and c[0].isdigit()}
    
    # Encontrar próximo código disponível
    proximo_codigo = base
    while proximo_codigo in codigos_usados_set:
        proximo_codigo += 1
    
    return str(proximo_codigo)


# Schemas
class PetCreate(BaseModel):
    nome: str
    especie: str
    raca: Optional[str] = None
    sexo: Optional[str] = None
    data_nascimento: Optional[date] = None
    cor: Optional[str] = None
    peso: Optional[float] = None
    observacoes: Optional[str] = None

    model_config = {"from_attributes": True}


class PetUpdate(BaseModel):
    nome: Optional[str] = None
    especie: Optional[str] = None
    raca: Optional[str] = None
    sexo: Optional[str] = None
    data_nascimento: Optional[dt] = None
    cor: Optional[str] = None
    peso: Optional[float] = None
    observacoes: Optional[str] = None
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
    cor: Optional[str]
    peso: Optional[float]
    peso_kg: Optional[float] = None  # Alias para compatibilidade
    idade_meses: Optional[int] = None  # Calculado a partir da data_nascimento
    observacoes: Optional[str]
    ativo: bool
    created_at: dt
    updated_at: dt

    model_config = {"from_attributes": True}


class ClienteCreate(BaseModel):
    # Tipo de cadastro
    tipo_cadastro: str = "cliente"  # cliente, fornecedor, veterinario, funcionario
    tipo_pessoa: str = "PF"  # PF ou PJ
    
    # Dados comuns
    nome: str  # Nome completo (PF) ou Nome Fantasia (PJ)
    telefone: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    
    # Pessoa Física
    cpf: Optional[str] = None
    
    # Pessoa Jurídica
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    responsavel: Optional[str] = None
    
    # Veterinário
    crmv: Optional[str] = None
    
    # Sistema de parceiros (comissões)
    parceiro_ativo: Optional[bool] = False
    parceiro_desde: Optional[str] = None
    parceiro_observacoes: Optional[str] = None
    
    # Endereço
    cep: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    
    # Endereços de entrega
    endereco_entrega: Optional[str] = None
    endereco_entrega_2: Optional[str] = None
    enderecos_adicionais: Optional[list] = None  # Array de endereços com tipo, apelido, etc.
    
    # 🚚 ENTREGADOR (SPRINT 1)
    is_entregador: bool = False
    entregador_padrao: bool = False
    is_terceirizado: bool = False
    recebe_repasse: bool = False
    gera_conta_pagar: bool = False
    tipo_vinculo_entrega: Optional[str] = None  # funcionario | terceirizado | eventual
    valor_padrao_entrega: Optional[Decimal] = None
    valor_por_km: Optional[Decimal] = None
    recebe_comissao_entrega: bool = False
    
    # 📆 ACERTO FINANCEIRO (ETAPA 4)
    tipo_acerto_entrega: Optional[str] = None  # semanal | quinzenal | mensal
    dia_semana_acerto: Optional[int] = None  # 1=segunda ... 7=domingo
    dia_mes_acerto: Optional[int] = None  # 1 a 28
    data_ultimo_acerto: Optional[str] = None  # Data do último acerto (YYYY-MM-DD)
    
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
    
    # Veterinário
    crmv: Optional[str] = None
    
    # Sistema de parceiros (comissões)
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
    
    # Endereços de entrega
    endereco_entrega: Optional[str] = None
    endereco_entrega_2: Optional[str] = None
    enderecos_adicionais: Optional[list] = None  # Array de endereços com tipo, apelido, etc.
    
    # 🚚 ENTREGADOR (SPRINT 1)
    is_entregador: Optional[bool] = None
    is_terceirizado: Optional[bool] = None
    recebe_repasse: Optional[bool] = None
    gera_conta_pagar: Optional[bool] = None
    tipo_vinculo_entrega: Optional[str] = None
    valor_padrao_entrega: Optional[Decimal] = None
    valor_por_km: Optional[Decimal] = None
    recebe_comissao_entrega: Optional[bool] = None
    
    # 🚚 ENTREGADOR - SISTEMA COMPLETO (FASE 2)
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
    
    # 📆 ACERTO FINANCEIRO (ETAPA 4)
    tipo_acerto_entrega: Optional[str] = None  # semanal | quinzenal | mensal
    dia_semana_acerto: Optional[int] = None  # 1=segunda ... 7=domingo
    dia_mes_acerto: Optional[int] = None  # 1 a 28
    data_ultimo_acerto: Optional[str] = None  # Data do último acerto (YYYY-MM-DD)
    
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
    
    # Veterinário
    crmv: Optional[str] = None
    
    # Sistema de parceiros (comissões)
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
    
    # Endereços adicionais
    endereco_entrega: Optional[str] = None
    endereco_entrega_2: Optional[str] = None
    enderecos_adicionais: Optional[list] = None
    
    # 🚚 ENTREGADOR (SPRINT 1)
    is_entregador: bool = False
    is_terceirizado: bool = False
    recebe_repasse: bool = False
    gera_conta_pagar: bool = False
    tipo_vinculo_entrega: Optional[str] = None
    valor_padrao_entrega: Optional[Decimal] = None
    valor_por_km: Optional[Decimal] = None
    recebe_comissao_entrega: bool = False
    
    # 🚚 ENTREGADOR - SISTEMA COMPLETO (FASE 2)
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
    
    # 📆 ACERTO FINANCEIRO (ETAPA 4)
    tipo_acerto_entrega: Optional[str] = None  # semanal | quinzenal | mensal
    dia_semana_acerto: Optional[int] = None  # 1=segunda ... 7=domingo
    dia_mes_acerto: Optional[int] = None  # 1 a 28
    data_ultimo_acerto: Optional[str] = None  # Data do último acerto (YYYY-MM-DD)
    
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
    
    # Validar documento conforme tipo de pessoa (CPF não é obrigatório)
    if cliente_data.tipo_pessoa == "PF":
        # Verificar se CPF já existe (se fornecido)
        if cliente_data.cpf:
            existing = db.query(Cliente).filter(
                Cliente.tenant_id == tenant_id,
                Cliente.cpf == cliente_data.cpf,
                Cliente.ativo == True
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Já existe um {cliente_data.tipo_cadastro} cadastrado com este CPF"
                )
    
    elif cliente_data.tipo_pessoa == "PJ":
        if not cliente_data.cnpj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNPJ é obrigatório para Pessoa Jurídica"
            )
        # Verificar se CNPJ já existe
        existing = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cnpj == cliente_data.cnpj,
            Cliente.ativo == True
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um {cliente_data.tipo_cadastro} cadastrado com este CNPJ"
            )
    
    # Verificar se CRMV já existe (se fornecido e for veterinário)
    if cliente_data.crmv and cliente_data.tipo_cadastro == "veterinario":
        existing_crmv = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.crmv == cliente_data.crmv,
            Cliente.ativo == True
        ).first()
        if existing_crmv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um veterinário cadastrado com este CRMV"
            )
    
    # Verificar se celular já existe (se fornecido)
    if cliente_data.celular:
        existing_cel = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.celular == cliente_data.celular,
            Cliente.ativo == True
        ).first()
        if existing_cel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um cadastro com este celular"
            )
    
    # Verificar se telefone já existe (se fornecido)
    if cliente_data.telefone:
        existing_tel = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.telefone == cliente_data.telefone,
            Cliente.ativo == True
        ).first()
        if existing_tel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um cliente cadastrado com este telefone"
            )
    
    # Gerar código usando a nova função
    codigo = gerar_codigo_cliente(db, cliente_data.tipo_cadastro, cliente_data.tipo_pessoa, tenant_id)
    
    # Preparar dados do cliente
    dados_cliente = cliente_data.model_dump()
    
    # 🚚 VALIDAÇÃO: Apenas 1 entregador padrão por vez
    if dados_cliente.get('entregador_padrao') is True:
        # Verificar se já existe outro entregador padrão
        entregador_padrao_atual = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.entregador_padrao == True,
            Cliente.ativo == True
        ).first()
        
        if entregador_padrao_atual:
            # Desmarcar o antigo como padrão
            entregador_padrao_atual.entregador_padrao = False
            entregador_padrao_atual.updated_at = dt.utcnow()
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🚚 Entregador padrão removido de: {entregador_padrao_atual.nome} (ID: {entregador_padrao_atual.id})")
    
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
    db.commit()
    db.refresh(novo_cliente)
    
    # Log de auditoria
    log_create(db, current_user.id, "cliente", novo_cliente.id, cliente_data.model_dump())
    
    return novo_cliente


@router.get("/", response_model=List[ClienteResponse])
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
    """Listar clientes/fornecedores do usuário"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    try:
        query = db.query(Cliente).filter(Cliente.tenant_id == tenant_id)
        
        # Filtro por tipo de cadastro (aceita lista ou string)
        if tipo_cadastro:
            if isinstance(tipo_cadastro, list):
                query = query.filter(Cliente.tipo_cadastro.in_(tipo_cadastro))
            else:
                query = query.filter(Cliente.tipo_cadastro == tipo_cadastro)
        
        # Filtro por entregador
        if is_entregador is not None:
            query = query.filter(Cliente.is_entregador == is_entregador)
        
        # Filtro de busca
        if search:
            query = query.filter(
                (Cliente.nome.ilike(f"%{search}%")) |
                (Cliente.cpf.ilike(f"%{search}%")) |
                (Cliente.cnpj.ilike(f"%{search}%")) |
                (Cliente.razao_social.ilike(f"%{search}%")) |
                (Cliente.email.ilike(f"%{search}%")) |
                (Cliente.telefone.ilike(f"%{search}%")) |
                (Cliente.celular.ilike(f"%{search}%"))
            )
        
        # Filtro de ativo (padrão True - mostrar apenas ativos)
        if ativo is None:
            ativo = True
        query = query.filter(Cliente.ativo == ativo)
        
        clientes = query.order_by(Cliente.nome).offset(skip).limit(limit).all()
        return clientes
        
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


# ==================== RAÇAS ====================

@router.get("/racas-teste")
def list_racas_teste(especie: str = ""):
    """Teste simples sem dependências"""
    return [
        {"id": 1, "nome": "Labrador", "especie": "Cão"},
        {"id": 2, "nome": "Siamês", "especie": "Gato"}
    ]

@router.get("/racas")
def list_racas(
    especie: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Listar raças cadastradas (filtro por espécie)"""
    
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
                detail="Já existe um cliente cadastrado com este CPF"
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
                detail="Já existe um cadastro com este CNPJ"
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
                detail="Já existe um veterinário cadastrado com este CRMV"
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
                detail="Já existe um cliente cadastrado com este celular"
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
                detail="Já existe um cliente cadastrado com este telefone"
            )
    
    # Atualizar campos
    update_data = cliente_data.model_dump(exclude_unset=True)
    
    # 🚚 VALIDAÇÃO: Apenas 1 entregador padrão por vez
    if 'entregador_padrao' in update_data and update_data['entregador_padrao'] is True:
        # Verificar se já existe outro entregador padrão
        entregador_padrao_atual = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.entregador_padrao == True,
            Cliente.id != cliente_id,
            Cliente.ativo == True
        ).first()
        
        if entregador_padrao_atual:
            # Desmarcar o antigo como padrão
            entregador_padrao_atual.entregador_padrao = False
            entregador_padrao_atual.updated_at = dt.utcnow()
            logger.info(f"🚚 Entregador padrão removido de: {entregador_padrao_atual.nome} (ID: {entregador_padrao_atual.id})")
    
    # Serializar enderecos_adicionais para JSON (SQLite armazena como TEXT)
    if 'enderecos_adicionais' in update_data and update_data['enderecos_adicionais'] is not None:
        import json
        update_data['enderecos_adicionais'] = json.dumps(update_data['enderecos_adicionais'])
    
    # 🔒 DETECTAR TRANSIÇÃO DE PARCEIRO_ATIVO (TRUE → FALSE)
    parceiro_desativado = False
    comissoes_desativadas_count = 0
    
    if 'parceiro_ativo' in update_data:
        # Cliente era parceiro e está sendo desmarcado
        if hasattr(cliente, 'parceiro_ativo') and cliente.parceiro_ativo and not update_data['parceiro_ativo']:
            parceiro_desativado = True
            
            # Desativar todas as comissões ativas dessa pessoa
            from sqlalchemy import text
            
            # Contar comissões ativas antes de desativar
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
            
            # Desativar comissões (preservando histórico)
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
    
    # Se estiver reativando e não tiver código, gerar um
    if cliente.ativo and not cliente.codigo:
        cliente.codigo = gerar_codigo_cliente(db, cliente.tipo_cadastro, cliente.tipo_pessoa, tenant_id)
    
    cliente.updated_at = dt.utcnow()
    db.commit()
    db.refresh(cliente)
    
    # Log de auditoria
    log_update(db, current_user.id, "cliente", cliente.id, old_data, update_data)
    
    # 📢 PREPARAR RESPOSTA COM AVISO SOBRE COMISSÕES
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
    
    # Adicionar aviso se comissões foram desativadas
    if parceiro_desativado and comissoes_desativadas_count > 0:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"🔒 {comissoes_desativadas_count} comissão(ões) desativada(s) automaticamente "
            f"para {cliente.nome} (ID: {cliente_id}) porque deixou de ser parceiro."
        )
        
        response["aviso"] = (
            f"Comissões desativadas automaticamente porque o cliente deixou de ser parceiro. "
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
    
    # Desativar pets também
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
    Ativar ou desativar um cliente como parceiro para receber comissões.
    
    Permite que QUALQUER pessoa (cliente, veterinário, funcionário, fornecedor)
    seja ativada como parceiro, independente do tipo_cadastro.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Salvar estado anterior para auditoria e lógica
    old_status = cliente.parceiro_ativo
    old_parceiro_desde = cliente.parceiro_desde
    
    # ========================================================================
    # LÓGICA DE ATIVAÇÃO/DESATIVAÇÃO COM PRESERVAÇÃO DE HISTÓRICO
    # ========================================================================
    
    # Cenário 1: Ativando parceiro (false → true ou None → true)
    if request.parceiro_ativo and not old_status:
        cliente.parceiro_ativo = True
        
        # Se é primeira ativação (nunca foi parceiro antes)
        if not old_parceiro_desde:
            cliente.parceiro_desde = dt.utcnow()
            acao = "primeira_ativacao"
        # Se é reativação (já foi parceiro antes)
        else:
            # Manter data original de parceiro_desde
            # Adicionar registro de reativação nas observações
            data_reativacao = dt.utcnow().strftime('%d/%m/%Y')
            observacao_reativacao = f"\n[Reativado como parceiro em {data_reativacao}]"
            
            if cliente.parceiro_observacoes:
                cliente.parceiro_observacoes += observacao_reativacao
            else:
                cliente.parceiro_observacoes = f"Reativado como parceiro em {data_reativacao}"
            
            acao = "reativacao"
    
    # Cenário 2: Desativando parceiro (true → false)
    elif not request.parceiro_ativo and old_status:
        cliente.parceiro_ativo = False
        # NÃO limpar parceiro_desde - preservar histórico
        # Adicionar registro de desativação nas observações
        data_desativacao = dt.utcnow().strftime('%d/%m/%Y')
        observacao_desativacao = f"\n[Desativado como parceiro em {data_desativacao}]"
        
        if cliente.parceiro_observacoes:
            cliente.parceiro_observacoes += observacao_desativacao
        else:
            cliente.parceiro_observacoes = f"Desativado como parceiro em {data_desativacao}"
        
        acao = "desativacao"
    
    # Cenário 3: Status não mudou (idempotência)
    else:
        acao = "sem_alteracao"
    
    # Atualizar observações adicionais se fornecidas pelo usuário
    # (concatena com as automáticas)
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
    
    # Mensagens específicas por ação
    mensagens = {
        "primeira_ativacao": f"Parceiro ativado pela primeira vez em {cliente.parceiro_desde.strftime('%d/%m/%Y')}",
        "reativacao": f"Parceiro reativado com sucesso (parceiro desde {cliente.parceiro_desde.strftime('%d/%m/%Y')})",
        "desativacao": f"Parceiro desativado (histórico preservado desde {cliente.parceiro_desde.strftime('%d/%m/%Y') if cliente.parceiro_desde else 'N/A'})",
        "sem_alteracao": f"Status de parceiro já estava como {'ativo' if cliente.parceiro_ativo else 'inativo'}"
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
    
    # Gerar código único para o pet baseado no código do cliente
    codigo_pet = f"{cliente.codigo}-PET-{db.query(Pet).filter(Pet.cliente_id == cliente_id).count() + 1:04d}"
    
    # Criar pet
    novo_pet = Pet(
        cliente_id=cliente_id,
        user_id=current_user.id,
        tenant_id=tenant_id,
        codigo=codigo_pet,
        **pet_data.model_dump()
    )
    
    db.add(novo_pet)
    db.commit()
    db.refresh(novo_pet)
    
    # Log de auditoria
    log_create(db, current_user.id, "pet", novo_pet.id, {
        "cliente_id": cliente_id,
        **pet_data.model_dump()
    })
    
    return novo_pet


@router.get("/pets/todos", response_model=List[PetResponse])
def listar_todos_pets(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Listar todos os pets do usuário (de todos os clientes)"""
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
            detail="Pet não encontrado"
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
        "cor": pet.cor,
        "peso": pet.peso,
        "peso_kg": pet.peso,  # Alias para compatibilidade
        "idade_meses": idade_meses,  # Calculado
        "observacoes": pet.observacoes,
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
            detail="Pet não encontrado"
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
    update_data = pet_data.model_dump(exclude_unset=True)
    
    # Se idade_aproximada foi fornecida, converter para data_nascimento
    if 'idade_aproximada' in update_data and update_data['idade_aproximada'] is not None:
        idade_meses = update_data['idade_aproximada']
        hoje = dt.utcnow()
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
        "cor": pet.cor,
        "peso": pet.peso,
        "peso_kg": pet.peso,  # Alias
        "idade_meses": idade_meses,
        "observacoes": pet.observacoes,
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
            detail="Pet não encontrado"
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
    e adiciona observação sobre a remoção.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Validar campo
    if campo not in ["telefone", "celular", "cpf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo inválido. Use: telefone, celular ou cpf"
        )
    
    # Buscar cliente antigo
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Validar que está ativo
    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Guardar valor antigo para log
    valor_antigo = getattr(cliente, campo)
    
    # Remover o campo
    setattr(cliente, campo, None)
    
    # Adicionar observação
    observacao_atual = cliente.observacoes or ""
    nova_observacao = f"[SISTEMA] {campo.capitalize()} removido (valor anterior: {valor_antigo}) - Transferido para cadastro do cliente código {novo_cliente_codigo}"
    
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
# GERENCIAMENTO DE CRÉDITO
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
    """Adiciona crédito ao saldo do cliente"""
    from decimal import Decimal
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    if dados.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor deve ser maior que zero"
        )
    
    # Adicionar crédito
    credito_anterior = float(cliente.credito or 0)
    cliente.credito = Decimal(str(credito_anterior + dados.valor))
    cliente.updated_at = dt.utcnow()
    
    # Adicionar observação no histórico
    observacao_atual = cliente.observacoes or ""
    nova_observacao = f"[{dt.now().strftime('%d/%m/%Y %H:%M')}] Crédito adicionado: R$ {dados.valor:.2f} - {dados.motivo}"
    
    if observacao_atual:
        cliente.observacoes = f"{observacao_atual}\n{nova_observacao}"
    else:
        cliente.observacoes = nova_observacao
    
    db.commit()
    
    # Log de auditoria
    log_update(db, current_user.id, "cliente", cliente.id,
        {"credito": credito_anterior},
        {"credito": float(cliente.credito)}
    )
    
    return {
        "message": "Crédito adicionado com sucesso",
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
    """Remove crédito do saldo do cliente"""
    from decimal import Decimal
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
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
            detail=f"Valor a remover (R$ {dados.valor:.2f}) excede o crédito disponível (R$ {credito_atual:.2f})"
        )
    
    # Remover crédito
    cliente.credito = Decimal(str(credito_atual - dados.valor))
    cliente.updated_at = dt.utcnow()
    
    # Adicionar observação no histórico
    observacao_atual = cliente.observacoes or ""
    nova_observacao = f"[{dt.now().strftime('%d/%m/%Y %H:%M')}] Crédito removido: R$ {dados.valor:.2f} - {dados.motivo}"
    
    if observacao_atual:
        cliente.observacoes = f"{observacao_atual}\n{nova_observacao}"
    else:
        cliente.observacoes = nova_observacao
    
    db.commit()
    
    # Log de auditoria
    log_update(db, current_user.id, "cliente", cliente.id,
        {"credito": credito_atual},
        {"credito": float(cliente.credito)}
    )
    
    return {
        "message": "Crédito removido com sucesso",
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        "credito_anterior": credito_atual,
        "valor_removido": dados.valor,
        "credito_atual": float(cliente.credito),
        "motivo": dados.motivo
    }


# ============================================================================
# HISTÓRICO DE COMPRAS
# ============================================================================

@router.get("/{cliente_id}/historico-compras")
async def get_historico_compras(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Retorna o histórico de compras do cliente"""
    from .vendas_models import Venda
    from sqlalchemy import func, desc
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Buscar vendas do cliente
    vendas = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id
    ).order_by(desc(Venda.data_venda)).all()
    
    # Estatísticas
    total_compras = len(vendas)
    total_gasto = sum(float(v.total or 0) for v in vendas if v.status == 'finalizada')
    ticket_medio = total_gasto / total_compras if total_compras > 0 else 0
    
    # Última compra
    ultima_compra = vendas[0].data_venda if vendas else None
    
    return {
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        # Campos no nível raiz para compatibilidade com frontend
        "total_compras": total_compras,
        "valor_total_gasto": round(total_gasto, 2),
        "ticket_medio": round(ticket_medio, 2),
        "ultima_compra": ultima_compra.isoformat() if ultima_compra else None,
        # Mantendo estatisticas também para compatibilidade
        "estatisticas": {
            "total_compras": total_compras,
            "total_gasto": round(total_gasto, 2),
            "ticket_medio": round(ticket_medio, 2),
            "ultima_compra": ultima_compra.isoformat() if ultima_compra else None
        },
        "vendas": [
            {
                "id": v.id,
                "numero_venda": v.id,  # O número da venda é o próprio ID
                "data_venda": v.data_venda.isoformat() if hasattr(v.data_venda, 'isoformat') else str(v.data_venda),
                "total": float(v.total or 0),
                "subtotal": float(v.subtotal or 0) if hasattr(v, 'subtotal') else float(v.total or 0),
                "desconto_valor": float(v.desconto_valor or 0) if hasattr(v, 'desconto_valor') else 0,
                "taxa_entrega": float(v.taxa_entrega or 0) if hasattr(v, 'taxa_entrega') else 0,
                "saldo_devedor": float(v.total or 0) - (sum(float(pag.valor or 0) for pag in v.pagamentos) if hasattr(v, 'pagamentos') and v.pagamentos else 0),
                "status": v.status,
                "total_itens": len(v.itens) if v.itens else 0,
                "forma_pagamento": v.pagamentos[0].forma_pagamento.nome if (v.pagamentos and v.pagamentos[0].forma_pagamento and hasattr(v.pagamentos[0].forma_pagamento, 'nome')) else (v.pagamentos[0].forma_pagamento if (v.pagamentos and hasattr(v.pagamentos[0], 'forma_pagamento')) else None)
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
    logger.info(f"🔍 DEBUG vendas-em-aberto: cliente_id={cliente_id}, user_id={current_user.id}")
    logger.info(f"📊 Total vendas encontradas: {len(vendas_aberto)}")
    
    # Filtrar apenas vendas com saldo devedor maior que zero
    vendas_com_saldo = []
    for v in vendas_aberto:
        valor_pago = sum(float(pag.valor or 0) for pag in v.pagamentos) if hasattr(v, 'pagamentos') and v.pagamentos else 0
        saldo = float(v.total or 0) - valor_pago
        
        if saldo > 0.01:  # Apenas vendas com saldo maior que 1 centavo
            vendas_com_saldo.append(v)
            logger.info(f"  ✅ ID: {v.id} | Status: {v.status} | Total: R$ {v.total} | Pago: R$ {valor_pago} | Saldo: R$ {saldo}")
        else:
            logger.info(f"  ❌ ID: {v.id} | Status: {v.status} | Saldo zerado - EXCLUÍDA")
    
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
                "numero_venda": v.numero_venda,  # Número formatado da venda (ex: 202601190004)
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
    """Dá baixa em múltiplas vendas de uma vez, gerando movimentações no caixa e contas a receber"""
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
        
        # Validar se há caixa aberto
        caixa_aberto = db.query(Caixa).filter(
            Caixa.usuario_id == current_user.id,
            Caixa.tenant_id == tenant_id,
            Caixa.status == 'aberto'
        ).first()
        
        logger.info(f"Caixa aberto: {caixa_aberto}")
        
        if not caixa_aberto:
            raise HTTPException(
                status_code=400,
                detail='Não há caixa aberto. Abra o caixa antes de dar baixa nas vendas.'
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
            raise HTTPException(status_code=400, detail='Algumas vendas não foram encontradas ou não estão em aberto')
        
        # Calcular saldo devedor de cada venda
        vendas_com_saldo = []
        total_saldo_devedor = 0
        
        for venda in vendas:
            valor_ja_pago = sum(float(p.valor or 0) for p in venda.pagamentos) if venda.pagamentos else 0
            saldo_devedor = float(venda.total or 0) - valor_ja_pago
            
            logger.info(f"Venda {venda.id}: Total={venda.total}, Pago={valor_ja_pago}, Saldo={saldo_devedor}")
            
            if saldo_devedor > 0.01:  # Tolerância de 1 centavo
                vendas_com_saldo.append({
                    'venda': venda,
                    'saldo_devedor': saldo_devedor,
                    'valor_ja_pago': valor_ja_pago
                })
                total_saldo_devedor += saldo_devedor
        
        logger.info(f"Vendas com saldo: {len(vendas_com_saldo)}, Total saldo: {total_saldo_devedor}")
        
        if not vendas_com_saldo:
            raise HTTPException(status_code=400, detail='Todas as vendas já estão quitadas')
        
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
            # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
            pagamento = VendaPagamento(
                venda_id=venda.id,
                tenant_id=tenant_id,  # ✅ Garantir isolamento entre empresas
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
            
            # Registrar movimentação no caixa (apenas para formas que movimentam caixa)
            formas_que_movimentam_caixa = ['dinheiro', 'Dinheiro', 'pix', 'PIX', 'cartao_debito', 'Cartão de Débito']
            if forma_pagamento in formas_que_movimentam_caixa:
                # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
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
                    tenant_id=tenant_id  # ✅ Garantir isolamento entre empresas
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
                
                # 🆕 Criar registro de recebimento
                recebimento = Recebimento(
                    conta_receber_id=conta_receber.id,
                    valor_recebido=valor_aplicar,
                    data_recebimento=dt.now().date(),
                    observacoes=f'Baixa em lote - {forma_pagamento}',
                    user_id=current_user.id,
                    tenant_id=tenant_id  # ✅ Garantir isolamento multi-tenant
                )
                db.add(recebimento)
                
                # 🆕 CRIAR LANÇAMENTO REALIZADO NO FLUXO DE CAIXA
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
                
                logger.info(f"✅ Fluxo de caixa REALIZADO criado: R$ {valor_aplicar:.2f}")
                
                # 🆕 CRIAR LANÇAMENTO PREVISTO NO FLUXO DE CAIXA (se houver saldo restante)
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
                    
                    logger.info(f"✅ Fluxo de caixa PREVISTO criado: R$ {saldo_conta:.2f} para {data_previsao.strftime('%d/%m/%Y')}")
            
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
    ⚠️ **DEPRECATED** - Esta rota será removida em versão futura
    
    **Problemas desta rota:**
    - ❌ Carrega TODAS as transações em memória (sem paginação)
    - ❌ Performance ruim com histórico grande (>500 transações)
    - ❌ Alto consumo de memória
    - ❌ Ordena tudo em Python (deveria ser no banco)
    
    **Migre para as novas rotas:**
    
    1. **Para histórico completo paginado:**
       ```
       GET /financeiro/cliente/{cliente_id}?page=1&per_page=20
       ```
       - Paginação obrigatória
       - Filtros: data_inicio, data_fim, tipo, status
       - Performance otimizada
    
    2. **Para resumo leve (uso no cadastro):**
       ```
       GET /financeiro/cliente/{cliente_id}/resumo
       ```
       - Apenas dados agregados (COUNT, SUM)
       - Muito mais rápido (~10-50ms vs 500-2000ms)
       - Ideal para Step 6 do wizard
    
    **Data de remoção planejada:** Junho/2026
    
    ---
    
    Retorna o histórico completo de transações do cliente:
    - Vendas realizadas
    - Devoluções
    - Contas a receber (em aberto e pagas)
    - Recebimentos
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    
    # Importar modelos necessários
    from app.vendas_models import Venda
    from app.financeiro_models import ContaReceber, Recebimento
    
    historico = []
    
    # 1. Buscar vendas do cliente (excluir canceladas/devolvidas do histórico principal)
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
    
    # 2. Buscar devoluções (vendas canceladas/devolvidas)
    devolucoes = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.status.in_(['cancelada', 'devolvida'])
    ).order_by(Venda.data_venda.desc()).all()
    
    for devolucao in devolucoes:
        historico.append({
            "tipo": "devolucao",
            "data": devolucao.data_venda.isoformat() if devolucao.data_venda else None,
            "descricao": f"Devolução - Venda #{devolucao.numero_venda}",
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
    
    # Ordenar histórico por data (mais recente primeiro)
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
    pet_id: Optional[int] = Query(None, description="Filtrar eventos de um pet específico"),
    limit: int = Query(20, ge=1, le=100, description="Limite de eventos"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna a timeline consolidada do cliente com eventos de:
    - Vendas
    - Contas a receber
    - Pets (cadastro e atualizações)
    
    Ordenação: mais recente → mais antigo
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Validar se cliente existe e pertence ao usuário
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return _obter_timeline("cliente_timeline", cliente_id, tipo_evento, pet_id, limit)


def _obter_timeline(view_name: str, entity_id: int, tipo_evento: Optional[str], pet_id: Optional[int], limit: int):
    """Função auxiliar para buscar timeline de qualquer entidade"""
    # Query na VIEW otimizada
    id_column = "cliente_id" if "cliente" in view_name else "fornecedor_id"
    
    query = f"""
        SELECT 
            tipo_evento,
            evento_id,
            {id_column} as entity_id,
            pet_id,
            data_evento,
            titulo,
            descricao,
            status,
            cor_badge
        FROM {view_name}
        WHERE {id_column} = :entity_id
    """
    
    params = {"entity_id": entity_id}
    
    # Filtro por tipo de evento
    if tipo_evento:
        query += " AND tipo_evento = :tipo_evento"
        params["tipo_evento"] = tipo_evento
    
    # Filtro por pet (apenas para clientes)
    if pet_id and "cliente" in view_name:
        query += " AND (pet_id = :pet_id OR pet_id IS NULL)"
        params["pet_id"] = pet_id
    
    # Ordenação e limite
    query += " ORDER BY data_evento DESC LIMIT :limit"
    params["limit"] = limit
    
    # Executar query
    from app.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    eventos = []
    for row in cursor.fetchall():
        eventos.append(TimelineEvento(
            tipo_evento=row['tipo_evento'],
            evento_id=row['evento_id'],
            cliente_id=row['entity_id'],
            pet_id=row['pet_id'],
            data_evento=datetime.fromisoformat(row['data_evento']) if isinstance(row['data_evento'], str) else row['data_evento'],
            titulo=row['titulo'],
            descricao=row['descricao'],
            status=row['status'],
            cor_badge=row['cor_badge']
        ))
    
    cursor.close()
    conn.close()
    
    return eventos


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
    
    Ordenação: mais recente → mais antigo
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Validar se fornecedor existe e pertence ao usuário
    fornecedor = db.query(Cliente).filter(
        Cliente.id == fornecedor_id,
        Cliente.tenant_id == tenant_id,
        Cliente.tipo_cadastro == 'fornecedor'
    ).first()
    
    if not fornecedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fornecedor não encontrado"
        )
    
    return _obter_timeline("fornecedor_timeline", fornecedor_id, tipo_evento, None, limit)


# ============================================================
# 🚚 ENTREGADORES - Custo Operacional
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
    - Calcula custo_por_entrega = custo_rh_ajustado / media_entregas_real (se disponível)
    - Senão usa media_entregas_configurada como fallback
    
    Para modelo 'taxa_fixa':
    - Retorna taxa_fixa_entrega
    
    Para modelo 'por_km':
    - Retorna valor_por_km_entrega (frontend precisa multiplicar pela distância)
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
            detail="Entregador não encontrado"
        )
    
    custo_por_entrega = 0
    modelo = entregador.modelo_custo_entrega
    detalhes = {}
    
    if modelo == 'rateio_rh' and entregador.controla_rh:
        # Usar custo_rh_ajustado se disponível
        if entregador.custo_rh_ajustado:
            custo_rh = float(entregador.custo_rh_ajustado)
            # Usar média real se disponível, senão configurada
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
            detalhes = {"aviso": "Custo RH não configurado"}
    
    elif modelo == 'taxa_fixa':
        custo_por_entrega = float(entregador.taxa_fixa_entrega or 0)
        detalhes = {"taxa_fixa": custo_por_entrega}
    
    elif modelo == 'por_km':
        custo_por_entrega = float(entregador.valor_por_km_entrega or 0)
        detalhes = {
            "valor_por_km": custo_por_entrega,
            "observacao": "Requer cálculo de distância no frontend"
        }
    
    else:
        # Sem modelo configurado
        detalhes = {"aviso": "Modelo de custo não configurado"}
    
    return {
        "entregador_id": entregador_id,
        "nome": entregador.nome_fantasia or entregador.nome,
        "modelo_custo": modelo,
        "custo_por_entrega": round(custo_por_entrega, 2),
        "detalhes": detalhes
    }
