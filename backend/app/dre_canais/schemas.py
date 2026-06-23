from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class LinhaCanal(BaseModel):
    """Uma linha da DRE de um canal específico"""

    descricao: str  # Ex: "Faturamento Mercado Livre"
    valor: float
    percentual: float
    cor: str  # Cor do canal
    cor_bg: str  # Cor de fundo
    canal: str  # ID do canal
    canal_nome: str  # Nome do canal
    nivel: int  # 0=seção, 1=linha normal, 2=total
    tipo: str  # 'receita', 'deducao', 'custo', 'despesa', 'lucro'
    origem: Optional[str] = None
    campo: Optional[str] = None
    detalhavel: bool = False


class DREPorCanalResponse(BaseModel):
    """DRE completa com linhas separadas por canal"""

    periodo: str
    mes: int
    ano: int
    linhas: List[LinhaCanal]
    totais: Dict
    canais_encontrados: List[str]


class DREDetalheItem(BaseModel):
    id: str
    origem_tipo: str
    origem_label: str
    data: Optional[str] = None
    descricao: str
    contraparte: Optional[str] = None
    documento: Optional[str] = None
    status: Optional[str] = None
    valor: float
    valor_auxiliar: Optional[float] = None
    link: Optional[str] = None
    meta: Dict[str, Any] = {}


class DREDetalheResponse(BaseModel):
    campo: str
    canal: str
    canal_nome: str
    periodo: str
    origem: Optional[str] = None
    total: float
    total_itens: int
    page: int
    page_size: int
    pages: int
    items: List[DREDetalheItem]
