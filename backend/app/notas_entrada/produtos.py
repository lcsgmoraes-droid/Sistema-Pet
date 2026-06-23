"""Helpers de produto usados no processamento de notas de entrada."""

from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.produtos_models import NotaEntrada, NotaEntradaItem, Produto, ProdutoFornecedor

from .fiscal import calcular_composicao_custos_nota
from .fornecedores import gerar_prefixo_fornecedor

logger = logging.getLogger(__name__)


def _valor_preenchido(valor) -> bool:
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    return True


def _aplicar_dados_fiscais_item_no_produto(
    produto, item, sobrescrever: bool = False
) -> bool:
    """Atualiza dados fiscais somente quando o item realmente trouxe o campo."""
    atualizou = False

    def aplicar_texto(campo: str) -> None:
        nonlocal atualizou
        valor_item = getattr(item, campo, None)
        if not _valor_preenchido(valor_item):
            return
        valor_produto = getattr(produto, campo, None)
        if sobrescrever or not _valor_preenchido(valor_produto):
            setattr(produto, campo, valor_item)
            atualizou = True

    def aplicar_aliquota(campo: str) -> None:
        nonlocal atualizou
        valor_item = getattr(item, campo, None)
        if valor_item is None:
            return
        if not sobrescrever and float(valor_item or 0) == 0:
            return
        valor_produto = getattr(produto, campo, None)
        if sobrescrever or valor_produto is None:
            setattr(produto, campo, valor_item)
            atualizou = True

    for campo_texto in ("ncm", "cfop", "cest", "origem"):
        aplicar_texto(campo_texto)

    for campo_aliquota in ("aliquota_icms", "aliquota_pis", "aliquota_cofins"):
        aplicar_aliquota(campo_aliquota)

    return atualizou


def gerar_sku_automatico(prefixo: str, db: Session, user_id: int) -> str:
    """
    Gera um SKU unico automaticamente para produtos sem codigo.

    Formato: {PREFIXO}-{NUMERO_SEQUENCIAL}
    Exemplo: PROD-00001
    """
    ultimo_produto = (
        db.query(Produto)
        .filter(Produto.user_id == user_id, Produto.codigo.like(f"{prefixo}-%"))
        .order_by(Produto.id.desc())
        .first()
    )

    if ultimo_produto:
        try:
            ultimo_numero = int(ultimo_produto.codigo.split("-")[-1])
            proximo_numero = ultimo_numero + 1
        except ValueError:
            proximo_numero = 1
    else:
        proximo_numero = 1

    novo_sku = f"{prefixo}-{proximo_numero:05d}"

    existe = (
        db.query(Produto)
        .filter(Produto.codigo == novo_sku, Produto.user_id == user_id)
        .first()
    )

    if existe:
        novo_sku = f"{prefixo}-{proximo_numero + 1:05d}"

    return novo_sku


def _buscar_produto_por_codigo_global(
    db: Session,
    codigo: Optional[str],
):
    codigo_limpo = (codigo or "").strip()
    if not codigo_limpo:
        return None

    return (
        db.query(Produto)
        .filter(
            func.lower(func.trim(Produto.codigo)) == codigo_limpo.lower(),
        )
        .first()
    )


def _produto_pertence_ao_tenant(produto: Optional[Produto], tenant_id) -> bool:
    if not produto:
        return False
    return getattr(produto, "tenant_id", None) == tenant_id


def _gerar_candidatos_sku_disponiveis(
    sku_base: str,
    prefixo: str,
    db: Session,
    tenant_id,
    user_id: int,
) -> List[Dict[str, Any]]:
    sugestoes: List[Dict[str, Any]] = []
    vistos = set()

    def adicionar_candidato(sku: Optional[str], descricao: str) -> None:
        sku_limpo = (sku or "").strip()
        if not sku_limpo or sku_limpo in vistos:
            return
        vistos.add(sku_limpo)

        existe = _buscar_produto_por_codigo_global(db, sku_limpo)
        if existe:
            return

        sugestoes.append(
            {
                "sku": sku_limpo,
                "descricao": descricao,
                "disponivel": True,
                "padrao": False,
            }
        )

    sku_base_limpo = (sku_base or "").strip()
    prefixo_limpo = re.sub(r"[^A-Z0-9]", "", (prefixo or "").upper()) or "PROD"

    if sku_base_limpo:
        adicionar_candidato(
            f"{prefixo_limpo}-{sku_base_limpo}",
            f"Prefixo {prefixo_limpo} + codigo do fornecedor",
        )
        adicionar_candidato(
            f"{sku_base_limpo}-{prefixo_limpo}",
            f"Codigo do fornecedor + sufixo {prefixo_limpo}",
        )
        for indice in range(1, 6):
            adicionar_candidato(
                f"{prefixo_limpo}-{sku_base_limpo}-V{indice}",
                f"Variacao {indice} com prefixo {prefixo_limpo}",
            )

    adicionar_candidato(
        gerar_sku_automatico(prefixo_limpo, db, user_id),
        f"Sequencial automatico com prefixo {prefixo_limpo}",
    )
    for indice in range(1, 6):
        adicionar_candidato(
            f"{prefixo_limpo}-{indice:05d}",
            f"Sequencial manual {indice} com prefixo {prefixo_limpo}",
        )

    if sugestoes:
        sugestoes[0]["padrao"] = True

    return sugestoes


