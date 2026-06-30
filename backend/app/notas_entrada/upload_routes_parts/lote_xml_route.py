"""Rota de upload em lote de XMLs de NF-e."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.notas_entrada.upload_routes_parts.common import (
    EntradaComItens,
    buscar_nota_por_chave,
    buscar_ou_criar_fornecedor_nfe,
    salvar_entrada_com_itens,
)
from app.notas_entrada.xml_parser import parse_nfe_xml

logger = logging.getLogger(__name__)
router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]
CurrentUserTenant = Annotated[Any, Depends(get_current_user_and_tenant)]
XmlUploadFiles = Annotated[list[UploadFile], File(...)]


@router.post("/upload-lote")
async def upload_lote_xml(
    files: XmlUploadFiles,
    db: DbSession,
    user_and_tenant: CurrentUserTenant,
):
    """
    Upload de multiplos XMLs de NF-e e processamento em lote.
    Retorna resumo de sucessos e erros.
    """
    current_user, tenant_id = user_and_tenant
    logger.info("Upload em lote de notas recebido (%s arquivos)", len(files))

    resultados = []
    for ordem, file in enumerate(files, 1):
        resultado = await _processar_arquivo_lote(
            file,
            ordem=ordem,
            db=db,
            current_user=current_user,
            tenant_id=tenant_id,
        )
        resultados.append(resultado)

    sucessos = sum(1 for resultado in resultados if resultado["sucesso"])
    erros = len(resultados) - sucessos
    logger.info(
        "Processamento em lote concluido: %s sucessos, %s erros",
        sucessos,
        erros,
    )

    return {
        "message": f"Processamento em lote concluido: {sucessos} sucessos, {erros} erros",
        "total_arquivos": len(files),
        "sucessos": sucessos,
        "erros": erros,
        "resultados": resultados,
    }


async def _processar_arquivo_lote(
    file: UploadFile,
    *,
    ordem: int,
    db: Session,
    current_user: Any,
    tenant_id: int,
) -> dict[str, Any]:
    resultado = _resultado_lote_inicial(file, ordem)
    try:
        xml_str = await _ler_xml_lote(file)
        dados_nfe = parse_nfe_xml(xml_str)
        _garantir_nota_inedita_lote(db, dados_nfe)
        fornecedor, _ = buscar_ou_criar_fornecedor_nfe(
            db,
            dados_nfe=dados_nfe,
            current_user=current_user,
            tenant_id=tenant_id,
            somente_ativos=False,
        )
        entrada = salvar_entrada_com_itens(
            db,
            dados_nfe=dados_nfe,
            xml_str=xml_str,
            fornecedor=fornecedor,
            current_user=current_user,
            tenant_id=tenant_id,
            origem_documento="lote",
            campos_xml_obrigatorios=True,
        )
        _marcar_lote_sucesso(resultado, entrada)
    except ValueError as exc:
        resultado["mensagem"] = f"Erro de validacao: {str(exc)}"
        logger.error("Arquivo do lote de notas rejeitado por validacao")
        db.rollback()
    except Exception as exc:
        resultado["mensagem"] = f"Erro ao processar: {str(exc)}"
        logger.exception("Erro inesperado ao processar arquivo do lote de notas")
        db.rollback()

    return resultado


def _resultado_lote_inicial(file: UploadFile, ordem: int) -> dict[str, Any]:
    return {
        "arquivo": file.filename,
        "ordem": ordem,
        "sucesso": False,
        "mensagem": "",
        "nota_id": None,
        "numero_nota": None,
        "fornecedor": None,
        "valor_total": None,
        "produtos_vinculados": None,
        "produtos_nao_vinculados": None,
    }


async def _ler_xml_lote(file: UploadFile) -> str:
    filename = file.filename or ""
    if not filename.lower().endswith(".xml"):
        raise ValueError("Arquivo deve ser .xml")

    xml_content = await file.read()
    return xml_content.decode("utf-8")


def _garantir_nota_inedita_lote(db: Session, dados_nfe: dict[str, Any]) -> None:
    nota_existente = buscar_nota_por_chave(db, dados_nfe["chave_acesso"])
    if nota_existente:
        raise ValueError(f"Nota ja cadastrada (ID: {nota_existente.id})")


def _marcar_lote_sucesso(
    resultado: dict[str, Any],
    entrada: EntradaComItens,
) -> None:
    nota = entrada.nota
    resultado.update(
        {
            "sucesso": True,
            "mensagem": "Processado com sucesso",
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "fornecedor": nota.fornecedor_nome,
            "valor_total": nota.valor_total,
            "produtos_vinculados": entrada.vinculados,
            "produtos_nao_vinculados": entrada.nao_vinculados,
        }
    )
    logger.info("Arquivo do lote de notas processado com sucesso")
