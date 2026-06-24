from __future__ import annotations

from unicodedata import normalize

BONIFICACAO_CFOPS = {"1910", "2910", "5910", "6910", "1949", "2949", "5949", "6949"}
BONIFICACAO_TERMOS = ("bonificacao", "brinde", "amostra", "remessa")


def _texto_normalizado(valor: object) -> str:
    texto = str(valor or "").strip().lower()
    sem_acentos = normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acentos


def _valor_float(valor: object) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _tem_cobranca(dados_xml: dict) -> bool:
    duplicatas = dados_xml.get("duplicatas") or dados_xml.get("cobrancas") or []
    return any(
        _valor_float(item.get("valor") or item.get("valor_duplicata") or 0) > 0
        for item in duplicatas
        if isinstance(item, dict)
    )


def _cfops(dados_xml: dict) -> set[str]:
    return {
        str(item.get("cfop") or "").strip()
        for item in (dados_xml.get("itens") or [])
        if isinstance(item, dict) and str(item.get("cfop") or "").strip()
    }


def detectar_contexto_processamento(dados_xml: dict) -> dict:
    natureza = _texto_normalizado(dados_xml.get("natureza_operacao"))
    texto_indica_bonificacao = any(
        _texto_normalizado(termo) in natureza for termo in BONIFICACAO_TERMOS
    )
    cfop_indica_bonificacao = bool(_cfops(dados_xml) & BONIFICACAO_CFOPS)
    tem_cobranca = _tem_cobranca(dados_xml)
    bonificacao = (
        texto_indica_bonificacao or cfop_indica_bonificacao
    ) and not tem_cobranca

    return {
        "contexto": "bonificacao" if bonificacao else "nota_comum",
        "bonificacao": bonificacao,
        "tem_cobranca": tem_cobranca,
        "cfops": sorted(_cfops(dados_xml)),
    }


def sugerir_acoes_processamento(dados_xml: dict) -> dict:
    contexto = detectar_contexto_processamento(dados_xml)
    if contexto["bonificacao"]:
        return {
            "contexto": "bonificacao",
            "mensagem": (
                "Bonificacao detectada: estoque e validade serao lancados usando "
                "o custo atual do sistema; custo, preco e financeiro ficaram desmarcados."
            ),
            "acoes": {
                "lancar_estoque": True,
                "atualizar_custo": False,
                "atualizar_preco_venda": False,
                "gerar_contas_pagar": False,
            },
        }

    return {
        "contexto": "nota_comum",
        "mensagem": "Nota comum detectada: estoque, custo e contas a pagar serao processados.",
        "acoes": {
            "lancar_estoque": True,
            "atualizar_custo": True,
            "atualizar_preco_venda": False,
            "gerar_contas_pagar": True,
        },
    }


def resolver_custo_operacional_entrada(
    *, custo_nf: float, custo_atual_sistema: float | None, atualizar_custo: bool
) -> float:
    if atualizar_custo:
        return _valor_float(custo_nf)

    custo_atual = _valor_float(custo_atual_sistema)
    if custo_atual > 0:
        return custo_atual

    return _valor_float(custo_nf)
