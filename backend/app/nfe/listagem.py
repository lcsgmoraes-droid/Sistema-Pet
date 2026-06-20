"""Helpers de listagem, normalizacao e sincronizacao de NF-e/NFC-e."""

import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime, timedelta
from time import monotonic, sleep

import requests
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.bling_integration import BlingAPI
from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_sync_service import BlingSyncService
from app.services.nfe_cache_service import (
    obter_detalhe_nota_cache,
    obter_estado_cache_notas,
    upsert_nota_cache,
)
from app.utils.logger import logger
from app.vendas_models import Venda

_STATUS_MAP = {
    0: "Pendente",
    1: "Pendente",
    2: "Emitida DANFE",
    4: "Cancelada",
    5: "Autorizada",
    6: "Rejeitada",
    9: "Autorizada",
}

_LOJA_ID_CANAL_MAP = {
    "204647675": "mercado_livre",
    "205367939": "shopee",
    "205639810": "amazon",
}

_REGIME_TRIBUTARIO_MAP = {
    "1": "Simples Nacional",
    "2": "Simples Nacional - excesso de sublimite",
    "3": "Regime Normal",
}

_FINALIDADE_MAP = {
    "1": "NF-e normal",
    "2": "NF-e complementar",
    "3": "NF-e de ajuste",
    "4": "Devolucao / Retorno",
}

_INDICADOR_PRESENCA_MAP = {
    "0": "0 - Nao se aplica",
    "1": "1 - Operacao presencial",
    "2": "2 - Operacao nao presencial, internet",
    "3": "3 - Operacao nao presencial, teleatendimento",
    "4": "4 - NFC-e em operacao com entrega em domicilio",
    "5": "5 - Operacao presencial, fora do estabelecimento",
    "9": "9 - Operacao nao presencial, outros",
}

_XML_NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
_NFE_LIST_CACHE_SECONDS = 45
_NFE_DETAIL_CACHE_SECONDS = 600
_NFE_SYNC_CACHE_TTL_SECONDS = 300
_NFE_SYNC_DEFAULT_LOOKBACK_DAYS = 7
_NFE_SYNC_SAFETY_LOOKBACK_DAYS = 2
_nfe_list_cache: dict[tuple[str, str, str, str], dict] = {}
_nfe_detail_cache: dict[tuple[str, str, str], dict] = {}


def _coerce_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sort_key_nota_por_numero_desc(nota: dict) -> tuple[int, str, int]:
    numero_texto = str(nota.get("numero") or "").strip()
    numero_digits = re.sub(r"\D", "", numero_texto)
    numero_int = _coerce_int(numero_digits, default=-1) if numero_digits else -1
    data_emissao = str(nota.get("data_emissao") or "").strip()
    nota_id = _coerce_int(nota.get("id"), default=-1)
    return (numero_int, data_emissao, nota_id)


def _cache_key_listar_nfes(
    tenant_id, data_inicial: str | None, data_final: str | None, situacao: str | None
) -> tuple[str, str, str, str]:
    return (
        str(tenant_id or ""),
        str(data_inicial or ""),
        str(data_final or ""),
        str((situacao or "")).strip().lower(),
    )


def _cache_key_detalhe_nfe(
    tenant_id, nfe_id: int, modelo: int | None = None
) -> tuple[str, str, str]:
    return (
        str(tenant_id or ""),
        str(nfe_id or ""),
        str(modelo or ""),
    )


def _obter_detalhe_nfe_cache(tenant_id, nfe_id: int, modelo: int | None = None):
    cache_key = _cache_key_detalhe_nfe(tenant_id, nfe_id, modelo)
    cache_atual = _nfe_detail_cache.get(cache_key)
    if not cache_atual:
        return None
    if (monotonic() - cache_atual.get("ts_monotonic", 0)) > _NFE_DETAIL_CACHE_SECONDS:
        _nfe_detail_cache.pop(cache_key, None)
        return None
    return deepcopy(cache_atual.get("payload"))


def _salvar_detalhe_nfe_cache(
    tenant_id, nfe_id: int, modelo: int | None, payload: dict
) -> None:
    _nfe_detail_cache[_cache_key_detalhe_nfe(tenant_id, nfe_id, modelo)] = {
        "ts_monotonic": monotonic(),
        "payload": deepcopy(payload),
    }


def _coerce_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _texto(value) -> str | None:
    if value is None:
        return None
    texto = str(value).strip()
    return texto or None


def _texto_relacionado(value, *keys: str, fallback_to_id: bool = True) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        chaves = keys or (
            "nome",
            "descricao",
            "descricaoPadrao",
            "fantasia",
            "apelido",
            "label",
            "sigla",
            "tipo",
            "endereco",
            "logradouro",
        )
        for chave in chaves:
            texto = _texto(value.get(chave))
            if texto:
                return texto
        identificador = _texto(value.get("id"))
        if fallback_to_id and identificador and identificador != "0":
            return f"ID {identificador}"
        return None
    if isinstance(value, list):
        partes = [_texto_relacionado(item, *keys) for item in value]
        partes = [parte for parte in partes if parte]
        return ", ".join(partes) or None
    return _texto(value)


