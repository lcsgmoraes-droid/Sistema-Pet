# -*- coding: utf-8 -*-
"""Schemas Pydantic para clientes, fornecedores, parceiros e pets."""

import json
from datetime import date, datetime as dt
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from app.services.cliente_alertas_pdv import normalizar_alertas_pdv

__all__ = [
    "AjustarCreditoRequest",
    "ClienteCreate",
    "ClienteResponse",
    "ClienteUpdate",
    "ClientesListResponse",
    "PessoaFusaoExecutarRequest",
    "PessoaFusaoPreviewRequest",
    "PetCreate",
    "PetResponse",
    "PetUpdate",
    "ToggleParceiroRequest",
]


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
    enderecos_adicionais: Optional[list] = (
        None  # Array de endereÃ§os com tipo, apelido, etc.
    )

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
    alertas_pdv: List[dict] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @validator("alertas_pdv", pre=True, always=True)
    def normalize_alertas_pdv(cls, v):
        return normalizar_alertas_pdv(v)

    @validator(
        "email",
        "cpf",
        "telefone",
        "celular",
        "cep",
        "endereco",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
        "observacoes",
        "cnpj",
        "inscricao_estadual",
        "razao_social",
        "nome_fantasia",
        "responsavel",
        "crmv",
        "endereco_entrega",
        "endereco_entrega_2",
        "parceiro_desde",
        "parceiro_observacoes",
        "tipo_vinculo_entrega",
        pre=True,
    )
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

    @validator("tipo_pessoa")
    def validate_tipo_pessoa(cls, v):
        if v not in ["PF", "PJ"]:
            raise ValueError("tipo_pessoa deve ser PF ou PJ")
        return v

    @validator("tipo_cadastro")
    def validate_tipo_cadastro(cls, v):
        if v not in ["cliente", "fornecedor", "veterinario", "funcionario"]:
            raise ValueError(
                "tipo_cadastro deve ser cliente, fornecedor, veterinario ou funcionario"
            )
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
    enderecos_adicionais: Optional[list] = (
        None  # Array de endereÃ§os com tipo, apelido, etc.
    )

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
    controla_dre: Optional[bool] = (
        None  # True = vai para DRE, False = nÃ£o classifica (produtos p/ revenda)
    )

    observacoes: Optional[str] = None
    alertas_pdv: Optional[List[dict]] = None
    ativo: Optional[bool] = None

    model_config = {"from_attributes": True}

    @validator("alertas_pdv", pre=True)
    def normalize_alertas_pdv(cls, v):
        return normalizar_alertas_pdv(v)

    @validator(
        "email",
        "cpf",
        "telefone",
        "celular",
        "cep",
        "endereco",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
        "observacoes",
        "cnpj",
        "inscricao_estadual",
        "razao_social",
        "nome_fantasia",
        "responsavel",
        "crmv",
        "parceiro_desde",
        "parceiro_observacoes",
        "tipo_vinculo_entrega",
        pre=True,
    )
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v


class ClienteResponse(BaseModel):
    id: int
    codigo: Optional[str] = None
    tipo_cadastro: str
    tipo_pessoa: str
    fornecedor_grupo_id: Optional[int] = None
    fornecedor_grupo_nome: Optional[str] = None
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
    controla_dre: bool = (
        True  # True = vai para DRE, False = nÃ£o classifica (produtos p/ revenda)
    )

    observacoes: Optional[str] = None
    alertas_pdv: List[dict] = Field(default_factory=list)
    ativo: bool = True
    credito: Optional[Decimal] = Decimal("0.00")
    created_at: dt
    updated_at: dt
    criado_por_id: Optional[int] = None
    criado_por_nome: Optional[str] = None
    criado_por_email: Optional[str] = None
    pets: List[PetResponse] = []

    @validator("parceiro_ativo", pre=True)
    def ensure_parceiro_ativo(cls, v):
        """Garantir que parceiro_ativo seja sempre bool"""
        if v is None:
            return False
        return bool(v)

    @validator("enderecos_adicionais", pre=True)
    def deserialize_enderecos(cls, v):
        """Desserializar JSON string para lista"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v

    @validator("alertas_pdv", pre=True, always=True)
    def normalize_alertas_pdv(cls, v):
        return normalizar_alertas_pdv(v)

    @validator("pets", pre=True)
    def filter_active_pets(cls, v):
        """Filtrar apenas pets ativos"""
        if isinstance(v, list):
            result = []
            for pet in v:
                try:
                    # Pet pode ser objeto ou dict
                    ativo = (
                        pet.ativo if hasattr(pet, "ativo") else pet.get("ativo", True)
                    )
                    if ativo:
                        result.append(pet)
                except Exception:
                    # Em caso de erro, incluir o pet
                    result.append(pet)
            return result
        return v if v else []

    # Campo de parceria (True = pertence ao tenant parceiro, False = próprio)
    de_parceiro: bool = False

    model_config = {"from_attributes": True}


class ClientesListResponse(BaseModel):
    items: List[ClienteResponse]
    total: int
    skip: int
    limit: int


class PessoaFusaoPreviewRequest(BaseModel):
    pessoa_principal_id: int
    pessoa_duplicada_id: int


class PessoaFusaoExecutarRequest(PessoaFusaoPreviewRequest):
    decisoes_campos: Dict[str, str] = Field(default_factory=dict)
    observacao: Optional[str] = None


class ToggleParceiroRequest(BaseModel):
    """Request para ativar/desativar parceiro"""

    parceiro_ativo: bool
    parceiro_observacoes: Optional[str] = None


class AjustarCreditoRequest(BaseModel):
    valor: float
    motivo: str
