from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConfigSyncRequest(BaseModel):
    """Configurar sincronização de um produto"""

    produto_id: int
    bling_produto_id: Optional[str] = None
    sincronizar: bool = True
    estoque_compartilhado: bool = True


class SyncStatusResponse(BaseModel):
    produto_id: int
    produto_nome: str
    sku: str
    estoque_sistema: float
    estoque_bling: Optional[float]
    divergencia: Optional[float]
    sincronizado: bool
    bling_produto_id: Optional[str]
    ultima_sincronizacao: Optional[datetime]
    status: str
    ultima_tentativa_sync: Optional[datetime] = None
    proxima_tentativa_sync: Optional[datetime] = None
    ultima_conferencia_bling: Optional[datetime] = None
    ultima_sincronizacao_sucesso: Optional[datetime] = None
    ultimo_estoque_bling: Optional[float] = None
    tentativas_sync: int = 0
    ultimo_erro: Optional[str] = None
    queue_id: Optional[int] = None
    queue_status: Optional[str] = None


class VincularProdutoRequest(BaseModel):
    produto_id: int
    bling_id: str


class CriarProdutoBlingFaltanteRequest(BaseModel):
    bling_id: str


class ReconciliarBatchRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=1000)
    minutes: int = Field(default=30, ge=5, le=1440)
