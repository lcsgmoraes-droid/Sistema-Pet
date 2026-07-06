"""Schemas das rotas de contas a pagar."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, field_validator


class ContaPagarCreate(BaseModel):
    descricao: str
    fornecedor_id: Optional[int] = None
    categoria_id: Optional[int] = None  # UX/Agrupamento

    # ============================
    # DRE - CAMPOS OBRIGATORIOS (com padrões)
    # ============================
    dre_subcategoria_id: Optional[int] = (
        None  # Obrigatorio via categoria vinculada a DRE ou envio direto
    )
    canal: str = (
        "loja_fisica"  # OBRIGATORIO - loja_fisica, mercado_livre, shopee, amazon
    )
    tipo_despesa_id: Optional[int] = None  # FK para TipoDespesa (fixo/variável)

    valor_original: float
    data_emissao: date
    data_vencimento: date
    documento: Optional[str] = None
    observacoes: Optional[str] = None
    nota_entrada_id: Optional[int] = None

    # Parcelamento
    eh_parcelado: bool = False
    total_parcelas: int = 1

    # Recorrência
    eh_recorrente: bool = False
    tipo_recorrencia: Optional[str] = (
        None  # 'semanal', 'quinzenal', 'mensal', 'personalizado'
    )
    intervalo_dias: Optional[int] = None  # Para tipo 'personalizado'
    data_inicio_recorrencia: Optional[date] = None
    data_fim_recorrencia: Optional[date] = None  # OU
    numero_repeticoes: Optional[int] = None  # alternativa ao data_fim

    @field_validator("data_inicio_recorrencia", "data_fim_recorrencia", mode="before")
    @classmethod
    def normalizar_datas_recorrencia_vazias(cls, valor):
        if isinstance(valor, str) and not valor.strip():
            return None
        return valor


class ContaPagarUpdate(BaseModel):
    descricao: Optional[str] = None
    fornecedor_id: Optional[int] = None
    categoria_id: Optional[int] = None
    dre_subcategoria_id: Optional[int] = None
    tipo_despesa_id: Optional[int] = None
    canal: Optional[str] = None
    valor_original: Optional[float] = None
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    documento: Optional[str] = None
    observacoes: Optional[str] = None
    eh_recorrente: Optional[bool] = None
    tipo_recorrencia: Optional[str] = None
    intervalo_dias: Optional[int] = None
    data_inicio_recorrencia: Optional[date] = None
    data_fim_recorrencia: Optional[date] = None
    numero_repeticoes: Optional[int] = None
    aplicar_recorrencia_futura: Optional[bool] = False

    @field_validator("data_inicio_recorrencia", "data_fim_recorrencia", mode="before")
    @classmethod
    def normalizar_datas_recorrencia_vazias(cls, valor):
        if isinstance(valor, str) and not valor.strip():
            return None
        return valor


class ContaPagarRecorrenciaBulkDelete(BaseModel):
    ids: List[int]


class ContaPagarRecorrenciaItemResponse(BaseModel):
    id: int
    descricao: str
    data_vencimento: date
    valor_final: float
    valor_pago: float
    status: str
    eh_origem: bool = False
    pode_excluir: bool = True
    motivo_bloqueio: Optional[str] = None


class ContaPagarClassificacaoUpdate(BaseModel):
    categoria_id: Optional[int] = None
    dre_subcategoria_id: Optional[int] = None
    tipo_despesa_id: Optional[int] = None
    canal: Optional[str] = None


class PagamentoCreate(BaseModel):
    valor_pago: float
    data_pagamento: date
    forma_pagamento_id: Optional[int] = None
    conta_bancaria_id: Optional[int] = None
    valor_juros: float = 0
    valor_multa: float = 0
    valor_desconto: float = 0
    observacoes: Optional[str] = None


class PagamentoLoteCreate(BaseModel):
    conta_ids: List[int]
    data_pagamento: date
    forma_pagamento_id: Optional[int] = None
    conta_bancaria_id: Optional[int] = None
    observacoes: Optional[str] = None

    @field_validator("conta_ids")
    @classmethod
    def validar_conta_ids(cls, valor):
        ids_unicos = list(dict.fromkeys(int(item) for item in valor if item))
        if not ids_unicos:
            raise ValueError("Selecione pelo menos uma conta para pagar.")
        return ids_unicos


class ContaPagarOperacaoRequest(BaseModel):
    motivo: Optional[str] = None


class ContaPagarResponse(BaseModel):
    id: int
    descricao: str
    fornecedor_nome: Optional[str] = None
    categoria_id: Optional[int] = None
    categoria_nome: Optional[str] = None
    valor_original: float
    valor_pago: float
    valor_final: float
    data_emissao: date
    data_vencimento: date
    data_pagamento: Optional[date] = None
    status: str
    dias_vencimento: Optional[int] = None
    eh_parcelado: bool
    eh_recorrente: bool = False
    tipo_recorrencia: Optional[str] = None
    intervalo_dias: Optional[int] = None
    data_inicio_recorrencia: Optional[date] = None
    data_fim_recorrencia: Optional[date] = None
    numero_repeticoes: Optional[int] = None
    proxima_recorrencia: Optional[date] = None
    conta_recorrencia_origem_id: Optional[int] = None
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    documento: Optional[str] = None
    nfe_numero: Optional[str] = None
    observacoes: Optional[str] = None
    nota_entrada_id: Optional[int] = None
    canal: Optional[str] = None
    dre_subcategoria_id: Optional[int] = None
    dre_subcategoria_nome: Optional[str] = None
    tipo_despesa_id: Optional[int] = None
    tipo_despesa_nome: Optional[str] = None
    e_custo_fixo: Optional[bool] = None
    origem_lancamento: Optional[str] = None
    origem_lancamento_label: Optional[str] = None
    caixa_referencia: Optional[str] = None

    model_config = {"from_attributes": True}
