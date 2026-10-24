"""Consultas em lote para a composição comercial, sempre limitadas ao tenant."""

from collections import defaultdict
from datetime import datetime, time, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from app.caixa.conferencia import instante_fechamento, moeda, valor_recebimento_dinheiro
from app.caixa.formas_pagamento import (
    carregar_nomes_formas_pagamento,
    nome_forma_pagamento,
)
from app.caixa.recebimentos import filtro_pagamentos_caixa
from app.financeiro_models import Recebimento
from app.services.faturamento_composicao import (
    _contas_planos,
    compor_recebimentos,
    compor_vendas,
    data_local,
    eh_plano,
    mesmo_tenant,
    normalizar,
)
from app.utils.timezone import as_brasilia_naive, now_brasilia
from app.vendas.status_pagamento import pagamento_valido_para_saldo
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas_models import Venda, VendaBaixaLoteItem, VendaPagamento


def opcoes_composicao_vendas():
    return (
        selectinload(Venda.pagamentos),
        selectinload(Venda.itens),
        selectinload(Venda.contas_receber),
    )


def carregar_vendas_periodo(db, tenant_id, inicio, fim, *, caixa_id=None):
    query = (
        db.query(Venda)
        .options(*opcoes_composicao_vendas())
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.data_venda >= datetime.combine(inicio, time.min),
            Venda.data_venda < datetime.combine(fim + timedelta(days=1), time.min),
            or_(
                Venda.status.is_(None), Venda.status.notin_(["cancelada", "cancelado"])
            ),
        )
    )
    if caixa_id is not None:
        query = query.filter(Venda.caixa_id == caixa_id)
    return query.all()


def montar_composicao_vendas(db, tenant_id, vendas, inicio, fim):
    devolucoes = defaultdict(list)
    ids_devolvidas = [
        v.id
        for v in vendas
        if "devol" in normalizar(getattr(v, "status", ""))
        and getattr(v, "id", None) is not None
    ]
    if ids_devolvidas:
        eventos = (
            db.query(VendaDevolucao)
            .filter(
                VendaDevolucao.tenant_id == tenant_id,
                VendaDevolucao.venda_id.in_(ids_devolvidas),
            )
            .all()
        )
        for evento in eventos:
            devolucoes[evento.venda_id].append(evento)

    contas_ids = set()
    pagamentos_lote = set()
    for venda in vendas:
        pagamentos = [
            p
            for p in (getattr(venda, "pagamentos", None) or [])
            if mesmo_tenant(venda, p) and pagamento_valido_para_saldo(p)
        ]
        for conta in _contas_planos(venda, pagamentos):
            if getattr(conta, "id", None) is not None:
                contas_ids.add(conta.id)
        pagamentos_lote.update(
            p.id
            for p in (getattr(venda, "pagamentos", None) or [])
            if mesmo_tenant(venda, p)
            if getattr(p, "baixa_lote_id", None) is not None
        )
    recebimentos = defaultdict(list)
    espelhos = set()
    if contas_ids:
        registros = (
            db.query(Recebimento)
            .options(joinedload(Recebimento.forma_pagamento))
            .filter(
                Recebimento.tenant_id == tenant_id,
                Recebimento.conta_receber_id.in_(contas_ids),
            )
            .all()
        )
        for registro in registros:
            recebimentos[registro.conta_receber_id].append(registro)
        if pagamentos_lote:
            vinculos = (
                db.query(VendaBaixaLoteItem)
                .filter(
                    VendaBaixaLoteItem.tenant_id == tenant_id,
                    VendaBaixaLoteItem.pagamento_id.in_(pagamentos_lote),
                )
                .all()
            )
            espelhos = {
                item.efeitos.get("recebimento_id")
                for item in vinculos
                if isinstance(item.efeitos, dict)
            }
    return compor_vendas(
        vendas,
        data_inicio=inicio,
        data_fim=fim,
        devolucoes_por_venda=devolucoes,
        recebimentos_por_conta=recebimentos,
        recebimentos_espelhados=espelhos,
    )