def _montar_sugestao_sku_produto(
    nota: NotaEntrada,
    item: NotaEntradaItem,
    db: Session,
    tenant_id,
    user_id: int,
    sku_base_customizado: Optional[str] = None,
) -> Dict[str, Any]:
    fornecedor_nome = (nota.fornecedor_nome or "").strip()
    prefixo = gerar_prefixo_fornecedor(fornecedor_nome) if fornecedor_nome else "PROD"
    prefixo = re.sub(r"[^A-Z0-9]", "", (prefixo or "").upper()) or "PROD"

    sku_base = (sku_base_customizado or item.codigo_produto or "").strip()
    if not sku_base:
        descricao_base = re.sub(r"[^A-Z0-9]", "", (item.descricao or "").upper())
        sku_base = (
            descricao_base[:10] or gerar_sku_automatico(prefixo, db, user_id)
        ).strip()

    produto_existente = _buscar_produto_por_codigo_global(db, sku_base)
    composicoes_custo = calcular_composicao_custos_nota(nota)
    composicao_item = composicoes_custo.get(item.id, {})

    if produto_existente:
        sugestoes = _gerar_candidatos_sku_disponiveis(
            sku_base=sku_base,
            prefixo=prefixo,
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
        )
    else:
        sugestoes = [
            {
                "sku": sku_base,
                "descricao": "Codigo original do fornecedor",
                "disponivel": True,
                "padrao": True,
            }
        ]

    payload: Dict[str, Any] = {
        "item_id": item.id,
        "descricao_item": item.descricao,
        "codigo_fornecedor": item.codigo_produto,
        "fornecedor": nota.fornecedor_nome,
        "prefixo_sugerido": prefixo,
        "sku_proposto": sku_base,
        "ja_existe": produto_existente is not None,
        "sugestoes": sugestoes,
        "dados_produto": {
            "nome": item.descricao,
            "unidade": item.unidade,
            "preco_custo": composicao_item.get(
                "custo_aquisicao_unitario", item.valor_unitario
            ),
            "ncm": item.ncm if hasattr(item, "ncm") else None,
            "ean": item.ean if hasattr(item, "ean") else None,
            "ean_tributario": getattr(item, "ean_tributario", None),
        },
    }

    if produto_existente:
        produto_do_tenant = _produto_pertence_ao_tenant(produto_existente, tenant_id)
        nome_produto_existente = (
            produto_existente.nome
            if produto_do_tenant
            else "SKU ja utilizado em outro cadastro"
        )
        payload["produto_existente"] = {
            "id": produto_existente.id if produto_do_tenant else None,
            "codigo": produto_existente.codigo,
            "nome": nome_produto_existente,
        }

    return payload


def calcular_similaridade(texto1: str, texto2: str) -> float:
    """Calcula similaridade entre dois textos (0-1)."""
    if not texto1 or not texto2:
        return 0.0
    return SequenceMatcher(None, texto1.lower(), texto2.lower()).ratio()


def normalizar_codigo_barras(valor: Optional[str]) -> str:
    if not valor:
        return ""
    return re.sub(r"\D", "", str(valor))


def _codigo_barras_valido_nf(valor: Optional[str]) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if texto.upper().replace(" ", "") == "SEMGTIN":
        return ""
    return normalizar_codigo_barras(texto)


def _codigos_barras_nf(item: Any) -> Dict[str, str]:
    ean = _codigo_barras_valido_nf(getattr(item, "ean", None))
    ean_tributario = _codigo_barras_valido_nf(getattr(item, "ean_tributario", None))
    return {
        "ean": ean,
        "ean_tributario": ean_tributario,
        "principal": ean_tributario or ean,
    }


