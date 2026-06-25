"""Rotas de parse de PDF/XML da baixa FULL por NF."""

import io
import logging
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..auth.dependencies import get_current_user_and_tenant
from .parsers import _extrair_itens_full_pdf, _parse_saida_full_xml


logger = logging.getLogger(__name__)
router = APIRouter()

try:
    import pdfplumber
except Exception:
    pdfplumber = None


@router.post("/saida-full-pdf/parse")
async def parse_saida_full_pdf(
    file: UploadFile = File(...),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Extrai SKU + quantidade de um PDF para preencher a baixa FULL por NF.
    Nao baixa estoque automaticamente; apenas retorna os itens interpretados.
    """
    if pdfplumber is None:
        raise HTTPException(
            status_code=500,
            detail="Leitura de PDF indisponivel no backend (pdfplumber nao instalado)",
        )

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo PDF nao informado")

    nome = file.filename.lower()
    if not nome.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF valido")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Arquivo PDF vazio")

    try:
        texto_paginas = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                texto_paginas.append(page.extract_text() or "")

        texto = "\n".join(texto_paginas).strip()
        if not texto:
            raise HTTPException(
                status_code=400, detail="Nao foi possivel ler texto do PDF"
            )

        itens = _extrair_itens_full_pdf(texto)
        if not itens:
            raise HTTPException(
                status_code=400,
                detail="Nenhum item SKU+quantidade foi identificado no PDF",
            )

        return {
            "success": True,
            "message": "Itens extraidos do PDF com sucesso",
            "total_itens": len(itens),
            "itens": itens,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao interpretar PDF FULL NF: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao interpretar PDF: {str(e)}"
        )


@router.post("/saida-full-xml/parse")
async def parse_saida_full_xml(
    file: UploadFile = File(...),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Extrai numero da NF e itens (SKU + quantidade) de XML da NF-e.
    Nao baixa estoque automaticamente; apenas preenche o formulario.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo XML nao informado")

    nome = file.filename.lower()
    if not nome.endswith(".xml"):
        raise HTTPException(status_code=400, detail="Envie um arquivo XML valido")

    xml_bytes = await file.read()
    if not xml_bytes:
        raise HTTPException(status_code=400, detail="Arquivo XML vazio")

    try:
        dados = _parse_saida_full_xml(xml_bytes)
        return {
            "success": True,
            "message": "XML lido com sucesso",
            **dados,
        }
    except HTTPException:
        raise
    except ET.ParseError:
        raise HTTPException(status_code=400, detail="XML invalido: erro de estrutura")
    except Exception as e:
        logger.error(f"Erro ao interpretar XML FULL NF: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao interpretar XML: {str(e)}"
        )
