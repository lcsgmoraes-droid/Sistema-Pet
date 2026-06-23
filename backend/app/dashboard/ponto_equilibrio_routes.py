"""Rotas de Ponto de Equilibrio do dashboard financeiro."""

import calendar
import math
from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..db import get_session
from ..auth.dependencies import get_current_user_and_tenant
from ..models import Cliente
from ..vendas_models import Venda, VendaItem
from ..financeiro_models import ContaPagar, CategoriaFinanceira, TipoDespesa
from ..produtos_models import Produto
from ..dre_plano_contas_models import DRESubcategoria
from ..ia.aba7_dre_detalhada_models import DREDetalheCanal
from .ponto_equilibrio import (
    MARGEM_PONTO_EQUILIBRIO_OPCOES,
    MARGEM_PONTO_EQUILIBRIO_PADRAO,
    MODO_CUSTO_FISCAL_PE_OPCOES,
    MODO_CUSTO_FISCAL_PE_PADRAO,
    PONTO_EQUILIBRIO_GRUPOS_CLASSIFICACAO,
    _calcular_complemento_folha_gerencial,
    _calcular_folha_gerencial_estimada,
    _calcular_margem_periodo_ponto_equilibrio,
    _calcular_margem_referencia_ponto_equilibrio,
    _classificar_conta_ponto_equilibrio,
    _conta_eh_compra_estoque_para_pe,
    _conta_eh_folha_para_pe,
    _conta_variavel_ja_coberta_pelo_snapshot_pe,
    _detalhe_conta_pe,
    _detalhe_sintetico_pe,
    _filtro_status_venda_relatorio,
    _formatar_data_br_ponto_equilibrio,
    _normalizar_item_detalhe_ponto_equilibrio,
    _paginar_detalhes_ponto_equilibrio,
    _round_money,
)

router = APIRouter()

