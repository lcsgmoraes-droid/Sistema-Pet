from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.dre_canais.base import CANAIS_CONFIG, ORIGENS_DRE, _decimal
from app.dre_canais.schemas import LinhaCanal


def _somar(dados_canais: Dict[str, Dict], campo: str) -> Decimal:
    return sum(
        (_decimal(dados.get(campo, 0)) for dados in dados_canais.values()), Decimal("0")
    )


def _percentual(valor: Decimal, receita_bruta_total: Decimal) -> float:
    if receita_bruta_total <= 0:
        return 0.0
    return round(float(valor / receita_bruta_total * Decimal("100")), 2)


def _linha_total(
    descricao: str,
    valor: Decimal,
    receita_bruta_total: Decimal,
    tipo: str,
    cor: str,
    cor_bg: str,
    origem: Optional[str] = None,
    campo: Optional[str] = None,
) -> LinhaCanal:
    percentual = (
        Decimal("100")
        if descricao.startswith("(+)") and receita_bruta_total > 0
        else Decimal(str(_percentual(valor, receita_bruta_total)))
    )
    return LinhaCanal(
        descricao=descricao,
        valor=float(valor),
        percentual=float(percentual),
        cor=cor,
        cor_bg=cor_bg,
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo=tipo,
        origem=origem,
        campo=campo,
        detalhavel=False,
    )


def _linha_canal(
    canal: str,
    descricao: str,
    valor: Decimal,
    receita_bruta_total: Decimal,
    tipo: str,
    origem: Optional[str] = None,
    campo: Optional[str] = None,
) -> LinhaCanal:
    config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG["loja_fisica"])
    return LinhaCanal(
        descricao=f"{descricao} {config['nome']}",
        valor=float(valor),
        percentual=_percentual(valor, receita_bruta_total),
        cor=config["cor"],
        cor_bg="#ffffff",
        canal=canal,
        canal_nome=config["nome"],
        nivel=1,
        tipo=tipo,
        origem=origem,
        campo=campo,
        detalhavel=bool(campo),
    )


def _adicionar_linhas_campo(
    linhas: List[LinhaCanal],
    dados_canais: Dict[str, Dict],
    receita_bruta_total: Decimal,
    campo: str,
    descricao: str,
    tipo: str,
    origem: Optional[str] = None,
) -> None:
    origem_linha = origem or ORIGENS_DRE.get(campo)
    for canal in sorted(dados_canais.keys()):
        linhas.append(
            _linha_canal(
                canal,
                descricao,
                _decimal(dados_canais[canal].get(campo, 0)),
                receita_bruta_total,
                tipo,
                origem_linha,
                campo,
            )
        )


