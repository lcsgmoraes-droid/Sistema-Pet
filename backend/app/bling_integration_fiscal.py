"""Helpers fiscais usados pela integracao Bling."""

import unicodedata
from collections import Counter
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.kit_config_fiscal_models import KitConfigFiscal
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.produto_config_fiscal_models import ProdutoConfigFiscal
from app.produtos_models import Produto
from app.services.fiscal_sugestao_service import sugerir_fiscal_por_descricao


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


def _cfops_venda_por_destino(cfop_especifico, empresa_fiscal):
    """Separa o CFOP especifico por destino sem reaproveitar 6xxx em venda interna."""

    specific = _limpar_texto_fiscal(cfop_especifico)
    internal = specific if specific and specific.startswith("5") else None
    interstate = specific if specific and specific.startswith("6") else None
    return (
        _primeiro_texto_fiscal(
            internal, getattr(empresa_fiscal, "cfop_venda_interna", None)
        ),
        _primeiro_texto_fiscal(
            interstate, getattr(empresa_fiscal, "cfop_venda_interestadual", None)
        ),
    )


def _valor_fiscal_produto(produto_fiscal, produto, campo_v2, campo_legado):
    """Usa o cadastro fiscal atual como fonte autoritativa, inclusive se vazio."""

    if produto_fiscal is not None:
        return getattr(produto_fiscal, campo_v2, None)
    return getattr(produto, campo_legado, None)


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
    empresa_fiscal = None

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
        empresa_fiscal = (
            db.query(EmpresaConfigFiscal)
            .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
            .first()
        )

    cfop_especifico = _primeiro_texto_fiscal(
        getattr(kit_fiscal, "cfop_venda", None),
        _valor_fiscal_produto(produto_fiscal, produto, "cfop_venda", "cfop"),
    )
    lote = getattr(item_venda, "lote", None)
    lote_icms_st = getattr(lote, "fiscal_icms_st", None)
    produto_icms_st = getattr(produto_fiscal, "icms_st", None)
    icms_st = lote_icms_st if lote_icms_st is not None else produto_icms_st
    regime = str(getattr(empresa_fiscal, "regime_tributario", "") or "").casefold()
    empresa_simples = bool(
        empresa_fiscal
        and (getattr(empresa_fiscal, "simples_ativo", False) or "simples" in regime)
    )
    substituido_simples = bool(icms_st and empresa_simples)
    if substituido_simples:
        cfop_especifico = "5405"
    cfop_interno, cfop_interestadual = _cfops_venda_por_destino(
        cfop_especifico, empresa_fiscal
    )

    return {
        "ncm": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "ncm", None),
            getattr(lote, "fiscal_ncm", None),
            _valor_fiscal_produto(produto_fiscal, produto, "ncm", "ncm"),
        ),
        "cest": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "cest", None),
            getattr(lote, "fiscal_cest", None),
            _valor_fiscal_produto(produto_fiscal, produto, "cest", "cest"),
        ),
        "origem_mercadoria": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "origem_mercadoria", None),
            getattr(lote, "fiscal_origem_mercadoria", None),
            _valor_fiscal_produto(
                produto_fiscal, produto, "origem_mercadoria", "origem"
            ),
        ),
        "cfop": _primeiro_texto_fiscal(
            cfop_especifico,
            cfop_interno,
            cfop_interestadual,
        ),
        "cfop_interno": cfop_interno,
        "cfop_interestadual": cfop_interestadual,
        "cfop_interestadual_nao_contribuinte": (
            "6108" if substituido_simples else cfop_interestadual
        ),
        "cst_icms": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "cst_icms", None),
            "500" if substituido_simples else None,
            getattr(produto_fiscal, "cst_icms", None),
        ),
        "icms_st": bool(icms_st),
        "icms_aliquota": (
            next(
                (
                    value
                    for value in (
                        getattr(kit_fiscal, "icms_aliquota", None),
                        getattr(produto_fiscal, "icms_aliquota", None),
                        getattr(empresa_fiscal, "icms_aliquota_interna", None),
                    )
                    if value is not None
                ),
                None,
            )
            if not substituido_simples
            else None
        ),
        "pis_cst": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "pis_cst", None),
            getattr(produto_fiscal, "pis_cst", None),
            getattr(empresa_fiscal, "pis_cst_padrao", None),
        ),
        "pis_aliquota": next(
            (
                value
                for value in (
                    getattr(kit_fiscal, "pis_aliquota", None),
                    getattr(produto_fiscal, "pis_aliquota", None),
                    getattr(empresa_fiscal, "pis_aliquota", None),
                )
                if value is not None
            ),
            None,
        ),
        "cofins_cst": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "cofins_cst", None),
            getattr(produto_fiscal, "cofins_cst", None),
            getattr(empresa_fiscal, "cofins_cst_padrao", None),
        ),
        "cofins_aliquota": next(
            (
                value
                for value in (
                    getattr(kit_fiscal, "cofins_aliquota", None),
                    getattr(produto_fiscal, "cofins_aliquota", None),
                    getattr(empresa_fiscal, "cofins_aliquota", None),
                )
                if value is not None
            ),
            None,
        ),
    }