@router.get("/financeiro/ponto-equilibrio")
async def obter_ponto_equilibrio(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    canais: Optional[str] = None,
    fonte_margem: Optional[str] = MARGEM_PONTO_EQUILIBRIO_PADRAO,
    modo_custo_fiscal: Optional[str] = MODO_CUSTO_FISCAL_PE_PADRAO,
    incluir_detalhes: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Calcula o ponto de equilibrio pela margem de contribuicao."""
    _, tenant_id = user_and_tenant

    hoje = datetime.now().date()
    inicio = data_inicio or hoje.replace(day=1)
    fim_padrao = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])
    fim = data_fim or fim_padrao
    if fim < inicio:
        raise HTTPException(
            status_code=422, detail="Data final deve ser maior ou igual a data inicial"
        )

    inicio_dt = datetime.combine(inicio, time.min)
    fim_dt = datetime.combine(fim, time.max)
    canais_lista = [
        canal.strip() for canal in (canais or "").split(",") if canal.strip()
    ]
    fonte_margem = (fonte_margem or MARGEM_PONTO_EQUILIBRIO_PADRAO).strip()
    if fonte_margem not in MARGEM_PONTO_EQUILIBRIO_OPCOES:
        opcoes = ", ".join(MARGEM_PONTO_EQUILIBRIO_OPCOES.keys())
        raise HTTPException(
            status_code=422, detail=f"Fonte da margem invalida. Use: {opcoes}"
        )
    modo_custo_fiscal = (modo_custo_fiscal or MODO_CUSTO_FISCAL_PE_PADRAO).strip()
    if modo_custo_fiscal not in MODO_CUSTO_FISCAL_PE_OPCOES:
        opcoes = ", ".join(MODO_CUSTO_FISCAL_PE_OPCOES.keys())
        raise HTTPException(
            status_code=422, detail=f"Modo de custo invalido. Use: {opcoes}"
        )

    produtos_sem_custo = (
        db.query(func.count(func.distinct(VendaItem.produto_id)))
        .join(
            Venda,
            VendaItem.venda_id == Venda.id,
        )
        .outerjoin(
            Produto,
            VendaItem.produto_id == Produto.id,
        )
        .filter(
            Venda.tenant_id == tenant_id,
            _filtro_status_venda_relatorio(),
            Venda.data_venda >= inicio_dt,
            Venda.data_venda <= fim_dt,
            VendaItem.tipo == "produto",
            VendaItem.produto_id.isnot(None),
            or_(Produto.preco_custo.is_(None), Produto.preco_custo <= 0),
        )
    )
    if canais_lista:
        produtos_sem_custo = produtos_sem_custo.filter(Venda.canal.in_(canais_lista))
    produtos_sem_custo = int(produtos_sem_custo.scalar() or 0)

    contas_query = (
        db.query(
            ContaPagar,
            TipoDespesa.e_custo_fixo.label("tipo_e_custo_fixo"),
            TipoDespesa.nome.label("tipo_despesa_nome"),
            CategoriaFinanceira.tipo_custo.label("categoria_tipo_custo"),
            CategoriaFinanceira.nome.label("categoria_nome"),
            DRESubcategoria.custo_pe.label("dre_custo_pe"),
            DRESubcategoria.tipo_custo.label("dre_tipo_custo"),
            DRESubcategoria.nome.label("dre_subcategoria_nome"),
            Cliente.nome.label("fornecedor_nome"),
        )
        .outerjoin(
            TipoDespesa,
            ContaPagar.tipo_despesa_id == TipoDespesa.id,
        )
        .outerjoin(
            CategoriaFinanceira,
            ContaPagar.categoria_id == CategoriaFinanceira.id,
        )
        .outerjoin(
            DRESubcategoria,
            ContaPagar.dre_subcategoria_id == DRESubcategoria.id,
        )
        .outerjoin(
            Cliente,
            and_(
                ContaPagar.fornecedor_id == Cliente.id, Cliente.tenant_id == tenant_id
            ),
        )
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.data_vencimento >= inicio,
            ContaPagar.data_vencimento <= fim,
            ContaPagar.status != "cancelado",
        )
    )
    if canais_lista:
        contas_query = contas_query.filter(
            or_(ContaPagar.canal.in_(canais_lista), ContaPagar.canal.is_(None))
        )

    despesas_fixas = 0.0
    outros_variaveis_contas = 0.0
    despesas_variaveis_ja_cobertas = 0.0
    despesas_sem_classificacao = 0.0
    despesas_estoque_excluidas = 0.0
    folha_lancada_contas_pagar = 0.0
    folha_provisoes_dre = 0.0
    quantidade_contas_sem_classificacao = 0
    quantidade_contas_estoque_excluidas = 0
    detalhes_classificacao = {
        "fixas": [],
        "variaveis": [],
        "custos_venda_snapshot": [],
        "sem_classificacao": [],
        "estoque_excluido": [],
    }

    def adicionar_detalhe_classificacao(grupo: str, detalhe: dict):
        if incluir_detalhes:
            detalhes_classificacao[grupo].append(detalhe)

    for (
        conta,
        tipo_e_custo_fixo,
        tipo_despesa_nome,
        categoria_tipo_custo,
        categoria_nome,
        dre_custo_pe,
        dre_tipo_custo,
        dre_subcategoria_nome,
        fornecedor_nome,
    ) in contas_query.all():
        valor = float(conta.valor_final or conta.valor_original or 0)

        if _conta_eh_compra_estoque_para_pe(conta, tipo_despesa_nome, categoria_nome):
            despesas_estoque_excluidas += valor
            quantidade_contas_estoque_excluidas += 1
            adicionar_detalhe_classificacao(
                "estoque_excluido",
                _detalhe_conta_pe(
                    conta,
                    valor=valor,
                    classificacao="estoque_excluido",
                    origem_classificacao="Compra de estoque/Produto para Revenda (CMV ja cobre quando vendido)",
                    fornecedor_nome=fornecedor_nome,
                    tipo_despesa_nome=tipo_despesa_nome,
                    categoria_nome=categoria_nome,
                    dre_subcategoria_nome=dre_subcategoria_nome,
                ),
            )
            continue

        if _conta_variavel_ja_coberta_pelo_snapshot_pe(
            conta,
            tipo_despesa_nome,
            categoria_nome,
            dre_subcategoria_nome,
        ):
            despesas_variaveis_ja_cobertas += valor
            adicionar_detalhe_classificacao(
                "custos_venda_snapshot",
                _detalhe_conta_pe(
                    conta,
                    valor=valor,
                    classificacao="coberto_snapshot",
                    origem_classificacao="Custo de venda ja considerado no snapshot da venda",
                    fornecedor_nome=fornecedor_nome,
                    tipo_despesa_nome=tipo_despesa_nome,
                    categoria_nome=categoria_nome,
                    dre_subcategoria_nome=dre_subcategoria_nome,
                ),
            )
            continue

        if _conta_eh_folha_para_pe(
            conta, tipo_despesa_nome, categoria_nome, dre_subcategoria_nome
        ):
            folha_lancada_contas_pagar += valor

        classificacao, origem_classificacao = _classificar_conta_ponto_equilibrio(
            conta,
            tipo_e_custo_fixo=tipo_e_custo_fixo,
            tipo_despesa_nome=tipo_despesa_nome,
            categoria_tipo_custo=categoria_tipo_custo,
            categoria_nome=categoria_nome,
            dre_custo_pe=dre_custo_pe,
            dre_subcategoria_nome=dre_subcategoria_nome,
            dre_tipo_custo=dre_tipo_custo,
        )

        if classificacao == "fixo":
            despesas_fixas += valor
            adicionar_detalhe_classificacao(
                "fixas",
                _detalhe_conta_pe(
                    conta,
                    valor=valor,
                    classificacao="fixo",
                    origem_classificacao=origem_classificacao,
                    fornecedor_nome=fornecedor_nome,
                    tipo_despesa_nome=tipo_despesa_nome,
                    categoria_nome=categoria_nome,
                    dre_subcategoria_nome=dre_subcategoria_nome,
                ),
            )
        elif classificacao == "variavel":
            outros_variaveis_contas += valor
            adicionar_detalhe_classificacao(
                "variaveis",
                _detalhe_conta_pe(
                    conta,
                    valor=valor,
                    classificacao="variavel",
                    origem_classificacao=origem_classificacao,
                    fornecedor_nome=fornecedor_nome,
                    tipo_despesa_nome=tipo_despesa_nome,
                    categoria_nome=categoria_nome,
                    dre_subcategoria_nome=dre_subcategoria_nome,
                ),
            )
        else:
            despesas_sem_classificacao += valor
            quantidade_contas_sem_classificacao += 1
            adicionar_detalhe_classificacao(
                "sem_classificacao",
                _detalhe_conta_pe(
                    conta,
                    valor=valor,
                    classificacao="sem_classificacao",
                    origem_classificacao=origem_classificacao,
                    fornecedor_nome=fornecedor_nome,
                    tipo_despesa_nome=tipo_despesa_nome,
                    categoria_nome=categoria_nome,
                    dre_subcategoria_nome=dre_subcategoria_nome,
                ),
            )

    provisoes_dre_query = db.query(DREDetalheCanal).filter(
        DREDetalheCanal.tenant_id == tenant_id,
        DREDetalheCanal.data_inicio <= fim,
        DREDetalheCanal.data_fim >= inicio,
        or_(
            DREDetalheCanal.origem == "PROVISAO",
            DREDetalheCanal.canal == "provisao",
        ),
    )
    if canais_lista:
        provisoes_dre_query = provisoes_dre_query.filter(
            or_(
                DREDetalheCanal.canal.in_(canais_lista),
                DREDetalheCanal.canal == "provisao",
            )
        )

    for provisao in provisoes_dre_query.all():
        despesas_pessoal = float(provisao.despesas_pessoal or 0)
        despesas_fixas_dre = (
            despesas_pessoal
            + float(provisao.despesas_administrativas or 0)
            + float(provisao.despesas_financeiras or 0)
            + float(provisao.outras_despesas or 0)
        )
        despesas_variaveis_dre = float(provisao.despesas_vendas or 0)

        if despesas_fixas_dre > 0:
            despesas_fixas += despesas_fixas_dre
            folha_provisoes_dre += despesas_pessoal
            adicionar_detalhe_classificacao(
                "fixas",
                _detalhe_sintetico_pe(
                    item_id=f"dre-provisao-{provisao.id}-fixo",
                    descricao=provisao.observacao or "Provisao DRE",
                    valor=despesas_fixas_dre,
                    data_vencimento=provisao.data_fim,
                    classificacao="fixo",
                    origem_classificacao="Provisao registrada na DRE",
                ),
            )

        if despesas_variaveis_dre > 0:
            outros_variaveis_contas += despesas_variaveis_dre
            adicionar_detalhe_classificacao(
                "variaveis",
                _detalhe_sintetico_pe(
                    item_id=f"dre-provisao-{provisao.id}-variavel",
                    descricao=provisao.observacao or "Provisao DRE",
                    valor=despesas_variaveis_dre,
                    data_vencimento=provisao.data_fim,
                    classificacao="variavel",
                    origem_classificacao="Provisao variavel registrada na DRE",
                ),
            )

    folha_gerencial = _calcular_folha_gerencial_estimada(db, tenant_id)
    folha_complemento_gerencial = _calcular_complemento_folha_gerencial(
        total_estimado=folha_gerencial["total"],
        total_lancado=folha_lancada_contas_pagar,
        total_provisoes_dre=folha_provisoes_dre,
    )
    if folha_complemento_gerencial > 0:
        despesas_fixas += folha_complemento_gerencial
        adicionar_detalhe_classificacao(
            "fixas",
            _detalhe_sintetico_pe(
                item_id="folha-gerencial-estimada",
                descricao="Complemento de folha gerencial estimada",
                valor=folha_complemento_gerencial,
                data_vencimento=fim,
                classificacao="fixo",
                origem_classificacao="Funcionarios ativos/cargos, descontando contas a pagar e provisoes DRE ja lancadas",
            ),
        )

    despesas_fixas = _round_money(despesas_fixas)
    outros_variaveis_contas = _round_money(outros_variaveis_contas)
    despesas_variaveis_ja_cobertas = _round_money(despesas_variaveis_ja_cobertas)
    despesas_sem_classificacao = _round_money(despesas_sem_classificacao)
    despesas_estoque_excluidas = _round_money(despesas_estoque_excluidas)
    folha_lancada_contas_pagar = _round_money(folha_lancada_contas_pagar)
    folha_provisoes_dre = _round_money(folha_provisoes_dre)

    margem_periodo = _calcular_margem_periodo_ponto_equilibrio(
        db,
        tenant_id,
        inicio,
        fim,
        canais_lista,
        modo_custo_fiscal=modo_custo_fiscal,
        outros_variaveis=outros_variaveis_contas,
        detalhes_outros_variaveis=detalhes_classificacao["variaveis"]
        if incluir_detalhes
        else None,
        incluir_detalhes=incluir_detalhes,
    )
    faturamento = margem_periodo["faturamento"]
    quantidade_vendas = margem_periodo["quantidade_vendas"]
    ticket_medio = margem_periodo["ticket_medio"]
    cmv_estimado = margem_periodo["cmv_estimado"]
    despesas_variaveis = margem_periodo["despesas_variaveis"]
    custos_variaveis = margem_periodo["custos_variaveis"]
    margem_contribuicao = margem_periodo["margem_contribuicao"]
    margem_contribuicao_percentual = margem_periodo["margem_decimal"]

    margem_referencia = _calcular_margem_referencia_ponto_equilibrio(
        db,
        tenant_id,
        inicio,
        fim,
        canais_lista,
        fonte_margem,
        margem_periodo,
        modo_custo_fiscal=modo_custo_fiscal,
    )
    margem_usada_decimal = float(margem_referencia.get("margem_decimal") or 0)
    margem_usada_percentual = round(margem_usada_decimal * 100, 2)
    ticket_medio_usado = (
        ticket_medio
        if ticket_medio > 0
        else _round_money(margem_referencia.get("ticket_medio"))
    )

    ponto_equilibrio = None
    falta_faturar = None
    percentual_atingido = 0
    vendas_necessarias = None
    status_pe = "sem_faturamento"

    if margem_usada_decimal > 0:
        ponto_equilibrio = despesas_fixas / margem_usada_decimal
        falta_faturar = max(0, ponto_equilibrio - faturamento)
        percentual_atingido = (
            (faturamento / ponto_equilibrio) * 100 if ponto_equilibrio > 0 else 100
        )
        vendas_necessarias = (
            int(math.ceil(falta_faturar / ticket_medio_usado))
            if falta_faturar and ticket_medio_usado > 0
            else 0
        )
        status_pe = "atingido" if falta_faturar == 0 else "nao_atingido"
    elif faturamento > 0:
        status_pe = "margem_insuficiente"

    return {
        "periodo": {
            "inicio": inicio,
            "fim": fim,
            "canais": canais_lista,
        },
        "formula": "ponto_equilibrio = custos fixos / margem de contribuicao escolhida",
        "fonte_margem": fonte_margem,
        "opcoes_fonte_margem": MARGEM_PONTO_EQUILIBRIO_OPCOES,
        "modo_custo_fiscal": modo_custo_fiscal,
        "opcoes_modo_custo_fiscal": MODO_CUSTO_FISCAL_PE_OPCOES,
        "faturamento": faturamento,
        "receita_produtos_servicos": margem_periodo.get("receita_produtos_servicos", 0),
        "receita_entrega": margem_periodo.get("receita_entrega", 0),
        "descontos": margem_periodo.get("descontos", 0),
        "beneficios_campanhas": margem_periodo.get("beneficios_campanhas", 0),
        "taxas_cartao": margem_periodo.get("taxas_cartao", 0),
        "repasse_entrega": margem_periodo.get("repasse_entrega", 0),
        "custo_operacional_entrega": margem_periodo.get("custo_operacional_entrega", 0),
        "comissoes": margem_periodo.get("comissoes", 0),
        "custo_fiscal": margem_periodo.get("custo_fiscal", 0),
        "outros_variaveis": margem_periodo.get("outros_variaveis", 0),
        "quantidade_vendas": quantidade_vendas,
        "ticket_medio": ticket_medio,
        "ticket_medio_usado": ticket_medio_usado,
        "ticket_medio_referencia": _round_money(margem_referencia.get("ticket_medio")),
        "cmv_estimado": cmv_estimado,
        "despesas_variaveis": despesas_variaveis,
        "despesas_variaveis_contas": outros_variaveis_contas,
        "despesas_variaveis_ja_cobertas": despesas_variaveis_ja_cobertas,
        "custos_variaveis": _round_money(custos_variaveis),
        "despesas_fixas": despesas_fixas,
        "despesas_sem_classificacao": despesas_sem_classificacao,
        "despesas_estoque_excluidas": despesas_estoque_excluidas,
        "quantidade_contas_sem_classificacao": quantidade_contas_sem_classificacao,
        "quantidade_contas_estoque_excluidas": quantidade_contas_estoque_excluidas,
        "folha_gerencial_estimada": folha_gerencial["total"],
        "folha_lancada_contas_pagar": folha_lancada_contas_pagar,
        "folha_provisoes_dre": folha_provisoes_dre,
        "folha_complemento_gerencial": folha_complemento_gerencial,
        "folha_funcionarios_ativos": folha_gerencial["quantidade_funcionarios"],
        "margem_contribuicao": _round_money(margem_contribuicao),
        "margem_contribuicao_percentual": round(
            margem_contribuicao_percentual * 100, 2
        ),
        "margem_periodo_percentual": round(margem_contribuicao_percentual * 100, 2),
        "margem_periodo_valor": _round_money(margem_contribuicao),
        "margem_usada_percentual": margem_usada_percentual,
        "margem_usada_valor": _round_money(
            margem_referencia.get("margem_contribuicao")
        ),
        "margem_usada_label": margem_referencia.get("label"),
        "margem_referencia": margem_referencia,
        "detalhes_margem": margem_periodo.get("detalhes_margem", {}),
        "ponto_equilibrio": _round_money(ponto_equilibrio)
        if ponto_equilibrio is not None
        else None,
        "falta_faturar": _round_money(falta_faturar)
        if falta_faturar is not None
        else None,
        "percentual_atingido": round(percentual_atingido, 2),
        "vendas_necessarias": vendas_necessarias,
        "produtos_sem_custo": produtos_sem_custo,
        "detalhes_classificacao": detalhes_classificacao,
        "status": status_pe,
    }


@router.get("/financeiro/ponto-equilibrio/detalhes")
async def obter_ponto_equilibrio_detalhes(
    grupo: str,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    canais: Optional[str] = None,
    fonte_margem: Optional[str] = MARGEM_PONTO_EQUILIBRIO_PADRAO,
    modo_custo_fiscal: Optional[str] = MODO_CUSTO_FISCAL_PE_PADRAO,
    page: int = 1,
    page_size: int = 30,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Carrega os lancamentos de uma linha do ponto de equilibrio sob demanda."""
    grupo = (grupo or "").strip()
    dados = await obter_ponto_equilibrio(
        data_inicio=data_inicio,
        data_fim=data_fim,
        canais=canais,
        fonte_margem=fonte_margem,
        modo_custo_fiscal=modo_custo_fiscal,
        incluir_detalhes=True,
        db=db,
        user_and_tenant=user_and_tenant,
    )

    detalhes_margem = dados.get("detalhes_margem") or {}
    subtotais = detalhes_margem.get("subtotais") or []
    componentes = detalhes_margem.get("componentes") or {}
    detalhes_classificacao = dados.get("detalhes_classificacao") or {}

    label = grupo
    origem = "Lancamentos usados no calculo do ponto de equilibrio."
    total = 0.0
    items = []

    subtotal = next((item for item in subtotais if item.get("id") == grupo), None)
    if subtotal is not None:
        label = subtotal.get("label") or label
        origem = "Snapshot financeiro das vendas no periodo filtrado."
        total = _round_money(subtotal.get("valor") or 0)
        items = [
            _normalizar_item_detalhe_ponto_equilibrio(item, "Venda")
            for item in componentes.get(grupo, [])
        ]
    elif grupo in PONTO_EQUILIBRIO_GRUPOS_CLASSIFICACAO:
        meta = PONTO_EQUILIBRIO_GRUPOS_CLASSIFICACAO[grupo]
        label = meta["label"]
        origem = meta["origem"]
        items = [
            _normalizar_item_detalhe_ponto_equilibrio(item, "Conta/DRE")
            for item in detalhes_classificacao.get(grupo, [])
        ]
        total_por_grupo = {
            "fixas": dados.get("despesas_fixas"),
            "variaveis": dados.get(
                "outros_variaveis", dados.get("despesas_variaveis_contas")
            ),
            "custos_venda_snapshot": dados.get("despesas_variaveis_ja_cobertas"),
            "sem_classificacao": dados.get("despesas_sem_classificacao"),
            "estoque_excluido": dados.get("despesas_estoque_excluidas"),
        }
        total = _round_money(total_por_grupo.get(grupo) or 0)
    else:
        raise HTTPException(status_code=404, detail="Grupo de detalhes nao encontrado")

    paginacao = _paginar_detalhes_ponto_equilibrio(
        items, page=page, page_size=page_size
    )
    periodo = dados.get("periodo") or {}
    inicio = periodo.get("inicio")
    fim = periodo.get("fim")

    return {
        "grupo": grupo,
        "label": label,
        "total": total,
        "origem": origem,
        "periodo": f"{_formatar_data_br_ponto_equilibrio(inicio)} - {_formatar_data_br_ponto_equilibrio(fim)}",
        **paginacao,
    }