def _lista_codigos_barras_unicos(valores: List[Any]) -> List[str]:
    codigos: List[str] = []
    vistos = set()

    for valor in valores:
        codigo = _codigo_barras_valido_nf(valor)
        if codigo and codigo not in vistos:
            codigos.append(codigo)
            vistos.add(codigo)

    return codigos


def _codigos_barras_alternativos_lista(produto: Produto) -> List[str]:
    valor = getattr(produto, "codigos_barras_alternativos", None)
    if not valor:
        return []

    bruto: List[Any]
    if isinstance(valor, list):
        bruto = valor
    else:
        texto = str(valor).strip()
        if not texto:
            return []

        try:
            carregado = json.loads(texto)
            bruto = carregado if isinstance(carregado, list) else [texto]
        except (TypeError, ValueError, json.JSONDecodeError):
            bruto = re.split(r"[,;\n]+", texto)

    return _lista_codigos_barras_unicos(bruto)


def _codigos_barras_produto(produto: Produto) -> List[str]:
    return _lista_codigos_barras_unicos(
        [
            getattr(produto, "codigo_barras", None),
            getattr(produto, "gtin_ean", None),
            getattr(produto, "gtin_ean_tributario", None),
            *_codigos_barras_alternativos_lista(produto),
        ]
    )


def _adicionar_codigos_barras_alternativos_produto(
    produto: Produto, codigos: List[str]
) -> bool:
    alternativos = _codigos_barras_alternativos_lista(produto)
    existentes = set(_codigos_barras_produto(produto))
    atualizou = False

    for codigo in _lista_codigos_barras_unicos(codigos):
        if codigo in existentes:
            continue
        alternativos.append(codigo)
        existentes.add(codigo)
        atualizou = True

    if atualizou:
        produto.codigos_barras_alternativos = json.dumps(alternativos)

    return atualizou


def _preencher_campo_codigo_barras_vazio(
    produto: Produto, campo: str, valor: str
) -> bool:
    if not valor:
        return False
    atual = _codigo_barras_valido_nf(getattr(produto, campo, None))
    if atual:
        return False
    setattr(produto, campo, valor)
    return True


def _aplicar_codigos_barras_item_no_produto(
    produto: Produto, item: NotaEntradaItem
) -> bool:
    """Preenche codigos vindos da NF-e sem sobrescrever cadastro divergente."""
    codigos = _codigos_barras_nf(item)
    atualizou = False

    atualizou = (
        _preencher_campo_codigo_barras_vazio(produto, "gtin_ean", codigos["ean"])
        or atualizou
    )
    atualizou = (
        _preencher_campo_codigo_barras_vazio(
            produto,
            "gtin_ean_tributario",
            codigos["ean_tributario"],
        )
        or atualizou
    )
    atualizou = (
        _preencher_campo_codigo_barras_vazio(
            produto, "codigo_barras", codigos["principal"]
        )
        or atualizou
    )
    atualizou = (
        _adicionar_codigos_barras_alternativos_produto(
            produto, [codigos["ean"], codigos["ean_tributario"]]
        )
        or atualizou
    )

    if atualizou:
        logger.info(
            "Codigos de barras da NF aplicados ao produto %s: ean=%s ean_tributario=%s principal=%s",
            getattr(produto, "codigo", None),
            codigos["ean"] or "-",
            codigos["ean_tributario"] or "-",
            codigos["principal"] or "-",
        )

    return atualizou


def _montar_divergencia_codigo_barras_item(item: NotaEntradaItem) -> Dict[str, Any]:
    if not item or not item.produto:
        return {"tem_divergencia": False, "mensagens": []}

    codigos_nf = _codigos_barras_nf(item)
    produto = item.produto
    codigos_produto = set(_codigos_barras_produto(produto))
    pares = [
        ("EAN comercial", codigos_nf["ean"]),
        ("EAN fiscal", codigos_nf["ean_tributario"]),
    ]
    mensagens = []

    for label, valor_nf in pares:
        if valor_nf and valor_nf not in codigos_produto:
            mensagens.append(f"{label} da NF nao encontrado no produto: NF={valor_nf}")

    return {"tem_divergencia": bool(mensagens), "mensagens": mensagens}