def montar_linhas_dre_competencia(
    dados_canais: Dict[str, Dict],
) -> tuple[List[LinhaCanal], Dict[str, Any]]:
    receita_produtos_total = _somar(dados_canais, "receita_produtos")
    receita_servicos_total = _somar(dados_canais, "receita_servicos")
    receita_frete_total = _somar(dados_canais, "receita_frete")
    receita_bruta_total = (
        receita_produtos_total + receita_servicos_total + receita_frete_total
    )

    descontos_total = _somar(dados_canais, "descontos")
    impostos_total = _somar(dados_canais, "impostos")
    deducoes_total = descontos_total + impostos_total
    receita_liquida_total = receita_bruta_total - deducoes_total

    cmv_total = _somar(dados_canais, "cmv") + _somar(dados_canais, "fretes_compras")
    lucro_bruto_total = receita_liquida_total - cmv_total

    despesas_variaveis_total = (
        _somar(dados_canais, "taxas_cartao")
        + _somar(dados_canais, "taxas_marketplace")
        + _somar(dados_canais, "repasse_entrega")
        + _somar(dados_canais, "taxa_operacional_entrega")
        + _somar(dados_canais, "comissoes")
        + _somar(dados_canais, "campanhas")
    )
    despesas_fixas_total = (
        _somar(dados_canais, "despesas_pessoal")
        + _somar(dados_canais, "despesas_administrativas")
        + _somar(dados_canais, "despesas_comerciais")
        + _somar(dados_canais, "despesas_financeiras")
        + _somar(dados_canais, "outras_despesas")
    )
    despesas_operacionais_total = despesas_variaveis_total + despesas_fixas_total
    resultado_operacional_total = lucro_bruto_total - despesas_operacionais_total
    lucro_liquido_total = resultado_operacional_total

    linhas: List[LinhaCanal] = []

    linhas.append(
        _linha_total(
            "(+) RECEITA BRUTA",
            receita_bruta_total,
            receita_bruta_total,
            "receita",
            "#111827",
            "#f3f4f6",
            ORIGENS_DRE["receita_bruta_total"],
        )
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "receita_produtos",
        "Vendas de Produtos",
        "receita",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "receita_servicos",
        "Vendas de Servicos",
        "receita",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "receita_frete",
        "Receita de Frete",
        "receita",
    )

    linhas.append(
        _linha_total(
            "(-) DEDUCOES DA RECEITA",
            deducoes_total,
            receita_bruta_total,
            "deducao",
            "#dc2626",
            "#fef2f2",
            ORIGENS_DRE["deducoes_total"],
        )
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "descontos",
        "Descontos Concedidos",
        "deducao",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "impostos",
        "Impostos sobre Vendas",
        "deducao",
    )

    linhas.append(
        _linha_total(
            "(=) RECEITA LIQUIDA",
            receita_liquida_total,
            receita_bruta_total,
            "receita",
            "#059669",
            "#d1fae5",
            ORIGENS_DRE["receita_liquida_total"],
        )
    )

    linhas.append(
        _linha_total(
            "(-) CUSTO DAS MERCADORIAS VENDIDAS (CMV)",
            cmv_total,
            receita_bruta_total,
            "custo",
            "#dc2626",
            "#fef2f2",
            ORIGENS_DRE["cmv_total"],
        )
    )
    _adicionar_linhas_campo(
        linhas, dados_canais, receita_bruta_total, "cmv", "CMV", "custo"
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "fretes_compras",
        "Fretes sobre Compras",
        "custo",
    )

    linhas.append(
        _linha_total(
            "(=) LUCRO BRUTO",
            lucro_bruto_total,
            receita_bruta_total,
            "lucro",
            "#059669",
            "#d1fae5",
            ORIGENS_DRE["lucro_bruto_total"],
        )
    )

    linhas.append(
        _linha_total(
            "(-) CUSTOS E DESPESAS VARIAVEIS DE VENDA",
            despesas_variaveis_total,
            receita_bruta_total,
            "despesa",
            "#dc2626",
            "#fff7ed",
            ORIGENS_DRE["despesas_variaveis_total"],
        )
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "taxas_cartao",
        "Taxas de Cartao/Meios de Pagamento",
        "despesa",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "taxas_marketplace",
        "Taxas de Marketplace",
        "despesa",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "repasse_entrega",
        "Repasse/Custo de Entrega",
        "despesa",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "taxa_operacional_entrega",
        "Custo Operacional de Entrega",
        "despesa",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "comissoes",
        "Comissoes de Venda",
        "despesa",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "campanhas",
        "Campanhas, Cupons e Cashback",
        "despesa",
    )

    linhas.append(
        _linha_total(
            "(-) DESPESAS OPERACIONAIS FIXAS/ADMINISTRATIVAS",
            despesas_fixas_total,
            receita_bruta_total,
            "despesa",
            "#dc2626",
            "#fef2f2",
            ORIGENS_DRE["despesas_fixas_total"],
        )
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "despesas_pessoal",
        "Folha, Salarios e Encargos",
        "despesa",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "despesas_administrativas",
        "Aluguel/Ocupacao e Administrativo",
        "despesa",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "despesas_comerciais",
        "Marketing e Comercial",
        "despesa",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "despesas_financeiras",
        "Despesas Financeiras",
        "despesa",
    )
    _adicionar_linhas_campo(
        linhas,
        dados_canais,
        receita_bruta_total,
        "outras_despesas",
        "Outras Despesas",
        "despesa",
    )

    linhas.append(
        _linha_total(
            "(=) RESULTADO OPERACIONAL",
            resultado_operacional_total,
            receita_bruta_total,
            "lucro",
            "#059669",
            "#d1fae5",
            ORIGENS_DRE["resultado_operacional_total"],
        )
    )
    linhas.append(
        _linha_total(
            "(=) LUCRO/PREJUIZO LIQUIDO",
            lucro_liquido_total,
            receita_bruta_total,
            "lucro",
            "#059669",
            "#d1fae5",
            ORIGENS_DRE["lucro_liquido_total"],
        )
    )

    totais = {
        "receita_bruta": float(receita_bruta_total),
        "vendas_produtos": float(receita_produtos_total),
        "vendas_servicos": float(receita_servicos_total),
        "receita_frete": float(receita_frete_total),
        "descontos": float(descontos_total),
        "impostos": float(impostos_total),
        "deducoes_total": float(deducoes_total),
        "receita_liquida": float(receita_liquida_total),
        "cmv": float(cmv_total),
        "lucro_bruto": float(lucro_bruto_total),
        "despesas_variaveis": float(despesas_variaveis_total),
        "despesas_operacionais": float(despesas_operacionais_total),
        "resultado_operacional": float(resultado_operacional_total),
        "resultado_financeiro": 0.0,
        "lucro_liquido": float(lucro_liquido_total),
        "margem_bruta": round(
            (float(lucro_bruto_total) / float(receita_liquida_total) * 100)
            if receita_liquida_total > 0
            else 0,
            2,
        ),
        "margem_liquida": round(
            (float(lucro_liquido_total) / float(receita_liquida_total) * 100)
            if receita_liquida_total > 0
            else 0,
            2,
        ),
    }

    return linhas, totais
