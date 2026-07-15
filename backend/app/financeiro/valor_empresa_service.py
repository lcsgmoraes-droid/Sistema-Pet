"""Motor explicavel de avaliacao gerencial da empresa."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.dashboard.ponto_equilibrio_routes import obter_ponto_equilibrio
from app.financeiro.imobilizado_service import calcular_valores_bem
from app.financeiro.models_contas import ContaPagar
from app.financeiro.models_imobilizado import BemImobilizado
from app.financeiro.models_valor_empresa import ValorEmpresaConfiguracao
from app.models import Cliente
from app.partner_utils import get_all_accessible_tenant_ids
from app.produtos.listagem import (
    _mapa_reservas_ativas_multitenant,
    _resolver_metricas_valorizacao_produto,
)
from app.produtos_models import Produto, ProdutoFornecedor
from app.vendas_models import Venda, VendaItem


CENTAVOS = Decimal("0.01")


def moeda(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def numero(valor) -> float:
    return float(moeda(valor))


def configuracao_padrao() -> dict:
    return {
        "periodo_dias": 60,
        "canais": "loja_fisica",
        "fornecedor_ids_excluidos": [],
        "folha_mensal_override": None,
        "despesas_fixas_mensais_override": None,
        "margem_contribuicao_override": None,
        "imobilizado_override": None,
        "outros_ativos": Decimal("0"),
        "incluir_dividas": False,
        "percentual_dividas_assumidas": Decimal("100"),
        "desconto_estoque_conservador": Decimal("45"),
        "desconto_estoque_provavel": Decimal("25"),
        "desconto_estoque_otimista": Decimal("10"),
        "multiplo_lucro_conservador": Decimal("18"),
        "multiplo_lucro_provavel": Decimal("24"),
        "multiplo_lucro_otimista": Decimal("30"),
        "dias_estoque_lento": 365,
        "observacoes": None,
    }


def dados_configuracao(config: ValorEmpresaConfiguracao | None) -> dict:
    dados = configuracao_padrao()
    if not config:
        return dados
    for campo in dados:
        valor = getattr(config, campo, None)
        if valor is not None:
            dados[campo] = valor
    dados["fornecedor_ids_excluidos"] = list(config.fornecedor_ids_excluidos or [])
    return dados


def calcular_cenarios(
    *,
    estoque_total: Decimal,
    estoque_lento: Decimal,
    imobilizado: Decimal,
    lucro_mensal: Decimal,
    outros_ativos: Decimal,
    dividas: Decimal,
    config: dict,
) -> list[dict]:
    cenarios = []
    for chave, nome in (
        ("conservador", "Conservador"),
        ("provavel", "Provável"),
        ("otimista", "Otimista"),
    ):
        desconto = Decimal(str(config[f"desconto_estoque_{chave}"]))
        multiplo = Decimal(str(config[f"multiplo_lucro_{chave}"]))
        ajuste_estoque = (estoque_lento * desconto / Decimal("100")).quantize(CENTAVOS)
        estoque_negociavel = max(estoque_total - ajuste_estoque, Decimal("0"))
        fundo_comercio = max(lucro_mensal, Decimal("0")) * multiplo
        valor = (
            estoque_negociavel + imobilizado + fundo_comercio + outros_ativos - dividas
        )
        cenarios.append(
            {
                "chave": chave,
                "nome": nome,
                "valor_sugerido": numero(max(valor, Decimal("0"))),
                "estoque_negociavel": numero(estoque_negociavel),
                "ajuste_estoque_lento": numero(ajuste_estoque),
                "imobilizado": numero(imobilizado),
                "fundo_comercio": numero(fundo_comercio),
                "outros_ativos": numero(outros_ativos),
                "dividas": numero(dividas),
                "multiplo_lucro_meses": float(multiplo),
                "desconto_estoque_lento_percentual": float(desconto),
            }
        )
    return cenarios


def _calcular_estoque(
    db: Session, tenant_id, fornecedor_ids: list[int], dias_lento: int
) -> dict:
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)
    query = db.query(Produto).filter(
        Produto.tenant_id.in_(access_ids),
        or_(Produto.ativo.is_(True), Produto.ativo.is_(None)),
        or_(
            Produto.tipo_produto.is_(None),
            Produto.tipo_produto == "SIMPLES",
            and_(
                Produto.tipo_produto.in_(["KIT", "VARIACAO"]),
                or_(Produto.tipo_kit.is_(None), Produto.tipo_kit != "VIRTUAL"),
            ),
        ),
    )
    if fornecedor_ids:
        query = query.filter(
            or_(
                Produto.fornecedor_id.is_(None),
                Produto.fornecedor_id.notin_(fornecedor_ids),
            ),
            ~Produto.fornecedores_alternativos.any(
                and_(
                    ProdutoFornecedor.fornecedor_id.in_(fornecedor_ids),
                    ProdutoFornecedor.ativo.is_(True),
                )
            ),
        )
    produtos = query.all()
    ids = [produto.id for produto in produtos]
    ultimas = {}
    if ids:
        ultimas = dict(
            db.query(VendaItem.produto_id, func.max(Venda.data_venda))
            .join(Venda, VendaItem.venda_id == Venda.id)
            .filter(
                Venda.tenant_id.in_(access_ids),
                VendaItem.produto_id.in_(ids),
                or_(Venda.status.is_(None), Venda.status != "cancelada"),
            )
            .group_by(VendaItem.produto_id)
            .all()
        )
    reservas = _mapa_reservas_ativas_multitenant(db, access_ids)
    limite = date.today() - timedelta(days=dias_lento)
    total = Decimal("0")
    lento = Decimal("0")
    sem_custo = 0
    produtos_com_estoque = 0
    produtos_lentos = 0
    for produto in produtos:
        metricas = _resolver_metricas_valorizacao_produto(
            db, produto, reservas_por_produto=reservas
        )
        if float(metricas["estoque_atual"] or 0) <= 0:
            continue
        produtos_com_estoque += 1
        valor = moeda(metricas["valor_custo_total"])
        total += valor
        if not produto.preco_custo or produto.preco_custo <= 0:
            sem_custo += 1
        ultima = ultimas.get(produto.id)
        ultima_data = ultima.date() if hasattr(ultima, "date") else ultima
        if ultima_data is None or ultima_data <= limite:
            lento += valor
            produtos_lentos += 1
    return {
        "valor_custo": numero(total),
        "valor_lento": numero(lento),
        "produtos_com_estoque": produtos_com_estoque,
        "produtos_lentos": produtos_lentos,
        "produtos_sem_custo": sem_custo,
        "dias_lento": dias_lento,
    }


def _calcular_imobilizado(db: Session, tenant_id) -> dict:
    bens = (
        db.query(BemImobilizado)
        .filter(
            BemImobilizado.tenant_id == tenant_id,
            BemImobilizado.status.in_(["ativo", "manutencao"]),
        )
        .all()
    )
    total = Decimal("0")
    com_mercado = 0
    for bem in bens:
        if bem.valor_mercado is not None:
            total += moeda(bem.valor_mercado)
            com_mercado += 1
        else:
            total += moeda(calcular_valores_bem(bem)["valor_contabil"])
    return {
        "valor": numero(total),
        "registros": len(bens),
        "com_valor_mercado": com_mercado,
    }


def _calcular_dividas(db: Session, tenant_id, fornecedor_ids: list[int]) -> dict:
    query = db.query(ContaPagar).filter(
        ContaPagar.tenant_id == tenant_id,
        ContaPagar.status.in_(["pendente", "vencido", "parcial"]),
    )
    if fornecedor_ids:
        query = query.filter(
            or_(
                ContaPagar.fornecedor_id.is_(None),
                ContaPagar.fornecedor_id.notin_(fornecedor_ids),
            )
        )
    total = sum(
        (
            max(moeda(conta.valor_final) - moeda(conta.valor_pago), Decimal("0"))
            for conta in query.all()
        ),
        Decimal("0"),
    )
    return {"saldo_aberto": numero(total)}


async def montar_avaliacao(
    db: Session, current_user, tenant_id, config_obj, faturamento_simulado=None
) -> dict:
    config = dados_configuracao(config_obj)
    fim = date.today()
    inicio = fim - timedelta(days=int(config["periodo_dias"]) - 1)
    canais = [
        item.strip() for item in str(config["canais"] or "").split(",") if item.strip()
    ]
    fornecedores = [int(item) for item in config["fornecedor_ids_excluidos"]]
    pe = await obter_ponto_equilibrio(
        data_inicio=inicio,
        data_fim=fim,
        canais=",".join(canais),
        fonte_margem="periodo_atual",
        modo_custo_fiscal="gerencial_completo",
        incluir_detalhes=False,
        fornecedor_ids_excluidos=",".join(map(str, fornecedores)),
        db=db,
        user_and_tenant=(current_user, tenant_id),
    )
    periodo_dias = int(config["periodo_dias"])
    fator_mensal = Decimal("30") / Decimal(str(periodo_dias))
    faturamento_periodo = moeda(pe["faturamento"])
    faturamento_mensal = (faturamento_periodo * fator_mensal).quantize(CENTAVOS)
    margem_percentual = Decimal(
        str(
            config["margem_contribuicao_override"]
            if config["margem_contribuicao_override"] is not None
            else pe["margem_periodo_percentual"]
        )
    )
    folha_sistema = moeda(pe["folha_gerencial_estimada"])
    folha_mensal = moeda(
        config["folha_mensal_override"]
        if config["folha_mensal_override"] is not None
        else folha_sistema
    )
    folha_reconhecida = sum(
        (
            moeda(pe[campo])
            for campo in (
                "folha_lancada_contas_pagar",
                "folha_provisoes_dre",
                "folha_complemento_gerencial",
            )
        ),
        Decimal("0"),
    )
    outras_fixas_periodo = max(
        moeda(pe["despesas_fixas"]) - folha_reconhecida, Decimal("0")
    )
    outras_fixas_mensais = moeda(
        config["despesas_fixas_mensais_override"]
        if config["despesas_fixas_mensais_override"] is not None
        else outras_fixas_periodo * fator_mensal
    )
    fixas_mensais = folha_mensal + outras_fixas_mensais
    lucro_mensal = (
        faturamento_mensal * margem_percentual / Decimal("100") - fixas_mensais
    ).quantize(CENTAVOS)

    estoque = _calcular_estoque(
        db, tenant_id, fornecedores, int(config["dias_estoque_lento"])
    )
    imobilizado_dados = _calcular_imobilizado(db, tenant_id)
    imobilizado = moeda(
        config["imobilizado_override"]
        if config["imobilizado_override"] is not None
        else imobilizado_dados["valor"]
    )
    dividas_dados = _calcular_dividas(db, tenant_id, fornecedores)
    dividas = Decimal("0")
    if config["incluir_dividas"]:
        dividas = (
            moeda(dividas_dados["saldo_aberto"])
            * Decimal(str(config["percentual_dividas_assumidas"]))
            / Decimal("100")
        ).quantize(CENTAVOS)
    cenarios = calcular_cenarios(
        estoque_total=moeda(estoque["valor_custo"]),
        estoque_lento=moeda(estoque["valor_lento"]),
        imobilizado=imobilizado,
        lucro_mensal=lucro_mensal,
        outros_ativos=moeda(config["outros_ativos"]),
        dividas=dividas,
        config=config,
    )
    receita_simulada = moeda(
        faturamento_simulado if faturamento_simulado is not None else faturamento_mensal
    )
    lucro_simulado = (
        receita_simulada * margem_percentual / Decimal("100") - fixas_mensais
    ).quantize(CENTAVOS)
    cenarios_simulados = calcular_cenarios(
        estoque_total=moeda(estoque["valor_custo"]),
        estoque_lento=moeda(estoque["valor_lento"]),
        imobilizado=imobilizado,
        lucro_mensal=lucro_simulado,
        outros_ativos=moeda(config["outros_ativos"]),
        dividas=dividas,
        config=config,
    )
    alertas = []
    pontos = 100
    if pe["quantidade_vendas"] == 0:
        alertas.append("Não há vendas no período selecionado.")
        pontos -= 35
    if estoque["produtos_sem_custo"]:
        alertas.append(
            f"{estoque['produtos_sem_custo']} produtos com estoque estão sem custo cadastrado."
        )
        pontos -= 15
    if imobilizado_dados["registros"] == 0 and config["imobilizado_override"] is None:
        alertas.append("Cadastre o imobilizado ou informe um valor manual.")
        pontos -= 20
    elif (
        imobilizado_dados["registros"]
        and imobilizado_dados["com_valor_mercado"] < imobilizado_dados["registros"]
    ):
        alertas.append(
            "Parte do imobilizado usa valor contábil por falta de valor de mercado."
        )
        pontos -= 10
    if config["folha_mensal_override"] is None:
        alertas.append(
            "A folha usa o quadro ativo do sistema; revise se este será o quadro entregue ao comprador."
        )
        pontos -= 5
    pontos = max(pontos, 0)
    nivel = "alta" if pontos >= 80 else "média" if pontos >= 55 else "baixa"
    nomes_fornecedores = []
    if fornecedores:
        nomes_fornecedores = [
            {"id": item.id, "nome": item.nome}
            for item in db.query(Cliente)
            .filter(Cliente.tenant_id == tenant_id, Cliente.id.in_(fornecedores))
            .all()
        ]
    config_response = {
        **config,
        "id": config_obj.id if config_obj else None,
        "fornecedores_excluidos": nomes_fornecedores,
    }
    return {
        "configuracao": config_response,
        "periodo": {
            "inicio": inicio,
            "fim": fim,
            "dias": periodo_dias,
            "canais": canais,
        },
        "operacao": {
            "faturamento_periodo": numero(faturamento_periodo),
            "faturamento_mensal_normalizado": numero(faturamento_mensal),
            "margem_contribuicao_percentual": float(margem_percentual),
            "folha_mensal": numero(folha_mensal),
            "folha_mensal_sistema": numero(folha_sistema),
            "outras_despesas_fixas_mensais": numero(outras_fixas_mensais),
            "despesas_fixas_mensais": numero(fixas_mensais),
            "lucro_operacional_mensal": numero(lucro_mensal),
            "quantidade_vendas": pe["quantidade_vendas"],
        },
        "ativos": {
            "estoque": estoque,
            "imobilizado": {**imobilizado_dados, "valor_usado": numero(imobilizado)},
            "outros": numero(config["outros_ativos"]),
        },
        "dividas": {
            **dividas_dados,
            "valor_considerado": numero(dividas),
            "incluidas_na_venda": config["incluir_dividas"],
        },
        "cenarios": cenarios,
        "simulacao": {
            "faturamento_mensal": numero(receita_simulada),
            "lucro_mensal": numero(lucro_simulado),
            "cenarios": cenarios_simulados,
        },
        "confianca": {"pontuacao": pontos, "nivel": nivel, "alertas": alertas},
        "fontes": [
            {
                "nome": "Vendas e Ponto de Equilíbrio",
                "rota": "/financeiro/ponto-equilibrio",
            },
            {
                "nome": "Valorização do Estoque",
                "rota": "/produtos/relatorio/valorizacao-estoque",
            },
            {"nome": "Imobilizado", "rota": "/financeiro/imobilizado"},
            {"nome": "Contas a Pagar", "rota": "/financeiro/contas-pagar"},
        ],
    }