def _primeiro_preenchido(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _canal_slug(value) -> str:
    texto = str(value or "").strip().lower()
    if not texto:
        return ""

    if (
        any(
            chave in texto
            for chave in ("mercado livre", "mercadolivre", "mercado_livre")
        )
        or texto == "ml"
    ):
        return "mercado_livre"
    if "shopee" in texto:
        return "shopee"
    if "amazon" in texto:
        return "amazon"
    if any(
        chave in texto for chave in ("loja virtual", "ecommerce", "e-commerce", "site")
    ):
        return "site"
    if any(chave in texto for chave in ("app", "aplicativo")):
        return "app"
    if "whatsapp" in texto:
        return "whatsapp"
    if "bling" in texto:
        return "bling"
    return texto.replace(" ", "_")


def _canal_label(slug: str, fallback: str | None = None) -> str | None:
    mapa = {
        "mercado_livre": "Mercado Livre",
        "shopee": "Shopee",
        "amazon": "Amazon",
        "site": "Site",
        "app": "App",
        "whatsapp": "WhatsApp",
        "bling": "Bling",
        "loja_fisica": "Loja fisica",
    }
    return mapa.get(slug) or _texto(fallback) or None


def _digitos(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _extrair_campo_texto(texto: str | None, *padroes: str) -> str | None:
    conteudo = _texto(texto)
    if not conteudo:
        return None
    for padrao in padroes:
        match = re.search(padrao, conteudo, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return _texto(match.group(1))
    return None


def _inferir_canal_por_numero(numero) -> str | None:
    texto = _texto(numero)
    if not texto:
        return None
    if re.fullmatch(r"\d{3}-\d{7}-\d{7}", texto):
        return "amazon"
    if texto.isdigit() and len(texto) >= 14:
        return "mercado_livre"
    if re.search(r"[A-Za-z]", texto) and re.search(r"\d", texto):
        return "shopee"
    return None


def _inferir_canal_por_loja_id(loja_id) -> str | None:
    return _LOJA_ID_CANAL_MAP.get(_texto(loja_id) or "")


def _formatar_endereco(value) -> str | None:
    if isinstance(value, dict):
        logradouro = _texto(
            _primeiro_preenchido(
                value.get("endereco"),
                value.get("logradouro"),
                value.get("descricao"),
                value.get("nome"),
            )
        )
        numero = _texto(value.get("numero"))
        bairro = _texto(value.get("bairro"))
        complemento = _texto(value.get("complemento"))
        municipio = _texto(
            _primeiro_preenchido(value.get("municipio"), value.get("cidade"))
        )
        uf = _texto(_primeiro_preenchido(value.get("uf"), value.get("estado")))

        linha_principal = logradouro or None
        if linha_principal and numero:
            linha_principal = f"{linha_principal}, {numero}"

        linha_secundaria = (
            ", ".join([parte for parte in (bairro, municipio, uf) if parte]) or None
        )
        partes = [
            parte for parte in (linha_principal, complemento, linha_secundaria) if parte
        ]
        return " - ".join(partes) or None

    return _texto(value)


def _texto_generico_baixo_valor(value) -> bool:
    texto = _texto(value)
    if not texto:
        return True
    texto_norm = texto.strip().lower()
    return texto_norm in {
        "outros",
        "outro",
        "online",
        "marketplace",
        "loja virtual",
        "e-commerce",
        "ecommerce",
        "id",
    } or texto_norm.startswith("id ")


def _formatar_data_iso(valor) -> str | None:
    texto = _texto(valor)
    if not texto:
        return None
    texto = texto.replace(" ", "T")
    try:
        return datetime.fromisoformat(texto).isoformat()
    except ValueError:
        return texto


def _detalhe_nota_valido(item: dict | None) -> bool:
    return (
        isinstance(item, dict)
        and bool(item)
        and bool(
            _primeiro_preenchido(
                item.get("id"),
                item.get("numero"),
                item.get("chaveAcesso"),
                item.get("contato"),
                item.get("itens"),
            )
        )
    )


def _tipo_pessoa_label(value, cpf_cnpj: str | None = None) -> str | None:
    texto = _texto(value)
    if texto:
        mapa = {
            "F": "Fisica",
            "J": "Juridica",
            "1": "Fisica",
            "2": "Juridica",
        }
        return mapa.get(texto.upper()) or texto

    numero_documento = _digitos(cpf_cnpj)
    if len(numero_documento) == 11:
        return "Fisica"
    if len(numero_documento) == 14:
        return "Juridica"
    return None


def _separar_data_hora(valor) -> tuple[str | None, str | None]:
    texto = _texto(valor)
    if not texto:
        return None, None

    texto_normalizado = texto
    if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", texto):
        texto_normalizado = texto.replace(" ", "T", 1)

    try:
        dt = datetime.fromisoformat(texto_normalizado)
        return dt.date().isoformat(), dt.strftime("%H:%M:%S")
    except ValueError:
        pass

    match = re.match(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", texto)
    if match:
        return match.group(1), match.group(2)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        return texto, None
    if re.fullmatch(r"\d{2}:\d{2}:\d{2}", texto):
        return None, texto
    return _formatar_data_iso(texto), None


def _label_codigo(mapa: dict[str, str], valor) -> str | None:
    texto = _texto_relacionado(
        valor, "descricao", "nome", "label", fallback_to_id=False
    )
    if texto:
        return texto
    codigo = _texto(
        _primeiro_preenchido(
            _dict(valor).get("valor") if isinstance(valor, dict) else None, valor
        )
    )
    if not codigo:
        return None
    return mapa.get(codigo, codigo)


def _extrair_campos_fiscais_do_xml(xml_texto: str | None) -> dict:
    if not _texto(xml_texto):
        return {}

    root = ET.fromstring(xml_texto)
    ide = root.find(".//nfe:ide", _XML_NS)
    emit = root.find(".//nfe:emit", _XML_NS)

    if ide is None:
        return {}

    data_emissao, hora_emissao = _separar_data_hora(
        ide.findtext("nfe:dhEmi", default="", namespaces=_XML_NS)
    )
    data_saida, hora_saida = _separar_data_hora(
        ide.findtext("nfe:dhSaiEnt", default="", namespaces=_XML_NS)
    )

    return {
        "data_emissao": data_emissao,
        "hora_emissao": hora_emissao,
        "data_saida": data_saida,
        "hora_saida": hora_saida,
        "natureza_operacao": _texto(
            ide.findtext("nfe:natOp", default="", namespaces=_XML_NS)
        ),
        "codigo_regime_tributario": _REGIME_TRIBUTARIO_MAP.get(
            _texto(emit.findtext("nfe:CRT", default="", namespaces=_XML_NS)) or "",
        ),
        "finalidade": _FINALIDADE_MAP.get(
            _texto(ide.findtext("nfe:finNFe", default="", namespaces=_XML_NS)) or "",
        ),
        "indicador_presenca": _INDICADOR_PRESENCA_MAP.get(
            _texto(ide.findtext("nfe:indPres", default="", namespaces=_XML_NS)) or "",
        ),
    }


def _consultar_campos_fiscais_no_xml(xml_url: str | None) -> dict:
    if not _texto(xml_url):
        return {}
    response = requests.get(xml_url, timeout=20)
    response.raise_for_status()
    return _extrair_campos_fiscais_do_xml(response.text)


def _enriquecer_detalhe_com_xml_link(item: dict, detalhe: dict) -> None:
    xml_url = _texto(
        _primeiro_preenchido(item.get("xml"), item.get("urlXml"), item.get("xmlUrl"))
    )
    if not xml_url:
        return

    try:
        campos_xml = _consultar_campos_fiscais_no_xml(xml_url)
    except Exception as exc:
        logger.warning("consultar_nfe", f"Falha ao enriquecer NF via XML: {exc}")
        return

    for campo in ("data_emissao", "hora_emissao", "data_saida", "hora_saida"):
        if campos_xml.get(campo):
            detalhe[campo] = campos_xml[campo]

    if campos_xml.get("natureza_operacao") and (
        not detalhe.get("natureza_operacao")
        or str(detalhe.get("natureza_operacao", "")).startswith("ID ")
    ):
        detalhe["natureza_operacao"] = campos_xml["natureza_operacao"]

    for campo in ("codigo_regime_tributario", "finalidade", "indicador_presenca"):
        if campos_xml.get(campo) and not detalhe.get(campo):
            detalhe[campo] = campos_xml[campo]


def _tipo_nota_label(modelo: int | str | None) -> str:
    return "NFC-e" if str(modelo or "") == "65" else "NF-e"


def _normalizar_resumo_canal(item: dict, venda: Venda | None = None) -> dict:
    loja = _dict(_primeiro_preenchido(item.get("loja"), item.get("lojaVirtual")))
    unidade_negocio = _dict(item.get("unidadeNegocio"))
    marketplace = _dict(item.get("marketplace"))
    info_adicionais = _dict(item.get("informacoesAdicionais"))
    intermediador = _dict(item.get("intermediador"))
    pedido_ref = _dict(
        _primeiro_preenchido(
            item.get("pedido"), item.get("pedidoVenda"), item.get("pedidoCompra")
        )
    )
    loja_nome = _texto_relacionado(loja, fallback_to_id=False)
    unidade_negocio_nome = _texto_relacionado(unidade_negocio, fallback_to_id=False)
    info_complementares = _texto(
        _primeiro_preenchido(
            info_adicionais.get("informacoesComplementares"),
            item.get("informacoesComplementares"),
            item.get("observacao"),
        )
    )
    numero_extraido_texto = _extrair_campo_texto(
        info_complementares,
        r"n[ºo°]?\s*pedido(?:\s*na\s*loja|\s*loja)?\s*:\s*([^\r\n|]+)",
        r"numero\s*loja\s*virtual\s*:\s*([^\r\n|]+)",
    )

    numero_loja_virtual = _texto(
        _primeiro_preenchido(
            item.get("numeroLojaVirtual"),
            item.get("numeroPedidoLoja"),
            item.get("numeroPedido"),
            pedido_ref.get("numeroPedidoLoja"),
            pedido_ref.get("numero"),
            info_adicionais.get("numeroLojaVirtual"),
            info_adicionais.get("numeroPedidoLoja"),
            numero_extraido_texto,
        )
    )
    canal_inferido = _primeiro_preenchido(
        _inferir_canal_por_numero(numero_loja_virtual),
        _inferir_canal_por_loja_id(loja.get("id")),
    )
    canal_inferido_label = _canal_label(canal_inferido)
    origem_loja_virtual = _texto(
        _primeiro_preenchido(
            item.get("origemLojaVirtual"),
            marketplace.get("nome"),
            marketplace.get("descricao"),
            info_adicionais.get("origemLojaVirtual"),
            canal_inferido_label,
            loja_nome,
        )
    )
    if _texto_generico_baixo_valor(origem_loja_virtual) and canal_inferido_label:
        origem_loja_virtual = canal_inferido_label

    origem_canal_venda = _texto(
        _primeiro_preenchido(
            item.get("origemCanalVenda"),
            info_adicionais.get("origemCanalVenda"),
            venda.canal if venda else None,
            canal_inferido_label,
        )
    )
    if _texto_generico_baixo_valor(origem_canal_venda) and canal_inferido_label:
        origem_canal_venda = canal_inferido_label

    canal_base = _primeiro_preenchido(
        origem_canal_venda,
        origem_loja_virtual,
        canal_inferido_label,
        loja_nome,
        venda.canal if venda else None,
    )
    canal = _canal_slug(canal_base)
    canal_label = _canal_label(canal, canal_base)

    return {
        "canal": canal or _texto(venda.canal if venda else None),
        "canal_label": canal_label,
        "loja": {
            "id": loja.get("id"),
            "nome": loja_nome or _texto(venda.loja_origem if venda else None),
        },
        "unidade_negocio": {
            "id": unidade_negocio.get("id"),
            "nome": unidade_negocio_nome,
        },
        "numero_loja_virtual": numero_loja_virtual,
        "origem_loja_virtual": origem_loja_virtual,
        "origem_canal_venda": origem_canal_venda,
        "numero_pedido_loja": numero_loja_virtual,
        "pedido_bling_id_ref": _texto(pedido_ref.get("id")),
        "intermediador": {
            "cnpj": _texto(
                _primeiro_preenchido(
                    intermediador.get("cnpj"), item.get("cnpjIntermediador")
                )
            ),
            "identificacao": _texto(
                _primeiro_preenchido(
                    intermediador.get("identificacao"),
                    intermediador.get("identificacaoIntermediador"),
                    item.get("identificacaoIntermediador"),
                )
            ),
        },
    }


def _normalizar_parcela(item: dict) -> dict:
    parcela = _dict(_primeiro_preenchido(item.get("parcela"), item))
    return {
        "dias": _coerce_int(
            _primeiro_preenchido(parcela.get("dias"), parcela.get("prazo")), 0
        ),
        "data": _texto(
            _primeiro_preenchido(parcela.get("data"), parcela.get("vencimento"))
        ),
        "valor": _coerce_float(
            _primeiro_preenchido(parcela.get("valor"), parcela.get("valorParcela")), 0.0
        ),
        "forma": _texto(
            _primeiro_preenchido(
                parcela.get("forma"),
                parcela.get("formaPagamento"),
                parcela.get("descricaoFormaPagamento"),
            )
        ),
        "observacao": _texto(
            _primeiro_preenchido(parcela.get("observacao"), parcela.get("descricao"))
        ),
    }


def _normalizar_item_nota(item: dict) -> dict:
    produto = _dict(item.get("produto"))
    return {
        "descricao": _texto(
            _primeiro_preenchido(
                item.get("descricao"), item.get("nome"), produto.get("nome")
            )
        ),
        "codigo": _texto(
            _primeiro_preenchido(
                item.get("codigo"),
                item.get("sku"),
                produto.get("codigo"),
                produto.get("id"),
            )
        ),
        "unidade": _texto(
            _primeiro_preenchido(
                item.get("unidade"), item.get("un"), item.get("siglaUnidade")
            )
        ),
        "quantidade": _coerce_float(item.get("quantidade"), 0.0),
        "valor_unitario": _coerce_float(
            _primeiro_preenchido(
                item.get("valor"),
                item.get("valorUnitario"),
                item.get("preco"),
                item.get("precoUnitario"),
            ),
            0.0,
        ),
        "valor_total": _coerce_float(
            _primeiro_preenchido(item.get("total"), item.get("valorTotal")), 0.0
        ),
        "ncm": _texto(
            _primeiro_preenchido(
                item.get("ncm"), item.get("classificacaoFiscal"), produto.get("ncm")
            )
        ),
    }


def _normalizar_detalhe_nota_bling(
    item: dict, modelo: int, venda: Venda | None = None
) -> dict:
    contato = _dict(
        _primeiro_preenchido(
            item.get("contato"), item.get("cliente"), item.get("destinatario")
        )
    )
    contato_endereco = _dict(contato.get("endereco"))
    endereco_entrega = _dict(
        _primeiro_preenchido(item.get("enderecoEntrega"), item.get("entrega"))
    )
    totais = _dict(item.get("totais"))
    transporte = _dict(
        _primeiro_preenchido(item.get("transporte"), item.get("transportador"))
    )
    pagamento = _dict(item.get("pagamento"))
    info_adicionais = _dict(item.get("informacoesAdicionais"))
    intermediador = _dict(item.get("intermediador"))
    resumo_canal = _normalizar_resumo_canal(item, venda=venda)
    pessoas_autorizadas = [
        _texto(
            _primeiro_preenchido(
                autorizada.get("nome"),
                autorizada.get("cpfCnpj"),
                autorizada.get("numeroDocumento"),
                autorizada.get("email"),
            )
        )
        for autorizada in _list(
            _primeiro_preenchido(
                item.get("pessoasAutorizadasAcessarXml"),
                item.get("pessoasAutorizadasXml"),
                item.get("pessoasAutorizadas"),
            )
        )
        if _texto(
            _primeiro_preenchido(
                autorizada.get("nome"),
                autorizada.get("cpfCnpj"),
                autorizada.get("numeroDocumento"),
                autorizada.get("email"),
            )
        )
    ]

    parcelas = [
        _normalizar_parcela(parcela)
        for parcela in _list(
            _primeiro_preenchido(
                pagamento.get("parcelas"),
                item.get("parcelas"),
            )
        )
    ]

    itens = [_normalizar_item_nota(item_nota) for item_nota in _list(item.get("itens"))]

    data_emissao_raw = _primeiro_preenchido(
        item.get("dataEmissao"), item.get("data_emissao")
    )
    data_saida_raw = _primeiro_preenchido(
        item.get("dataSaida"), item.get("dataOperacao"), item.get("data_saida")
    )
    data_emissao, hora_emissao_extra = _separar_data_hora(data_emissao_raw)
    data_saida, hora_saida_extra = _separar_data_hora(data_saida_raw)

    consumidor_final = _primeiro_preenchido(
        item.get("consumidorFinal"),
        contato.get("consumidorFinal"),
    )
    cpf_cnpj = _texto(
        _primeiro_preenchido(
            contato.get("cpf"),
            contato.get("cnpj"),
            contato.get("cpfCnpj"),
            contato.get("numeroDocumento"),
        )
    )

    cliente = {
        "nome": _texto(
            _primeiro_preenchido(
                contato.get("nome"),
                contato.get("descricao"),
                venda.cliente.nome if venda and venda.cliente else None,
            )
        ),
        "tipo_pessoa": _tipo_pessoa_label(
            _primeiro_preenchido(
                contato.get("tipoPessoa"),
                contato.get("tipo"),
                contato.get("tipoDocumento"),
            ),
            cpf_cnpj=cpf_cnpj,
        ),
        "cpf_cnpj": cpf_cnpj,
        "consumidor_final": bool(consumidor_final)
        if consumidor_final is not None
        else None,
        "cep": _texto(
            _primeiro_preenchido(contato.get("cep"), contato_endereco.get("cep"))
        ),
        "uf": _texto(
            _primeiro_preenchido(
                contato.get("uf"),
                contato.get("estado"),
                contato_endereco.get("uf"),
                contato_endereco.get("estado"),
            )
        ),
        "municipio": _texto(
            _primeiro_preenchido(
                contato.get("municipio"),
                contato.get("cidade"),
                contato_endereco.get("municipio"),
                contato_endereco.get("cidade"),
            )
        ),
        "bairro": _texto(
            _primeiro_preenchido(contato.get("bairro"), contato_endereco.get("bairro"))
        ),
        "endereco": _formatar_endereco(
            _primeiro_preenchido(
                contato.get("endereco"), contato.get("logradouro"), contato_endereco
            )
        ),
        "numero": _texto(
            _primeiro_preenchido(contato.get("numero"), contato_endereco.get("numero"))
        ),
        "complemento": _texto(
            _primeiro_preenchido(
                contato.get("complemento"), contato_endereco.get("complemento")
            )
        ),
        "telefone": _texto(
            _primeiro_preenchido(contato.get("telefone"), contato.get("celular"))
        ),
        "email": _texto(contato.get("email")),
        "vendedor": _texto_relacionado(
            _primeiro_preenchido(
                item.get("vendedor"),
                contato.get("vendedor"),
                venda.vendedor.nome if venda and venda.vendedor else None,
            ),
            "nome",
            "descricao",
            "apelido",
        ),
    }

    return {
        "id": str(item.get("id", "")),
        "venda_id": venda.id if venda else None,
        "numero": _texto(item.get("numero")),
        "serie": _texto(item.get("serie")),
        "modelo": int(modelo),
        "tipo": "nfce" if int(modelo) == 65 else "nfe",
        "tipo_label": _tipo_nota_label(modelo),
        "chave": _texto(
            _primeiro_preenchido(item.get("chaveAcesso"), item.get("chave"))
        ),
        "status": _status_nota_bling(item),
        "data_emissao": data_emissao or _formatar_data_iso(data_emissao_raw),
        "hora_emissao": _texto(
            _primeiro_preenchido(
                item.get("horaEmissao"), item.get("hora_emissao"), hora_emissao_extra
            )
        ),
        "data_saida": data_saida or _formatar_data_iso(data_saida_raw),
        "hora_saida": _texto(
            _primeiro_preenchido(
                item.get("horaSaida"),
                item.get("horaOperacao"),
                item.get("hora_saida"),
                hora_saida_extra,
            )
        ),
        "natureza_operacao": _texto(
            _primeiro_preenchido(
                _texto_relacionado(
                    item.get("naturezaOperacao"), "nome", "descricao", "descricaoPadrao"
                ),
                item.get("naturezaOperacaoDescricao"),
            )
        ),
        "codigo_regime_tributario": _texto(
            _primeiro_preenchido(
                _label_codigo(
                    _REGIME_TRIBUTARIO_MAP, item.get("codigoRegimeTributario")
                ),
                _label_codigo(_REGIME_TRIBUTARIO_MAP, item.get("regimeTributario")),
            )
        ),
        "finalidade": _texto(
            _primeiro_preenchido(
                _label_codigo(_FINALIDADE_MAP, item.get("finalidade")),
                item.get("finalidade"),
            )
        ),
        "indicador_presenca": _texto(
            _primeiro_preenchido(
                _label_codigo(_INDICADOR_PRESENCA_MAP, item.get("indicadorPresenca")),
                item.get("indicadorPresenca"),
            )
        ),
        "cliente": cliente,
        "itens": itens,
        "totais": {
            "valor_produtos": _coerce_float(
                _primeiro_preenchido(
                    totais.get("valorProdutos"), item.get("valorProdutos")
                ),
                0.0,
            ),
            "valor_frete": _coerce_float(
                _primeiro_preenchido(totais.get("valorFrete"), item.get("valorFrete")),
                0.0,
            ),
            "valor_seguro": _coerce_float(
                _primeiro_preenchido(
                    totais.get("valorSeguro"), item.get("valorSeguro")
                ),
                0.0,
            ),
            "outras_despesas": _coerce_float(
                _primeiro_preenchido(
                    totais.get("outrasDespesas"), item.get("outrasDespesas")
                ),
                0.0,
            ),
            "valor_desconto": _coerce_float(
                _primeiro_preenchido(
                    totais.get("valorDesconto"), item.get("valorDesconto")
                ),
                0.0,
            ),
            "valor_total": _extrair_valor_nota(item),
        },
        "transporte": {
            "tipo": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(transporte.get("tipo")),
                    _texto_relacionado(transporte.get("modalidade")),
                )
            ),
            "frete_por_conta": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(transporte.get("fretePorConta")),
                    _texto_relacionado(item.get("fretePorConta")),
                )
            ),
        },
        "endereco_entrega": {
            "nome": _texto(
                _primeiro_preenchido(endereco_entrega.get("nome"), contato.get("nome"))
            ),
            "cep": _texto(endereco_entrega.get("cep")),
            "uf": _texto(
                _primeiro_preenchido(
                    endereco_entrega.get("uf"), endereco_entrega.get("estado")
                )
            ),
            "municipio": _texto(
                _primeiro_preenchido(
                    endereco_entrega.get("municipio"), endereco_entrega.get("cidade")
                )
            ),
            "bairro": _texto(endereco_entrega.get("bairro")),
            "endereco": _formatar_endereco(
                _primeiro_preenchido(
                    endereco_entrega.get("endereco"),
                    endereco_entrega.get("logradouro"),
                    endereco_entrega,
                )
            ),
            "numero": _texto(endereco_entrega.get("numero")),
            "complemento": _texto(endereco_entrega.get("complemento")),
        },
        "pagamento": {
            "condicao": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(pagamento.get("condicaoPagamento")),
                    _texto_relacionado(pagamento.get("descricaoCondicaoPagamento")),
                    item.get("condicaoPagamento"),
                )
            ),
            "categoria": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(pagamento.get("categoria")),
                    _texto_relacionado(item.get("categoria")),
                )
            ),
            "parcelas": parcelas,
        },
        "intermediador": {
            "ativo": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(intermediador.get("tipo")),
                    _texto_relacionado(intermediador.get("ativo")),
                )
            ),
            "cnpj": _texto(
                _primeiro_preenchido(
                    intermediador.get("cnpj"),
                    resumo_canal.get("intermediador", {}).get("cnpj"),
                )
            ),
            "identificacao": _texto(
                _primeiro_preenchido(
                    intermediador.get("identificacao"),
                    intermediador.get("identificacaoIntermediador"),
                    resumo_canal.get("intermediador", {}).get("identificacao"),
                )
            ),
        },
        "informacoes_adicionais": {
            "numero_loja_virtual": resumo_canal.get("numero_loja_virtual"),
            "origem_loja_virtual": resumo_canal.get("origem_loja_virtual"),
            "origem_canal_venda": resumo_canal.get("origem_canal_venda"),
            "numero_pedido_loja": resumo_canal.get("numero_pedido_loja"),
            "informacoes_complementares": _texto(
                _primeiro_preenchido(
                    info_adicionais.get("informacoesComplementares"),
                    item.get("informacoesComplementares"),
                )
            ),
            "informacoes_fisco": _texto(
                _primeiro_preenchido(
                    info_adicionais.get("informacoesAdicionaisInteresseFisco"),
                    info_adicionais.get("informacoesInteresseFisco"),
                    item.get("informacoesAdicionaisInteresseFisco"),
                )
            ),
        },
        "pessoas_autorizadas_xml": pessoas_autorizadas,
        "canal": resumo_canal.get("canal"),
        "canal_label": resumo_canal.get("canal_label"),
        "loja": resumo_canal.get("loja"),
        "unidade_negocio": resumo_canal.get("unidade_negocio"),
        "origem": "bling",
    }


