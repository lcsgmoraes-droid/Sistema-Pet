"""
SPRINT 6 - PASSO 6: Modelos Pydantic para Conferência Avançada e Pagamento Parcial

Incluem:
- Filtros por grupo/produto/período
- Pagamento parcial com saldo
- Resposta com totais filtrados
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal


# ======================== MODELS DE REQUEST ========================

class FiltrosConferencia(BaseModel):
    """Filtros para a tela de conferência"""
    
    grupo_produto: Optional[int] = Field(None, description="ID do grupo/categoria de produto")
    produto_id: Optional[int] = Field(None, description="ID do produto específico")
    data_inicio: Optional[date] = Field(None, description="Data inicial do período (YYYY-MM-DD)")
    data_fim: Optional[date] = Field(None, description="Data final do período (YYYY-MM-DD)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "grupo_produto": 1,
                "produto_id": None,
                "data_inicio": "2026-01-15",
                "data_fim": "2026-01-22"
            }
        }


class FecharComissaoComPagamento(BaseModel):
    """Modelo para fechar comissão com pagamento parcial"""
    
    comissoes_ids: List[int] = Field(..., description="IDs das comissões a fechar")
    valor_pago: Decimal = Field(..., description="Valor a ser pago (pode ser parcial)")
    forma_pagamento: str = Field(
        "nao_informado",
        description="Forma de pagamento: dinheiro, transferencia, cheque, cartao_credito, pix"
    )
    data_pagamento: date = Field(..., description="Data do pagamento (YYYY-MM-DD)")
    observacoes: Optional[str] = Field(None, description="Observações adicionais do pagamento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "comissoes_ids": [1, 2, 3],
                "valor_pago": "100.50",
                "forma_pagamento": "transferencia",
                "data_pagamento": "2026-01-22",
                "observacoes": "Pagamento parcial - saldo em 30 dias"
            }
        }


# ======================== MODELS DE RESPONSE ========================

class ComissaoItem(BaseModel):
    """Item individual de comissão"""
    
    id: int
    venda_id: int
    data_venda: str
    produto_id: int
    nome_produto: str
    cliente_nome: Optional[str]
    quantidade: float
    valor_venda: float
    valor_base_calculo: float
    percentual_comissao: float
    valor_comissao: float
    tipo_calculo: str
    status: str
    forma_pagamento: Optional[str]
    valor_pago: Optional[float]
    saldo_restante: Optional[float]


class PeriodoSelecionado(BaseModel):
    """Período selecionado nos filtros"""
    
    data_inicio: Optional[date]
    data_fim: Optional[date]
    grupo_produto: Optional[int]
    produto_id: Optional[int]
    grupo_produto_nome: Optional[str]
    produto_nome: Optional[str]


class ResumoComFiltros(BaseModel):
    """Resumo financeiro com filtros aplicados"""
    
    quantidade_comissoes: int = Field(..., description="Quantidade de comissões no resultado")
    valor_total: float = Field(..., description="Soma dos valores das comissões")
    valor_pago_total: Optional[float] = Field(
        0.0,
        description="Soma dos valores já pagos"
    )
    saldo_restante_total: Optional[float] = Field(
        None,
        description="Saldo restante (valor_total - valor_pago_total)"
    )
    percentual_pago: Optional[float] = Field(
        0.0,
        description="Percentual do total que foi pago"
    )


class ConferenciaComFiltrosResponse(BaseModel):
    """Resposta da endpoint de conferência com filtros avançados"""
    
    success: bool
    funcionario: Dict[str, Any]
    periodo_selecionado: PeriodoSelecionado
    resumo: ResumoComFiltros
    comissoes: List[ComissaoItem]
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "funcionario": {
                    "id": 14,
                    "nome": "Dra Juliana Duarte"
                },
                "periodo_selecionado": {
                    "data_inicio": "2026-01-15",
                    "data_fim": "2026-01-22",
                    "grupo_produto": None,
                    "produto_id": None,
                    "grupo_produto_nome": None,
                    "produto_nome": None
                },
                "resumo": {
                    "quantidade_comissoes": 4,
                    "valor_total": 100.50,
                    "valor_pago_total": 50.25,
                    "saldo_restante_total": 50.25,
                    "percentual_pago": 50.0
                },
                "comissoes": [
                    {
                        "id": 1,
                        "venda_id": 100,
                        "data_venda": "2026-01-20",
                        "produto_id": 50,
                        "nome_produto": "Ração Premium",
                        "cliente_nome": "Cliente X",
                        "quantidade": 2.0,
                        "valor_venda": 100.0,
                        "valor_base_calculo": 100.0,
                        "percentual_comissao": 5.0,
                        "valor_comissao": 5.0,
                        "tipo_calculo": "percentual",
                        "status": "pendente",
                        "forma_pagamento": None,
                        "valor_pago": None,
                        "saldo_restante": None
                    }
                ]
            }
        }


class FecharComPagamentoResponse(BaseModel):
    """Resposta ao fechar comissões com pagamento"""
    
    success: bool
    total_processadas: int
    total_ignoradas: int
    valor_total_fechado: float
    valor_total_pago: float
    saldo_total_restante: float
    comissoes_com_saldo: int = Field(
        0,
        description="Quantidade de comissões que ficaram com saldo restante"
    )
    forma_pagamento: str
    data_pagamento: str
    observacoes: Optional[str]
    mensagem: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_processadas": 4,
                "total_ignoradas": 0,
                "valor_total_fechado": 100.50,
                "valor_total_pago": 50.25,
                "saldo_total_restante": 50.25,
                "comissoes_com_saldo": 4,
                "forma_pagamento": "transferencia",
                "data_pagamento": "2026-01-22",
                "observacoes": "Pagamento parcial",
                "mensagem": "4 comissões fechadas com pagamento parcial. Saldo: R$ 50.25"
            }
        }


class FormaPagamento(BaseModel):
    """Opção de forma de pagamento"""
    
    id: int
    nome: str
    descricao: str
    ativo: bool


class ListaFormasPagamento(BaseModel):
    """Lista de formas de pagamento disponíveis"""
    
    success: bool
    formas: List[FormaPagamento]
