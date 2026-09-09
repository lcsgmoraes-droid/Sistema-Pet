"""Obtencao de documentos oficiais usando a conexao e a nota do tenant."""

from urllib.parse import urlparse

import requests
from fastapi import HTTPException

from app.bling_integration import BlingAPI
from app.nfe.danfe_nfce import gerar_danfe_nfce, validar_xml_nota
from app.nfe_cache_models import BlingNotaFiscalCache
from app.tenancy.context import tenant_context
from app.vendas_models import Venda

HOSTS_DOCUMENTOS = {"bling.com.br", "www.bling.com.br", "api.bling.com.br"}
LIMITE_DOCUMENTO = 10 * 1024 * 1024


def validar_link_documento(url):
    partes = urlparse(str(url or ""))
    if (
        partes.scheme != "https"
        or partes.hostname not in HOSTS_DOCUMENTOS
        or partes.username
        or partes.password
        or partes.port not in (None, 443)
    ):
        raise ValueError("O Bling não retornou um link de documento válido.")
    return url


def baixar_link_documento(url):
    for _ in range(4):
        validar_link_documento(url)
        # Somente hosts oficiais, inclusive em cada redirecionamento.
        with requests.get(
            url, timeout=(5, 30), stream=True, allow_redirects=False
        ) as response:
            if response.is_redirect:
                from urllib.parse import urljoin

                url = urljoin(url, response.headers.get("Location", ""))
                continue
            response.raise_for_status()
            partes, tamanho = [], 0
            for parte in response.iter_content(65536):
                tamanho += len(parte)
                if tamanho > LIMITE_DOCUMENTO:
                    raise ValueError("O documento excedeu o tamanho permitido.")
                partes.append(parte)
            return b"".join(partes)
    raise ValueError("Não foi possível obter o documento no Bling.")


def obter_nota_documento(db, tenant_id, nfe_id):
    registro = (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            BlingNotaFiscalCache.bling_id == str(nfe_id),
        )
        .first()
    )
    venda = (
        db.query(Venda)
        .filter(Venda.tenant_id == tenant_id, Venda.nfe_bling_id == nfe_id)
        .first()
    )
    if not registro and not venda:
        raise HTTPException(404, "Nota não encontrada nesta empresa.")
    modelo = int(registro.modelo if registro else venda.nfe_modelo)
    chave = str(
        (registro.chave if registro else None)
        or (venda.nfe_chave if venda else None)
        or ""
    )
    with tenant_context(tenant_id):
        bling = BlingAPI()
        detalhe = (
            bling.consultar_nfce(nfe_id)
            if modelo == 65
            else bling.consultar_nfe(nfe_id)
        )
    chave_remota = str(detalhe.get("chaveAcesso") or "")
    if (
        not chave_remota
        or (chave and chave != chave_remota)
        or str(detalhe.get("id")) != str(nfe_id)
    ):
        raise ValueError("O documento retornado não corresponde à nota solicitada.")
    return detalhe, modelo, venda


def obter_xml_documento(detalhe, modelo):
    xml = baixar_link_documento(detalhe.get("xml"))
    validar_xml_nota(xml, detalhe["chaveAcesso"], modelo)
    return xml


def obter_pdf_documento(detalhe, modelo):
    if modelo == 65:
        if detalhe.get("situacao") != 5:
            raise HTTPException(
                409, "O PDF desta NFC-e está disponível após a autorização."
            )
        return gerar_danfe_nfce(
            obter_xml_documento(detalhe, modelo), detalhe["chaveAcesso"]
        )
    pdf = baixar_link_documento(detalhe.get("linkPDF"))
    if not pdf.startswith(b"%PDF-"):
        raise ValueError("O Bling não disponibilizou o PDF desta nota.")
    return pdf
