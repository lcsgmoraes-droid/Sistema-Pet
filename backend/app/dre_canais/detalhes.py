from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.dre_canais.agregacao import (
    _devolucoes_periodo_query,
    _contas_receber_manuais_query,
    _valor_recebivel_competencia,
    _preparar_snapshots_vendas,
    _subcategorias_contas_map,
    _valor_snapshot_campo,
    agregar_devolucoes_por_canal,
    obter_vendas_por_canal,
)
from app.dre_canais.base import (
    CANAIS_CONFIG,
    ORIGENS_DRE,
    _classificar_conta_dre,
    _conta_valor,
    _data_iso,
    _decimal,
    _eh_custo_de_venda_ja_vindo_da_venda,
    _filtro_status_venda_dre,
    _normalizar_canal,
    _periodo_label_intervalo,
    _periodo_meses,
    _texto_conta,
)
from app.dre_canais.contas import (
    classificacoes_contas_pagar,
    eh_compra_estoque,
    filtros_contas_pagar_dre,
    ids_fretes_sobre_compras,
)
from app.dre_canais.folha import (
    calcular_resumo_folha_gerencial,
    canal_provisao_folha,
)
from app.dre_canais.schemas import DREDetalheItem, DREDetalheResponse
from app.financeiro_models import ContaPagar, ContaReceber
from app.vendas_models import Venda, VendaItem

router = APIRouter()


CAMPOS_DETALHE_VENDAS = {
    "receita_produtos",
    "receita_servicos",
    "receita_frete",
    "descontos",
    "impostos",
    "cmv",
    "custo_servicos",
    "cmv_estimado",
    "taxas_cartao",
    "repasse_entrega",
    "taxa_operacional_entrega",
    "comissoes",
    "campanhas",
}


CAMPOS_DETALHE_CONTAS = {
    "fretes_compras",
    "taxas_marketplace",
    "despesas_pessoal",
    "despesas_administrativas",
    "despesas_comerciais",
    "despesas_financeiras",
    "outras_despesas",
}

CAMPOS_DETALHE_RECEBIVEIS = {"receita_outras"}
CAMPOS_DETALHE_DEVOLUCOES = {"devolucoes"}


def _detalhes_devolucoes_campo(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    canal: str,
    campo: str,
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> List[DREDetalheItem]:
    inicio, fim = _periodo_meses(mes_inicial or mes, mes, ano, data_final)
    eventos = _devolucoes_periodo_query(db, tenant_id, inicio, fim).all()
    detalhes = []
    for evento in eventos:
        if _normalizar_canal(evento.canal) != canal:
            continue
        if campo == "devolucoes":
            valor = _decimal(evento.valor_devolvido)
        elif campo == "cmv":
            valor = -_decimal(evento.custo_produtos_estornado)
        else:
            valor = -_decimal(evento.custo_servicos_estornado)
        if abs(valor) <= Decimal("0.004"):
            continue
        detalhes.append(
            DREDetalheItem(
                id=f"devolucao-{evento.id}",
                origem_tipo="devolucao_venda",
                origem_label="Devolucao de venda",
                data=_data_iso(evento.data_competencia),
                descricao=f"Devolucao da venda #{evento.venda_id}",
                contraparte=evento.forma_estorno,
                documento=str(evento.venda_id),
                valor=float(valor),
                valor_auxiliar=float(_decimal(evento.valor_devolvido)),
                link="/financeiro/vendas",
                meta={
                    "canal": canal,
                    "devolucao_id": evento.id,
                    "motivo": evento.motivo,
                    "custo_pendente": bool(evento.custo_pendente),
                    "itens": evento.itens or [],
                },
            )
        )
    return detalhes


def _paginar_detalhes(
    items: List[DREDetalheItem],
    page: int,
    page_size: int,
) -> tuple[List[DREDetalheItem], int, int]:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 30), 1), 100)
    total_itens = len(items)
    pages = (total_itens + page_size - 1) // page_size if total_itens else 0
    inicio = (page - 1) * page_size
    return items[inicio : inicio + page_size], page_size, pages


