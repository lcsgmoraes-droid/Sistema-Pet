"""Schemas das rotas de contas a receber."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class ContaReceberCreate(BaseModel):
    descricao: str
    cliente_id: Optional[int] = None
    categoria_id: Optional[int] = None  # UX/Agrupamento

    # ============================
    # DRE - CAMPOS OBRIGATORIOS
    # ============================
    dre_subcategoria_id: Optional[int] = (
        None  # OPCIONAL - serÃ¡ classificado automaticamente se nÃ£o fornecido
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

    # RecorrÃªncia
    eh_recorrente: bool = False
    tipo_recorrencia: Optional[str] = (
        None  # 'semanal', 'quinzenal', 'mensal', 'personalizado'
    )
    intervalo_dias: Optional[int] = None
    data_inicio_recorrencia: Optional[date] = None
    data_fim_recorrencia: Optional[date] = None
    numero_repeticoes: Optional[int] = None


class RecebimentoCreate(BaseModel):
    valor_recebido: float
    data_recebimento: date
    forma_pagamento_id: Optional[int] = None
    valor_juros: float = 0
    valor_multa: float = 0
    valor_desconto: float = 0
    observacoes: Optional[str] = None


class ContaReceberResponse(BaseModel):
    id: int
    descricao: str
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
    numero_venda: Optional[str] = None  # âœ… CAMPO ADICIONADO

    # ============================
    # CONCILIAÃ‡ÃƒO DE CARTÃƒO
    # ============================
    nsu: Optional[str] = None
    adquirente: Optional[str] = None
    conciliado: bool = False
    data_conciliacao: Optional[date] = None

    model_config = {"from_attributes": True}


# ============================================================================
# FUNÃ‡ÃƒO HELPER: CALCULAR PRÃ“XIMA DATA DE RECORRÃŠNCIA
# ============================================================================