def montar_composicoes_caixa(db, *, caixa, tenant_id, movimentacoes):
    inicio = as_brasilia_naive(caixa.data_abertura).date()
    fechamento = instante_fechamento(caixa) if caixa.status == "fechado" else None
    fim = as_brasilia_naive(fechamento).date() if fechamento else now_brasilia().date()
    fim = max(inicio, fim)
    # O caixa tem dois recortes distintos: vendas de origem nele e dentro de
    # suas datas civis; recebimentos vinculados a ele, mesmo de vendas antigas.
    # Painel e app chamam carregar_vendas_periodo sem caixa_id (empresa inteira).
    vendas = carregar_vendas_periodo(db, tenant_id, inicio, fim, caixa_id=caixa.id)
    composicao_vendas = montar_composicao_vendas(db, tenant_id, vendas, inicio, fim)
    composicao_vendas.update(
        escopo="caixa",
        caixa_id=caixa.id,
        numero_caixa=caixa.numero_caixa,
        criterio="origem_caixa_e_data_venda",
    )
    # Não há filtro pela origem da venda. Recebimento pertence ao caixa que o
    # registrou; dinheiro vem dos movimentos, e os demais meios dos pagamentos.
    pagamentos = (
        db.query(VendaPagamento, Venda.id, Venda.numero_venda, Venda.data_venda)
        .join(Venda, VendaPagamento.venda_id == Venda.id)
        .filter(
            filtro_pagamentos_caixa(caixa),
            Venda.tenant_id == tenant_id,
            VendaPagamento.tenant_id == tenant_id,
        )
        .all()
    )
    nomes_formas = carregar_nomes_formas_pagamento(
        db,
        tenant_id=tenant_id,
        forma_ids=[pagamento.forma_pagamento_id for pagamento, *_ in pagamentos],
    )
    entradas_dinheiro = [
        m
        for m in movimentacoes
        if normalizar(m.forma_pagamento) == "dinheiro"
        and (m.tipo == "venda" or (m.tipo == "devolucao" and m.venda_id))
    ]
    ids = {m.venda_id for m in entradas_dinheiro if m.venda_id}
    referencias = (
        {
            venda_id: (numero, data)
            for venda_id, numero, data in db.query(
                Venda.id, Venda.numero_venda, Venda.data_venda
            )
            .filter(Venda.tenant_id == tenant_id, Venda.id.in_(ids))
            .all()
        }
        if ids
        else {}
    )
    eventos = []
    for movimento in entradas_dinheiro:
        numero, data = referencias.get(movimento.venda_id, (None, None))
        valor = valor_recebimento_dinheiro(movimento)
        eventos.append(
            {
                "id": f"movimento-{movimento.id}",
                "origem": "movimento",
                "venda_id": movimento.venda_id,
                "numero_venda": numero,
                "data_venda": data_local(data),
                "data_recebimento": data_local(movimento.data_movimento),
                "forma_pagamento": "Dinheiro",
                "valor": float(valor),
                "tipo": "devolucao" if valor < 0 else "pagamento",
            }
        )
    for pagamento, venda_id, numero, data in pagamentos:
        if normalizar(pagamento.forma_pagamento) == "dinheiro" or eh_plano(pagamento):
            continue
        valor = moeda(pagamento.valor)
        eventos.append(
            {
                "id": f"pagamento-{pagamento.id}",
                "origem": "pagamento",
                "venda_id": venda_id,
                "numero_venda": numero,
                "data_venda": data_local(data),
                "data_recebimento": data_local(pagamento.data_pagamento),
                "forma_pagamento": nome_forma_pagamento(pagamento, nomes_formas),
                "forma_pagamento_tipo": pagamento.forma_pagamento,
                "valor": float(valor),
                "tipo": "estorno" if valor < 0 else "pagamento",
            }
        )
    composicao_recebimentos = compor_recebimentos(
        eventos, data_inicio=inicio, data_fim=fim
    )
    composicao_recebimentos.update(
        caixa_id=caixa.id,
        numero_caixa=caixa.numero_caixa,
        criterio="vinculo_recebimento_caixa",
    )
    return {
        "vendas_periodo": composicao_vendas,
        "composicao_recebimentos": composicao_recebimentos,
    }