def _consultar_detalhe_nota_bling(
    bling: BlingAPI,
    db: Session,
    tenant_id,
    nfe_id: int,
    *,
    modelo: int | None = None,
) -> tuple[dict, int, Venda | None]:
    venda = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.nfe_bling_id == nfe_id,
        )
        .first()
    )

    modelos_tentativa: list[int] = []
    if str(modelo or "") == "65":
        modelos_tentativa.append(65)
    elif str(modelo or "") == "55":
        modelos_tentativa.append(55)

    if venda and str(getattr(venda, "nfe_modelo", "") or "") in {"55", "65"}:
        modelos_tentativa.append(int(str(venda.nfe_modelo)))

    modelos_tentativa.extend([55, 65])

    erros: list[str] = []
    usados: set[int] = set()

    for modelo_atual in modelos_tentativa:
        if modelo_atual in usados:
            continue
        usados.add(modelo_atual)
        detalhe_cache = _obter_detalhe_nfe_cache(tenant_id, nfe_id, modelo_atual)
        if not _detalhe_nota_valido(detalhe_cache):
            detalhe_cache = obter_detalhe_nota_cache(
                db=db,
                tenant_id=tenant_id,
                nfe_id=nfe_id,
                modelo=modelo_atual,
            )
        if _detalhe_nota_valido(detalhe_cache):
            return detalhe_cache, modelo_atual, venda
        try:
            detalhe = (
                bling.consultar_nfce(nfe_id)
                if modelo_atual == 65
                else bling.consultar_nfe(nfe_id)
            )
            if _detalhe_nota_valido(detalhe):
                _salvar_detalhe_nfe_cache(tenant_id, nfe_id, modelo_atual, detalhe)
                upsert_nota_cache(
                    db,
                    tenant_id,
                    _normalizar_nota_bling(detalhe, modelo_atual),
                    source="bling_detail",
                    resumo_payload=detalhe,
                    detalhe_payload=detalhe,
                )
                db.commit()
                return detalhe, modelo_atual, venda
        except Exception as exc:
            erros.append(str(exc))

    detalhe_venda = {
        "id": nfe_id,
        "numero": venda.nfe_numero if venda else None,
        "serie": venda.nfe_serie if venda else None,
        "chaveAcesso": venda.nfe_chave if venda else None,
        "situacao": {"descricao": venda.nfe_status}
        if venda and venda.nfe_status
        else None,
        "dataEmissao": venda.nfe_data_emissao.isoformat()
        if venda and venda.nfe_data_emissao
        else None,
        "contato": {
            "nome": venda.cliente.nome if venda and venda.cliente else None,
            "cpfCnpj": (venda.cliente.cpf or venda.cliente.cnpj)
            if venda and venda.cliente
            else None,
        },
        "totais": {
            "valorTotal": float(venda.total or 0) if venda else 0,
        },
    }
    if venda and _detalhe_nota_valido(detalhe_venda):
        modelo_venda = 65 if _venda_usa_nfce(venda) else 55
        return detalhe_venda, modelo_venda, venda

    raise HTTPException(
        status_code=404,
        detail="Nao foi possivel consultar os detalhes desta nota no Bling."
        + (f" Ultimos erros: {' | '.join(erros[:2])}" if erros else ""),
    )