def _detalhes_cmv_estimado(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    canal: str,
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> List[DREDetalheItem]:
    dados_canais = obter_vendas_por_canal(
        db,
        mes,
        ano,
        tenant_id,
        mes_inicial=mes_inicial,
        data_final=data_final,
    )
    agregar_devolucoes_por_canal(
        db,
        mes,
        ano,
        tenant_id,
        dados_canais,
        mes_inicial=mes_inicial,
        data_final=data_final,
    )
    dados = dados_canais.get(canal, {})
    itens = list(dados.get("itens_cmv_estimado", []) or [])
    itens.extend(dados.get("itens_cmv_estornado", []) or [])
    detalhes = []
    for indice, item in enumerate(itens):
        codigo = item.get("produto_codigo")
        nome = item.get("produto_nome") or "Produto removido"
        numero_venda = item.get("numero_venda") or f"#{item.get('venda_id')}"
        percentual = _decimal(item.get("percentual_custo", 0))
        devolucao_id = item.get("devolucao_id")
        origem_estorno = item.get("origem_cmv_estornado")
        if origem_estorno == "custo_atribuido_sem_comprovante":
            origem_label = "Estorno provisório de CMV sem custo comprovado"
        elif devolucao_id:
            origem_label = "Estorno de custo provisório"
        else:
            origem_label = "Custo provisório"
        contraparte = (
            f"Venda {numero_venda} • CMV anterior sem comprovante"
            if origem_estorno == "custo_atribuido_sem_comprovante"
            else f"Venda {numero_venda} • custo aplicado {float(percentual):.2f}%"
        )
        detalhes.append(
            DREDetalheItem(
                id=(
                    f"cmv-estimado-{item.get('venda_id')}-"
                    f"{item.get('venda_item_id')}-{devolucao_id or 'venda'}-{indice}"
                ),
                origem_tipo=(
                    "estorno_estimativa_cmv" if devolucao_id else "estimativa_cmv"
                ),
                origem_label=origem_label,
                data=item.get("data"),
                descricao=f"{codigo} - {nome}" if codigo else nome,
                contraparte=contraparte,
                documento=str(numero_venda),
                valor=float(_decimal(item.get("valor_estimado", 0))),
                valor_auxiliar=float(_decimal(item.get("valor_venda", 0))),
                link="/produtos",
                meta={
                    "produto_id": item.get("produto_id"),
                    "quantidade": item.get("quantidade"),
                    "valor_venda": item.get("valor_venda"),
                    "percentual_custo": float(percentual),
                    "origem_percentual": item.get("origem_percentual"),
                    "provisorio": True,
                    "devolucao_id": devolucao_id,
                    "origem_cmv_estornado": origem_estorno,
                },
            )
        )

    detalhes.sort(key=lambda detalhe: detalhe.data or "", reverse=True)
    return detalhes


def _detalhes_vendas_campo(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    canal: str,
    campo: str,
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> List[DREDetalheItem]:
    if campo == "cmv_estimado":
        return _detalhes_cmv_estimado(
            db,
            mes,
            ano,
            tenant_id,
            canal,
            mes_inicial=mes_inicial,
            data_final=data_final,
        )

    inicio, fim = _periodo_meses(mes_inicial or mes, mes, ano, data_final)
    vendas = (
        db.query(Venda)
        .options(
            selectinload(Venda.cliente),
            selectinload(Venda.itens).selectinload(VendaItem.produto),
            selectinload(Venda.pagamentos),
        )
        .filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio,
                Venda.data_venda < fim,
                _filtro_status_venda_dre(),
            )
        )
        .all()
    )
    vendas = [
        venda
        for venda in vendas
        if _normalizar_canal(getattr(venda, "canal", None)) == canal
    ]
    snapshots = _preparar_snapshots_vendas(db, tenant_id, vendas)

    detalhes: List[DREDetalheItem] = []
    for venda in vendas:
        snapshot = snapshots.get(int(venda.id), {})
        valor = _valor_snapshot_campo(campo, venda, snapshot)
        if abs(valor) <= Decimal("0.004"):
            continue

        pagamentos = []
        for pagamento in list(getattr(venda, "pagamentos", []) or []):
            forma = getattr(pagamento, "forma_pagamento", None) or getattr(
                pagamento, "tipo", None
            )
            if forma:
                pagamentos.append(str(forma))

        cliente_nome = (
            getattr(getattr(venda, "cliente", None), "nome", None) or "Sem cliente"
        )
        numero = getattr(venda, "numero_venda", None) or f"#{venda.id}"
        detalhes.append(
            DREDetalheItem(
                id=f"venda-{venda.id}",
                origem_tipo="venda",
                origem_label="Venda",
                data=_data_iso(getattr(venda, "data_venda", None)),
                descricao=f"{numero} - {cliente_nome}",
                contraparte=cliente_nome,
                documento=str(numero),
                status=getattr(venda, "status", None),
                valor=float(valor),
                valor_auxiliar=float(_decimal(getattr(venda, "total", 0))),
                link="/financeiro/vendas",
                meta={
                    "canal": canal,
                    "cupom": getattr(venda, "cupom_code", None),
                    "pagamentos": ", ".join(pagamentos),
                },
            )
        )

    if campo in {"cmv", "custo_servicos"}:
        detalhes.extend(
            _detalhes_devolucoes_campo(
                db,
                mes,
                ano,
                tenant_id,
                canal,
                campo,
                mes_inicial=mes_inicial,
                data_final=data_final,
            )
        )

    detalhes.sort(key=lambda item: item.data or "", reverse=True)
    return detalhes


