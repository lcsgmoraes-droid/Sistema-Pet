"""Montagem dos dados complementares enviados no cadastro de produtos do Bling."""

from __future__ import annotations

import logging
import os
import unicodedata
from datetime import date, datetime
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from app.bling_integration import BlingAPI
from app.bling_sync.routes_common import utc_now
from app.produtos_models import Produto, ProdutoBlingSync

logger = logging.getLogger(__name__)


def _texto(valor: Any, max_length: Optional[int] = None) -> str:
    texto = str(valor or "").strip()
    if max_length and len(texto) > max_length:
        return texto[:max_length].rstrip()
    return texto


def _float_or_none(valor: Any) -> Optional[float]:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _float_or_zero(valor: Any) -> float:
    return _float_or_none(valor) or 0.0


def _digits(valor: Any, allowed_lengths: Optional[set[int]] = None) -> str:
    texto = "".join(ch for ch in str(valor or "") if ch.isdigit())
    if allowed_lengths and len(texto) not in allowed_lengths:
        return ""
    return texto


def _origem_fiscal(valor: Any) -> Optional[int]:
    texto = _texto(valor)
    if texto.isdigit():
        origem = int(texto)
        if 0 <= origem <= 8:
            return origem
    return None


def _tipo_bling(produto: Produto) -> str:
    tipo = _texto(getattr(produto, "tipo", "")).lower()
    return "S" if tipo in {"servico", "servico_produto"} else "P"


def _data_bling(valor: Any) -> Optional[str]:
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = _texto(valor)
    return texto[:10] if len(texto) >= 10 else None


def _condicao_bling(valor: Any) -> int:
    return {"novo": 1, "usado": 2}.get(_texto(valor).lower(), 0)


def _tipo_producao_bling(valor: Any) -> Optional[str]:
    return {
        "propria": "P",
        "própria": "P",
        "terceiros": "T",
        "terceiro": "T",
    }.get(_texto(valor).lower())


def _url_imagem_publica(valor: Any) -> Optional[str]:
    url = _texto(valor)
    if not url:
        return None

    parsed = urlparse(url)
    if not parsed.scheme and not parsed.netloc:
        base_url = next(
            (
                _texto(os.getenv(nome)).rstrip("/")
                for nome in (
                    "ECOMMERCE_PUBLIC_BASE_URL",
                    "FRONTEND_PUBLIC_BASE_URL",
                    "FRONTEND_URL",
                )
                if _texto(os.getenv(nome))
            ),
            "",
        )
        if not base_url:
            return None
        url = urljoin(f"{base_url}/", url.lstrip("/"))
        parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if (parsed.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}:
        return None
    return url


def _urls_imagens_produto(produto: Produto) -> list[str]:
    candidatos: list[Any] = [getattr(produto, "imagem_principal", None)]
    imagens = sorted(
        list(getattr(produto, "imagens", None) or []),
        key=lambda imagem: (
            not bool(getattr(imagem, "e_principal", False)),
            int(getattr(imagem, "ordem", 0) or 0),
            int(getattr(imagem, "id", 0) or 0),
        ),
    )
    candidatos.extend(getattr(imagem, "url", None) for imagem in imagens)

    urls: list[str] = []
    for candidato in candidatos:
        url = _url_imagem_publica(candidato)
        if url and url not in urls:
            urls.append(url)
    return urls


