# ruff: noqa: F401
"""Fachada das rotas de upload de notas de entrada."""

from datetime import datetime, timedelta
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro_models import ContaPagar
from app.models import Cliente
from app.notas_entrada.conferencia import (
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
from app.notas_entrada.conferencia_routes import (
    desfazer_conferencia_nota,
    gerar_rascunho_nf_devolucao,
    router as conferencia_router,
    salvar_conferencia_nota,
)
from app.notas_entrada.financeiro import criar_contas_pagar_da_nota
from app.notas_entrada.fiscal import (
    calcular_composicao_custos_nota,
    calcular_quantidade_custo_efetivos,
)
from app.notas_entrada.fornecedores import criar_fornecedor_automatico
from app.notas_entrada.itens_produto_routes import router as itens_produto_router
from app.notas_entrada.processamento_acoes import (
    detectar_contexto_processamento,
    resolver_custo_operacional_entrada,
    sugerir_acoes_processamento,
)
from app.notas_entrada.processamento_routes import (
    _acoes_processamento_dict,
    _aplicar_precos_venda_processamento,
    _atualizar_custo_produto_entrada,
    _carregar_acoes_processamento_nota,
    _reverter_historicos_precos_nota,
    atualizar_precos_produtos,
    preview_processamento,
    processar_entrada_estoque,
    router as processamento_router,
)
from app.notas_entrada.produtos import (
    _aplicar_codigos_barras_item_no_produto,
    _aplicar_dados_fiscais_item_no_produto,
    _montar_divergencia_codigo_barras_item,
    _montar_sugestao_sku_produto,
    encontrar_produto_similar,
    gerar_sku_automatico,
    obter_detalhe_vinculo_item,
)
from app.notas_entrada.rateio_routes import router as rateio_router
from app.notas_entrada.reversao_routes import (
    reverter_entrada_estoque,
    router as reversao_router,
)
from app.notas_entrada.schemas import (
    AtualizarPrecoRequest,
    ConferenciaNotaPayload,
    NotaEntradaResponse,
    ProcessarConfig,
)
from app.notas_entrada.xml_parser import parse_nfe_xml
from app.notas_entrada_pdf_parser import (
    PDFEntradaFornecedor,
    build_pdf_synthetic_nfe_xml,
    extract_pdf_text,
    parse_pedido_pdf_text,
)
from app.produtos_models import NotaEntrada, NotaEntradaItem

from app.notas_entrada.upload_routes_parts import (
    lote_xml_router,
    pdf_router,
    upload_lote_xml,
    upload_pdf,
    upload_xml,
    xml_router,
)

logger = logging.getLogger(__name__)
router = APIRouter()
router.include_router(xml_router)
router.include_router(pdf_router)
router.include_router(lote_xml_router)

__all__ = [
    "_montar_sugestao_sku_produto",
    "parse_nfe_xml",
    "router",
    "upload_lote_xml",
    "upload_pdf",
    "upload_xml",
]
