"""Helpers fiscais usados pela integracao Bling."""

import unicodedata
from collections import Counter
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.kit_config_fiscal_models import KitConfigFiscal
from app.produto_config_fiscal_models import ProdutoConfigFiscal
from app.produtos_models import Produto


def _limpar_texto_fiscal(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _primeiro_texto_fiscal(*values) -> Optional[str]:
    for value in values:
        text = _limpar_texto_fiscal(value)
        if text is not None:
            return text
    return None


def _sku_produto(produto) -> str:
    return (
        _limpar_texto_fiscal(getattr(produto, "codigo", None))
        or _limpar_texto_fiscal(getattr(produto, "codigo_barras", None))
        or f"ID {getattr(produto, 'id', 'sem-id')}"
    )


def _resolver_fiscal_item_nfe(
    db: Session, venda, item_venda
) -> Dict[str, Optional[str]]:
    produto = getattr(item_venda, "produto", None)
    if not produto:
        return {
            "ncm": None,
            "cest": None,
            "origem_mercadoria": None,
            "cfop": None,
            "cst_icms": None,
        }

    tenant_id = getattr(venda, "tenant_id", None) or getattr(produto, "tenant_id", None)
    kit_fiscal = None
    produto_fiscal = None

    if db is not None and tenant_id is not None:
        if getattr(produto, "tipo_produto", None) == "KIT":
            kit_fiscal = (
                db.query(KitConfigFiscal)
                .filter(
                    KitConfigFiscal.tenant_id == tenant_id,
                    KitConfigFiscal.produto_kit_id == produto.id,
                )
                .first()
            )

        produto_fiscal = (
            db.query(ProdutoConfigFiscal)
            .filter(
                ProdutoConfigFiscal.tenant_id == tenant_id,
                ProdutoConfigFiscal.produto_id == produto.id,
            )
            .first()
        )

    return {
        "ncm": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "ncm", None),
            getattr(produto_fiscal, "ncm", None),
            getattr(produto, "ncm", None),
        ),
        "cest": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "cest", None),
            getattr(produto_fiscal, "cest", None),
            getattr(produto, "cest", None),
        ),
        "origem_mercadoria": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "origem_mercadoria", None),
            getattr(produto_fiscal, "origem_mercadoria", None),
            getattr(produto, "origem", None),
        ),
        "cfop": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "cfop_venda", None),
            getattr(produto_fiscal, "cfop_venda", None),
            getattr(produto, "cfop", None),
            "5102",
        ),
        "cst_icms": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "cst_icms", None),
            getattr(produto_fiscal, "cst_icms", None),
            "102",
        ),
    }


_NCM_SUBSTITUICOES_SEGURAS = {
    "42010000": {
        "valor": "42010090",
        "motivo": "4201.00.00 e um codigo de familia; para guias, coleiras e enforcadores de outros materiais o subitem usual e 4201.00.90.",
    },
}

_NCM_POR_TERMO_PRODUTO = [
    (
        (
            "racao",
            "ração",
            "sache",
            "sachê",
            "petisco",
            "alimento para cao",
            "alimento para caes",
            "alimento para cão",
            "alimento para cães",
            "alimento para gato",
            "alimento para gatos",
        ),
        "23091000",
        "Produto parece alimento para caes ou gatos acondicionado para venda a retalho; confirme com o responsavel fiscal.",
    ),
    (
        ("guia", "coleira", "enforcador", "peitoral", "focinheira"),
        "42010090",
        "Produto parece acessorio para animais; sugestao conservadora para outros materiais.",
    ),
]


def _somente_digitos(value) -> str:
    return "".join(filter(str.isdigit, str(value or "")))


def _ncm_normalizado(value) -> Optional[str]:
    digits = _somente_digitos(value)
    return digits if digits else None


def _ncm_basico_aceitavel(value) -> bool:
    ncm = _ncm_normalizado(value)
    return bool(
        ncm
        and len(ncm) == 8
        and ncm != "00000000"
        and ncm not in _NCM_SUBSTITUICOES_SEGURAS
    )


def _texto_busca_produto(value) -> str:
    texto = str(value or "").lower()
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in normalizado if not unicodedata.combining(ch))


def _sugerir_ncm_por_historico(
    db: Session, tenant_id, produto
) -> Optional[Dict[str, str]]:
    if db is None or tenant_id is None or produto is None:
        return None

    filtros_base = [
        ProdutoConfigFiscal.tenant_id == tenant_id,
        ProdutoConfigFiscal.produto_id != produto.id,
        ProdutoConfigFiscal.ncm.isnot(None),
    ]

    filtros_escopo = []
    if getattr(produto, "categoria_id", None):
        filtros_escopo.append(Produto.categoria_id == produto.categoria_id)
    if getattr(produto, "departamento_id", None):
        filtros_escopo.append(Produto.departamento_id == produto.departamento_id)

    if not filtros_escopo:
        return None

    candidatos = (
        db.query(ProdutoConfigFiscal.ncm)
        .join(Produto, Produto.id == ProdutoConfigFiscal.produto_id)
        .filter(*filtros_base)
        .filter(*filtros_escopo[:1])
        .limit(50)
        .all()
    )
    ncms = [
        _ncm_normalizado(row[0]) for row in candidatos if _ncm_basico_aceitavel(row[0])
    ]
    if not ncms:
        return None

    ncm, ocorrencias = Counter(ncms).most_common(1)[0]
    return {
        "valor": ncm,
        "motivo": f"NCM mais usado em produtos parecidos cadastrados ({ocorrencias} ocorrencia(s)).",
    }


