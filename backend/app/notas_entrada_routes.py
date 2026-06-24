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
import json
import logging

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .models import Cliente
from .produtos_models import (
    Produto,
    ProdutoLote,
    EstoqueMovimentacao,
    NotaEntrada,
    NotaEntradaItem,
    ProdutoHistoricoPreco,
    ProdutoFornecedor,
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
from .notas_entrada.xml_parser import parse_nfe_xml

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notas-entrada", tags=["Notas de Entrada (XML)"])
router.include_router(itens_produto_router)
router.include_router(rateio_router)


def _acoes_processamento_dict(config: ProcessarConfig) -> dict:
    return {
        "lancar_estoque": bool(config.lancar_estoque),
        "atualizar_custo": bool(config.atualizar_custo),
        "atualizar_preco_venda": bool(config.atualizar_preco_venda),
        "gerar_contas_pagar": bool(config.gerar_contas_pagar),
    }


def _carregar_acoes_processamento_nota(nota: NotaEntrada) -> dict:
    if getattr(nota, "processamento_acoes", None):
        try:
            dados = json.loads(nota.processamento_acoes)
            if isinstance(dados, dict):
                return {
                    "lancar_estoque": bool(dados.get("lancar_estoque")),
                    "atualizar_custo": bool(dados.get("atualizar_custo")),
                    "atualizar_preco_venda": bool(dados.get("atualizar_preco_venda")),
                    "gerar_contas_pagar": bool(dados.get("gerar_contas_pagar")),
                }
        except (TypeError, ValueError):
            pass

    legado_processado = bool(getattr(nota, "entrada_estoque_realizada", False))
    return {
        "lancar_estoque": legado_processado,
        "atualizar_custo": legado_processado,
        "atualizar_preco_venda": legado_processado,
        "gerar_contas_pagar": legado_processado,
    }


def _reverter_historicos_precos_nota(
    *, produto: Produto, nota: NotaEntrada, db: Session, tenant_id
) -> int:
    historicos = (
        db.query(ProdutoHistoricoPreco)
        .filter(
            ProdutoHistoricoPreco.produto_id == produto.id,
            ProdutoHistoricoPreco.nota_entrada_id == nota.id,
            ProdutoHistoricoPreco.motivo.in_(["nfe_entrada", "nfe_revisao_precos"]),
            ProdutoHistoricoPreco.tenant_id == tenant_id,
        )
        .order_by(ProdutoHistoricoPreco.id.desc())
        .all()
    )

    for historico in historicos:
        produto.preco_custo = float(historico.preco_custo_anterior or 0)
        produto.preco_venda = float(historico.preco_venda_anterior or 0)
        db.delete(historico)

    return len(historicos)


def _atualizar_custo_produto_entrada(
    *,
    produto: Produto,
    nota: NotaEntrada,
    custo_unitario_entrada: float,
    custo_unitario_manual: float | None,
    db: Session,
    current_user,
    tenant_id,
) -> bool:
    preco_custo_anterior = produto.preco_custo or 0
    if custo_unitario_entrada == preco_custo_anterior:
        return False

    preco_venda_anterior = produto.preco_venda or 0
    margem_anterior = (
        ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100)
        if preco_venda_anterior > 0
        else 0
    )

    produto.preco_custo = custo_unitario_entrada
    preco_venda_novo = produto.preco_venda or 0
    margem_nova = (
        ((preco_venda_novo - produto.preco_custo) / preco_venda_novo * 100)
        if preco_venda_novo > 0
        else 0
    )
    variacao_custo = (
        ((produto.preco_custo - preco_custo_anterior) / preco_custo_anterior * 100)
        if preco_custo_anterior > 0
        else 0
    )

    db.add(
        ProdutoHistoricoPreco(
            produto_id=produto.id,
            preco_custo_anterior=preco_custo_anterior,
            preco_custo_novo=produto.preco_custo,
            preco_venda_anterior=preco_venda_anterior,
            preco_venda_novo=preco_venda_novo,
            margem_anterior=margem_anterior,
            margem_nova=margem_nova,
            variacao_custo_percentual=variacao_custo,
            variacao_venda_percentual=0,
            motivo="nfe_entrada",
            nota_entrada_id=nota.id,
            referencia=f"NF-e {nota.numero_nota}",
            observacoes=(
                f"Entrada via NF-e: custo alterado de R$ {preco_custo_anterior:.2f} "
                f"para R$ {produto.preco_custo:.2f}"
                f"{' (ajuste manual aplicado no processamento)' if custo_unitario_manual is not None else ''}"
            ),
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
    )
    return True


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


@router.post("/{nota_id}/conferencia")
def salvar_conferencia_nota(
    nota_id: int,
    payload: ConferenciaNotaPayload,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Salva a conferência física da NF, assumindo tudo OK por padrão e ajustando apenas exceções."""
    current_user, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    itens_por_id = {item.id: item for item in nota.itens}
    payload_por_id = {item.item_id: item for item in payload.itens}

    itens_invalidos = [
        item_id for item_id in payload_por_id if item_id not in itens_por_id
    ]
    if itens_invalidos:
        raise HTTPException(
            status_code=400,
            detail=f"Itens de conferência inválidos: {', '.join(str(item_id) for item_id in itens_invalidos)}",
        )

    for item in nota.itens:
        quantidade_nf = _round_quantity(item.quantidade)
        payload_item = payload_por_id.get(item.id)

        quantidade_conferida = (
            item.quantidade_conferida
            if item.quantidade_conferida is not None
            else quantidade_nf
        )
        quantidade_avariada = item.quantidade_avariada or 0
        observacao_conferencia = item.observacao_conferencia
        acao_sugerida = item.acao_sugerida

        if payload_item:
            quantidade_conferida = _round_quantity(payload_item.quantidade_conferida)
            quantidade_avariada = _round_quantity(payload_item.quantidade_avariada)
            observacao_conferencia = payload_item.observacao_conferencia
            acao_sugerida = payload_item.acao_sugerida

        if quantidade_conferida < 0 or quantidade_avariada < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Quantidades inválidas para o item {item.numero_item}.",
            )

        if quantidade_conferida > quantidade_nf:
            raise HTTPException(
                status_code=400,
                detail=f"A quantidade conferida do item {item.numero_item} não pode ser maior que a quantidade da NF.",
            )

        if quantidade_conferida + quantidade_avariada > quantidade_nf:
            raise HTTPException(
                status_code=400,
                detail=f"A soma de conferida + avariada do item {item.numero_item} não pode ultrapassar a quantidade da NF.",
            )

        tem_divergencia = (
            quantidade_conferida + quantidade_avariada
        ) < quantidade_nf or quantidade_avariada > 0

        item.quantidade_conferida = quantidade_conferida
        item.quantidade_avariada = quantidade_avariada
        item.observacao_conferencia = _normalizar_texto_curto(observacao_conferencia)
        item.acao_sugerida = _obter_acao_conferencia(acao_sugerida, tem_divergencia)

    nota.conferencia_observacoes = _normalizar_texto_curto(payload.observacao_geral)
    nota.conferencia_realizada_em = datetime.utcnow()

    resumo = _resumir_conferencia_nota(nota)
    nota.conferencia_status = (
        CONFERENCIA_STATUS_COM_DIVERGENCIA
        if resumo["itens_com_divergencia"] > 0
        else CONFERENCIA_STATUS_SEM_DIVERGENCIA
    )
    nota.conferencia_user_id = current_user.id

    db.commit()

    return {
        "message": "Conferência salva com sucesso",
        "nota_id": nota.id,
        "conferencia": _resumir_conferencia_nota(nota),
    }


@router.post("/{nota_id}/conferencia/desfazer")
def desfazer_conferencia_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Limpa a conferencia registrada da NF antes do processamento do estoque."""
    current_user, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    if nota.entrada_estoque_realizada or nota.status == "processada":
        raise HTTPException(
            status_code=400,
            detail="Nao e possivel desfazer a conferencia apos processar a entrada no estoque.",
        )

    for item in nota.itens:
        item.quantidade_conferida = None
        item.quantidade_avariada = 0
        item.observacao_conferencia = None
        item.acao_sugerida = "sem_acao"

    nota.conferencia_observacoes = None
    nota.conferencia_realizada_em = None
    nota.conferencia_status = CONFERENCIA_STATUS_NAO_INICIADA
    nota.conferencia_user_id = None

    db.commit()

    return {
        "message": "Conferencia desfeita com sucesso",
        "nota_id": nota.id,
        "conferencia": _resumir_conferencia_nota(nota),
    }


@router.get("/{nota_id}/devolucao-draft")
def gerar_rascunho_nf_devolucao(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Gera um rascunho de NF de devolução com base nos itens avariados da conferência."""
    _, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    itens_devolucao = []
    valor_total_estimado = 0.0

    for item in nota.itens:
        conferencia_item = _serializar_conferencia_item(item)
        quantidade_devolucao = conferencia_item["quantidade_para_devolucao"]
        if quantidade_devolucao <= 0:
            continue

        valor_total_item = round(
            quantidade_devolucao * float(item.valor_unitario or 0), 2
        )
        valor_total_estimado += valor_total_item
        itens_devolucao.append(
            {
                "item_id": item.id,
                "numero_item_nf": item.numero_item,
                "codigo_produto": item.codigo_produto,
                "descricao": item.descricao,
                "unidade": item.unidade,
                "quantidade_devolucao": quantidade_devolucao,
                "valor_unitario": float(item.valor_unitario or 0),
                "valor_total": valor_total_item,
                "observacao_conferencia": conferencia_item["observacao_conferencia"],
            }
        )

    observacao_padrao = (
        f"Rascunho de NF de devolução referente à NF de entrada {nota.numero_nota}. "
        "Gerado a partir das divergências por avaria registradas na conferência física."
    )

    return {
        "disponivel": len(itens_devolucao) > 0,
        "nota_entrada_id": nota.id,
        "numero_nota_origem": nota.numero_nota,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "data_emissao_origem": nota.data_emissao.isoformat()
        if nota.data_emissao
        else None,
        "itens": itens_devolucao,
        "quantidade_itens": len(itens_devolucao),
        "valor_total_estimado": round(valor_total_estimado, 2),
        "observacao_sugerida": observacao_padrao,
        "message": (
            "Rascunho gerado com sucesso"
            if itens_devolucao
            else "Nenhuma divergência com avaria foi encontrada para gerar NF de devolução"
        ),
    }


# ============================================================================
# PREVIEW DE ENTRADA NO ESTOQUE - REVISÃƒO DE PREÃ‡OS
# ============================================================================


@router.get("/{nota_id}/preview-processamento")
def preview_processamento(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna preview da entrada com comparaÃ§Ã£o de custos e preÃ§os atuais
    """
    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto))
        .filter(NotaEntrada.id == nota_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃ£o vinculados",
        )

    composicoes_custo = calcular_composicao_custos_nota(nota)
    preview_itens = []

    for item in nota.itens:
        composicao_custo = composicoes_custo.get(item.id, {})
        conferencia_item = _serializar_conferencia_item(item)
        # Dados do item da NF (sempre presente)
        dados_pack = calcular_quantidade_custo_efetivos(
            item.descricao, item.quantidade, item.valor_unitario, item.valor_total
        )

        item_nf = {
            "item_id": item.id,
            "codigo_produto_nf": item.codigo_produto,
            "descricao_nf": item.descricao,
            "quantidade_nf": item.quantidade,
            "valor_unitario_nf": item.valor_unitario,
            "quantidade_efetiva_nf": dados_pack["quantidade_efetiva"],
            "custo_unitario_efetivo_nf": dados_pack["custo_unitario_efetivo"],
            "custo_aquisicao_unitario_nf": composicao_custo.get(
                "custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]
            ),
            "custo_aquisicao_total_nf": composicao_custo.get(
                "custo_aquisicao_total", item.valor_total
            ),
            "composicao_custo": composicao_custo,
            "pack_detectado_automatico": dados_pack["pack_detectado"],
            "pack_multiplicador_detectado": dados_pack["multiplicador_pack"],
            "ean_nf": item.ean,
            "ean_tributario_nf": getattr(item, "ean_tributario", None),
            "ncm_nf": item.ncm,
            "vinculado": item.vinculado,
            "confianca_vinculo": item.confianca_vinculo,
            "divergencia_codigo_barras": _montar_divergencia_codigo_barras_item(item),
            **conferencia_item,
        }

        detalhe_vinculo = obter_detalhe_vinculo_item(item)
        item_nf["origem_vinculo_automatico"] = detalhe_vinculo["origem"]
        item_nf["referencia_vinculo"] = detalhe_vinculo["referencia"]

        # Dados do produto vinculado (se houver)
        produto_vinculado = None
        if item.produto_id:
            produto = item.produto
            custo_atual = produto.preco_custo or 0
            custo_novo = composicao_custo.get(
                "custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]
            )
            variacao_custo = (
                ((custo_novo - custo_atual) / custo_atual * 100)
                if custo_atual > 0
                else 0
            )

            # Calcular margem de referencia (com custo atual do cadastro)
            preco_venda_atual = produto.preco_venda or 0
            if preco_venda_atual > 0 and custo_atual > 0:
                margem_atual = (
                    (preco_venda_atual - custo_atual) / preco_venda_atual
                ) * 100
            else:
                margem_atual = 0

            # Calcular margem projetada mantendo o preço de venda atual e aplicando o novo custo
            if preco_venda_atual > 0 and custo_novo > 0:
                margem_projetada = (
                    (preco_venda_atual - custo_novo) / preco_venda_atual
                ) * 100
            else:
                margem_projetada = 0

            produto_vinculado = {
                "produto_id": produto.id,
                "produto_codigo": produto.codigo,
                "produto_nome": produto.nome,
                "produto_ean": produto.codigo_barras,
                "produto_codigo_barras": produto.codigo_barras,
                "produto_gtin_ean": produto.gtin_ean,
                "produto_ean_tributario": produto.gtin_ean_tributario,
                "divergencia_codigo_barras": _montar_divergencia_codigo_barras_item(
                    item
                ),
                "custo_anterior": custo_atual,
                "custo_novo": custo_novo,
                "variacao_custo_percentual": round(variacao_custo, 2),
                "preco_venda_atual": preco_venda_atual,
                "margem_atual": round(margem_atual, 2),
                "margem_projetada_custo_novo": round(margem_projetada, 2),
                "estoque_atual": produto.estoque_atual or 0,
            }

        preview_itens.append({**item_nf, "produto_vinculado": produto_vinculado})

    try:
        dados_xml = parse_nfe_xml(nota.xml_content)
    except Exception:
        dados_xml = {
            "natureza_operacao": "",
            "valor_total": nota.valor_total,
            "itens": [
                {"cfop": getattr(item, "cfop", None), "valor_total": item.valor_total}
                for item in nota.itens
            ],
        }
    sugestao_acoes = sugerir_acoes_processamento(dados_xml)

    return {
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "data_emissao": nota.data_emissao.isoformat() if nota.data_emissao else None,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "valor_total": nota.valor_total,
        "conferencia": _resumir_conferencia_nota(nota),
        "acoes_processamento_sugeridas": sugestao_acoes["acoes"],
        "processamento_contexto": sugestao_acoes["contexto"],
        "processamento_mensagem": sugestao_acoes["mensagem"],
        "itens": preview_itens,
    }


# ============================================================================
# ATUALIZAR PREÃ‡OS DOS PRODUTOS
# ============================================================================


def _aplicar_precos_venda_processamento(
    *,
    nota: NotaEntrada,
    precos: List[AtualizarPrecoRequest],
    db: Session,
    current_user,
    tenant_id,
) -> int:
    atualizados = 0
    for preco_data in precos:
        produto = (
            db.query(Produto)
            .filter(Produto.id == preco_data.produto_id, Produto.tenant_id == tenant_id)
            .first()
        )
        if not produto:
            continue

        preco_venda_anterior = produto.preco_venda or 0
        preco_custo_anterior = produto.preco_custo or 0
        if preco_venda_anterior == preco_data.preco_venda:
            continue

        margem_anterior = (
            ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100)
            if preco_venda_anterior > 0
            else 0
        )
        produto.preco_venda = preco_data.preco_venda
        margem_nova = (
            (
                (produto.preco_venda - (produto.preco_custo or 0))
                / produto.preco_venda
                * 100
            )
            if produto.preco_venda > 0
            else 0
        )
        variacao_venda = (
            ((produto.preco_venda - preco_venda_anterior) / preco_venda_anterior * 100)
            if preco_venda_anterior > 0
            else 0
        )

        db.add(
            ProdutoHistoricoPreco(
                produto_id=produto.id,
                preco_custo_anterior=preco_custo_anterior,
                preco_custo_novo=produto.preco_custo,
                preco_venda_anterior=preco_venda_anterior,
                preco_venda_novo=produto.preco_venda,
                margem_anterior=margem_anterior,
                margem_nova=margem_nova,
                variacao_custo_percentual=0,
                variacao_venda_percentual=variacao_venda,
                motivo="nfe_revisao_precos",
                nota_entrada_id=nota.id,
                referencia=f"NF-e {nota.numero_nota} - Revisao de precos",
                observacoes=(
                    f"Preco ajustado de R$ {preco_venda_anterior:.2f} "
                    f"para R$ {produto.preco_venda:.2f}"
                ),
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
        )
        atualizados += 1

    return atualizados


@router.post("/{nota_id}/atualizar-precos")
def atualizar_precos_produtos(
    nota_id: int,
    precos: List[AtualizarPrecoRequest],
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza preÃ§os de venda dos produtos antes de processar a nota
    Registra histÃ³rico de alteraÃ§Ãµes
    """
    current_user, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    for preco_data in precos:
        produto = (
            db.query(Produto)
            .filter(Produto.id == preco_data.produto_id, Produto.tenant_id == tenant_id)
            .first()
        )
        if produto:
            # Capturar valores anteriores
            preco_venda_anterior = produto.preco_venda
            preco_custo_anterior = produto.preco_custo
            margem_anterior = (
                (
                    (preco_venda_anterior - preco_custo_anterior)
                    / preco_venda_anterior
                    * 100
                )
                if preco_venda_anterior > 0
                else 0
            )

            # Atualizar preÃ§o
            produto.preco_venda = preco_data.preco_venda

            # Calcular nova margem
            margem_nova = (
                (
                    (produto.preco_venda - produto.preco_custo)
                    / produto.preco_venda
                    * 100
                )
                if produto.preco_venda > 0
                else 0
            )

            # Registrar histÃ³rico se houve alteraÃ§Ã£o
            if preco_venda_anterior != produto.preco_venda:
                variacao_venda = (
                    (
                        (produto.preco_venda - preco_venda_anterior)
                        / preco_venda_anterior
                        * 100
                    )
                    if preco_venda_anterior > 0
                    else 0
                )

                historico = ProdutoHistoricoPreco(
                    produto_id=produto.id,
                    preco_custo_anterior=preco_custo_anterior,
                    preco_custo_novo=produto.preco_custo,
                    preco_venda_anterior=preco_venda_anterior,
                    preco_venda_novo=produto.preco_venda,
                    margem_anterior=margem_anterior,
                    margem_nova=margem_nova,
                    variacao_custo_percentual=0,  # Custo nÃ£o mudou neste caso
                    variacao_venda_percentual=variacao_venda,
                    motivo="nfe_revisao_precos",
                    nota_entrada_id=nota.id,
                    referencia=f"NF-e {nota.numero_nota} - RevisÃ£o de PreÃ§os",
                    observacoes=f"PreÃ§o ajustado de R$ {preco_venda_anterior:.2f} para R$ {produto.preco_venda:.2f} (margem: {margem_anterior:.1f}% â†’ {margem_nova:.1f}%)",
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                )
                db.add(historico)

                logger.info(
                    f"ðŸ“Š HistÃ³rico registrado: {produto.nome} - "
                    f"PreÃ§o R$ {preco_venda_anterior:.2f} â†’ R$ {produto.preco_venda:.2f} "
                    f"({variacao_venda:+.2f}%)"
                )

    db.commit()

    return {"message": "PreÃ§os atualizados com sucesso"}


# ============================================================================
# DAR ENTRADA NO ESTOQUE
# ============================================================================


@router.post("/{nota_id}/processar")
def processar_entrada_estoque(
    nota_id: int,
    config: ProcessarConfig = ProcessarConfig(),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Processa entrada no estoque de todos os itens vinculados.
    Aceita:
    - multiplicadores_override: {"item_id": multiplicador} para packs manuais
    - custos_override: {"item_id": custo_unitario} para custo manual de sistema
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"ðŸ“¦ Processando entrada no estoque - Nota {nota_id}")

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    if nota.entrada_estoque_realizada or nota.status == "processada":
        raise HTTPException(
            status_code=400, detail="Entrada no estoque jÃ¡ foi realizada"
        )

    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃ£o vinculados. "
            "Vincule todos os produtos antes de processar.",
        )

    try:
        dados_xml_processamento = parse_nfe_xml(nota.xml_content)
    except Exception:
        dados_xml_processamento = {
            "natureza_operacao": "",
            "valor_total": nota.valor_total,
            "itens": [
                {"cfop": getattr(item, "cfop", None), "valor_total": item.valor_total}
                for item in nota.itens
            ],
        }

    acoes_processamento = _acoes_processamento_dict(config)
    contexto_processamento = detectar_contexto_processamento(dados_xml_processamento)
    nota.processamento_contexto = contexto_processamento["contexto"]
    nota.processamento_acoes = json.dumps(acoes_processamento, sort_keys=True)

    precos_venda_atualizados = 0
    if config.atualizar_preco_venda and config.precos_venda_override:
        precos_venda_atualizados = _aplicar_precos_venda_processamento(
            nota=nota,
            precos=config.precos_venda_override,
            db=db,
            current_user=current_user,
            tenant_id=tenant_id,
        )

    itens_processados = []
    custos_atualizados = 0
    composicoes_custo = calcular_composicao_custos_nota(nota)
    lotes_rastro_por_item = _mapear_lotes_rastro_xml(nota.xml_content)

    # Processar cada item
    for item in nota.itens:
        if not item.produto_id:
            continue

        composicao_custo = composicoes_custo.get(item.id, {})
        conferencia_item = _serializar_conferencia_item(item)
        quantidade_base_conferida = conferencia_item["quantidade_conferida"]

        # Verificar override manual antes de usar auto-deteccao
        override_raw = _obter_override_mapa(config.multiplicadores_override, item.id)
        try:
            override_mult = int(override_raw) if override_raw is not None else None
        except (ValueError, TypeError):
            override_mult = None
        custo_unitario_manual = _normalizar_custo_unitario_override(
            _obter_override_mapa(config.custos_override, item.id),
            item.id,
        )

        if override_mult is not None and 1 <= override_mult <= 200:
            multiplicador_pack = override_mult
            quantidade_total_efetiva_nf = (item.quantidade or 0) * override_mult
            quantidade_entrada = quantidade_base_conferida * override_mult
            custo_total_aquisicao = composicao_custo.get(
                "custo_aquisicao_total", item.valor_total
            )
            custo_unitario_entrada = (
                (custo_total_aquisicao / quantidade_total_efetiva_nf)
                if quantidade_total_efetiva_nf > 0
                else item.valor_unitario
            )
            logger.info(
                f"📦 Pack MANUAL no item {item.id}: x{override_mult} (qtd NF {item.quantidade} → qtd entrada {quantidade_entrada})"
            )
        else:
            dados_pack = calcular_quantidade_custo_efetivos(
                item.descricao, item.quantidade, item.valor_unitario, item.valor_total
            )
            quantidade_entrada = (
                quantidade_base_conferida * dados_pack["multiplicador_pack"]
            )
            custo_unitario_entrada = composicao_custo.get(
                "custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]
            )
            multiplicador_pack = dados_pack["multiplicador_pack"]

        custo_unitario_calculado_nf = custo_unitario_entrada

        if custo_unitario_manual is not None and config.atualizar_custo:
            custo_unitario_entrada = custo_unitario_manual
            logger.info(
                f"💰 Custo manual aplicado no item {item.id}: "
                f"R$ {custo_unitario_entrada:.4f} por unidade"
            )

        if quantidade_entrada <= 0:
            item.status = "processado"
            itens_processados.append(
                {
                    "produto_id": item.produto.id,
                    "produto_nome": item.produto.nome,
                    "quantidade": 0,
                    "lote": None,
                    "estoque_atual": item.produto.estoque_atual or 0,
                    "pack_multiplicador": multiplicador_pack,
                    "status_conferencia": conferencia_item["status_conferencia"],
                }
            )
            logger.info(
                f"  ⚠️ {item.produto.nome}: sem entrada em estoque "
                f"(conferida: {quantidade_base_conferida}, avariada: {conferencia_item['quantidade_avariada']}, "
                f"faltante: {conferencia_item['quantidade_faltante']})"
            )
            continue

        produto = item.produto
        if not config.atualizar_custo:
            custo_unitario_entrada = resolver_custo_operacional_entrada(
                custo_nf=custo_unitario_calculado_nf,
                custo_atual_sistema=produto.preco_custo,
                atualizar_custo=False,
            )

        # âœ… REATIVAR produto se estiver inativo
        if not produto.ativo:
            produto.ativo = True
            logger.info(
                f"  â™»ï¸  Produto reativado: {produto.codigo} - {produto.nome}"
            )

        # Atualizar dados fiscais do produto com informacoes do XML quando vierem preenchidas.
        # Entradas PDF preservam o cadastro atual, pois o arquivo nao contem dados fiscais reais.
        _aplicar_dados_fiscais_item_no_produto(
            produto,
            item,
            sobrescrever=nota.serie != "PDF",
        )

        _aplicar_codigos_barras_item_no_produto(produto, item)

        # âœ… VINCULAR ao fornecedor da nota
        if nota.fornecedor_id:
            vinculo_existente = (
                db.query(ProdutoFornecedor)
                .filter(
                    ProdutoFornecedor.produto_id == produto.id,
                    ProdutoFornecedor.fornecedor_id == nota.fornecedor_id,
                )
                .first()
            )

            if not vinculo_existente:
                novo_vinculo = ProdutoFornecedor(
                    produto_id=produto.id,
                    fornecedor_id=nota.fornecedor_id,
                    preco_custo=custo_unitario_entrada,
                    e_principal=True,
                    ativo=True,
                    tenant_id=tenant_id,
                )
                db.add(novo_vinculo)
                logger.info(
                    f"  ðŸ”— Produto {produto.codigo} vinculado ao fornecedor {nota.fornecedor_id}"
                )
            else:
                # Reativar vÃ­nculo se estiver inativo
                if not vinculo_existente.ativo:
                    vinculo_existente.ativo = True
                    logger.info(
                        f"  â™»ï¸  VÃ­nculo de fornecedor reativado: {produto.codigo}"
                    )
                # Atualizar preÃ§o de custo no vÃ­nculo
                if config.atualizar_custo:
                    vinculo_existente.preco_custo = custo_unitario_entrada

        if not config.lancar_estoque:
            if config.atualizar_custo and _atualizar_custo_produto_entrada(
                produto=produto,
                nota=nota,
                custo_unitario_entrada=custo_unitario_entrada,
                custo_unitario_manual=custo_unitario_manual,
                db=db,
                current_user=current_user,
                tenant_id=tenant_id,
            ):
                custos_atualizados += 1
            item.status = "processado"
            continue

        lotes_entrada = _montar_lotes_entrada_item(
            item,
            nota,
            quantidade_entrada,
            lotes_rastro_por_item,
        )
        if not lotes_entrada:
            continue

        lotes_criados = []
        ordem_base = int(datetime.utcnow().timestamp())
        for lote_index, lote_entrada in enumerate(lotes_entrada):
            quantidade_lote = _round_quantity(lote_entrada["quantidade"])
            if quantidade_lote <= 0:
                continue

            lote = ProdutoLote(
                produto_id=produto.id,
                nome_lote=lote_entrada["nome_lote"],
                quantidade_inicial=quantidade_lote,
                quantidade_disponivel=quantidade_lote,
                custo_unitario=float(custo_unitario_entrada),
                data_fabricacao=lote_entrada.get("data_fabricacao"),
                data_validade=lote_entrada.get("data_validade"),
                ordem_entrada=ordem_base + lote_index,
                tenant_id=tenant_id,
            )
            db.add(lote)
            db.flush()
            lotes_criados.append((lote, quantidade_lote))

        if not lotes_criados:
            continue

        # Atualizar estoque
        estoque_anterior = produto.estoque_atual or 0
        produto.estoque_atual = estoque_anterior + quantidade_entrada

        # Atualizar preÃ§o de custo e registrar histÃ³rico
        preco_custo_anterior = produto.preco_custo or 0
        preco_venda_anterior = produto.preco_venda or 0
        margem_anterior = (
            ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100)
            if preco_venda_anterior > 0
            else 0
        )

        alterou_custo = False
        if config.atualizar_custo and custo_unitario_entrada != preco_custo_anterior:
            produto.preco_custo = custo_unitario_entrada
            alterou_custo = True
            custos_atualizados += 1

        # Calcular margem nova
        preco_venda_novo = produto.preco_venda or 0
        margem_nova = (
            ((preco_venda_novo - (produto.preco_custo or 0)) / preco_venda_novo * 100)
            if preco_venda_novo > 0
            else 0
        )

        # Registrar histÃ³rico de preÃ§o se houve alteraÃ§Ã£o
        if alterou_custo:
            variacao_custo = (
                (
                    (produto.preco_custo - preco_custo_anterior)
                    / preco_custo_anterior
                    * 100
                )
                if preco_custo_anterior > 0
                else 0
            )

            historico = ProdutoHistoricoPreco(
                produto_id=produto.id,
                preco_custo_anterior=preco_custo_anterior,
                preco_custo_novo=produto.preco_custo,
                preco_venda_anterior=preco_venda_anterior,
                preco_venda_novo=preco_venda_novo,
                margem_anterior=margem_anterior,
                margem_nova=margem_nova,
                variacao_custo_percentual=variacao_custo,
                variacao_venda_percentual=0,  # PreÃ§o de venda nÃ£o mudou
                motivo="nfe_entrada",
                nota_entrada_id=nota.id,
                referencia=f"NF-e {nota.numero_nota}",
                observacoes=(
                    f"Entrada via NF-e: custo alterado de R$ {preco_custo_anterior:.2f} "
                    f"para R$ {produto.preco_custo:.2f}"
                    f"{' (ajuste manual aplicado no processamento)' if custo_unitario_manual is not None else ''}"
                ),
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(historico)

            logger.info(
                f"  ðŸ“Š HistÃ³rico registrado: {produto.nome} - "
                f"Custo R$ {preco_custo_anterior:.2f} â†’ R$ {produto.preco_custo:.2f} "
                f"({variacao_custo:+.2f}%)"
            )

        observacao_movimentacao = (
            (
                f"Entrada NF-e {nota.numero_nota} - {item.descricao}"
                if conferencia_item["status_conferencia"] == "ok"
                else (
                    f"Entrada NF-e {nota.numero_nota} - {item.descricao} | "
                    f"Conferida: {conferencia_item['quantidade_conferida']} | "
                    f"Avariada: {conferencia_item['quantidade_avariada']} | "
                    f"Faltante: {conferencia_item['quantidade_faltante']}"
                )
            )
            + (
                f" | Custo sistema manual: R$ {custo_unitario_entrada:.4f}"
                if custo_unitario_manual is not None and config.atualizar_custo
                else ""
            )
            + (
                " | Custo do cadastro preservado; entrada valorizada pelo custo atual do sistema"
                if not config.atualizar_custo
                else ""
            )
        )

        estoque_movimento_anterior = estoque_anterior
        for lote, quantidade_lote in lotes_criados:
            estoque_movimento_novo = _round_quantity(
                estoque_movimento_anterior + quantidade_lote
            )
            movimentacao = EstoqueMovimentacao(
                produto_id=produto.id,
                lote_id=lote.id,
                tipo="entrada",
                motivo="compra",
                quantidade=quantidade_lote,
                quantidade_anterior=estoque_movimento_anterior,
                quantidade_nova=estoque_movimento_novo,
                custo_unitario=float(custo_unitario_entrada),
                valor_total=float(quantidade_lote * custo_unitario_entrada),
                documento=nota.chave_acesso,
                referencia_tipo="nota_entrada",
                referencia_id=nota.id,
                observacao=observacao_movimentacao,
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(movimentacao)
            estoque_movimento_anterior = estoque_movimento_novo

        # Atualizar status do item
        item.status = "processado"

        itens_processados.append(
            {
                "produto_id": produto.id,
                "produto_nome": produto.nome,
                "quantidade": quantidade_entrada,
                "lote": ", ".join(lote.nome_lote for lote, _ in lotes_criados),
                "estoque_atual": produto.estoque_atual,
                "pack_multiplicador": multiplicador_pack,
                "status_conferencia": conferencia_item["status_conferencia"],
                "custo_unitario_aplicado": float(custo_unitario_entrada),
                "custo_manual_aplicado": (
                    custo_unitario_manual is not None and config.atualizar_custo
                ),
            }
        )

        logger.info(
            f"  âœ… {produto.nome}: +{quantidade_entrada} unidades "
            f"em {len(lotes_criados)} lote(s) "
            f"(estoque: {estoque_anterior} â†’ {produto.estoque_atual})"
        )

        if multiplicador_pack > 1:
            logger.info(
                f"  ðŸ“¦ Pack detectado automaticamente no item {item.numero_item}: "
                f"x{multiplicador_pack} (qtd NF {item.quantidade} â†’ qtd entrada {quantidade_entrada})"
            )

    resumo_conferencia = _resumir_conferencia_nota(nota)
    if not nota.conferencia_realizada_em:
        nota.conferencia_realizada_em = datetime.utcnow()
        nota.conferencia_user_id = current_user.id
    nota.conferencia_status = (
        CONFERENCIA_STATUS_COM_DIVERGENCIA
        if resumo_conferencia["itens_com_divergencia"] > 0
        else CONFERENCIA_STATUS_SEM_DIVERGENCIA
    )
    resumo_conferencia = _resumir_conferencia_nota(nota)

    # Atualizar nota
    nota.status = "processada"
    nota.entrada_estoque_realizada = bool(config.lancar_estoque)
    nota.processada_em = datetime.utcnow()

    # CRIAR CONTAS A PAGAR apÃ³s processar estoque
    contas_ids = []
    try:
        # Buscar dados do XML salvos na nota para pegar duplicatas
        dados_xml = dados_xml_processamento

        contas_ids = (
            criar_contas_pagar_da_nota(nota, dados_xml, db, current_user.id, tenant_id)
            if config.gerar_contas_pagar
            else []
        )
        logger.info(f"ðŸ’° {len(contas_ids)} contas a pagar criadas")
    except Exception as e:
        logger.error(f"âš ï¸ Erro ao criar contas a pagar: {str(e)}")
        # NÃ£o abortar o processo, apenas avisar

    db.commit()

    # SINCRONIZAR ESTOQUE COM BLING para todos os itens processados
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        for item_proc in itens_processados:
            sincronizar_bling_background(
                item_proc["produto_id"], item_proc["estoque_atual"], "entrada_nfe"
            )
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (entrada_nfe): {e_sync}")

    # VERIFICAR E NOTIFICAR PENDÊNCIAS DE ESTOQUE
    from app.services.pendencia_estoque_service import verificar_e_notificar_pendencias

    try:
        for item_proc in itens_processados:
            produto_id = item_proc["produto_id"]
            quantidade = item_proc["quantidade"]
            notificacoes = verificar_e_notificar_pendencias(
                db=db,
                tenant_id=tenant_id,
                produto_id=produto_id,
                quantidade_entrada=quantidade,
            )
            if notificacoes > 0:
                logger.info(
                    f"WhatsApp: {notificacoes} clientes notificados sobre {item_proc['produto']}"
                )
    except Exception as e:
        logger.error(f"Erro ao notificar pendencias: {str(e)}")
        # Não abortar, apenas logar o erro

    logger.info(f"âœ… Entrada processada: {len(itens_processados)} produtos")

    return {
        "message": "Entrada no estoque realizada com sucesso",
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "itens_processados": len(itens_processados),
        "contas_pagar_criadas": len(contas_ids),
        "custos_atualizados": custos_atualizados,
        "precos_venda_atualizados": precos_venda_atualizados,
        "acoes_processamento": acoes_processamento,
        "conferencia": resumo_conferencia,
        "detalhes": itens_processados,
    }


# ============================================================================
# REVERTER/ESTORNAR ENTRADA NO ESTOQUE
# ============================================================================


@router.post("/{nota_id}/reverter")
def reverter_entrada_estoque(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Reverte a entrada no estoque de uma nota jÃ¡ processada
    Remove estoque, exclui lotes, movimentaÃ§Ãµes e contas a pagar
    Reverte preÃ§os de custo dos produtos
    """
    current_user, tenant_id = user_and_tenant

    logger.info(f"ðŸ”„ Revertendo entrada no estoque - Nota {nota_id}")

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    if not nota.entrada_estoque_realizada and nota.status != "processada":
        raise HTTPException(
            status_code=400, detail="Esta nota ainda nÃ£o foi processada"
        )

    acoes_nota = _carregar_acoes_processamento_nota(nota)

    # REVERTER CONTAS A PAGAR vinculadas a esta nota
    logger.info("ðŸ’° Excluindo contas a pagar vinculadas...")
    contas_pagar = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.nota_entrada_id == nota.id, ContaPagar.tenant_id == tenant_id
        )
        .all()
    )

    contas_excluidas = 0
    for conta in contas_pagar:
        if conta.status != "pago":
            db.delete(conta)
            contas_excluidas += 1
            logger.info(
                f"   âœ… Conta excluÃ­da: {conta.descricao} - R$ {float(conta.valor_final):.2f}"
            )
        else:
            logger.warning(
                f"   âš ï¸ Conta JÃ PAGA nÃ£o pode ser excluÃ­da: {conta.descricao}"
            )

    if contas_excluidas > 0:
        logger.info(f"âœ… Total de contas excluÃ­das: {contas_excluidas}")

    itens_revertidos = []
    produtos_precos_revertidos = set()

    try:
        # Reverter cada item
        for item in nota.itens:
            if not item.produto_id:
                continue

            try:
                produto = item.produto
                if (
                    acoes_nota["atualizar_custo"] or acoes_nota["atualizar_preco_venda"]
                ) and produto.id not in produtos_precos_revertidos:
                    _reverter_historicos_precos_nota(
                        produto=produto,
                        nota=nota,
                        db=db,
                        tenant_id=tenant_id,
                    )
                    produtos_precos_revertidos.add(produto.id)

                # Buscar lotes criados para esta entrada. Notas podem ter mais de um
                # rastro/lote para o mesmo item do XML.
                lotes = (
                    db.query(ProdutoLote)
                    .join(
                        EstoqueMovimentacao,
                        EstoqueMovimentacao.lote_id == ProdutoLote.id,
                    )
                    .filter(
                        ProdutoLote.produto_id == produto.id,
                        ProdutoLote.tenant_id == tenant_id,
                        EstoqueMovimentacao.referencia_tipo == "nota_entrada",
                        EstoqueMovimentacao.referencia_id == nota.id,
                        EstoqueMovimentacao.produto_id == produto.id,
                        EstoqueMovimentacao.tenant_id == tenant_id,
                    )
                    .distinct()
                    .all()
                )

                if not lotes:
                    nome_lote = (
                        item.lote
                        if item.lote
                        else f"NF{nota.numero_nota}-{item.numero_item}"
                    )
                    lote_fallback = (
                        db.query(ProdutoLote)
                        .filter(
                            ProdutoLote.produto_id == produto.id,
                            ProdutoLote.nome_lote == nome_lote,
                            ProdutoLote.tenant_id == tenant_id,
                        )
                        .first()
                    )
                    lotes = [lote_fallback] if lote_fallback else []

                if lotes:
                    quantidade_lancada = float(
                        sum(lote.quantidade_inicial or 0 for lote in lotes)
                    )
                    lote_base = lotes[0]

                    # REVERTER PREÇO DE CUSTO se foi alterado
                    try:
                        historico_preco = (
                            db.query(ProdutoHistoricoPreco)
                            .filter(
                                ProdutoHistoricoPreco.produto_id == produto.id,
                                ProdutoHistoricoPreco.nota_entrada_id == nota.id,
                                ProdutoHistoricoPreco.motivo.in_(
                                    ["nfe_entrada", "nfe_revisao_precos"]
                                ),
                                ProdutoHistoricoPreco.tenant_id == tenant_id,
                            )
                            .first()
                        )

                        if historico_preco:
                            # Reverter preços anteriores (com fallback para 0 se None)
                            preco_custo_revertido = float(
                                historico_preco.preco_custo_anterior or 0
                            )
                            preco_venda_revertido = float(
                                historico_preco.preco_venda_anterior or 0
                            )

                            try:
                                logger.info(
                                    f"  💰 Revertendo preço de custo: R$ {float(produto.preco_custo or 0):.2f} → R$ {preco_custo_revertido:.2f}"
                                )
                            except Exception:
                                logger.info(
                                    f"  💰 Revertendo preços do produto {produto.id}"
                                )

                            produto.preco_custo = preco_custo_revertido
                            produto.preco_venda = preco_venda_revertido

                            # Excluir histórico
                            db.delete(historico_preco)
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erro ao reverter preços: {str(e)}")

                    # Remover quantidade do estoque
                    estoque_anterior = produto.estoque_atual or 0
                    produto.estoque_atual = max(
                        0, estoque_anterior - quantidade_lancada
                    )

                    # Registrar movimentação de estorno (sem referência ao lote que será deletado)
                    try:
                        movimentacao_estorno = EstoqueMovimentacao(
                            produto_id=produto.id,
                            lote_id=None,  # Não referenciar o lote que será deletado
                            tipo="saida",
                            motivo="ajuste",
                            quantidade=quantidade_lancada,
                            quantidade_anterior=float(estoque_anterior),
                            quantidade_nova=float(produto.estoque_atual or 0),
                            custo_unitario=float(
                                lote_base.custo_unitario or item.valor_unitario or 0
                            ),
                            valor_total=float(
                                quantidade_lancada
                                * float(
                                    lote_base.custo_unitario or item.valor_unitario or 0
                                )
                            ),
                            documento=nota.chave_acesso or "",
                            referencia_tipo="estorno_nota_entrada",
                            referencia_id=nota.id,
                            observacao=f"Estorno NF-e {nota.numero_nota} - {item.descricao or ''}",
                            user_id=current_user.id,
                            tenant_id=tenant_id,
                        )
                        db.add(movimentacao_estorno)
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erro ao criar movimentação: {str(e)}")

                    for lote in lotes:
                        # Excluir movimentações de estoque vinculadas ao lote (antes de deletar o lote)
                        movimentacoes_lote = (
                            db.query(EstoqueMovimentacao)
                            .filter(
                                EstoqueMovimentacao.lote_id == lote.id,
                                EstoqueMovimentacao.tenant_id == tenant_id,
                            )
                            .all()
                        )

                        for mov in movimentacoes_lote:
                            db.delete(mov)

                        if movimentacoes_lote:
                            logger.info(
                                f"  🗑️  {len(movimentacoes_lote)} movimentações do lote excluídas"
                            )

                        # Excluir lote
                        db.delete(lote)

                    # Adicionar à lista de revertidos
                    itens_revertidos.append(
                        {
                            "produto_id": produto.id,
                            "produto_nome": produto.nome,
                            "quantidade_removida": quantidade_lancada,
                            "estoque_atual": float(produto.estoque_atual or 0),
                        }
                    )

                    logger.info(
                        f"  ↩️  {produto.nome}: -{quantidade_lancada} unidades "
                        f"(estoque: {estoque_anterior} → {produto.estoque_atual})"
                    )

                # Restaurar status do item
                item.status = "vinculado"

            except Exception as e:
                logger.error(f"  ❌ Erro ao reverter item {item.id}: {str(e)}")
                # Continuar com próximo item ao invés de parar tudo

        # Atualizar status da nota
        nota.status = "pendente"
        nota.entrada_estoque_realizada = False
        nota.processada_em = None
        nota.processamento_contexto = None
        nota.processamento_acoes = None

        db.commit()

        # SINCRONIZAR ESTOQUE COM BLING para todos os itens revertidos
        try:
            from app.bling_estoque_sync import sincronizar_bling_background

            for item_rev in itens_revertidos:
                sincronizar_bling_background(
                    item_rev["produto_id"], item_rev["estoque_atual"], "estorno_nfe"
                )
        except Exception as e_sync:
            logger.warning(f"[BLING-SYNC] Erro ao agendar sync (estorno_nfe): {e_sync}")

        logger.info(f"âœ… Entrada revertida: {len(itens_revertidos)} produtos")

        return {
            "message": "Entrada no estoque revertida com sucesso",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "itens_revertidos": len(itens_revertidos),
            "detalhes": itens_revertidos,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"âŒ Erro ao reverter entrada: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao reverter entrada: {str(e)}"
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