def _situacao_num(val) -> int:
    """Extrai o código real da situação retornada pelo Bling."""
    if isinstance(val, dict):
        if "valor" in val:
            return _coerce_int(val.get("valor"), 0)
        if "id" in val:
            return _coerce_int(val.get("id"), 0)
        return 0
    return _coerce_int(val, 0)


def _texto_situacao(val) -> str:
    if not isinstance(val, dict):
        return ""

    for chave in ("descricao", "descricaoSituacao", "nome", "label"):
        texto = str(val.get(chave) or "").strip()
        if texto:
            return texto.lower()
    return ""


def _status_nota_bling(item: dict) -> str:
    situacao = item.get("situacao")
    situacao_txt = _texto_situacao(situacao)
    chave = str(item.get("chaveAcesso") or item.get("chave") or "").strip()
    sit_num = _situacao_num(situacao)

    if "cancel" in situacao_txt:
        return "Cancelada"
    if "rejeit" in situacao_txt:
        return "Rejeitada"
    if "deneg" in situacao_txt:
        return "Denegada"
    if "inutil" in situacao_txt:
        return "Inutilizada"
    if "autoriz" in situacao_txt:
        return "Autorizada"
    if "emit" in situacao_txt and not chave:
        return "Emitida DANFE"
    if "pend" in situacao_txt:
        return "Pendente"

    if sit_num == 4:
        return "Cancelada"
    if sit_num == 6:
        return "Rejeitada"
    if sit_num == 2 and not chave:
        return "Emitida DANFE"
    if sit_num in {2, 5, 9}:
        return "Autorizada"
    if sit_num == 1 and chave:
        return "Autorizada"

    return _STATUS_MAP.get(sit_num, "Pendente")


