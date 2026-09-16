"""Consulta assistida de referencias fiscais para produtos.

A consulta nunca grava dados. Resultados vindos do historico e do catalogo mestre
sao evidencias para revisao humana; as tabelas de codigos trazem a descricao da
documentacao oficial, mas nao decidem o enquadramento tributario da operacao.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.fiscal_catalogo_produtos_models import FiscalCatalogoProdutos

FONTE_NCM_OFICIAL = {
    "rotulo": "Classificação fiscal oficial (Receita Federal)",
    "url": "https://portalunico.siscomex.gov.br/classif/",
}
FONTE_SPED = {
    "rotulo": "Tabelas oficiais da EFD-Contribuições (SPED)",
    "url": "https://sped.rfb.gov.br/item/show/1616",
}
FONTE_NFE = {
    "rotulo": "Portal Nacional da NF-e",
    "url": "https://www.nfe.fazenda.gov.br/portal/principal.aspx",
}


CSOSN_REFERENCIAS = (
    ("101", "Tributada pelo Simples Nacional com permissão de crédito"),
    ("102", "Tributada pelo Simples Nacional sem permissão de crédito"),
    ("103", "Isenção do ICMS no Simples Nacional para faixa de receita bruta"),
    (
        "201",
        "Simples Nacional com crédito e cobrança do ICMS por substituição tributária",
    ),
    (
        "202",
        "Simples Nacional sem crédito e com cobrança do ICMS por substituição tributária",
    ),
    (
        "203",
        "Isenção no Simples Nacional e cobrança do ICMS por substituição tributária",
    ),
    ("300", "Imune"),
    ("400", "Não tributada pelo Simples Nacional"),
    ("500", "ICMS cobrado anteriormente por substituição tributária ou antecipação"),
    ("900", "Outros"),
)

PIS_COFINS_REFERENCIAS = (
    ("01", "Operação tributável com alíquota básica"),
    ("02", "Operação tributável com alíquota diferenciada"),
    ("03", "Operação tributável por unidade de medida"),
    ("04", "Operação tributável monofásica, revenda a alíquota zero"),
    ("05", "Operação tributável por substituição tributária"),
    ("06", "Operação tributável a alíquota zero"),
    ("07", "Operação isenta da contribuição"),
    ("08", "Operação sem incidência da contribuição"),
    ("09", "Operação com suspensão da contribuição"),
    ("49", "Outras operações de saída"),
    ("99", "Outras operações"),
)


def _chave_busca(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _somente_digitos(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _ncm_valido(value: Any) -> bool:
    digits = _somente_digitos(value)
    return len(digits) == 8 and digits != "00000000"


def _score_texto(consulta: str, nome: str, codigo: str | None = None) -> int:
    chave = _chave_busca(consulta)
    nome_chave = _chave_busca(nome)
    consulta_digitos = _somente_digitos(consulta)
    codigo_digitos = _somente_digitos(codigo)
    if consulta_digitos and codigo_digitos and consulta_digitos == codigo_digitos:
        return 100
    if chave and chave == nome_chave:
        return 95
    tokens = [token for token in chave.split() if len(token) >= 2]
    encontrados = sum(1 for token in tokens if token in nome_chave)
    if not tokens or not encontrados:
        return 0
    return min(90, 35 + int(55 * encontrados / len(tokens)))


def _referencias_codigo() -> dict[str, Any]:
    return {
        "csosn": [
            {"codigo": codigo, "descricao": descricao, "fonte": FONTE_NFE}
            for codigo, descricao in CSOSN_REFERENCIAS
        ],
        "pis": [
            {"codigo": codigo, "descricao": descricao, "fonte": FONTE_SPED}
            for codigo, descricao in PIS_COFINS_REFERENCIAS
        ],
        "cofins": [
            {"codigo": codigo, "descricao": descricao, "fonte": FONTE_SPED}
            for codigo, descricao in PIS_COFINS_REFERENCIAS
        ],
    }


def _buscar_historico_tenant(
    db: Session, tenant_id: UUID, consulta: str, limite: int
) -> list[dict[str, Any]]:
    from app.produto_config_fiscal_models import ProdutoConfigFiscal
    from app.produtos_catalogo_models import Produto

    padrao = f"%{consulta.strip()}%"
    digits = _somente_digitos(consulta)
    filtros = [Produto.nome.ilike(padrao), Produto.codigo.ilike(padrao)]
    if digits:
        filtros.extend(
            [
                Produto.codigo_barras == digits,
                Produto.ncm == digits,
                ProdutoConfigFiscal.ncm == digits,
            ]
        )
    rows = (
        db.query(Produto, ProdutoConfigFiscal)
        .outerjoin(
            ProdutoConfigFiscal,
            (ProdutoConfigFiscal.produto_id == Produto.id)
            & (ProdutoConfigFiscal.tenant_id == tenant_id),
        )
        .filter(Produto.tenant_id == tenant_id, or_(*filtros))
        .limit(max(20, limite * 5))
        .all()
    )
    results = []
    for produto, fiscal in rows:
        ncm = getattr(fiscal, "ncm", None) or produto.ncm
        if not _ncm_valido(ncm):
            continue
        score = _score_texto(
            consulta, produto.nome, produto.codigo_barras or produto.codigo
        )
        if score <= 0:
            continue
        results.append(
            {
                "ncm": _somente_digitos(ncm),
                "cest": _somente_digitos(getattr(fiscal, "cest", None) or produto.cest)
                or None,
                "descricao": produto.nome,
                "fonte": "cadastro_confirmado_da_empresa",
                "fonte_rotulo": "cadastro fiscal já usado por esta empresa",
                "score": score,
                "qualidade": 100 if fiscal else 75,
            }
        )
    return results


def _buscar_catalogo_mestre(
    db: Session, consulta: str, limite: int
) -> list[dict[str, Any]]:
    from app.catalogo_mestre_models import CatalogoMestreProduto

    padrao = f"%{consulta.strip()}%"
    digits = _somente_digitos(consulta)
    filtros = [CatalogoMestreProduto.nome.ilike(padrao)]
    if digits:
        filtros.extend(
            [
                CatalogoMestreProduto.gtin == digits,
                CatalogoMestreProduto.ncm == digits,
            ]
        )
    rows = (
        db.query(CatalogoMestreProduto)
        .filter(
            CatalogoMestreProduto.ativo.is_(True),
            CatalogoMestreProduto.ncm.isnot(None),
            or_(*filtros),
        )
        .limit(max(30, limite * 8))
        .all()
    )
    results = []
    for produto in rows:
        if not _ncm_valido(produto.ncm):
            continue
        score = _score_texto(consulta, produto.nome, produto.gtin)
        if score <= 0:
            continue
        results.append(
            {
                "ncm": _somente_digitos(produto.ncm),
                "cest": _somente_digitos(produto.cest) or None,
                "descricao": produto.nome,
                "fonte": "catalogo_mestre_corepet",
                "fonte_rotulo": "catálogo mestre do CorePet",
                "score": score,
                "qualidade": int(produto.qualidade_percentual or 0),
            }
        )
    return results


def _consolidar_resultados(
    rows: list[dict[str, Any]], limite: int
) -> list[dict[str, Any]]:
    grupos: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    for row in rows:
        grupos.setdefault((row["ncm"], row.get("cest")), []).append(row)

    results = []
    for (ncm, cest), items in grupos.items():
        items.sort(key=lambda item: (item["score"], item["qualidade"]), reverse=True)
        best = items[0]
        ocorrencias = len(items)
        fontes = Counter(item["fonte_rotulo"] for item in items)
        score = max(item["score"] for item in items)
        quality = max(item["qualidade"] for item in items)
        if ocorrencias >= 3 and score >= 70:
            confianca, percentual = "alta", min(94, 82 + ocorrencias)
        elif score >= 70 or quality >= 75:
            confianca, percentual = "media", min(79, max(60, score - 10))
        else:
            confianca, percentual = "baixa", min(55, max(30, score))
        results.append(
            {
                "ncm": ncm,
                "cest": cest,
                "descricao": best["descricao"],
                "fonte": " + ".join(fontes.keys()),
                "ocorrencias": ocorrencias,
                "confianca": confianca,
                "confianca_percentual": percentual,
                "fonte_oficial": FONTE_NCM_OFICIAL,
                "aviso": (
                    "Confira a descrição e a composição do produto na classificação oficial "
                    "antes de aplicar. Produtos com nomes parecidos podem ter NCM diferente."
                ),
                "_ordem": (percentual, ocorrencias, score),
            }
        )
    results.sort(key=lambda item: item["_ordem"], reverse=True)
    for item in results:
        item.pop("_ordem", None)
    return results[:limite]


def pesquisar_base_fiscal(
    db: Session,
    tenant_id: UUID,
    consulta: str,
    limite: int = 8,
) -> dict[str, Any]:
    consulta = str(consulta or "").strip()
    if len(consulta) < 2:
        return {
            "consulta": consulta,
            "resultados": [],
            "referencias": _referencias_codigo(),
            "fontes": [FONTE_NCM_OFICIAL, FONTE_SPED, FONTE_NFE],
        }

    rows: list[dict[str, Any]] = []
    for loader in (
        lambda: _buscar_historico_tenant(db, tenant_id, consulta, limite),
        lambda: _buscar_catalogo_mestre(db, consulta, limite),
    ):
        try:
            with db.begin_nested():
                rows.extend(loader())
        except SQLAlchemyError:
            continue

    return {
        "consulta": consulta,
        "resultados": _consolidar_resultados(rows, limite),
        "referencias": _referencias_codigo(),
        "fontes": [FONTE_NCM_OFICIAL, FONTE_SPED, FONTE_NFE],
    }


def sugerir_fiscal_por_descricao(db: Session, descricao_produto: str):
    """Mantém a sugestão legada do catálogo fiscal sem quebrar a transação."""

    descricao = _chave_busca(descricao_produto)
    sugestoes = []
    try:
        with db.begin_nested():
            registros = (
                db.query(FiscalCatalogoProdutos)
                .filter(FiscalCatalogoProdutos.ativo.is_(True))
                .all()
            )
    except SQLAlchemyError:
        return []

    for registro in registros:
        palavras = [_chave_busca(p) for p in registro.palavras_chave.split(",")]
        score = sum(1 for palavra in palavras if palavra and palavra in descricao)
        if score <= 0:
            continue
        sugestoes.append(
            {
                "categoria_fiscal": registro.categoria_fiscal,
                "ncm": registro.ncm,
                "cest": registro.cest,
                "cst_icms": registro.cst_icms,
                "icms_st": registro.icms_st,
                "pis_cst": registro.pis_cst,
                "cofins_cst": registro.cofins_cst,
                "observacao": registro.observacao,
                "score": score,
            }
        )
    sugestoes.sort(key=lambda item: item["score"], reverse=True)
    return sugestoes
