from types import SimpleNamespace

import os


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app import dashboard_routes


def _classificar(**kwargs):
    func = getattr(dashboard_routes, "_classificar_conta_ponto_equilibrio", None)
    assert func is not None

    conta = SimpleNamespace(
        descricao=kwargs.pop("descricao", ""),
        nota_entrada_id=kwargs.pop("nota_entrada_id", None),
    )
    classificacao, _origem = func(conta, **kwargs)
    return classificacao


def test_ponto_equilibrio_classifica_despesas_recorrentes_como_fixas():
    assert (
        _classificar(
            descricao="Pr\u00f3-Labore Karine e James",
            categoria_tipo_custo="ambos",
            categoria_nome="Despesas Operacionais",
            dre_subcategoria_nome="Pr\u00f3-Labore S\u00f3cios",
            dre_tipo_custo="CORPORATIVO",
        )
        == "fixo"
    )
    assert (
        _classificar(
            descricao="Internet e Telefone",
            categoria_tipo_custo="ambos",
            categoria_nome="Despesas Operacionais",
            dre_subcategoria_nome="Internet e Telefonia",
            dre_tipo_custo="INDIRETO_RATEAVEL",
        )
        == "fixo"
    )
    assert (
        _classificar(
            descricao="Sistema",
            categoria_tipo_custo="ambos",
            dre_subcategoria_nome="Softwares e Sistemas - ERP",
            dre_tipo_custo="CORPORATIVO",
        )
        == "fixo"
    )
    assert (
        _classificar(
            descricao="Energia",
            categoria_nome="Energia El\u00e9trica",
            dre_subcategoria_nome="Energia El\u00e9trica",
            dre_tipo_custo="INDIRETO_RATEAVEL",
        )
        == "fixo"
    )
    assert (
        _classificar(
            descricao="Escrit\u00f3rio",
            categoria_tipo_custo="ambos",
            dre_subcategoria_nome="Taxa Cart\u00e3o de Cr\u00e9dito",
            dre_tipo_custo="DIRETO",
        )
        == "fixo"
    )


def test_ponto_equilibrio_classifica_custos_de_venda_como_variaveis():
    assert (
        _classificar(
            descricao="Taxa Cr\u00e9dito - Venda 202604130015",
            dre_subcategoria_nome="Taxas de Cartao de Credito - Loja Fisica",
            dre_tipo_custo="DIRETO",
        )
        == "variavel"
    )
    assert (
        _classificar(
            descricao="Tarifa envio FULL NF 17140",
            tipo_despesa_nome="Frete/Entregas",
            dre_subcategoria_nome="Frete/Entregas",
            dre_custo_pe="variavel",
        )
        == "variavel"
    )


def test_ponto_equilibrio_complementa_folha_sem_duplicar_lancamentos_existentes():
    func = getattr(dashboard_routes, "_calcular_complemento_folha_gerencial", None)
    assert func is not None

    assert (
        func(total_estimado=10000, total_lancado=6000, total_provisoes_dre=1500) == 2500
    )
    assert func(total_estimado=10000, total_lancado=11000, total_provisoes_dre=0) == 0