def _sugerir_ncm(
    produto, fiscal_item: Dict[str, Optional[str]], db: Session, tenant_id
) -> Optional[Dict[str, str]]:
    ncm_atual = _ncm_normalizado(fiscal_item.get("ncm"))
    if ncm_atual in _NCM_SUBSTITUICOES_SEGURAS:
        return _NCM_SUBSTITUICOES_SEGURAS[ncm_atual]

    historico = _sugerir_ncm_por_historico(db, tenant_id, produto)
    if historico:
        return historico

    nome = _texto_busca_produto(getattr(produto, "nome", ""))
    for termos, ncm, motivo in _NCM_POR_TERMO_PRODUTO:
        if any(_texto_busca_produto(termo) in nome for termo in termos):
            return {"valor": ncm, "motivo": motivo}

    return None


def prevalidar_fiscal_venda(venda, tipo_nota: str = "nfce", db: Session = None) -> Dict:
    tenant_id = getattr(venda, "tenant_id", None)
    correcoes = []
    bloqueios = []

    if not getattr(venda, "itens", None):
        bloqueios.append(
            {
                "campo": "itens",
                "mensagem": "Venda nao possui itens para emitir nota fiscal.",
            }
        )

    if tipo_nota == "nfe":
        cliente = getattr(venda, "cliente", None)
        cpf_cnpj = _somente_digitos(
            getattr(cliente, "cnpj", None) or getattr(cliente, "cpf", None)
        )
        if len(cpf_cnpj) != 14:
            bloqueios.append(
                {
                    "campo": "cliente.cnpj",
                    "mensagem": "NF-e requer cliente empresa com CNPJ cadastrado. Para pessoa fisica use NFC-e.",
                }
            )

    for item in getattr(venda, "itens", []) or []:
        produto = getattr(item, "produto", None)
        if not produto:
            bloqueios.append(
                {
                    "campo": "produto",
                    "mensagem": f"Item {getattr(item, 'id', '')}: produto nao vinculado.",
                }
            )
            continue

        fiscal_item = _resolver_fiscal_item_nfe(db, venda, item)
        sku = _sku_produto(produto)
        ncm_atual = _ncm_normalizado(fiscal_item.get("ncm"))
        origem_atual = _limpar_texto_fiscal(fiscal_item.get("origem_mercadoria"))

        if not _ncm_basico_aceitavel(ncm_atual):
            sugestao_ncm = _sugerir_ncm(produto, fiscal_item, db, tenant_id)
            if sugestao_ncm:
                correcoes.append(
                    {
                        "produto_id": produto.id,
                        "produto_nome": produto.nome,
                        "sku": sku,
                        "campo": "ncm",
                        "valor_atual": ncm_atual or "",
                        "valor_sugerido": sugestao_ncm["valor"],
                        "motivo": sugestao_ncm["motivo"],
                    }
                )
            else:
                bloqueios.append(
                    {
                        "produto_id": produto.id,
                        "produto_nome": produto.nome,
                        "sku": sku,
                        "campo": "ncm",
                        "mensagem": "NCM ausente ou invalido e o sistema ainda nao tem sugestao segura.",
                    }
                )

        if origem_atual is None:
            correcoes.append(
                {
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "sku": sku,
                    "campo": "origem_mercadoria",
                    "valor_atual": "",
                    "valor_sugerido": "0",
                    "motivo": "Padrao para mercadoria nacional quando a origem nao foi informada.",
                }
            )

    return {
        "success": True,
        "pode_emitir": not bloqueios and not correcoes,
        "requer_autorizacao": bool(correcoes),
        "correcoes": correcoes,
        "bloqueios": bloqueios,
    }


def aplicar_correcoes_fiscais_venda(
    venda, tipo_nota: str, db: Session, user_id=None
) -> Dict:
    validacao = prevalidar_fiscal_venda(venda, tipo_nota, db)
    if validacao["bloqueios"]:
        raise ValueError(
            "Existem pendencias fiscais sem sugestao segura para correcao automatica."
        )

    tenant_id = getattr(venda, "tenant_id", None)
    por_produto = {}
    for correcao in validacao["correcoes"]:
        por_produto.setdefault(correcao["produto_id"], []).append(correcao)

    for produto_id, correcoes in por_produto.items():
        config = (
            db.query(ProdutoConfigFiscal)
            .filter(
                ProdutoConfigFiscal.tenant_id == tenant_id,
                ProdutoConfigFiscal.produto_id == produto_id,
            )
            .first()
        )
        if not config:
            config = ProdutoConfigFiscal(
                tenant_id=tenant_id,
                produto_id=produto_id,
                herdado_da_empresa=False,
            )
            db.add(config)

        for correcao in correcoes:
            campo = correcao["campo"]
            valor = correcao["valor_sugerido"]
            if campo == "ncm":
                config.ncm = valor
            elif campo == "origem_mercadoria":
                config.origem_mercadoria = valor

        config.observacao_fiscal = (
            f"Correcao fiscal autorizada no PDV em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            + (f" por usuario {user_id}" if user_id else "")
        )

    return validacao
