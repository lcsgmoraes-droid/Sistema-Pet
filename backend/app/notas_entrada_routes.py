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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notas-entrada", tags=["Notas de Entrada (XML)"])
router.include_router(itens_produto_router)
router.include_router(rateio_router)
router.include_router(conferencia_router)
router.include_router(processamento_router)
router.include_router(reversao_router)

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


# ============================================================================
# UPLOAD DE XML
# ============================================================================


@router.post("/upload")
async def upload_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Upload de XML de NF-e e parse automÃ¡tico"""
    current_user, tenant_id = user_and_tenant

    logger.info("Upload de XML recebido")

    try:
        # Validar extensÃ£o
        if not file.filename.endswith(".xml"):
            logger.error("Arquivo XML invalido recebido")
            raise HTTPException(status_code=400, detail="Arquivo deve ser .xml")

        # Ler conteÃºdo
        logger.info("ðŸ“– Lendo conteÃºdo do arquivo...")
        xml_content = await file.read()
        logger.info(f"   - Tamanho: {len(xml_content)} bytes")

        xml_str = xml_content.decode("utf-8")
        logger.info("âœ… Arquivo decodificado com sucesso")

        # Parse do XML
        logger.info("ðŸ” Fazendo parse do XML...")
        try:
            dados_nfe = parse_nfe_xml(xml_str)
            logger.info("âœ… Parse concluÃ­do:")
            logger.info(f"   - Chave: {dados_nfe.get('chave_acesso', 'N/A')}")
            logger.info(f"   - NÃºmero: {dados_nfe.get('numero_nota', 'N/A')}")
            logger.info(f"   - Fornecedor: {dados_nfe.get('fornecedor_nome', 'N/A')}")
            logger.info(f"   - Valor total: R$ {dados_nfe.get('valor_total', 0):.2f}")
            logger.info(f"   - Itens: {len(dados_nfe.get('itens', []))}")
        except ValueError as e:
            logger.error(f"âŒ Erro no parse do XML: {str(e)}")
            logger.error(f"   - Tipo: {type(e).__name__}")
            raise HTTPException(
                status_code=400, detail=f"Erro ao processar XML: {str(e)}"
            )
        except Exception as e:
            logger.error(f"âŒ Erro inesperado no parse: {str(e)}")
            logger.error(f"   - Tipo: {type(e).__name__}")
            raise HTTPException(
                status_code=500, detail=f"Erro interno ao processar XML: {str(e)}"
            )

        # Verificar se nota jÃ¡ existe
        logger.info(
            f"ðŸ”Ž Verificando se nota jÃ¡ existe (chave: {dados_nfe['chave_acesso']})..."
        )
        nota_existente = (
            db.query(NotaEntrada)
            .filter(NotaEntrada.chave_acesso == dados_nfe["chave_acesso"])
            .first()
        )

        if nota_existente:
            logger.warning(f"âš ï¸ Nota jÃ¡ cadastrada! ID: {nota_existente.id}")
            raise HTTPException(
                status_code=400,
                detail=f"Nota fiscal jÃ¡ cadastrada (ID: {nota_existente.id})",
            )

        logger.info("âœ… Nota nÃ£o existe, prosseguindo...")

        # Buscar ou criar fornecedor automaticamente
        logger.info(
            f"ðŸ”Ž Buscando fornecedor por CNPJ: {dados_nfe['fornecedor_cnpj']}..."
        )
        fornecedor = (
            db.query(Cliente)
            .filter(
                Cliente.cnpj == dados_nfe["fornecedor_cnpj"],
                Cliente.tenant_id == tenant_id,
                Cliente.ativo,
            )
            .first()
        )

        fornecedor_criado_automaticamente = False

        if fornecedor:
            logger.info(
                f"âœ… Fornecedor encontrado: {fornecedor.nome} (ID: {fornecedor.id})"
            )
        else:
            logger.warning(
                "âš ï¸ Fornecedor nÃ£o cadastrado, criando automaticamente..."
            )
            try:
                fornecedor, fornecedor_criado_automaticamente = (
                    criar_fornecedor_automatico(dados_nfe, db, current_user, tenant_id)
                )
                logger.info(
                    f"âœ… Fornecedor criado: {fornecedor.nome} (ID: {fornecedor.id})"
                )
            except Exception as e:
                logger.error(f"âŒ Erro ao criar fornecedor: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Erro ao criar fornecedor: {str(e)}"
                )

        # Criar nota
        logger.info("ðŸ’¾ Criando registro da nota no banco...")
        nota = NotaEntrada(
            numero_nota=dados_nfe["numero_nota"],
            serie=dados_nfe["serie"],
            chave_acesso=dados_nfe["chave_acesso"],
            fornecedor_cnpj=dados_nfe["fornecedor_cnpj"],
            fornecedor_nome=dados_nfe["fornecedor_nome"],
            fornecedor_id=fornecedor.id if fornecedor else None,
            data_emissao=dados_nfe["data_emissao"],
            data_entrada=datetime.utcnow(),
            valor_produtos=dados_nfe["valor_produtos"],
            valor_frete=dados_nfe["valor_frete"],
            valor_desconto=dados_nfe["valor_desconto"],
            valor_total=dados_nfe["valor_total"],
            xml_content=xml_str,
            status="pendente",
            user_id=current_user.id,
            tenant_id=tenant_id,
        )

        db.add(nota)
        db.flush()
        logger.info(f"âœ… Nota criada com ID: {nota.id}")

        # Processar itens e fazer matching automÃ¡tico
        logger.info(f"ðŸ”„ Processando {len(dados_nfe['itens'])} itens...")
        vinculados = 0
        nao_vinculados = 0
        produtos_reativados = 0

        for item_data in dados_nfe["itens"]:
            # Tentar encontrar produto similar (com fornecedor para matching mais preciso)
            produto, confianca, foi_inativo, origem_vinculo, referencia_vinculo = (
                encontrar_produto_similar(
                    item_data["descricao"],
                    item_data["codigo_produto"],
                    db,
                    tenant_id=tenant_id,
                    fornecedor_id=fornecedor.id if fornecedor else None,
                    ean=item_data.get("ean"),
                    ean_tributario=item_data.get("ean_tributario"),
                )
            )

            if produto:
                vinculados += 1
                if foi_inativo:
                    produtos_reativados += 1
                produto_id = produto.id
                vinculado = True
                item_status = "vinculado"

                # âœ… Apenas gerar SKU se necessÃ¡rio (nÃ£o atualizar outros dados no upload)
                if not produto.codigo or produto.codigo.strip() == "":
                    novo_sku = gerar_sku_automatico("PROD", db, current_user.id)
                    produto.codigo = novo_sku
                    logger.info(f"  ðŸ”– SKU gerado automaticamente: {novo_sku}")

                # Log de status do produto
                status_msg = (
                    " (INATIVO - serÃ¡ reativado no processamento)"
                    if foi_inativo
                    else ""
                )
                detalhe_match = ""
                if origem_vinculo and referencia_vinculo:
                    detalhe_match = (
                        f" [match por {origem_vinculo}: {referencia_vinculo}]"
                    )
                logger.info(
                    f"  âœ… {item_data['descricao'][:50]} â†’ "
                    f"{produto.nome} (confianÃ§a: {confianca:.0%}){detalhe_match}{status_msg}"
                )
            else:
                nao_vinculados += 1
                produto_id = None
                vinculado = False
                item_status = "nao_vinculado"
                confianca = 0
                logger.warning(
                    f"  âš ï¸  {item_data['descricao'][:50]} â†’ NÃ£o vinculado"
                )

            # Criar item
            item = NotaEntradaItem(
                nota_entrada_id=nota.id,
                numero_item=item_data["numero_item"],
                codigo_produto=item_data["codigo_produto"],
                descricao=item_data["descricao"],
                ncm=item_data["ncm"],
                cest=item_data.get("cest"),
                cfop=item_data["cfop"],
                origem=item_data.get("origem", "0"),
                aliquota_icms=item_data.get("aliquota_icms", 0),
                aliquota_pis=item_data.get("aliquota_pis", 0),
                aliquota_cofins=item_data.get("aliquota_cofins", 0),
                unidade=item_data["unidade"],
                quantidade=item_data["quantidade"],
                valor_unitario=item_data["valor_unitario"],
                valor_total=item_data["valor_total"],
                ean=item_data.get("ean"),
                ean_tributario=item_data.get("ean_tributario"),
                lote=item_data.get("lote"),
                data_validade=item_data.get("data_validade"),
                produto_id=produto_id,
                vinculado=vinculado,
                confianca_vinculo=confianca,
                status=item_status,
                tenant_id=tenant_id,
            )
            db.add(item)
            if produto:
                _aplicar_codigos_barras_item_no_produto(produto, item)

        # Atualizar contadores
        nota.produtos_vinculados = vinculados
        nota.produtos_nao_vinculados = nao_vinculados

        db.commit()
        db.refresh(nota)

        # Log de resumo com informaÃ§Ã£o de reativaÃ§Ãµes
        if produtos_reativados > 0:
            logger.info(
                f"â™»ï¸  {produtos_reativados} produto(s) inativo(s) foram reativados automaticamente"
            )

        logger.info(
            f"âœ… Nota {nota.numero_nota} processada: "
            f"{vinculados} vinculados, {nao_vinculados} nÃ£o vinculados"
        )

        return {
            "message": "XML processado com sucesso",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "chave_acesso": nota.chave_acesso,
            "fornecedor": nota.fornecedor_nome,
            "fornecedor_id": nota.fornecedor_id,
            "fornecedor_criado_automaticamente": fornecedor_criado_automaticamente,
            "valor_total": nota.valor_total,
            "itens_total": len(dados_nfe["itens"]),
            "produtos_vinculados": vinculados,
            "produtos_nao_vinculados": nao_vinculados,
            "produtos_reativados": produtos_reativados,
        }

    except HTTPException:
        # Re-raise HTTP exceptions (jÃ¡ tratadas)
        raise
    except Exception as e:
        logger.error(f"âŒ Erro inesperado no upload: {str(e)}")
        logger.error(f"   - Tipo: {type(e).__name__}")
        logger.error(f"   - Stack: {e.__traceback__}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar XML: {str(e)}")


# ============================================================================
# UPLOAD DE PDF DE PEDIDO/ROMANEIO
# ============================================================================


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    fornecedor_id: int = Form(...),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Upload de pedido/romaneio PDF e entrada pelo fluxo existente."""
    current_user, tenant_id = user_and_tenant
    filename = file.filename or ""

    logger.info("Upload de PDF de entrada recebido")
    logger.info("Fornecedor selecionado para upload de PDF")
    logger.info("   - Usuario autenticado")

    try:
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")

        fornecedor = (
            db.query(Cliente)
            .filter(
                Cliente.id == fornecedor_id,
                Cliente.tenant_id == tenant_id,
                Cliente.tipo_cadastro == "fornecedor",
                Cliente.ativo,
            )
            .first()
        )

        if not fornecedor:
            raise HTTPException(
                status_code=404, detail="Fornecedor ativo nao encontrado"
            )

        pdf_content = await file.read()
        if not pdf_content:
            raise HTTPException(status_code=400, detail="PDF vazio")

        try:
            pdf_text = extract_pdf_text(pdf_content)
            pedido_pdf = parse_pedido_pdf_text(pdf_text)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        fornecedor_pdf = PDFEntradaFornecedor(
            id=fornecedor.id,
            nome=fornecedor.razao_social or fornecedor.nome_fantasia or fornecedor.nome,
            cnpj=fornecedor.cnpj or fornecedor.cpf or "",
        )
        xml_str = build_pdf_synthetic_nfe_xml(
            pedido_pdf,
            fornecedor_pdf,
            tenant_id=tenant_id,
        )
        dados_nfe = parse_nfe_xml(xml_str)

        nota_existente = (
            db.query(NotaEntrada)
            .filter(NotaEntrada.chave_acesso == dados_nfe["chave_acesso"])
            .first()
        )

        if nota_existente:
            raise HTTPException(
                status_code=400,
                detail=f"PDF ja importado como entrada (ID: {nota_existente.id})",
            )

        nota = NotaEntrada(
            numero_nota=dados_nfe["numero_nota"],
            serie=dados_nfe["serie"],
            chave_acesso=dados_nfe["chave_acesso"],
            fornecedor_cnpj=dados_nfe["fornecedor_cnpj"],
            fornecedor_nome=dados_nfe["fornecedor_nome"],
            fornecedor_id=fornecedor.id,
            data_emissao=dados_nfe["data_emissao"],
            data_entrada=datetime.utcnow(),
            valor_produtos=dados_nfe["valor_produtos"],
            valor_frete=dados_nfe["valor_frete"],
            valor_desconto=dados_nfe["valor_desconto"],
            valor_total=dados_nfe["valor_total"],
            xml_content=xml_str,
            status="pendente",
            user_id=current_user.id,
            tenant_id=tenant_id,
        )

        db.add(nota)
        db.flush()

        vinculados = 0
        nao_vinculados = 0
        produtos_reativados = 0

        for item_data in dados_nfe["itens"]:
            produto, confianca, foi_inativo, origem_vinculo, referencia_vinculo = (
                encontrar_produto_similar(
                    item_data["descricao"],
                    item_data["codigo_produto"],
                    db,
                    tenant_id=tenant_id,
                    fornecedor_id=fornecedor.id,
                    ean=item_data.get("ean"),
                    ean_tributario=item_data.get("ean_tributario"),
                )
            )

            if produto:
                vinculados += 1
                if foi_inativo:
                    produtos_reativados += 1
                produto_id = produto.id
                vinculado = True
                item_status = "vinculado"

                if not produto.codigo or produto.codigo.strip() == "":
                    novo_sku = gerar_sku_automatico("PROD", db, current_user.id)
                    produto.codigo = novo_sku

                detalhe_match = ""
                if origem_vinculo and referencia_vinculo:
                    detalhe_match = (
                        f" [match por {origem_vinculo}: {referencia_vinculo}]"
                    )
                logger.info(
                    f"PDF item vinculado: {item_data['descricao'][:50]} -> "
                    f"{produto.nome} (confianca: {confianca:.0%}){detalhe_match}"
                )
            else:
                nao_vinculados += 1
                produto_id = None
                vinculado = False
                item_status = "nao_vinculado"
                confianca = 0

            item = NotaEntradaItem(
                nota_entrada_id=nota.id,
                numero_item=item_data["numero_item"],
                codigo_produto=item_data.get("codigo_produto"),
                descricao=item_data["descricao"],
                ncm=item_data.get("ncm"),
                cest=item_data.get("cest"),
                cfop=item_data.get("cfop"),
                origem=item_data.get("origem"),
                aliquota_icms=item_data.get("aliquota_icms"),
                aliquota_pis=item_data.get("aliquota_pis"),
                aliquota_cofins=item_data.get("aliquota_cofins"),
                unidade=item_data.get("unidade") or "UN",
                quantidade=item_data["quantidade"],
                valor_unitario=item_data["valor_unitario"],
                valor_total=item_data["valor_total"],
                ean=item_data.get("ean"),
                ean_tributario=item_data.get("ean_tributario"),
                lote=item_data.get("lote"),
                data_validade=item_data.get("data_validade"),
                produto_id=produto_id,
                vinculado=vinculado,
                confianca_vinculo=confianca,
                status=item_status,
                tenant_id=tenant_id,
            )
            db.add(item)
            if produto:
                _aplicar_codigos_barras_item_no_produto(produto, item)

        nota.produtos_vinculados = vinculados
        nota.produtos_nao_vinculados = nao_vinculados

        db.commit()
        db.refresh(nota)

        avisos = [
            "PDF importado como pedido/romaneio; nao e NF-e validada pela SEFAZ.",
            "O PDF nao traz chave fiscal real, CFOP, NCM, impostos ou lotes. Revise os produtos antes de processar.",
            "Produtos ja cadastrados preservam os dados fiscais existentes quando o PDF nao trouxer essas informacoes.",
        ]

        return {
            "message": "PDF processado com sucesso",
            "origem_documento": "pdf",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "chave_acesso": nota.chave_acesso,
            "fornecedor": nota.fornecedor_nome,
            "fornecedor_id": nota.fornecedor_id,
            "fornecedor_criado_automaticamente": False,
            "valor_total": nota.valor_total,
            "itens_total": len(dados_nfe["itens"]),
            "produtos_vinculados": vinculados,
            "produtos_nao_vinculados": nao_vinculados,
            "produtos_reativados": produtos_reativados,
            "avisos": avisos,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Erro inesperado no upload PDF: {str(e)}")
        logger.error(f"   - Tipo: {type(e).__name__}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")


# ============================================================================
# UPLOAD EM LOTE DE MÃšLTIPLOS XMLs
# ============================================================================


@router.post("/upload-lote")
async def upload_lote_xml(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Upload de mÃºltiplos XMLs de NF-e e processamento em lote
    Retorna resumo de sucessos e erros
    """
    current_user, tenant_id = user_and_tenant

    logger.info("Upload em lote de notas recebido (%s arquivos)", len(files))

    resultados = []
    sucessos = 0
    erros = 0

    for i, file in enumerate(files, 1):
        logger.info("\n%s", "=" * 60)
        logger.info("Processando arquivo do lote de notas (%s/%s)", i, len(files))
        logger.info("%s", "=" * 60)

        resultado = {
            "arquivo": file.filename,
            "ordem": i,
            "sucesso": False,
            "mensagem": "",
            "nota_id": None,
            "numero_nota": None,
            "fornecedor": None,
            "valor_total": None,
            "produtos_vinculados": None,
            "produtos_nao_vinculados": None,
        }

        try:
            # Validar extensÃ£o
            if not file.filename.endswith(".xml"):
                raise ValueError("Arquivo deve ser .xml")

            # Ler e decodificar
            xml_content = await file.read()
            xml_str = xml_content.decode("utf-8")

            # Parse do XML
            dados_nfe = parse_nfe_xml(xml_str)

            # Verificar se nota jÃ¡ existe
            nota_existente = (
                db.query(NotaEntrada)
                .filter(NotaEntrada.chave_acesso == dados_nfe["chave_acesso"])
                .first()
            )

            if nota_existente:
                raise ValueError(f"Nota jÃ¡ cadastrada (ID: {nota_existente.id})")

            # Buscar ou criar fornecedor
            fornecedor = (
                db.query(Cliente)
                .filter(
                    Cliente.cnpj == dados_nfe["fornecedor_cnpj"],
                    Cliente.tenant_id == tenant_id,
                )
                .first()
            )

            fornecedor_criado = False
            if not fornecedor:
                fornecedor, fornecedor_criado = criar_fornecedor_automatico(
                    dados_nfe, db, current_user, tenant_id
                )

            # Criar nota
            nota = NotaEntrada(
                numero_nota=dados_nfe["numero_nota"],
                serie=dados_nfe["serie"],
                chave_acesso=dados_nfe["chave_acesso"],
                fornecedor_cnpj=dados_nfe["fornecedor_cnpj"],
                fornecedor_nome=dados_nfe["fornecedor_nome"],
                fornecedor_id=fornecedor.id if fornecedor else None,
                data_emissao=dados_nfe["data_emissao"],
                data_entrada=datetime.utcnow(),
                valor_produtos=dados_nfe["valor_produtos"],
                valor_frete=dados_nfe["valor_frete"],
                valor_desconto=dados_nfe["valor_desconto"],
                valor_total=dados_nfe["valor_total"],
                xml_content=xml_str,
                status="pendente",
                user_id=current_user.id,
                tenant_id=tenant_id,
            )

            db.add(nota)
            db.flush()

            # Processar itens com matching
            vinculados = 0
            nao_vinculados = 0
            produtos_reativados = 0

            for item_data in dados_nfe["itens"]:
                produto, confianca, foi_reativado, _, _ = encontrar_produto_similar(
                    item_data["descricao"],
                    item_data["codigo_produto"],
                    db,
                    tenant_id=tenant_id,
                    fornecedor_id=fornecedor.id if fornecedor else None,
                    ean=item_data.get("ean"),
                    ean_tributario=item_data.get("ean_tributario"),
                )

                if produto:
                    vinculados += 1
                    if foi_reativado:
                        produtos_reativados += 1
                    produto_id = produto.id
                    vinculado = True
                    item_status = "vinculado"
                else:
                    nao_vinculados += 1
                    produto_id = None
                    vinculado = False
                    item_status = "nao_vinculado"
                    confianca = 0

                item = NotaEntradaItem(
                    nota_entrada_id=nota.id,
                    numero_item=item_data["numero_item"],
                    codigo_produto=item_data["codigo_produto"],
                    descricao=item_data["descricao"],
                    ncm=item_data["ncm"],
                    cfop=item_data["cfop"],
                    unidade=item_data["unidade"],
                    quantidade=item_data["quantidade"],
                    valor_unitario=item_data["valor_unitario"],
                    valor_total=item_data["valor_total"],
                    ean=item_data.get("ean"),
                    ean_tributario=item_data.get("ean_tributario"),
                    lote=item_data.get("lote"),
                    data_validade=item_data.get("data_validade"),
                    produto_id=produto_id,
                    vinculado=vinculado,
                    confianca_vinculo=confianca,
                    status=item_status,
                    tenant_id=tenant_id,
                )
                db.add(item)
                if produto:
                    _aplicar_codigos_barras_item_no_produto(produto, item)

            # Atualizar contadores
            nota.produtos_vinculados = vinculados
            nota.produtos_nao_vinculados = nao_vinculados

            db.commit()
            db.refresh(nota)

            # Log de reativaÃ§Ãµes
            if produtos_reativados > 0:
                logger.info(
                    "Produtos inativos reativados durante importacao de nota: %s",
                    produtos_reativados,
                )

            # Sucesso!
            resultado["sucesso"] = True
            resultado["mensagem"] = "Processado com sucesso"
            resultado["nota_id"] = nota.id
            resultado["numero_nota"] = nota.numero_nota
            resultado["fornecedor"] = nota.fornecedor_nome
            resultado["valor_total"] = nota.valor_total
            resultado["produtos_vinculados"] = vinculados
            resultado["produtos_nao_vinculados"] = nao_vinculados

            sucessos += 1
            logger.info("Arquivo do lote de notas processado com sucesso")

        except ValueError as e:
            resultado["mensagem"] = f"Erro de validaÃ§Ã£o: {str(e)}"
            erros += 1
            logger.error("Arquivo do lote de notas rejeitado por validacao")
            db.rollback()

        except Exception as e:
            resultado["mensagem"] = f"Erro ao processar: {str(e)}"
            erros += 1
            logger.error(
                "Erro inesperado ao processar arquivo do lote de notas", exc_info=True
            )
            db.rollback()

        resultados.append(resultado)

    logger.info(f"\n{'=' * 60}")
    logger.info("ðŸ“Š RESUMO DO LOTE:")
    logger.info(f"   - Total de arquivos: {len(files)}")
    logger.info(f"   - âœ… Sucessos: {sucessos}")
    logger.info(f"   - âŒ Erros: {erros}")
    logger.info(f"{'=' * 60}\n")

    return {
        "message": f"Processamento em lote concluÃ­do: {sucessos} sucessos, {erros} erros",
        "total_arquivos": len(files),
        "sucessos": sucessos,
        "erros": erros,
        "resultados": resultados,
    }


# ============================================================================
# LISTAR NOTAS
# ============================================================================


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
