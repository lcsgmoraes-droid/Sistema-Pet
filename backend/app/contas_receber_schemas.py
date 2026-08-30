"""Schemas das rotas de contas a receber."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ContaReceberCreate(BaseModel):
    descricao: str
    cliente_id: Optional[int] = None
    categoria_id: Optional[int] = None  # UX/Agrupamento

    # ============================
    # DRE - CAMPOS OBRIGATORIOS
    # ============================
    dre_subcategoria_id: Optional[int] = (
        None  # OPCIONAL - será classificado automaticamente se não fornecido
    )
    canal: str = (
        "loja_fisica"  # OBRIGATORIO - loja_fisica, mercado_livre, shopee, amazon
    )

    valor_original: float
    data_emissao: date
    data_vencimento: date
    documento: Optional[str] = None
    observacoes: Optional[str] = None
    venda_id: Optional[int] = None

    # Parcelamento
    eh_parcelado: bool = False
    total_parcelas: int = 1

    # Recorrência
    eh_recorrente: bool = False
    tipo_recorrencia: Optional[str] = (
        None  # 'semanal', 'quinzenal', 'mensal', 'personalizado'
    )
    intervalo_dias: Optional[int] = None
    data_inicio_recorrencia: Optional[date] = None
    data_fim_recorrencia: Optional[date] = None
    numero_repeticoes: Optional[int] = None


class RecebimentoCreate(BaseModel):
    valor_recebido: float = Field(ge=0)
    data_recebimento: date
    forma_pagamento_id: Optional[int] = None
    valor_juros: float = Field(default=0, ge=0)
    valor_multa: float = Field(default=0, ge=0)
    valor_desconto: float = Field(default=0, ge=0)
    observacoes: Optional[str] = None
    aplicar_encargos_automaticos: bool = False
    quitar: bool = False


class RecebimentoLoteCreate(BaseModel):
    conta_ids: List[int] = Field(min_length=1, max_length=500)
    data_recebimento: date
    forma_pagamento_id: Optional[int] = None
    observacoes: Optional[str] = None
    aplicar_encargos_automaticos: bool = True

    @field_validator("conta_ids")
    @classmethod
    def validar_contas_unicas(cls, value: List[int]) -> List[int]:
        if any(conta_id <= 0 for conta_id in value):
            raise ValueError("Todos os IDs de contas devem ser positivos")
        if len(value) != len(set(value)):
            raise ValueError("A lista de contas não pode conter IDs repetidos")
        return value


class ContaReceberResponse(BaseModel):
    id: int
    descricao: str
    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = None
    categoria_nome: Optional[str] = None
    valor_original: float
    valor_recebido: float
    valor_final: float
    data_emissao: date
    data_vencimento: date
    data_recebimento: Optional[date] = None
    status: str
    dias_vencimento: Optional[int] = None
    eh_parcelado: bool
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    documento: Optional[str] = None
    venda_id: Optional[int] = None
    numero_venda: Optional[str] = None  # ✅ CAMPO ADICIONADO
    forma_pagamento_id: Optional[int] = None
    forma_pagamento_tipo: Optional[str] = None
    eh_crediario: bool = False
    encargos_automaticos_ativos: bool = False
    dias_atraso: int = 0
    valor_juros_calculado: float = 0
    valor_multa_calculada: float = 0
    saldo_atualizado: float = 0

    # ============================
    # CONCILIAÇÃO DE CARTÃO
    # ============================
    nsu: Optional[str] = None
    adquirente: Optional[str] = None
    conciliado: bool = False
    data_conciliacao: Optional[date] = None

    model_config = {"from_attributes": True}


# ============================================================================
# FUNÇÃO HELPER: CALCULAR PRÓXIMA DATA DE RECORRÊNCIA
# ============================================================================