def _nota_autorizada_bling(item: dict) -> bool:
    return _status_nota_bling(item) == "Autorizada"


def _nota_cancelada_bling(item: dict) -> bool:
    return _status_nota_bling(item) == "Cancelada"


def _venda_usa_nfce(venda: Venda) -> bool:
    tipo = str(getattr(venda, "nfe_tipo", "") or "").strip().lower()
    modelo = str(getattr(venda, "nfe_modelo", "") or "").strip()
    return tipo in {"nfce", "1"} or modelo == "65"


def _extrair_valor_nota(item: dict) -> float:
    totais = item.get("totais") or {}
    pagamento = _dict(item.get("pagamento"))
    candidatos = (
        item.get("valorNota"),
        item.get("valorNotaNf"),
        item.get("valorTotalNf"),
        item.get("valorTotal"),
        item.get("valor_total"),
        item.get("total"),
        item.get("valor"),
        totais.get("valorTotal"),
        totais.get("valor_total"),
        totais.get("total"),
    )
    for valor in candidatos:
        try:
            if valor is None or valor == "":
                continue
            return float(valor)
        except (TypeError, ValueError):
            continue

    parcelas = _list(
        _primeiro_preenchido(pagamento.get("parcelas"), item.get("parcelas"))
    )
    if parcelas:
        total_parcelas = 0.0
        encontrou_parcela = False
        for parcela in parcelas:
            valor = _coerce_float(
                _primeiro_preenchido(
                    _dict(parcela).get("valor"), _dict(parcela).get("valorParcela")
                ),
                None,
            )
            if valor is None:
                continue
            total_parcelas += valor
            encontrou_parcela = True
        if encontrou_parcela:
            return total_parcelas

    valor_produtos = _coerce_float(
        _primeiro_preenchido(totais.get("valorProdutos"), item.get("valorProdutos")),
        None,
    )
    valor_frete = _coerce_float(
        _primeiro_preenchido(totais.get("valorFrete"), item.get("valorFrete")), 0.0
    )
    valor_seguro = _coerce_float(
        _primeiro_preenchido(totais.get("valorSeguro"), item.get("valorSeguro")), 0.0
    )
    outras_despesas = _coerce_float(
        _primeiro_preenchido(totais.get("outrasDespesas"), item.get("outrasDespesas")),
        0.0,
    )
    valor_desconto = _coerce_float(
        _primeiro_preenchido(totais.get("valorDesconto"), item.get("valorDesconto")),
        0.0,
    )
    if valor_produtos is not None:
        return max(
            valor_produtos
            + valor_frete
            + valor_seguro
            + outras_despesas
            - valor_desconto,
            0.0,
        )
    return 0.0


def _identificadores_pedido_integrado(pedido: PedidoIntegrado) -> set[str]:
    payload = _dict(pedido.payload)
    pedido_payload = _dict(_primeiro_preenchido(payload.get("pedido"), payload))
    ultima_nf = _dict(
        _primeiro_preenchido(
            payload.get("ultima_nf"),
            pedido_payload.get("notaFiscal"),
            pedido_payload.get("nota"),
            pedido_payload.get("nfe"),
        )
    )
    identificadores = {
        _texto(pedido.pedido_bling_id),
        _texto(pedido.pedido_bling_numero),
        _texto(
            _primeiro_preenchido(
                pedido_payload.get("numeroPedidoLoja"),
                pedido_payload.get("numeroLoja"),
                pedido_payload.get("numeroPedido"),
                pedido_payload.get("numero"),
            )
        ),
        _texto(_primeiro_preenchido(ultima_nf.get("id"), ultima_nf.get("nfe_id"))),
        _texto(ultima_nf.get("numero")),
    }
    return {identificador for identificador in identificadores if identificador}


def _extrair_total_pedido_integrado(pedido: PedidoIntegrado) -> float:
    payload = _dict(pedido.payload)
    pedido_payload = _dict(_primeiro_preenchido(payload.get("pedido"), payload))
    ultima_nf = _dict(
        _primeiro_preenchido(
            payload.get("ultima_nf"),
            pedido_payload.get("notaFiscal"),
            pedido_payload.get("nota"),
            pedido_payload.get("nfe"),
        )
    )
    totais = _dict(
        _primeiro_preenchido(
            pedido_payload.get("totais"),
            pedido_payload.get("financeiro"),
            payload.get("totais"),
        )
    )

    valor_total = _extrair_valor_nota(ultima_nf)
    if valor_total > 0:
        return valor_total

    valor_total = _coerce_float(
        _primeiro_preenchido(
            pedido_payload.get("total"),
            pedido_payload.get("valorTotal"),
            pedido_payload.get("valor_total"),
            totais.get("valorTotal"),
            totais.get("total"),
        ),
        0.0,
    )
    if valor_total > 0:
        return valor_total

    itens = _list(
        _primeiro_preenchido(pedido_payload.get("itens"), payload.get("itens"))
    )
    total_itens = 0.0
    encontrou_item = False
    for item in itens:
        item_dict = _dict(_primeiro_preenchido(item.get("item"), item))
        quantidade = _coerce_float(
            _primeiro_preenchido(item_dict.get("quantidade"), item.get("quantidade")),
            0.0,
        )
        total_item = _coerce_float(
            _primeiro_preenchido(
                item_dict.get("total"),
                item_dict.get("valorTotal"),
                item.get("total"),
                item.get("valorTotal"),
            ),
            None,
        )
        if total_item is None:
            valor_unitario = _coerce_float(
                _primeiro_preenchido(
                    item_dict.get("valor"),
                    item_dict.get("preco"),
                    item.get("valor"),
                    item.get("preco"),
                ),
                0.0,
            )
            desconto_item = _coerce_float(
                _primeiro_preenchido(
                    item_dict.get("desconto"),
                    item.get("desconto"),
                    item_dict.get("valorDesconto"),
                    item.get("valorDesconto"),
                ),
                0.0,
            )
            total_item = max((valor_unitario * quantidade) - desconto_item, 0.0)
        if total_item > 0:
            encontrou_item = True
            total_itens += total_item

    if encontrou_item:
        frete = _coerce_float(
            _primeiro_preenchido(
                pedido_payload.get("frete"),
                _dict(pedido_payload.get("transporte")).get("frete"),
                totais.get("valorFrete"),
            ),
            0.0,
        )
        desconto = _coerce_float(
            _primeiro_preenchido(
                pedido_payload.get("desconto"),
                pedido_payload.get("valorDesconto"),
                totais.get("valorDesconto"),
            ),
            0.0,
        )
        return max(total_itens + frete - desconto, 0.0)

    return 0.0


def _resumo_pedido_integrado(pedido: PedidoIntegrado) -> dict:
    payload = _dict(pedido.payload)
    pedido_payload = _dict(_primeiro_preenchido(payload.get("pedido"), payload))
    loja = _dict(pedido_payload.get("loja"))
    marketplace = _dict(pedido_payload.get("marketplace"))
    loja_nome = _texto_relacionado(loja, fallback_to_id=False)
    canal_base = _primeiro_preenchido(
        pedido_payload.get("canal"),
        pedido_payload.get("origem"),
        marketplace.get("nome"),
        marketplace.get("descricao"),
        loja_nome,
        pedido.canal,
    )
    canal = _canal_slug(canal_base)
    return {
        "canal": canal or _texto(pedido.canal),
        "canal_label": _canal_label(canal, canal_base),
        "valor_total": _extrair_total_pedido_integrado(pedido),
        "loja": {
            "id": loja.get("id"),
            "nome": loja_nome,
        },
        "numero_loja_virtual": _texto(
            _primeiro_preenchido(
                pedido_payload.get("numeroPedidoLoja"),
                pedido_payload.get("numeroLoja"),
                pedido_payload.get("numeroPedido"),
                pedido_payload.get("numero"),
            )
        ),
        "numero_pedido_loja": _texto(
            _primeiro_preenchido(
                pedido_payload.get("numeroPedidoLoja"),
                pedido_payload.get("numeroLoja"),
                pedido_payload.get("numeroPedido"),
                pedido_payload.get("numero"),
            )
        ),
        "origem_loja_virtual": _texto(
            _primeiro_preenchido(
                pedido_payload.get("origemLojaVirtual"),
                marketplace.get("nome"),
                marketplace.get("descricao"),
                loja_nome,
            )
        ),
        "origem_canal_venda": _texto(
            _primeiro_preenchido(
                pedido_payload.get("origemCanalVenda"),
                marketplace.get("nome"),
                marketplace.get("descricao"),
                _canal_label(canal, canal_base),
            )
        ),
    }