def _montar_payload_produto_bling(produto: Produto) -> dict[str, Any]:
    nome = _texto(produto.nome, 120) or _texto(produto.codigo, 120)
    payload: dict[str, Any] = {
        "nome": nome,
        "codigo": _texto(produto.codigo, 80),
        "preco": _float_or_zero(produto.preco_venda),
        "tipo": _tipo_bling(produto),
        "situacao": "A" if bool(produto.situacao) else "I",
        "formato": "S",
        "unidade": _texto(produto.unidade, 10) or "UN",
        "condicao": _condicao_bling(getattr(produto, "condicao", None)),
        "freteGratis": bool(getattr(produto, "frete_gratis", False)),
    }

    data_validade = _data_bling(getattr(produto, "data_validade", None))
    if data_validade:
        payload["dataValidade"] = data_validade

    itens_por_caixa = _float_or_none(getattr(produto, "itens_por_caixa", None))
    if itens_por_caixa and itens_por_caixa > 0:
        payload["itensPorCaixa"] = itens_por_caixa

    tipo_producao = _tipo_producao_bling(getattr(produto, "producao", None))
    if tipo_producao:
        payload["tipoProducao"] = tipo_producao

    descricao_curta = _texto(produto.descricao_curta, 500)
    descricao_completa = _texto(produto.descricao_completa, 4000)
    if descricao_curta:
        payload["descricaoCurta"] = descricao_curta
    if descricao_completa:
        payload["descricaoComplementar"] = descricao_completa

    gtin = _digits(produto.gtin_ean or produto.codigo_barras, {8, 12, 13, 14})
    gtin_embalagem = _digits(produto.gtin_ean_tributario, {8, 12, 13})
    if gtin:
        payload["gtin"] = gtin
    if gtin_embalagem:
        payload["gtinEmbalagem"] = gtin_embalagem

    marca_nome = _texto(getattr(getattr(produto, "marca", None), "nome", ""), 120)
    if marca_nome:
        payload["marca"] = marca_nome

    peso_liquido = _float_or_none(produto.peso_liquido)
    peso_bruto = _float_or_none(produto.peso_bruto)
    if peso_liquido and peso_liquido > 0:
        payload["pesoLiquido"] = peso_liquido
    if peso_bruto and peso_bruto > 0:
        payload["pesoBruto"] = peso_bruto

    estoque: dict[str, Any] = {}
    estoque_minimo = _float_or_none(produto.estoque_minimo)
    estoque_maximo = _float_or_none(produto.estoque_maximo)
    localizacao = _texto(getattr(produto, "localizacao", ""), 80)
    crossdocking = getattr(produto, "crossdocking_dias", None)
    if estoque_minimo is not None:
        estoque["minimo"] = estoque_minimo
    if estoque_maximo is not None and estoque_maximo > 0:
        estoque["maximo"] = estoque_maximo
    if localizacao:
        estoque["localizacao"] = localizacao
    if isinstance(crossdocking, int) and crossdocking > 0:
        estoque["crossdocking"] = crossdocking
    if estoque:
        payload["estoque"] = estoque

    tributacao: dict[str, Any] = {}
    ncm = _digits(produto.ncm, {8})
    cest = _digits(produto.cest, {7})
    origem = _origem_fiscal(produto.origem)
    dados_adicionais = _texto(getattr(produto, "informacoes_adicionais_nf", ""), 500)
    if ncm:
        tributacao["ncm"] = ncm
    if cest:
        tributacao["cest"] = cest
    if origem is not None:
        tributacao["origem"] = origem
    if dados_adicionais:
        tributacao["dadosAdicionais"] = dados_adicionais

    sped_tipo_item = _texto(getattr(produto, "tipo_item", ""), 50)
    codigo_excecao_tipi = _texto(getattr(produto, "ipi_codigo_excecao", ""), 20)
    if sped_tipo_item:
        tributacao["spedTipoItem"] = sped_tipo_item
    if codigo_excecao_tipi:
        tributacao["codigoExcecaoTipi"] = codigo_excecao_tipi

    for origem_attr, destino_attr in [
        ("percentual_tributos", "percentualTributos"),
        ("icms_base_retencao", "valorBaseStRetencao"),
        ("icms_valor_retencao", "valorStRetencao"),
        ("icms_valor_proprio", "valorICMSSubstituto"),
        ("pis_valor_fixo", "valorPisFixo"),
        ("cofins_valor_fixo", "valorCofinsFixo"),
    ]:
        valor = _float_or_none(getattr(produto, origem_attr, None))
        if valor is not None:
            tributacao[destino_attr] = valor
    if tributacao:
        payload["tributacao"] = tributacao

    dimensoes: dict[str, Any] = {}
    for origem_attr, destino_attr in [
        ("largura", "largura"),
        ("altura", "altura"),
        ("profundidade", "profundidade"),
    ]:
        valor = _float_or_none(getattr(produto, origem_attr, None))
        if valor and valor > 0:
            dimensoes[destino_attr] = valor
    if dimensoes:
        dimensoes["unidadeMedida"] = 1
        payload["dimensoes"] = dimensoes

    imagens = _urls_imagens_produto(produto)
    if imagens:
        payload["midia"] = {
            "video": {"url": ""},
            "imagens": {
                "imagensURL": [{"link": url} for url in imagens],
            },
        }

    return payload