def _detalhes_recebiveis_manuais(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    canal: str,
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> List[DREDetalheItem]:
    inicio, fim = _periodo_meses(mes_inicial or mes, mes, ano, data_final)
    contas = (
        _contas_receber_manuais_query(db, tenant_id, inicio, fim)
        .options(selectinload(ContaReceber.cliente))
        .all()
    )
    detalhes = []
    for conta in contas:
        if _normalizar_canal(getattr(conta, "canal", None)) != canal:
            continue
        valor = _valor_recebivel_competencia(conta)
        if abs(valor) <= Decimal("0.004"):
            continue
        detalhes.append(
            DREDetalheItem(
                id=f"conta-receber-{conta.id}",
                origem_tipo="conta_receber",
                origem_label="Conta a receber",
                data=_data_iso(getattr(conta, "data_emissao", None)),
                descricao=getattr(conta, "descricao", "") or f"Conta #{conta.id}",
                contraparte=getattr(getattr(conta, "cliente", None), "nome", None),
                documento=getattr(conta, "documento", None),
                status=getattr(conta, "status", None),
                valor=float(valor),
                link="/financeiro/contas-receber",
                meta={"canal": canal},
            )
        )
    detalhes.sort(key=lambda item: item.data or "", reverse=True)
    return detalhes


def _detalhes_contas_campo(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    canal: str,
    campo: str,
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> List[DREDetalheItem]:
    inicio, fim = _periodo_meses(mes_inicial or mes, mes, ano, data_final)
    frete_ids = ids_fretes_sobre_compras(db, tenant_id)
    if campo == "fretes_compras":
        if not frete_ids:
            return []
        contas = (
            db.query(ContaPagar)
            .options(selectinload(ContaPagar.fornecedor))
            .filter(
                *filtros_contas_pagar_dre(tenant_id, inicio, fim),
                ContaPagar.dre_subcategoria_id.in_(frete_ids),
            )
            .all()
        )
        contas = [
            conta
            for conta in contas
            if _normalizar_canal(getattr(conta, "canal", None)) == canal
        ]
        subcategorias = _subcategorias_contas_map(db, tenant_id, contas)
    else:
        contas_base = (
            db.query(ContaPagar)
            .options(selectinload(ContaPagar.fornecedor))
            .filter(*filtros_contas_pagar_dre(tenant_id, inicio, fim))
            .all()
        )
        subcategorias = _subcategorias_contas_map(db, tenant_id, contas_base)
        tipos, categorias = classificacoes_contas_pagar(db, tenant_id, contas_base)
        contas = []
        contas_folha = []
        for conta in contas_base:
            if conta.dre_subcategoria_id in frete_ids or eh_compra_estoque(
                conta, tipos, categorias
            ):
                continue
            contas_folha.append(conta)
            if _normalizar_canal(getattr(conta, "canal", None)) != canal:
                continue
            subcategoria = subcategorias.get(
                getattr(conta, "dre_subcategoria_id", None)
            )
            texto = _texto_conta(conta, subcategoria)
            campo_conta = _classificar_conta_dre(texto)
            if (
                campo_conta != "taxas_marketplace"
                and _eh_custo_de_venda_ja_vindo_da_venda(texto)
            ):
                continue
            if campo_conta == campo:
                contas.append(conta)

    detalhes: List[DREDetalheItem] = []
    for conta in contas:
        fornecedor_nome = getattr(getattr(conta, "fornecedor", None), "nome", None)
        documento = getattr(conta, "documento", None) or getattr(
            conta, "nfe_numero", None
        )
        subcategoria = subcategorias.get(getattr(conta, "dre_subcategoria_id", None))
        valor = (
            _decimal(getattr(conta, "valor_original", 0))
            if campo == "fretes_compras"
            else _conta_valor(conta)
        )
        if abs(valor) <= Decimal("0.004"):
            continue
        detalhes.append(
            DREDetalheItem(
                id=f"conta-pagar-{conta.id}",
                origem_tipo="conta_pagar",
                origem_label="Conta a pagar",
                data=_data_iso(getattr(conta, "data_emissao", None)),
                descricao=getattr(conta, "descricao", "") or f"Conta #{conta.id}",
                contraparte=fornecedor_nome,
                documento=str(documento) if documento else None,
                status=getattr(conta, "status", None),
                valor=float(valor),
                valor_auxiliar=float(_decimal(getattr(conta, "valor_pago", 0))),
                link="/financeiro/contas-pagar",
                meta={
                    "vencimento": _data_iso(getattr(conta, "data_vencimento", None)),
                    "subcategoria": getattr(subcategoria, "nome", None),
                    "canal": canal,
                },
            )
        )

    if campo == "despesas_pessoal":
        resumo_folha = calcular_resumo_folha_gerencial(
            db,
            mes,
            ano,
            tenant_id,
            contas_folha,
            subcategorias,
            mes_inicial=mes_inicial,
            data_final=data_final,
        )
        for provisao in resumo_folha["provisoes"]:
            if canal_provisao_folha(provisao) != canal:
                continue
            valor_provisao = _decimal(getattr(provisao, "despesas_pessoal", 0))
            if abs(valor_provisao) <= Decimal("0.004"):
                continue
            detalhes.append(
                DREDetalheItem(
                    id=f"provisao-folha-{provisao.id}",
                    origem_tipo="provisao_dre",
                    origem_label="Provisao da folha",
                    data=_data_iso(getattr(provisao, "data_fim", None)),
                    descricao=getattr(provisao, "observacao", None)
                    or "Provisao trabalhista registrada",
                    contraparte="DRE / provisoes trabalhistas",
                    valor=float(valor_provisao),
                    meta={"canal": canal},
                )
            )

        complemento = resumo_folha["complemento_loja_fisica"]
        if canal == "loja_fisica" and complemento > Decimal("0.004"):
            quantidade = resumo_folha["quantidade_funcionarios"]
            lancado = resumo_folha["folha_lancada_por_canal"].get(
                "loja_fisica", Decimal("0")
            )
            provisoes = resumo_folha["provisoes_por_canal"].get(
                "loja_fisica", Decimal("0")
            )
            detalhes.append(
                DREDetalheItem(
                    id=f"folha-gerencial-estimada-{ano}-{mes_inicial or mes:02d}-{mes:02d}",
                    origem_tipo="folha_gerencial",
                    origem_label="Cadastro de remuneracao",
                    data=f"{ano:04d}-{mes:02d}-01",
                    descricao=(
                        f"Complemento gerencial de {quantidade} funcionario(s) ativo(s)"
                    ),
                    contraparte="Funcionarios e cargos",
                    valor=float(complemento),
                    link="/configuracoes/rh/funcionarios",
                    meta={
                        "estimado": float(resumo_folha["estimado"]),
                        "contas_lancadas": float(lancado),
                        "provisoes": float(provisoes),
                        "canal": canal,
                    },
                )
            )

    detalhes.sort(key=lambda item: item.data or "", reverse=True)
    return detalhes


@router.get("/detalhes", response_model=DREDetalheResponse)
def detalhar_linha_dre_por_canal(
    ano: int = Query(..., description="Ano do DRE"),
    mes: int = Query(..., description="Mês do DRE (1-12)"),
    mes_inicial: Optional[int] = Query(
        None, description="Mês inicial para período acumulado (1-12)"
    ),
    data_final: Optional[date] = Query(
        None, description="Último dia incluído no período acumulado"
    ),
    canal: str = Query(..., description="Canal da linha"),
    campo: str = Query(..., description="Campo da DRE"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    mes_inicial = mes if mes_inicial is None else mes_inicial
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Mês deve estar entre 1 e 12")
    if mes_inicial < 1 or mes_inicial > mes:
        raise HTTPException(
            status_code=400,
            detail="Mês inicial deve estar entre 1 e o mês final",
        )
    if data_final is not None and (
        data_final.year != ano
        or data_final.month < mes_inicial
        or data_final.month > mes
    ):
        raise HTTPException(
            status_code=400,
            detail="Data final deve pertencer ao período informado",
        )

    campo = (campo or "").strip()
    canal = _normalizar_canal(canal)
    if (
        campo not in CAMPOS_DETALHE_VENDAS
        and campo not in CAMPOS_DETALHE_CONTAS
        and campo not in CAMPOS_DETALHE_RECEBIVEIS
        and campo not in CAMPOS_DETALHE_DEVOLUCOES
    ):
        raise HTTPException(
            status_code=400, detail="Linha da DRE sem detalhamento disponivel"
        )

    _, tenant_id = user_and_tenant
    if campo in CAMPOS_DETALHE_VENDAS:
        detalhes = _detalhes_vendas_campo(
            db,
            mes,
            ano,
            tenant_id,
            canal,
            campo,
            mes_inicial=mes_inicial,
            data_final=data_final,
        )
    elif campo in CAMPOS_DETALHE_RECEBIVEIS:
        detalhes = _detalhes_recebiveis_manuais(
            db,
            mes,
            ano,
            tenant_id,
            canal,
            mes_inicial=mes_inicial,
            data_final=data_final,
        )
    elif campo in CAMPOS_DETALHE_DEVOLUCOES:
        detalhes = _detalhes_devolucoes_campo(
            db,
            mes,
            ano,
            tenant_id,
            canal,
            campo,
            mes_inicial=mes_inicial,
            data_final=data_final,
        )
    else:
        detalhes = _detalhes_contas_campo(
            db,
            mes,
            ano,
            tenant_id,
            canal,
            campo,
            mes_inicial=mes_inicial,
            data_final=data_final,
        )

    total = sum((_decimal(item.valor) for item in detalhes), Decimal("0"))
    pagina_items, page_size_final, pages = _paginar_detalhes(detalhes, page, page_size)
    config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG["loja_fisica"])

    return DREDetalheResponse(
        campo=campo,
        canal=canal,
        canal_nome=config["nome"],
        periodo=_periodo_label_intervalo(mes_inicial, mes, ano, data_final),
        origem=ORIGENS_DRE.get(campo),
        total=float(total),
        total_itens=len(detalhes),
        page=max(int(page or 1), 1),
        page_size=page_size_final,
        pages=pages,
        items=pagina_items,
    )