def _parse_data_referencia(value) -> datetime | None:
    texto = _texto(value)
    if not texto:
        return None

    candidatos = [
        texto,
        texto.replace("Z", "+00:00"),
        texto.split("T")[0],
    ]
    for candidato in candidatos:
        try:
            return datetime.fromisoformat(candidato)
        except ValueError:
            continue

    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto[:10], formato)
        except ValueError:
            continue
    return None


def _formatar_data_param_bling(value) -> str | None:
    data_ref = _parse_data_referencia(value)
    return data_ref.date().isoformat() if data_ref else None


def _planejar_sincronizacao_bling_nfes(
    *,
    force_refresh: bool,
    data_inicial: str | None,
    data_final: str | None,
    cache_total: int,
    cache_intervalo_tem_dados: bool,
    ultimo_sync: datetime | None,
    ultima_data_emissao: datetime | None,
    agora: datetime | None = None,
) -> tuple[bool, str | None, str | None, str]:
    agora_ref = agora or datetime.now()
    data_final_sync = (
        _formatar_data_param_bling(data_final) or agora_ref.date().isoformat()
    )
    data_inicial_sync = _formatar_data_param_bling(data_inicial)
    cache_stale = (
        force_refresh
        or not ultimo_sync
        or (agora_ref - ultimo_sync).total_seconds() > _NFE_SYNC_CACHE_TTL_SECONDS
    )

    if data_inicial or data_final:
        if force_refresh or not cache_intervalo_tem_dados or cache_stale:
            return True, data_inicial_sync, data_final_sync, "intervalo_especifico"
        return False, None, None, "cache_intervalo_recente"

    if cache_total <= 0:
        return (
            True,
            (agora_ref - timedelta(days=_NFE_SYNC_DEFAULT_LOOKBACK_DAYS))
            .date()
            .isoformat(),
            data_final_sync,
            "bootstrap_cache_vazio",
        )

    if not cache_stale:
        return False, None, None, "cache_global_recente"

    base_data = ultima_data_emissao or agora_ref
    janela_inicial = max(
        (base_data - timedelta(days=_NFE_SYNC_SAFETY_LOOKBACK_DAYS)).date(),
        (agora_ref - timedelta(days=_NFE_SYNC_DEFAULT_LOOKBACK_DAYS)).date(),
    )
    return (
        True,
        janela_inicial.isoformat(),
        data_final_sync,
        "janela_incremental_recente",
    )


def _status_local_ultima_nf(ultima_nf: dict) -> str:
    situacao_textual = _texto(
        _primeiro_preenchido(ultima_nf.get("situacao"), ultima_nf.get("status"))
    )
    if situacao_textual:
        if situacao_textual.isdigit():
            return _STATUS_MAP.get(_coerce_int(situacao_textual, 0), situacao_textual)
        return situacao_textual

    situacao_codigo = _coerce_int(ultima_nf.get("situacao_codigo"), 0)
    return _STATUS_MAP.get(situacao_codigo, "Pendente")


def _normalizar_nota_pedido_integrado(pedido: PedidoIntegrado) -> dict | None:
    payload = _dict(pedido.payload)
    pedido_payload = _dict(_primeiro_preenchido(payload.get("pedido"), payload))
    ultima_nf = _dict(
        _primeiro_preenchido(
            payload.get("ultima_nf"),
            pedido_payload.get("notaFiscal"),
            pedido_payload.get("nota"),
            pedido_payload.get("nfe"),
        )
    )
    resumo = _resumo_pedido_integrado(pedido)
    contato = _dict(
        _primeiro_preenchido(
            pedido_payload.get("contato"), pedido_payload.get("cliente")
        )
    )

    nf_bling_id = _texto(
        _primeiro_preenchido(ultima_nf.get("id"), ultima_nf.get("nfe_id"))
    )
    if nf_bling_id in {"-1", "0"}:
        nf_bling_id = None
    nf_numero = _texto(ultima_nf.get("numero"))

    if not nf_bling_id and not nf_numero:
        return None

    data_emissao = _primeiro_preenchido(
        ultima_nf.get("dataEmissao"),
        ultima_nf.get("data_emissao"),
        ultima_nf.get("dataEmissaoNf"),
        ultima_nf.get("data"),
        pedido.updated_at.isoformat() if getattr(pedido, "updated_at", None) else None,
        pedido.created_at.isoformat() if getattr(pedido, "created_at", None) else None,
    )

    return {
        "id": str(nf_bling_id or ""),
        "venda_id": None,
        "numero": nf_numero,
        "serie": _texto(ultima_nf.get("serie")),
        "tipo": "nfe",
        "tipo_codigo": 0,
        "modelo": 55,
        "chave": _texto(
            _primeiro_preenchido(ultima_nf.get("chave"), ultima_nf.get("chaveAcesso"))
        ),
        "status": _status_local_ultima_nf(ultima_nf),
        "data_emissao": data_emissao,
        "valor": _coerce_float(
            _primeiro_preenchido(
                ultima_nf.get("valor_total"), resumo.get("valor_total")
            ),
            0.0,
        ),
        "cliente": {
            "id": contato.get("id"),
            "nome": _texto_relacionado(contato, fallback_to_id=False),
            "cpf_cnpj": _texto(
                _primeiro_preenchido(
                    contato.get("cpf"), contato.get("cnpj"), contato.get("cpfCnpj")
                )
            ),
        },
        "canal": resumo.get("canal"),
        "canal_label": resumo.get("canal_label"),
        "loja": resumo.get("loja"),
        "unidade_negocio": {"id": None, "nome": None},
        "numero_loja_virtual": resumo.get("numero_loja_virtual"),
        "origem_loja_virtual": resumo.get("origem_loja_virtual"),
        "origem_canal_venda": resumo.get("origem_canal_venda"),
        "numero_pedido_loja": resumo.get("numero_pedido_loja"),
        "pedido_bling_id_ref": _texto(pedido.pedido_bling_id),
        "origem": "pedido_integrado",
    }


def _adicionar_notas_de_pedidos_integrados(
    db: Session,
    tenant_id,
    notas: list[dict],
    *,
    situacao: str | None = None,
    data_inicial: str | None = None,
    data_final: str | None = None,
    limite_scan: int = 3000,
) -> None:
    pedidos = (
        db.query(PedidoIntegrado)
        .filter(PedidoIntegrado.tenant_id == tenant_id)
        .order_by(PedidoIntegrado.updated_at.desc(), PedidoIntegrado.created_at.desc())
        .limit(limite_scan)
        .all()
    )

    data_inicial_ref = _parse_data_referencia(data_inicial)
    data_final_ref = _parse_data_referencia(data_final)
    chaves_existentes = {
        (
            _texto(nota.get("id")) or "",
            _texto(nota.get("numero")) or "",
        )
        for nota in notas
    }

    for pedido in pedidos:
        nota = _normalizar_nota_pedido_integrado(pedido)
        if not nota:
            continue

        chave_nota = (
            _texto(nota.get("id")) or "",
            _texto(nota.get("numero")) or "",
        )
        if chave_nota in chaves_existentes:
            continue

        if situacao and str(nota.get("status") or "").lower() != situacao.lower():
            continue

        data_nota = _parse_data_referencia(nota.get("data_emissao"))
        if (
            data_inicial_ref
            and data_nota
            and data_nota.date() < data_inicial_ref.date()
        ):
            continue
        if data_final_ref and data_nota and data_nota.date() > data_final_ref.date():
            continue

        notas.append(nota)
        chaves_existentes.add(chave_nota)


