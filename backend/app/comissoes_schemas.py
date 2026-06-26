"""Schemas e helpers de payload para rotas de comissoes."""

from typing import List, Optional

from pydantic import BaseModel


# ==========================================
# SCHEMAS
# ==========================================


class ConfiguracaoComissaoCreate(BaseModel):
    """Schema para criar/atualizar uma configuração de comissão"""

    funcionario_id: int
    tipo: str  # 'categoria', 'subcategoria', 'produto', 'geral'
    referencia_id: int
    tipo_calculo: str  # 'percentual' ou 'lucro'
    percentual: float
    percentual_loja: Optional[float] = None
    desconta_taxa_cartao: bool = True
    desconta_impostos: bool = True
    desconta_custo_entrega: bool = False
    comissao_venda_parcial: bool = True
    permite_edicao_venda: bool = False
    observacoes: Optional[str] = None


class ConfiguracoesBatchCreate(BaseModel):
    """Schema para criar múltiplas configurações de uma vez"""

    configuracoes: List[ConfiguracaoComissaoCreate]


class ConfiguracaoComissaoResponse(BaseModel):
    """Schema de resposta para configuração"""

    id: int
    funcionario_id: int
    tipo: str
    referencia_id: int
    nome_item: Optional[str]
    tipo_calculo: str
    percentual: float
    percentual_loja: Optional[float]
    desconta_taxa_cartao: bool
    desconta_impostos: bool
    desconta_custo_entrega: bool
    permite_edicao_venda: bool
    ativo: bool
    observacoes: Optional[str]
    data_criacao: str


class ConfiguracaoSistemaUpdate(BaseModel):
    """Schema para atualizar configurações do sistema"""

    gerar_comissao_venda_parcial: Optional[bool] = None
    percentual_imposto_padrao: Optional[float] = None
    dias_vencimento_padrao: Optional[int] = None
    email_assunto_template: Optional[str] = None
    email_corpo_template: Optional[str] = None
    pdf_formato_padrao: Optional[str] = None


class DuplicarConfiguracaoRequest(BaseModel):
    """Schema para duplicar configuração"""

    funcionario_origem_id: int
    funcionario_destino_id: int


def _normalizar_configuracao_comissao(
    config: ConfiguracaoComissaoCreate,
) -> ConfiguracaoComissaoCreate:
    if config.tipo == "geral":
        config.referencia_id = 0
    return config