_NCM_SUBSTITUICOES_SEGURAS = {
    "42010000": {
        "valor": "42010090",
        "motivo": "4201.00.00 e um codigo de familia; para guias, coleiras e enforcadores de outros materiais o subitem usual e 4201.00.90.",
        "fonte_sugestao": "correcao_de_codigo_incompleto",
        "confianca": "alta",
        "confianca_percentual": 95,
        "preenchimento_automatico": True,
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
) -> Optional[Dict[str, object]]:
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
    total = len(ncms)
    consenso = ocorrencias / total
    nome_escopo = _texto_busca_produto(
        getattr(getattr(produto, "categoria", None), "nome", "")
        or getattr(getattr(produto, "departamento", None), "nome", "")
    )
    escopo_generico = any(
        termo in nome_escopo for termo in ("diversos", "outros", "geral")
    )

    if ocorrencias >= 5 and consenso >= 0.8 and not escopo_generico:
        confianca, percentual = "alta", 90
    elif ocorrencias >= 3 and consenso >= 0.7 and not escopo_generico:
        confianca, percentual = "media", 72
    else:
        confianca, percentual = "baixa", min(55, 30 + ocorrencias * 8)

    return {
        "valor": ncm,
        "motivo": (
            f"Encontrado em {ocorrencias} de {total} produto(s) do mesmo grupo. "
            "A classificacao deve ser conferida pela descricao e composicao do item."
        ),
        "fonte_sugestao": "historico_de_produtos_semelhantes",
        "confianca": confianca,
        "confianca_percentual": percentual,
        "preenchimento_automatico": confianca == "alta",
    }


def _sugerir_ncm(
    produto, fiscal_item: Dict[str, Optional[str]], db: Session, tenant_id
) -> Optional[Dict[str, object]]:
    ncm_atual = _ncm_normalizado(fiscal_item.get("ncm"))
    if ncm_atual in _NCM_SUBSTITUICOES_SEGURAS:
        return _NCM_SUBSTITUICOES_SEGURAS[ncm_atual]

    historico = _sugerir_ncm_por_historico(db, tenant_id, produto)
    if historico:
        return historico

    nome = _texto_busca_produto(getattr(produto, "nome", ""))
    for termos, ncm, motivo in _NCM_POR_TERMO_PRODUTO:
        if any(_texto_busca_produto(termo) in nome for termo in termos):
            return {
                "valor": ncm,
                "motivo": motivo,
                "fonte_sugestao": "palavras_da_descricao",
                "confianca": "baixa",
                "confianca_percentual": 45,
                "preenchimento_automatico": False,
            }

    return None


def _melhor_sugestao_catalogo(db: Session, produto) -> Optional[Dict]:
    if db is None or produto is None:
        return None
    try:
        # O catalogo e uma fonte opcional. Execute a consulta em um savepoint para
        # que uma instalacao sem essa tabela (ou com o catalogo indisponivel) nao
        # aborte a transacao principal da pre-validacao fiscal.
        with db.begin_nested():
            sugestoes = sugerir_fiscal_por_descricao(
                db, getattr(produto, "nome", None) or ""
            )
        return sugestoes[0] if sugestoes else None
    except Exception:
        # O catalogo auxilia o preenchimento, mas nunca pode impedir a validacao.
        return None


def _config_fiscal_empresa(db: Session, tenant_id):
    if db is None or tenant_id is None:
        return None
    return (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )


def _empresa_no_simples(empresa_fiscal) -> bool:
    regime = str(getattr(empresa_fiscal, "regime_tributario", "") or "").casefold()
    return bool(
        empresa_fiscal
        and (getattr(empresa_fiscal, "simples_ativo", False) or "simples" in regime)
    )


def _sugerir_tributo_ausente(
    campo: str,
    fiscal_item: Dict[str, Optional[str]],
    empresa_fiscal,
    sugestao_catalogo: Optional[Dict],
) -> Optional[Dict[str, object]]:
    campo_catalogo = {
        "cst_icms": "cst_icms",
        "pis_cst": "pis_cst",
        "cofins_cst": "cofins_cst",
    }.get(campo)
    valor_catalogo = (
        _limpar_texto_fiscal(sugestao_catalogo.get(campo_catalogo))
        if sugestao_catalogo and campo_catalogo
        else None
    )
    if valor_catalogo:
        score = int(sugestao_catalogo.get("score") or 0)
        confianca = "alta" if score >= 2 else "media"
        return {
            "valor": valor_catalogo,
            "motivo": (
                sugestao_catalogo.get("observacao")
                or f"Catalogo fiscal associado a {sugestao_catalogo.get('categoria_fiscal') or 'este tipo de produto'}."
            ),
            "fonte_sugestao": "catalogo_fiscal",
            "confianca": confianca,
            "confianca_percentual": 88 if confianca == "alta" else 68,
            "preenchimento_automatico": confianca == "alta",
        }

    if campo in {"pis_cst", "cofins_cst"}:
        atributo = "pis_cst_padrao" if campo == "pis_cst" else "cofins_cst_padrao"
        valor_empresa = _limpar_texto_fiscal(getattr(empresa_fiscal, atributo, None))
        if valor_empresa:
            return {
                "valor": valor_empresa,
                "motivo": "Valor padrao definido na configuracao fiscal desta empresa.",
                "fonte_sugestao": "configuracao_fiscal_da_empresa",
                "confianca": "alta",
                "confianca_percentual": 95,
                "preenchimento_automatico": True,
            }

    if not _empresa_no_simples(empresa_fiscal):
        return None

    if campo == "cst_icms" and fiscal_item.get("icms_st"):
        return {
            "valor": "500",
            "motivo": (
                "O produto esta marcado como ICMS-ST e a empresa esta no Simples Nacional; "
                "o CSOSN 500 indica imposto cobrado anteriormente por substituicao tributaria."
            ),
            "fonte_sugestao": "xml_ou_cadastro_do_produto_e_regime_da_empresa",
            "confianca": "alta",
            "confianca_percentual": 94,
            "preenchimento_automatico": True,
        }

    if campo == "cst_icms":
        return {
            "valor": "102",
            "motivo": (
                "Possivel CSOSN para venda pelo Simples Nacional sem permissao de credito. "
                "Nao foi encontrada evidencia suficiente sobre ICMS-ST ou beneficio fiscal deste produto."
            ),
            "fonte_sugestao": "regime_da_empresa_sem_historico_do_produto",
            "confianca": "baixa",
            "confianca_percentual": 42,
            "preenchimento_automatico": False,
        }

    if campo in {"pis_cst", "cofins_cst"}:
        return {
            "valor": "49",
            "motivo": (
                "Possivel enquadramento como outras operacoes de saida para empresa do Simples. "
                "A empresa ainda nao definiu um CST padrao e nao ha historico fiscal confiavel para este produto."
            ),
            "fonte_sugestao": "regime_da_empresa_sem_padrao_configurado",
            "confianca": "baixa",
            "confianca_percentual": 40,
            "preenchimento_automatico": False,
        }

    return None


def prevalidar_produtos_fiscais_venda(
    venda, db: Session = None, *, exigir_documento_completo: bool = False
) -> Dict:
    tenant_id = getattr(venda, "tenant_id", None)
    empresa_fiscal = _config_fiscal_empresa(db, tenant_id)
    correcoes = []
    bloqueios = []

    if not getattr(venda, "itens", None):
        bloqueios.append(
            {
                "campo": "itens",
                "mensagem": "Venda nao possui itens para emitir nota fiscal.",
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
        dados_produto = {
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "produto_tipo": getattr(produto, "tipo_produto", None),
            "sku": sku,
            "codigo_barras": getattr(produto, "codigo_barras", None),
        }
        ncm_atual = _ncm_normalizado(fiscal_item.get("ncm"))
        origem_atual = _limpar_texto_fiscal(fiscal_item.get("origem_mercadoria"))
        sugestao_catalogo = _melhor_sugestao_catalogo(db, produto)

        if not _ncm_basico_aceitavel(ncm_atual):
            sugestao_ncm = _sugerir_ncm(produto, fiscal_item, db, tenant_id)
            if sugestao_ncm:
                correcoes.append(
                    {
                        **dados_produto,
                        "campo": "ncm",
                        "valor_atual": ncm_atual or "",
                        "valor_sugerido": sugestao_ncm["valor"],
                        "motivo": sugestao_ncm["motivo"],
                        "fonte_sugestao": sugestao_ncm.get("fonte_sugestao"),
                        "confianca": sugestao_ncm.get("confianca"),
                        "confianca_percentual": sugestao_ncm.get(
                            "confianca_percentual"
                        ),
                        "preenchimento_automatico": sugestao_ncm.get(
                            "preenchimento_automatico", False
                        ),
                    }
                )
            else:
                bloqueios.append(
                    {
                        **dados_produto,
                        "campo": "ncm",
                        "mensagem": "NCM ausente ou invalido e o sistema ainda nao tem sugestao segura.",
                    }
                )

        if origem_atual is None:
            correcoes.append(
                {
                    **dados_produto,
                    "campo": "origem_mercadoria",
                    "valor_atual": "",
                    "valor_sugerido": "0",
                    "motivo": "Padrao para mercadoria nacional quando a origem nao foi informada.",
                    "fonte_sugestao": "padrao_operacional_sem_origem_informada",
                    "confianca": "baixa",
                    "confianca_percentual": 45,
                    "preenchimento_automatico": False,
                }
            )

        campos_obrigatorios = (
            (
                ("cfop", "CFOP", None),
                ("cst_icms", "CSOSN/CST de ICMS", "cst_icms"),
                ("pis_cst", "CST de PIS", "pis_cst"),
                ("cofins_cst", "CST de COFINS", "cofins_cst"),
            )
            if exigir_documento_completo
            else ()
        )
        for campo, rotulo, _campo_catalogo in campos_obrigatorios:
            valor_atual = _limpar_texto_fiscal(fiscal_item.get(campo))
            if valor_atual:
                continue
            sugestao = _sugerir_tributo_ausente(
                campo,
                fiscal_item,
                empresa_fiscal,
                sugestao_catalogo,
            )
            if sugestao:
                correcoes.append(
                    {
                        **dados_produto,
                        "campo": campo,
                        "valor_atual": "",
                        "valor_sugerido": sugestao["valor"],
                        "motivo": sugestao["motivo"],
                        "fonte_sugestao": sugestao["fonte_sugestao"],
                        "confianca": sugestao["confianca"],
                        "confianca_percentual": sugestao["confianca_percentual"],
                        "preenchimento_automatico": sugestao[
                            "preenchimento_automatico"
                        ],
                    }
                )
            else:
                bloqueios.append(
                    {
                        **dados_produto,
                        "campo": campo,
                        "mensagem": f"{rotulo} nao informado. Preencha para continuar.",
                    }
                )

    return {
        "success": True,
        "pode_emitir": not bloqueios and not correcoes,
        "requer_autorizacao": bool(correcoes),
        "correcoes": correcoes,
        "bloqueios": bloqueios,
        "contexto_fiscal": {
            "regime_tributario": getattr(empresa_fiscal, "regime_tributario", None),
            "uf": getattr(empresa_fiscal, "uf", None),
            "simples_nacional": _empresa_no_simples(empresa_fiscal),
        },
    }


def prevalidar_fiscal_venda(venda, tipo_nota: str = "nfce", db: Session = None) -> Dict:
    validacao = prevalidar_produtos_fiscais_venda(venda, db)
    bloqueios = list(validacao["bloqueios"])

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

    return {
        **validacao,
        "pode_emitir": not bloqueios and not validacao["correcoes"],
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
            elif campo == "cfop":
                config.cfop_venda = valor
            elif campo == "cst_icms":
                config.cst_icms = valor
            elif campo == "pis_cst":
                config.pis_cst = valor
            elif campo == "cofins_cst":
                config.cofins_cst = valor

        config.observacao_fiscal = (
            f"Correcao fiscal autorizada no PDV em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            + (f" por usuario {user_id}" if user_id else "")
        )

    return validacao