def _enriquecer_notas_com_pedidos_integrados(
    db: Session, tenant_id, notas: list[dict], limite_scan: int = 3000
) -> None:
    identificadores_desejados: set[str] = set()
    for nota in notas:
        for identificador in (
            _texto(nota.get("pedido_bling_id_ref")),
            _texto(nota.get("numero_pedido_loja")),
            _texto(nota.get("numero_loja_virtual")),
            _texto(nota.get("id")),
            _texto(nota.get("numero")),
        ):
            if identificador:
                identificadores_desejados.add(identificador)

    if not identificadores_desejados:
        return

    pedidos = (
        db.query(PedidoIntegrado)
        .filter(PedidoIntegrado.tenant_id == tenant_id)
        .order_by(PedidoIntegrado.created_at.desc())
        .limit(limite_scan)
        .all()
    )

    mapa_identificadores: dict[str, dict] = {}
    for pedido in pedidos:
        resumo = _resumo_pedido_integrado(pedido)
        for identificador in _identificadores_pedido_integrado(pedido):
            if identificador and identificador not in mapa_identificadores:
                mapa_identificadores[identificador] = resumo

    for nota in notas:
        candidatos = [
            _texto(nota.get("pedido_bling_id_ref")),
            _texto(nota.get("numero_pedido_loja")),
            _texto(nota.get("numero_loja_virtual")),
            _texto(nota.get("id")),
            _texto(nota.get("numero")),
        ]
        contexto = next(
            (
                mapa_identificadores.get(candidato)
                for candidato in candidatos
                if candidato and mapa_identificadores.get(candidato)
            ),
            None,
        )
        if not contexto:
            continue

        nota["canal"] = nota.get("canal") or contexto.get("canal")
        nota["canal_label"] = nota.get("canal_label") or contexto.get("canal_label")
        loja_atual = nota.get("loja") if isinstance(nota.get("loja"), dict) else {}
        if not loja_atual.get("nome"):
            nota["loja"] = contexto.get("loja")
        if not nota.get("valor") and contexto.get("valor_total"):
            nota["valor"] = float(contexto.get("valor_total") or 0)
        nota["numero_loja_virtual"] = nota.get("numero_loja_virtual") or contexto.get(
            "numero_loja_virtual"
        )
        nota["origem_loja_virtual"] = nota.get("origem_loja_virtual") or contexto.get(
            "origem_loja_virtual"
        )
        nota["origem_canal_venda"] = nota.get("origem_canal_venda") or contexto.get(
            "origem_canal_venda"
        )
        nota["numero_pedido_loja"] = nota.get("numero_pedido_loja") or contexto.get(
            "numero_pedido_loja"
        )


def _normalizar_nota_bling(item: dict, modelo: int) -> dict:
    contato = item.get("contato") or {}
    resumo_canal = _normalizar_resumo_canal(item)
    return {
        "id": str(item.get("id", "")),
        "venda_id": None,
        "numero": str(item.get("numero", "")),
        "serie": str(item.get("serie", "")),
        "tipo": "nfce" if modelo == 65 else "nfe",
        "tipo_codigo": 1 if modelo == 65 else 0,
        "modelo": modelo,
        "chave": item.get("chaveAcesso") or "",
        "status": _status_nota_bling(item),
        "data_emissao": item.get("dataEmissao") or item.get("data_emissao"),
        "valor": _extrair_valor_nota(item),
        "cliente": {
            "id": contato.get("id"),
            "nome": contato.get("nome") or contato.get("descricao"),
            "cpf_cnpj": contato.get("cpf")
            or contato.get("cnpj")
            or contato.get("cpfCnpj"),
        },
        "canal": resumo_canal.get("canal"),
        "canal_label": resumo_canal.get("canal_label"),
        "loja": resumo_canal.get("loja"),
        "unidade_negocio": resumo_canal.get("unidade_negocio"),
        "numero_loja_virtual": resumo_canal.get("numero_loja_virtual"),
        "origem_loja_virtual": resumo_canal.get("origem_loja_virtual"),
        "origem_canal_venda": resumo_canal.get("origem_canal_venda"),
        "numero_pedido_loja": resumo_canal.get("numero_pedido_loja"),
        "pedido_bling_id_ref": resumo_canal.get("pedido_bling_id_ref"),
        "origem": "bling",
    }


def _normalizar_nota_venda_local(venda: Venda) -> dict:
    canal_slug = _canal_slug(venda.canal)
    return {
        "id": str(venda.nfe_bling_id),
        "venda_id": venda.id,
        "numero": venda.nfe_numero,
        "serie": venda.nfe_serie,
        "tipo": "nfce" if _venda_usa_nfce(venda) else "nfe",
        "tipo_codigo": 1 if _venda_usa_nfce(venda) else 0,
        "modelo": _coerce_int(venda.nfe_modelo, 65 if _venda_usa_nfce(venda) else 55),
        "chave": venda.nfe_chave,
        "status": venda.nfe_status or "Pendente",
        "data_emissao": venda.nfe_data_emissao.isoformat()
        if venda.nfe_data_emissao
        else None,
        "valor": float(venda.total or 0),
        "cliente": {
            "id": venda.cliente.id if venda.cliente else None,
            "nome": venda.cliente.nome if venda.cliente else None,
            "cpf_cnpj": (venda.cliente.cpf or venda.cliente.cnpj)
            if venda.cliente
            else None,
        },
        "canal": _texto(venda.canal),
        "canal_label": _canal_label(canal_slug, venda.canal),
        "loja": {
            "id": None,
            "nome": _texto(venda.loja_origem),
        },
        "unidade_negocio": {
            "id": None,
            "nome": None,
        },
        "numero_loja_virtual": None,
        "origem_loja_virtual": None,
        "origem_canal_venda": _texto(venda.canal),
        "numero_pedido_loja": _texto(venda.numero_venda),
        "origem": "local",
    }


def _sincronizar_vendas_em_cache(
    db: Session,
    tenant_id,
    *,
    desde: datetime | None = None,
) -> None:
    query = db.query(Venda).filter(
        Venda.tenant_id == tenant_id,
        Venda.nfe_bling_id.isnot(None),
    )
    if desde:
        query = query.filter(
            or_(
                Venda.updated_at >= desde,
                Venda.nfe_data_emissao >= desde,
            )
        )

    for venda in query.order_by(
        Venda.updated_at.desc(), Venda.nfe_data_emissao.desc()
    ).all():
        upsert_nota_cache(
            db,
            tenant_id,
            _normalizar_nota_venda_local(venda),
            source="local_venda",
        )


def _sincronizar_pedidos_integrados_em_cache(
    db: Session,
    tenant_id,
    *,
    desde: datetime | None = None,
    limite_scan: int = 2000,
) -> None:
    query = db.query(PedidoIntegrado).filter(PedidoIntegrado.tenant_id == tenant_id)
    if desde:
        query = query.filter(PedidoIntegrado.updated_at >= desde)

    pedidos = (
        query.order_by(
            PedidoIntegrado.updated_at.desc(), PedidoIntegrado.created_at.desc()
        )
        .limit(limite_scan)
        .all()
    )
    for pedido in pedidos:
        nota = _normalizar_nota_pedido_integrado(pedido)
        if not nota or not _texto(nota.get("id")):
            continue
        upsert_nota_cache(
            db,
            tenant_id,
            nota,
            source="pedido_integrado",
            resumo_payload=_dict(pedido.payload),
        )


def _sincronizar_fontes_locais_nfe_em_cache(
    db: Session,
    tenant_id,
    *,
    estado_cache: dict | None = None,
    force_refresh: bool = False,
) -> None:
    estado = estado_cache or obter_estado_cache_notas(db, tenant_id)
    desde = None
    if (
        estado.get("total")
        and not force_refresh
        and isinstance(estado.get("ultimo_sync"), datetime)
    ):
        desde = estado["ultimo_sync"] - timedelta(hours=6)

    _sincronizar_vendas_em_cache(db, tenant_id, desde=desde)
    _sincronizar_pedidos_integrados_em_cache(db, tenant_id, desde=desde)


def _enriquecer_notas_com_vendas(db: Session, tenant_id, notas: list[dict]) -> None:
    ids_bling = {
        _coerce_int(nota.get("id"), 0)
        for nota in notas
        if _coerce_int(nota.get("id"), 0) > 0
    }
    if not ids_bling:
        return

    vendas = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.nfe_bling_id.in_(ids_bling),
        )
        .all()
    )
    vendas_por_bling_id = {
        str(venda.nfe_bling_id): venda for venda in vendas if venda.nfe_bling_id
    }

    for nota in notas:
        venda = vendas_por_bling_id.get(str(nota.get("id") or ""))
        if not venda:
            continue

        nota["venda_id"] = nota.get("venda_id") or venda.id
        nota["chave"] = nota.get("chave") or venda.nfe_chave or ""

        if not nota.get("valor") and venda.total is not None:
            nota["valor"] = float(venda.total or 0)

        cliente = nota.get("cliente") or {}
        if venda.cliente:
            cliente["id"] = cliente.get("id") or venda.cliente.id
            cliente["nome"] = cliente.get("nome") or venda.cliente.nome
            cliente["cpf_cnpj"] = (
                cliente.get("cpf_cnpj") or venda.cliente.cpf or venda.cliente.cnpj
            )
        nota["cliente"] = cliente

        nota["canal"] = nota.get("canal") or _texto(venda.canal)
        nota["canal_label"] = nota.get("canal_label") or _canal_label(
            _canal_slug(venda.canal), venda.canal
        )
        nota["numero_pedido_loja"] = nota.get("numero_pedido_loja") or _texto(
            venda.numero_venda
        )
        if not isinstance(nota.get("loja"), dict) or not nota.get("loja", {}).get(
            "nome"
        ):
            nota["loja"] = {
                "id": None,
                "nome": _texto(venda.loja_origem),
            }


