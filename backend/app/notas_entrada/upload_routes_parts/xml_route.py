"""Rota de upload unitario de XML de NF-e."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.notas_entrada.upload_routes_parts.common import (
    buscar_nota_por_chave,
    buscar_ou_criar_fornecedor_nfe,
    montar_resposta_upload,
    salvar_entrada_com_itens,
)
from app.notas_entrada.xml_parser import parse_nfe_xml

logger = logging.getLogger(__name__)
router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]
CurrentUserTenant = Annotated[Any, Depends(get_current_user_and_tenant)]
XmlUploadFile = Annotated[UploadFile, File(...)]

UPLOAD_XML_RESPONSES = {
    400: {"description": "Arquivo invalido, XML invalido ou nota duplicada"},
    500: {"description": "Erro interno ao processar XML"},
}


@router.post("/upload", responses=UPLOAD_XML_RESPONSES)
async def upload_xml(
    file: XmlUploadFile,
    db: DbSession,
    user_and_tenant: CurrentUserTenant,
):
    """Upload de XML de NF-e e parse automatico."""
    current_user, tenant_id = user_and_tenant
    logger.info("Upload de XML recebido")

    try:
        xml_str = await _ler_xml_upload(file)
        dados_nfe = _parsear_xml_upload(xml_str)
        _garantir_nota_inedita(db, dados_nfe)
        fornecedor, fornecedor_criado = _obter_fornecedor_xml(
            db, dados_nfe, current_user, tenant_id
        )
        entrada = salvar_entrada_com_itens(
            db,
            dados_nfe=dados_nfe,
            xml_str=xml_str,
            fornecedor=fornecedor,
            current_user=current_user,
            tenant_id=tenant_id,
            origem_documento="xml",
            campos_xml_obrigatorios=True,
        )
        return montar_resposta_upload(
            entrada=entrada,
            dados_nfe=dados_nfe,
            message="XML processado com sucesso",
            fornecedor_criado_automaticamente=fornecedor_criado,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        logger.exception("Erro inesperado no upload XML")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar XML: {str(exc)}"
        ) from exc


async def _ler_xml_upload(file: UploadFile) -> str:
    filename = file.filename or ""
    if not filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xml")

    xml_content = await file.read()
    logger.info("XML recebido com %s bytes", len(xml_content))
    return xml_content.decode("utf-8")


def _parsear_xml_upload(xml_str: str) -> dict[str, Any]:
    try:
        dados_nfe = parse_nfe_xml(xml_str)
    except ValueError as exc:
        logger.exception("Erro no parse do XML")
        raise HTTPException(
            status_code=400, detail=f"Erro ao processar XML: {str(exc)}"
        ) from exc
    except Exception as exc:
        logger.exception("Erro inesperado no parse do XML")
        raise HTTPException(
            status_code=500, detail=f"Erro interno ao processar XML: {str(exc)}"
        ) from exc

    logger.info(
        "XML parseado: chave=%s numero=%s fornecedor=%s itens=%s",
        dados_nfe.get("chave_acesso", "N/A"),
        dados_nfe.get("numero_nota", "N/A"),
        dados_nfe.get("fornecedor_nome", "N/A"),
        len(dados_nfe.get("itens", [])),
    )
    return dados_nfe


def _garantir_nota_inedita(db: Session, dados_nfe: dict[str, Any]) -> None:
    nota_existente = buscar_nota_por_chave(db, dados_nfe["chave_acesso"])
    if not nota_existente:
        return

    raise HTTPException(
        status_code=400,
        detail=f"Nota fiscal ja cadastrada (ID: {nota_existente.id})",
    )


def _obter_fornecedor_xml(
    db: Session,
    dados_nfe: dict[str, Any],
    current_user: Any,
    tenant_id: int,
):
    try:
        return buscar_ou_criar_fornecedor_nfe(
            db,
            dados_nfe=dados_nfe,
            current_user=current_user,
            tenant_id=tenant_id,
            somente_ativos=True,
        )
    except Exception as exc:
        logger.exception("Erro ao criar fornecedor no upload XML")
        raise HTTPException(
            status_code=500, detail=f"Erro ao criar fornecedor: {str(exc)}"
        ) from exc
