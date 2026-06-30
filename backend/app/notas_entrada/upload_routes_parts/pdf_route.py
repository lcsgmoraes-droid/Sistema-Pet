"""Rota de upload de pedido ou romaneio em PDF."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.notas_entrada.upload_routes_parts.common import (
    buscar_nota_por_chave,
    montar_resposta_upload,
    salvar_entrada_com_itens,
)
from app.notas_entrada.xml_parser import parse_nfe_xml
from app.notas_entrada_pdf_parser import (
    PDFEntradaFornecedor,
    build_pdf_synthetic_nfe_xml,
    extract_pdf_text,
    parse_pedido_pdf_text,
)

logger = logging.getLogger(__name__)
router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]
CurrentUserTenant = Annotated[Any, Depends(get_current_user_and_tenant)]
PdfUploadFile = Annotated[UploadFile, File(...)]
FornecedorId = Annotated[int, Form(...)]

PDF_AVISOS = [
    "PDF importado como pedido/romaneio; nao e NF-e validada pela SEFAZ.",
    "O PDF nao traz chave fiscal real, CFOP, NCM, impostos ou lotes. Revise os produtos antes de processar.",
    "Produtos ja cadastrados preservam os dados fiscais existentes quando o PDF nao trouxer essas informacoes.",
]

UPLOAD_PDF_RESPONSES = {
    400: {"description": "Arquivo invalido, PDF vazio, PDF invalido ou nota duplicada"},
    404: {"description": "Fornecedor ativo nao encontrado"},
    500: {"description": "Erro interno ao processar PDF"},
}


@router.post("/upload-pdf", responses=UPLOAD_PDF_RESPONSES)
async def upload_pdf(
    file: PdfUploadFile,
    fornecedor_id: FornecedorId,
    db: DbSession,
    user_and_tenant: CurrentUserTenant,
):
    """Upload de pedido/romaneio PDF e entrada pelo fluxo existente."""
    current_user, tenant_id = user_and_tenant
    logger.info("Upload de PDF de entrada recebido")

    try:
        _validar_nome_pdf(file)
        fornecedor = _buscar_fornecedor_pdf(db, fornecedor_id, tenant_id)
        pdf_content = await _ler_pdf_upload(file)
        dados_nfe, xml_str = _converter_pdf_para_nfe(pdf_content, fornecedor, tenant_id)
        _garantir_pdf_inedito(db, dados_nfe)
        entrada = salvar_entrada_com_itens(
            db,
            dados_nfe=dados_nfe,
            xml_str=xml_str,
            fornecedor=fornecedor,
            current_user=current_user,
            tenant_id=tenant_id,
            origem_documento="pdf",
            campos_xml_obrigatorios=False,
        )
        return montar_resposta_upload(
            entrada=entrada,
            dados_nfe=dados_nfe,
            message="PDF processado com sucesso",
            fornecedor_criado_automaticamente=False,
            origem_documento="pdf",
            avisos=PDF_AVISOS,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        logger.exception("Erro inesperado no upload PDF")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar PDF: {str(exc)}"
        ) from exc


def _validar_nome_pdf(file: UploadFile) -> None:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")


def _buscar_fornecedor_pdf(
    db: Session,
    fornecedor_id: int,
    tenant_id: int,
) -> Cliente:
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
    if fornecedor:
        return fornecedor

    raise HTTPException(status_code=404, detail="Fornecedor ativo nao encontrado")


async def _ler_pdf_upload(file: UploadFile) -> bytes:
    pdf_content = await file.read()
    if not pdf_content:
        raise HTTPException(status_code=400, detail="PDF vazio")
    return pdf_content


def _converter_pdf_para_nfe(
    pdf_content: bytes,
    fornecedor: Cliente,
    tenant_id: int,
) -> tuple[dict[str, Any], str]:
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
    return parse_nfe_xml(xml_str), xml_str


def _garantir_pdf_inedito(db: Session, dados_nfe: dict[str, Any]) -> None:
    nota_existente = buscar_nota_por_chave(db, dados_nfe["chave_acesso"])
    if not nota_existente:
        return

    raise HTTPException(
        status_code=400,
        detail=f"PDF ja importado como entrada (ID: {nota_existente.id})",
    )