def _enriquecer_notas_com_detalhes_bling(
    bling: BlingAPI,
    db: Session,
    tenant_id,
    notas: list[dict],
    limite_consultas: int = 120,
) -> None:
    consultas = 0
    ultima_consulta_ts = 0.0

    for nota in notas:
        if consultas >= limite_consultas:
            break

        try:
            valor_atual = float(nota.get("valor") or 0)
        except (TypeError, ValueError):
            valor_atual = 0.0

        status_atual = _texto(nota.get("status")).lower()
        precisa_numero = not _texto(nota.get("numero"))
        precisa_chave = not _texto(nota.get("chave"))
        precisa_reconciliar_status = status_atual in {"pendente", "emitida danfe"}
        precisa_resumo_canal = not any(
            (
                nota.get("canal_label"),
                nota.get("loja", {}).get("nome")
                if isinstance(nota.get("loja"), dict)
                else None,
                nota.get("origem_loja_virtual"),
                nota.get("numero_pedido_loja"),
            )
        )

        if (
            valor_atual > 0
            and not precisa_resumo_canal
            and not precisa_numero
            and not precisa_chave
            and not precisa_reconciliar_status
        ):
            continue

        nota_id = _coerce_int(nota.get("id"), 0)
        if nota_id <= 0:
            continue

        try:
            modelo_nota = _coerce_int(nota.get("modelo"), 55)
            detalhe = _obter_detalhe_nfe_cache(tenant_id, nota_id, modelo_nota)
            if not _detalhe_nota_valido(detalhe):
                detalhe = obter_detalhe_nota_cache(
                    db=db,
                    tenant_id=tenant_id,
                    nfe_id=nota_id,
                    modelo=modelo_nota,
                )
            fetched_remotamente = False
            if not _detalhe_nota_valido(detalhe):
                if ultima_consulta_ts:
                    intervalo = monotonic() - ultima_consulta_ts
                    if intervalo < 0.36:
                        sleep(0.36 - intervalo)
                detalhe = (
                    bling.consultar_nfce(nota_id)
                    if modelo_nota == 65
                    else bling.consultar_nfe(nota_id)
                )
                ultima_consulta_ts = monotonic()
                if _detalhe_nota_valido(detalhe):
                    _salvar_detalhe_nfe_cache(tenant_id, nota_id, modelo_nota, detalhe)
                    fetched_remotamente = True
            if not _detalhe_nota_valido(detalhe):
                continue
            nota["numero"] = (
                _texto(_primeiro_preenchido(detalhe.get("numero"), nota.get("numero")))
                or ""
            )
            nota["serie"] = (
                _texto(_primeiro_preenchido(detalhe.get("serie"), nota.get("serie")))
                or ""
            )
            nota["data_emissao"] = _primeiro_preenchido(
                detalhe.get("dataEmissao"),
                detalhe.get("data_emissao"),
                nota.get("data_emissao"),
            )
            nota["valor"] = _extrair_valor_nota(detalhe) or nota.get("valor") or 0.0
            nota["status"] = _status_nota_bling(detalhe)
            nota["chave"] = detalhe.get("chaveAcesso") or nota.get("chave") or ""
            contato = detalhe.get("contato") or {}
            cliente = nota.get("cliente") or {}
            cliente["id"] = cliente.get("id") or contato.get("id")
            cliente["nome"] = (
                cliente.get("nome") or contato.get("nome") or contato.get("descricao")
            )
            cliente["cpf_cnpj"] = (
                cliente.get("cpf_cnpj")
                or contato.get("cpf")
                or contato.get("cnpj")
                or contato.get("cpfCnpj")
            )
            nota["cliente"] = cliente
            resumo_canal = _normalizar_resumo_canal(detalhe)
            nota["canal"] = nota.get("canal") or resumo_canal.get("canal")
            nota["canal_label"] = nota.get("canal_label") or resumo_canal.get(
                "canal_label"
            )
            if not isinstance(nota.get("loja"), dict) or not nota.get("loja", {}).get(
                "nome"
            ):
                nota["loja"] = resumo_canal.get("loja")
            nota["unidade_negocio"] = nota.get("unidade_negocio") or resumo_canal.get(
                "unidade_negocio"
            )
            nota["numero_loja_virtual"] = nota.get(
                "numero_loja_virtual"
            ) or resumo_canal.get("numero_loja_virtual")
            nota["origem_loja_virtual"] = nota.get(
                "origem_loja_virtual"
            ) or resumo_canal.get("origem_loja_virtual")
            nota["origem_canal_venda"] = nota.get(
                "origem_canal_venda"
            ) or resumo_canal.get("origem_canal_venda")
            nota["numero_pedido_loja"] = nota.get(
                "numero_pedido_loja"
            ) or resumo_canal.get("numero_pedido_loja")
            nota["pedido_bling_id_ref"] = nota.get(
                "pedido_bling_id_ref"
            ) or resumo_canal.get("pedido_bling_id_ref")
            if (
                fetched_remotamente
                or precisa_numero
                or precisa_chave
                or precisa_resumo_canal
                or precisa_reconciliar_status
            ):
                upsert_nota_cache(
                    db,
                    tenant_id,
                    nota,
                    source="bling_detail",
                    resumo_payload=nota,
                    detalhe_payload=detalhe,
                )
            if fetched_remotamente:
                consultas += 1
        except Exception as e:
            logger.warning(
                "listar_nfes",
                f"Falha ao enriquecer NF {nota_id} via detalhe do Bling: {e}",
            )
            mensagem = str(e).upper()
            if "429" in mensagem or "TOO_MANY_REQUESTS" in mensagem:
                break


def _sincronizar_cache_nfes_com_bling(
    db: Session,
    tenant_id,
    *,
    data_inicial: str | None = None,
    data_final: str | None = None,
    situacao: str | None = None,
) -> tuple[bool, list[dict]]:
    notas_sincronizadas: list[dict] = []
    bling_ok = False
    try:
        bling = BlingAPI()
    except Exception as e:
        logger.warning(
            "listar_nfes", f"Bling indisponivel para sincronizacao incremental: {e}"
        )
        return False, []

    try:
        resp_nfe = bling.listar_nfes(
            data_inicial=data_inicial,
            data_final=data_final,
            situacao=situacao,
        )
        for item in resp_nfe.get("data") or []:
            notas_sincronizadas.append(_normalizar_nota_bling(item, modelo=55))
        bling_ok = True
    except Exception as e:
        logger.warning(
            "listar_nfes",
            f"Bling NF-e nao disponivel para sincronizacao incremental: {e}",
        )
        if "TOO_MANY_REQUESTS" in str(e).upper() or "429" in str(e):
            BlingSyncService.register_rate_limit_cooldown(e)
            return False, []

    try:
        resp_nfce = bling.listar_nfces(
            data_inicial=data_inicial,
            data_final=data_final,
            situacao=situacao,
        )
        ids_ja_adicionados = {
            (str(nota.get("id") or ""), _coerce_int(nota.get("modelo"), 55))
            for nota in notas_sincronizadas
        }
        for item in resp_nfce.get("data") or []:
            nota = _normalizar_nota_bling(item, modelo=65)
            chave = (str(nota.get("id") or ""), _coerce_int(nota.get("modelo"), 65))
            if chave in ids_ja_adicionados:
                continue
            notas_sincronizadas.append(nota)
            ids_ja_adicionados.add(chave)
        bling_ok = True
    except Exception as e:
        logger.warning(
            "listar_nfes",
            f"Bling NFC-e nao disponivel para sincronizacao incremental: {e}",
        )
        if "TOO_MANY_REQUESTS" in str(e).upper() or "429" in str(e):
            BlingSyncService.register_rate_limit_cooldown(e)
            return False, []

    if not notas_sincronizadas:
        return bling_ok, []

    _enriquecer_notas_com_vendas(db, tenant_id, notas_sincronizadas)
    _enriquecer_notas_com_pedidos_integrados(db, tenant_id, notas_sincronizadas)
    _enriquecer_notas_com_detalhes_bling(
        bling,
        db,
        tenant_id,
        notas_sincronizadas[:20],
        limite_consultas=8,
    )
    for nota in notas_sincronizadas:
        upsert_nota_cache(
            db,
            tenant_id,
            nota,
            source="bling_api",
            resumo_payload=nota,
        )
    db.commit()
    return bling_ok, notas_sincronizadas
