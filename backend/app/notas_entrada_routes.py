# ruff: noqa: F401
"""
ROTAS DE ENTRADA POR XML - Sistema Pet Shop Pro
Upload e processamento de NF-e de fornecedores

Funcionalidades:
- Upload de XML de NF-e
- Parser automÃ¡tico de XML
- Matching automÃ¡tico de produtos
- Entrada automÃ¡tica no estoque
- GestÃ£o de produtos nÃ£o vinculados
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .models import Cliente
from .produtos_models import (
    NotaEntrada,
    NotaEntradaItem,
)
from .financeiro_models import ContaPagar
from .notas_entrada_pdf_parser import (
    PDFEntradaFornecedor,
    build_pdf_synthetic_nfe_xml,
    extract_pdf_text,
    parse_pedido_pdf_text,
)
from .notas_entrada.conferencia import (
    CONFERENCIA_STATUS_COM_DIVERGENCIA,
    CONFERENCIA_STATUS_NAO_INICIADA,
    CONFERENCIA_STATUS_SEM_DIVERGENCIA,
    _mapear_lotes_rastro_xml,
    _montar_lotes_entrada_item,
    _montar_payload_nota,
    _normalizar_custo_unitario_override,
    _normalizar_texto_curto,
    _obter_acao_conferencia,
    _obter_override_mapa,
    _resumir_conferencia_nota,
    _round_quantity,
    _serializar_conferencia_item,
)
from .notas_entrada.fiscal import (
    calcular_composicao_custos_nota,
    calcular_quantidade_custo_efetivos,
)
from .notas_entrada.financeiro import (
    criar_contas_pagar_da_nota,
)
from .notas_entrada.fornecedores import (
    criar_fornecedor_automatico,
)
from .notas_entrada.processamento_acoes import (
    detectar_contexto_processamento,
    resolver_custo_operacional_entrada,
    sugerir_acoes_processamento,
)
from .notas_entrada.itens_produto_routes import router as itens_produto_router
from .notas_entrada.produtos import (
    _aplicar_codigos_barras_item_no_produto,
    _aplicar_dados_fiscais_item_no_produto,
    _montar_divergencia_codigo_barras_item,
    _montar_sugestao_sku_produto,  # noqa: F401 - reexport legado usado por testes/integrações
    encontrar_produto_similar,
    gerar_sku_automatico,
    obter_detalhe_vinculo_item,
)
from .notas_entrada.schemas import (
    AtualizarPrecoRequest,
    ConferenciaNotaPayload,
    NotaEntradaResponse,
    ProcessarConfig,
)
from .notas_entrada.rateio_routes import router as rateio_router
from .notas_entrada.conferencia_routes import (
    router as conferencia_router,
    desfazer_conferencia_nota,
    gerar_rascunho_nf_devolucao,
    salvar_conferencia_nota,
)
from .notas_entrada.reversao_routes import (
    router as reversao_router,
    reverter_entrada_estoque,
)
from .notas_entrada.xml_parser import parse_nfe_xml
from .notas_entrada.processamento_routes import (
    router as processamento_router,
    _acoes_processamento_dict,
    _aplicar_precos_venda_processamento,
    _atualizar_custo_produto_entrada,
    _carregar_acoes_processamento_nota,
    _reverter_historicos_precos_nota,
    atualizar_precos_produtos,
    preview_processamento,
    processar_entrada_estoque,
)

from .notas_entrada.upload_routes import router as upload_router
from .notas_entrada.upload_routes import upload_lote_xml, upload_pdf, upload_xml
from .notas_entrada.consulta_routes import router as consulta_router
from .notas_entrada.consulta_routes import buscar_nota, excluir_nota, listar_notas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notas-entrada", tags=["Notas de Entrada (XML)"])
router.include_router(itens_produto_router)
router.include_router(rateio_router)
router.include_router(conferencia_router)
router.include_router(processamento_router)
router.include_router(reversao_router)
router.include_router(upload_router)
router.include_router(consulta_router)

__all__ = [
    "_acoes_processamento_dict",
    "_aplicar_dados_fiscais_item_no_produto",
    "_aplicar_precos_venda_processamento",
    "_atualizar_custo_produto_entrada",
    "_carregar_acoes_processamento_nota",
    "_mapear_lotes_rastro_xml",
    "_montar_lotes_entrada_item",
    "_montar_sugestao_sku_produto",
    "_normalizar_custo_unitario_override",
    "_normalizar_texto_curto",
    "_obter_acao_conferencia",
    "_obter_override_mapa",
    "_reverter_historicos_precos_nota",
    "_round_quantity",
    "AtualizarPrecoRequest",
    "atualizar_precos_produtos",
    "calcular_composicao_custos_nota",
    "CONFERENCIA_STATUS_COM_DIVERGENCIA",
    "CONFERENCIA_STATUS_NAO_INICIADA",
    "CONFERENCIA_STATUS_SEM_DIVERGENCIA",
    "ConferenciaNotaPayload",
    "desfazer_conferencia_nota",
    "gerar_rascunho_nf_devolucao",
    "criar_contas_pagar_da_nota",
    "detectar_contexto_processamento",
    "parse_nfe_xml",
    "preview_processamento",
    "ProcessarConfig",
    "processar_entrada_estoque",
    "resolver_custo_operacional_entrada",
    "salvar_conferencia_nota",
    "reverter_entrada_estoque",
    "router",
    "sugerir_acoes_processamento",
]