def obter_detalhe_vinculo_item(item: NotaEntradaItem) -> Dict[str, Optional[str]]:
    """Identifica por qual referencia o item da NF-e coincide com o produto vinculado."""
    if not item or not item.produto_id or not item.produto:
        return {"origem": None, "referencia": None}

    referencia_nf_codigo = (item.codigo_produto or "").strip()
    referencias_nf_ean = [
        _codigo_barras_valido_nf(getattr(item, "ean_tributario", None)),
        _codigo_barras_valido_nf(item.ean),
    ]
    produto_codigo = (item.produto.codigo or "").strip()

    produto_codigos_barras = {
        normalizar_codigo_barras(item.produto.codigo_barras),
        normalizar_codigo_barras(getattr(item.produto, "gtin_ean", None)),
        normalizar_codigo_barras(getattr(item.produto, "gtin_ean_tributario", None)),
    }
    produto_codigos_barras.discard("")

    for referencia_nf_ean in referencias_nf_ean:
        if referencia_nf_ean and referencia_nf_ean in produto_codigos_barras:
            return {"origem": "codigo_barras", "referencia": referencia_nf_ean}

    if referencia_nf_codigo and referencia_nf_codigo == produto_codigo:
        return {"origem": "sku", "referencia": referencia_nf_codigo}

    codigo_nf_normalizado = normalizar_codigo_barras(referencia_nf_codigo)
    if codigo_nf_normalizado and codigo_nf_normalizado in produto_codigos_barras:
        return {"origem": "codigo_barras", "referencia": codigo_nf_normalizado}

    return {"origem": None, "referencia": None}


def encontrar_produto_similar(
    descricao: str,
    codigo: str,
    db: Session,
    tenant_id=None,
    fornecedor_id: int = None,
    ean: Optional[str] = None,
    ean_tributario: Optional[str] = None,
) -> tuple:
    """
    Encontra produto similar no banco (ativo OU inativo).

    Retorna (produto, confianca, foi_encontrado_inativo, origem_match, referencia_match).
    Matching por similaridade de nome foi removido para evitar vinculos errados.
    """
    if codigo:
        query = db.query(Produto).filter(Produto.codigo == codigo)
        if tenant_id is not None:
            query = query.filter(Produto.tenant_id == tenant_id)

        if fornecedor_id:
            query_fornecedor = query.join(
                ProdutoFornecedor, ProdutoFornecedor.produto_id == Produto.id
            ).filter(
                ProdutoFornecedor.fornecedor_id == fornecedor_id,
                ProdutoFornecedor.ativo.is_(True),
            )
            if tenant_id is not None:
                query_fornecedor = query.join(
                    ProdutoFornecedor, ProdutoFornecedor.produto_id == Produto.id
                ).filter(
                    ProdutoFornecedor.fornecedor_id == fornecedor_id,
                    ProdutoFornecedor.ativo.is_(True),
                    ProdutoFornecedor.tenant_id == tenant_id,
                )

            produto_com_fornecedor = query_fornecedor.first()

            if produto_com_fornecedor:
                foi_inativo = not produto_com_fornecedor.ativo
                logger.info(
                    "Match por SKU + Fornecedor: %s", produto_com_fornecedor.nome
                )
                return (produto_com_fornecedor, 1.0, foi_inativo, "sku", codigo)

        produto = query.first()
        if produto:
            foi_inativo = not produto.ativo
            logger.info("Match por SKU: %s", produto.nome)
            return (produto, 1.0, foi_inativo, "sku", codigo)

    referencias_codigo_barras = []
    ean_tributario_normalizado = _codigo_barras_valido_nf(ean_tributario)
    ean_normalizado = _codigo_barras_valido_nf(ean)
    codigo_normalizado = normalizar_codigo_barras(codigo)

    if ean_tributario_normalizado:
        referencias_codigo_barras.append(ean_tributario_normalizado)
    if ean_normalizado and ean_normalizado not in referencias_codigo_barras:
        referencias_codigo_barras.append(ean_normalizado)
    if codigo_normalizado and codigo_normalizado not in referencias_codigo_barras:
        referencias_codigo_barras.append(codigo_normalizado)

    for referencia in referencias_codigo_barras:
        query = db.query(Produto).filter(
            or_(
                Produto.codigo_barras == referencia,
                Produto.gtin_ean == referencia,
                Produto.gtin_ean_tributario == referencia,
                Produto.codigos_barras_alternativos.ilike(f"%{referencia}%"),
            )
        )
        if tenant_id is not None:
            query = query.filter(Produto.tenant_id == tenant_id)

        produto = query.first()

        if produto:
            foi_inativo = not produto.ativo
            logger.info("Match por EAN: %s", produto.nome)
            return (produto, 1.0, foi_inativo, "codigo_barras", referencia)

    logger.info("Nenhum match encontrado para: %s (SKU: %s)", descricao[:50], codigo)
    return (None, 0, False, None, None)
