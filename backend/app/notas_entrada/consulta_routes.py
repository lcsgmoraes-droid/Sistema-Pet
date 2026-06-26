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

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.models import Cliente
from app.produtos_models import (
    NotaEntrada,
    NotaEntradaItem,
)
from app.financeiro_models import ContaPagar
from app.notas_entrada_pdf_parser import (
    PDFEntradaFornecedor,
    build_pdf_synthetic_nfe_xml,
    extract_pdf_text,
    parse_pedido_pdf_text,
)
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
from app.notas_entrada.fiscal import (
    calcular_composicao_custos_nota,
    calcular_quantidade_custo_efetivos,
)
from app.notas_entrada.financeiro import (
    criar_contas_pagar_da_nota,
)
from app.notas_entrada.fornecedores import (
    criar_fornecedor_automatico,
)
from app.notas_entrada.processamento_acoes import (
    detectar_contexto_processamento,
    resolver_custo_operacional_entrada,
    sugerir_acoes_processamento,
)
from app.notas_entrada.itens_produto_routes import router as itens_produto_router
from app.notas_entrada.produtos import (
    _aplicar_codigos_barras_item_no_produto,
    _aplicar_dados_fiscais_item_no_produto,
    _montar_divergencia_codigo_barras_item,
    _montar_sugestao_sku_produto,  # noqa: F401 - reexport legado usado por testes/integrações
    encontrar_produto_similar,
    gerar_sku_automatico,
    obter_detalhe_vinculo_item,
)
from app.notas_entrada.schemas import (
    AtualizarPrecoRequest,
    ConferenciaNotaPayload,
    NotaEntradaResponse,
    ProcessarConfig,
)
from app.notas_entrada.rateio_routes import router as rateio_router
from app.notas_entrada.conferencia_routes import (
    router as conferencia_router,
    desfazer_conferencia_nota,
    gerar_rascunho_nf_devolucao,
    salvar_conferencia_nota,
)
from app.notas_entrada.reversao_routes import (
    router as reversao_router,
    reverter_entrada_estoque,
)
from app.notas_entrada.xml_parser import parse_nfe_xml
from app.notas_entrada.processamento_routes import (
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

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[NotaEntradaResponse])
def listar_notas(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    fornecedor_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista notas de entrada"""
    user, tenant_id = user_and_tenant

    query = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(NotaEntrada.tenant_id == tenant_id)
    )

    if status:
        query = query.filter(NotaEntrada.status == status)
    if fornecedor_id:
        query = query.filter(NotaEntrada.fornecedor_id == fornecedor_id)

    query = query.order_by(desc(NotaEntrada.data_entrada))

    total = query.count()
    notas = query.offset(offset).limit(limit).all()

    logger.info(f"ðŸ“‹ {len(notas)} notas encontradas (total: {total})")

    respostas = []
    for nota in notas:
        conferencia = _resumir_conferencia_nota(nota)
        respostas.append(
            NotaEntradaResponse.model_validate(
                {
                    "id": nota.id,
                    "numero_nota": nota.numero_nota,
                    "serie": nota.serie,
                    "chave_acesso": nota.chave_acesso,
                    "fornecedor_nome": nota.fornecedor_nome,
                    "fornecedor_cnpj": nota.fornecedor_cnpj,
                    "fornecedor_id": nota.fornecedor_id,
                    "data_emissao": nota.data_emissao,
                    "valor_total": nota.valor_total,
                    "status": nota.status,
                    "produtos_vinculados": nota.produtos_vinculados,
                    "produtos_nao_vinculados": nota.produtos_nao_vinculados,
                    "entrada_estoque_realizada": nota.entrada_estoque_realizada,
                    "conferencia_status": conferencia["status"],
                    "divergencias_count": conferencia["itens_com_divergencia"],
                }
            )
        )

    return respostas


# ============================================================================
# BUSCAR NOTA POR ID
# ============================================================================


@router.get("/{nota_id}")
def buscar_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Busca nota completa com itens"""
    user, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    # Verificar se fornecedor foi criado recentemente (Ãºltimas 24h)
    fornecedor_criado_automaticamente = False
    if nota.fornecedor_id:
        fornecedor = db.query(Cliente).filter(Cliente.id == nota.fornecedor_id).first()
        if fornecedor and fornecedor.created_at:
            # Se o fornecedor foi criado menos de 24h antes da nota
            # Garantir compatibilidade de timezone
            data_entrada = (
                nota.data_entrada.replace(tzinfo=None)
                if nota.data_entrada.tzinfo
                else nota.data_entrada
            )
            created_at = (
                fornecedor.created_at.replace(tzinfo=None)
                if fornecedor.created_at.tzinfo
                else fornecedor.created_at
            )
            diferenca = data_entrada - created_at
            if diferenca < timedelta(hours=24):
                fornecedor_criado_automaticamente = True

    composicoes_custo = calcular_composicao_custos_nota(nota)
    itens_formatados = []
    for item in nota.itens:
        composicao_custo = composicoes_custo.get(item.id, {})
        detalhe_vinculo = obter_detalhe_vinculo_item(item)
        dados_pack = calcular_quantidade_custo_efetivos(
            item.descricao, item.quantidade, item.valor_unitario, item.valor_total
        )
        conferencia_item = _serializar_conferencia_item(item)
        itens_formatados.append(
            {
                "id": item.id,
                "numero_item": item.numero_item,
                "codigo_produto": item.codigo_produto,
                "descricao": item.descricao,
                "ncm": item.ncm,
                "cfop": item.cfop,
                "unidade": item.unidade,
                "quantidade": item.quantidade,
                "valor_unitario": item.valor_unitario,
                "valor_total": item.valor_total,
                "ean": item.ean,
                "ean_tributario": getattr(item, "ean_tributario", None),
                "lote": item.lote,
                "data_validade": item.data_validade.isoformat()
                if item.data_validade
                else None,
                "produto_id": item.produto_id,
                "produto_nome": item.produto.nome if item.produto else None,
                "produto_codigo": item.produto.codigo if item.produto else None,
                "produto_ean": (
                    item.produto.codigo_barras
                    or item.produto.gtin_ean
                    or item.produto.gtin_ean_tributario
                )
                if item.produto
                else None,
                "produto_codigo_barras": item.produto.codigo_barras
                if item.produto
                else None,
                "produto_gtin_ean": item.produto.gtin_ean if item.produto else None,
                "produto_ean_tributario": item.produto.gtin_ean_tributario
                if item.produto
                else None,
                "divergencia_codigo_barras": _montar_divergencia_codigo_barras_item(
                    item
                ),
                "vinculado": item.vinculado,
                "confianca_vinculo": item.confianca_vinculo,
                "origem_vinculo_automatico": detalhe_vinculo["origem"],
                "referencia_vinculo": detalhe_vinculo["referencia"],
                "status": item.status,
                "pack_detectado_automatico": dados_pack["pack_detectado"],
                "pack_multiplicador_detectado": dados_pack["multiplicador_pack"],
                "quantidade_efetiva": dados_pack["quantidade_efetiva"],
                "custo_unitario_efetivo": dados_pack["custo_unitario_efetivo"],
                "custo_aquisicao_unitario": composicao_custo.get(
                    "custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]
                ),
                "custo_aquisicao_total": composicao_custo.get(
                    "custo_aquisicao_total", item.valor_total
                ),
                "composicao_custo": composicao_custo,
                **conferencia_item,
            }
        )

    return _montar_payload_nota(
        nota,
        itens_formatados,
        fornecedor_criado_automaticamente=fornecedor_criado_automaticamente,
    )


# ============================================================================
# EXCLUIR NOTA
# ============================================================================


@router.delete("/{nota_id}")
def excluir_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exclui uma nota de entrada e seus itens (cascade)"""
    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    # Verificar se jÃ¡ teve entrada no estoque
    if nota.entrada_estoque_realizada:
        raise HTTPException(
            status_code=400,
            detail="NÃ£o Ã© possÃ­vel excluir nota que jÃ¡ teve entrada no estoque",
        )

    numero_nota = nota.numero_nota
    total_itens = len(nota.itens)

    # Excluir contas a pagar vinculadas (se existirem)
    contas_pagar = (
        db.query(ContaPagar).filter(ContaPagar.nota_entrada_id == nota.id).all()
    )

    contas_excluidas = 0
    pagamentos_excluidos = 0
    for conta in contas_pagar:
        # Excluir pagamentos da conta antes de excluir a conta
        from app.financeiro_models import Pagamento

        pagamentos = (
            db.query(Pagamento).filter(Pagamento.conta_pagar_id == conta.id).all()
        )
        for pagamento in pagamentos:
            db.delete(pagamento)
            pagamentos_excluidos += 1

        db.delete(conta)
        contas_excluidas += 1

    if contas_excluidas > 0:
        logger.info(
            f"ðŸ—‘ï¸ {contas_excluidas} contas a pagar e {pagamentos_excluidos} pagamentos excluÃ­dos junto com a nota"
        )

    # Excluir nota (cascade deleta os itens automaticamente)
    db.delete(nota)
    db.commit()

    logger.info(f"ðŸ—‘ï¸ Nota excluÃ­da: {numero_nota} ({total_itens} itens)")

    return {
        "message": "Nota excluída com sucesso",
        "numero_nota": numero_nota,
        "itens_excluidos": total_itens,
        "contas_pagar_excluidas": contas_excluidas,
    }


# ============================================================================
# IMPORTAÇÃO AUTOMÁTICA DE DOCS DA SEFAZ (chamado pelo loop do main.py)