def _normalizar_nome(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", _texto(valor).casefold())
    sem_acentos = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(sem_acentos.split())


def _documento_fornecedor(fornecedor: Any) -> str:
    return _digits(
        getattr(fornecedor, "cnpj", None) or getattr(fornecedor, "cpf", None),
        {11, 14},
    )


def _itens_resposta_bling(resposta: Any) -> list[dict[str, Any]]:
    if not isinstance(resposta, dict):
        return []
    data = resposta.get("data", [])
    return (
        [item for item in data if isinstance(item, dict)]
        if isinstance(data, list)
        else []
    )


def _localizar_contato_fornecedor_bling(
    bling: BlingAPI, fornecedor: Any
) -> Optional[str]:
    documento = _documento_fornecedor(fornecedor)
    if documento:
        resposta = bling.listar_contatos(numero_documento=documento, limite=20)
        candidatos = [
            item
            for item in _itens_resposta_bling(resposta)
            if _digits(item.get("numeroDocumento"), {11, 14}) == documento
            and _texto(item.get("situacao")).upper() == "A"
        ]
    else:
        nome = _texto(
            getattr(fornecedor, "razao_social", None)
            or getattr(fornecedor, "nome_fantasia", None)
            or getattr(fornecedor, "nome", None),
            255,
        )
        if not nome:
            return None
        resposta = bling.listar_contatos(pesquisa=nome, limite=20)
        nome_normalizado = _normalizar_nome(nome)
        candidatos = [
            item
            for item in _itens_resposta_bling(resposta)
            if _normalizar_nome(item.get("nome")) == nome_normalizado
            and _texto(item.get("situacao")).upper() == "A"
        ]

    ids = list(dict.fromkeys(_texto(item.get("id")) for item in candidatos))
    ids = [bling_id for bling_id in ids if bling_id]
    return ids[0] if len(ids) == 1 else None


def _vinculos_fornecedores_produto(produto: Produto) -> list[tuple[Any, Any, bool]]:
    vinculos: list[tuple[Any, Any, bool]] = []
    vistos: set[int] = set()

    alternativos = sorted(
        [
            vinculo
            for vinculo in list(
                getattr(produto, "fornecedores_alternativos", None) or []
            )
            if bool(getattr(vinculo, "ativo", True))
            and getattr(vinculo, "fornecedor", None)
        ],
        key=lambda vinculo: (
            not bool(getattr(vinculo, "e_principal", False)),
            int(getattr(vinculo, "id", 0) or 0),
        ),
    )
    for vinculo in alternativos:
        fornecedor = vinculo.fornecedor
        fornecedor_id = int(getattr(fornecedor, "id", 0) or 0)
        if not fornecedor_id or fornecedor_id in vistos:
            continue
        vistos.add(fornecedor_id)
        principal = bool(getattr(vinculo, "e_principal", False)) or (
            fornecedor_id == int(getattr(produto, "fornecedor_id", 0) or 0)
        )
        vinculos.append((fornecedor, vinculo, principal))

    fornecedor_direto = getattr(produto, "fornecedor", None)
    fornecedor_direto_id = int(getattr(fornecedor_direto, "id", 0) or 0)
    if fornecedor_direto_id and fornecedor_direto_id not in vistos:
        vinculos.insert(0, (fornecedor_direto, None, True))

    if vinculos and not any(principal for _fornecedor, _vinculo, principal in vinculos):
        fornecedor, vinculo, _principal = vinculos[0]
        vinculos[0] = (fornecedor, vinculo, True)
    return vinculos


def _enviar_fornecedores_produto_bling(
    bling: BlingAPI,
    produto: Produto,
    bling_produto_id: str,
) -> dict[str, Any]:
    enviados = 0
    nao_localizados = 0
    erros = 0

    for fornecedor, vinculo, principal in _vinculos_fornecedores_produto(produto):
        try:
            fornecedor_bling_id = _localizar_contato_fornecedor_bling(bling, fornecedor)
            if not fornecedor_bling_id:
                nao_localizados += 1
                continue

            custo = _float_or_none(getattr(vinculo, "preco_custo", None))
            if custo is None:
                custo = _float_or_zero(getattr(produto, "preco_custo", None))

            payload_fornecedor = {
                "descricao": _texto(produto.nome, 255),
                "codigo": _texto(
                    getattr(vinculo, "codigo_fornecedor", None) or produto.codigo,
                    80,
                ),
                "precoCusto": custo,
                "precoCompra": custo,
                "padrao": bool(principal),
                "produto": {"id": int(bling_produto_id)},
                "fornecedor": {"id": int(fornecedor_bling_id)},
            }
            bling.criar_produto_fornecedor(payload_fornecedor)
            enviados += 1
        except Exception as error:
            erros += 1
            logger.warning(
                "Falha ao enviar fornecedor do produto ao Bling; produto_id=%s fornecedor_id=%s error_type=%s",
                produto.id,
                getattr(fornecedor, "id", None),
                type(error).__name__,
            )

    detalhes = []
    if nao_localizados:
        detalhes.append(f"{nao_localizados} fornecedor(es) nao localizado(s) no Bling")
    if erros:
        detalhes.append(f"{erros} fornecedor(es) recusado(s) pelo Bling")
    return {
        "fornecedores_enviados": enviados,
        "fornecedores_nao_localizados": nao_localizados,
        "fornecedores_erros": erros,
        "fornecedores_detail": "; ".join(detalhes) or None,
    }


def _erro_bling_nao_encontrado(error: Exception) -> bool:
    mensagem = str(error).upper()
    return "404" in mensagem


def _detalhe_bling_confirma_produto(detalhe_bling: Any, bling_produto_id: str) -> bool:
    if not isinstance(detalhe_bling, dict):
        return False
    detalhe_id = _texto(detalhe_bling.get("id"))
    if not detalhe_id or detalhe_id != _texto(bling_produto_id):
        return False
    situacao = _normalizar_nome(detalhe_bling.get("situacao")).upper()
    return situacao not in {"E", "EXCLUIDO", "EXCLUIDA"}


def _limpar_vinculo_bling_inexistente(sync: ProdutoBlingSync) -> None:
    sync.bling_produto_id = None
    sync.sincronizar = False
    sync.status = "pausado"
    sync.erro_mensagem = None
    sync.ultima_conferencia_bling = utc_now()
    sync.updated_at = utc_now()
