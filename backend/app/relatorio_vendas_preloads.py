"""Consultas e agregados de apoio do relatorio de vendas."""

import logging

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, selectinload

from .comissoes_models import ComissaoItem
from .empresa_config_fiscal_models import EmpresaConfigFiscal
from .financeiro_models import FormaPagamento
from .models import Cliente
from .produtos_models import EstoqueMovimentacao, Produto
from .relatorio_vendas_common import (
    _normalizar_forma_pagamento_label,
    _valores_operacionais_venda,
)
from .vendas_models import Venda, VendaItem


logger = logging.getLogger(__name__)


def carregar_vendas_relatorio(
    *,
    db: Session,
    tenant_id,
    data_inicio_dt,
    data_fim_dt,
    canal_normalizado: str | None,
):
    filtros_vendas = [
        Venda.tenant_id == tenant_id,
        Venda.data_venda >= data_inicio_dt,
        Venda.data_venda <= data_fim_dt,
        or_(Venda.status.is_(None), Venda.status != "cancelada"),
    ]
    if canal_normalizado:
        filtros_vendas.append(Venda.canal == canal_normalizado)

    return (
        db.query(Venda)
        .options(
            selectinload(Venda.cliente),
            selectinload(Venda.usuario),
            selectinload(Venda.itens)
            .selectinload(VendaItem.produto)
            .selectinload(Produto.categoria),
            selectinload(Venda.itens)
            .selectinload(VendaItem.produto)
            .selectinload(Produto.marca),
            selectinload(Venda.pagamentos),
        )
        .filter(and_(*filtros_vendas))
        .all()
    )


def carregar_contexto_relatorio_vendas(*, db: Session, tenant_id, vendas) -> dict:
    venda_ids = [v.id for v in vendas]

    comissoes_map = _carregar_comissoes_por_venda(db, tenant_id, venda_ids)

    return {
        "impostos_percentual_global": _carregar_impostos_percentual_global(
            db, tenant_id
        ),
        "comissoes_map": comissoes_map,
        "comissao_total_por_venda": {
            venda_id: round(sum(float(item.valor_comissao or 0) for item in itens), 2)
            for venda_id, itens in comissoes_map.items()
        },
        "formas_pagamento_map": _carregar_formas_pagamento_map(db, tenant_id),
        "cashback_por_venda": _carregar_cashback_por_venda(db, tenant_id, venda_ids),
        "cupons_por_venda": _carregar_cupons_por_venda(db, tenant_id, venda_ids),
        "entregadores_map": _carregar_entregadores_map(db, tenant_id, vendas),
        "estoque_custos_por_venda": _carregar_estoque_custos_por_venda(
            db, tenant_id, venda_ids
        ),
    }


def montar_agregados_operacionais_relatorio(vendas) -> dict:
    valores_operacionais_por_venda = {
        venda.id: _valores_operacionais_venda(venda) for venda in vendas
    }
    venda_bruta = sum(v["valor_bruto"] for v in valores_operacionais_por_venda.values())
    taxa_entrega = sum(
        v["taxa_entrega"] for v in valores_operacionais_por_venda.values()
    )
    desconto = sum(v["desconto"] for v in valores_operacionais_por_venda.values())
    venda_liquida = sum(
        v["valor_liquido"] for v in valores_operacionais_por_venda.values()
    )
    valor_recebido = sum(
        v["valor_recebido"] for v in valores_operacionais_por_venda.values()
    )
    em_aberto = sum(v["saldo_aberto"] for v in valores_operacionais_por_venda.values())
    percentual_desconto = round(
        (desconto / venda_bruta * 100) if venda_bruta > 0 else 0, 1
    )

    return {
        "valores_operacionais_por_venda": valores_operacionais_por_venda,
        "resumo": {
            "venda_bruta": round(venda_bruta, 2),
            "taxa_entrega": round(taxa_entrega, 2),
            "desconto": round(desconto, 2),
            "percentual_desconto": percentual_desconto,
            "venda_liquida": round(venda_liquida, 2),
            "valor_recebido": round(valor_recebido, 2),
            "em_aberto": round(em_aberto, 2),
            "quantidade_vendas": len(vendas),
        },
        "vendas_por_data_lista": _montar_vendas_por_data(
            vendas, valores_operacionais_por_venda
        ),
        "formas_recebimento_lista": _montar_formas_recebimento(vendas),
        "vendas_por_funcionario_lista": _montar_vendas_por_funcionario(
            vendas, valores_operacionais_por_venda
        ),
        "vendas_por_tipo_lista": _montar_vendas_por_tipo(
            vendas, valores_operacionais_por_venda
        ),
    }


def _carregar_impostos_percentual_global(db: Session, tenant_id) -> float:
    try:
        config_fiscal = (
            db.query(EmpresaConfigFiscal)
            .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
            .first()
        )
        return (
            float(config_fiscal.aliquota_simples_vigente)
            if config_fiscal and config_fiscal.aliquota_simples_vigente
            else 0.0
        )
    except Exception as exc:
        logger.warning(f"Erro ao buscar config fiscal (tabela pode nao existir): {exc}")
        return 0.0


def _carregar_comissoes_por_venda(db: Session, tenant_id, venda_ids: list[int]) -> dict:
    comissoes_map = {}
    if not venda_ids:
        return comissoes_map

    try:
        comissoes_itens = (
            db.query(ComissaoItem)
            .filter(
                and_(
                    ComissaoItem.venda_id.in_(venda_ids),
                    ComissaoItem.tenant_id == tenant_id,
                )
            )
            .all()
        )
        for com_item in comissoes_itens:
            comissoes_map.setdefault(com_item.venda_id, []).append(com_item)
    except Exception as exc:
        logger.warning(f"Erro ao buscar comissoes (tabela pode nao existir): {exc}")
    return comissoes_map


def _carregar_formas_pagamento_map(db: Session, tenant_id) -> dict:
    formas_pagamento_map = {}
    try:
        formas_pag_list = (
            db.query(FormaPagamento)
            .filter(
                and_(
                    FormaPagamento.ativo.is_(True),
                    FormaPagamento.tenant_id == tenant_id,
                )
            )
            .all()
        )
        for fp in formas_pag_list:
            formas_pagamento_map[fp.nome.lower().strip()] = fp
    except Exception as exc:
        logger.warning(
            f"Erro ao buscar formas de pagamento (tabela pode nao existir): {exc}"
        )
    return formas_pagamento_map


def _carregar_cashback_por_venda(db: Session, tenant_id, venda_ids: list[int]) -> dict:
    if not venda_ids:
        return {}

    try:
        from app.campaigns.models import CashbackTransaction

        resgates = (
            db.query(
                CashbackTransaction.source_id, func.sum(CashbackTransaction.amount)
            )
            .filter(
                CashbackTransaction.tenant_id == tenant_id,
                CashbackTransaction.amount < 0,
                CashbackTransaction.source_id.in_(venda_ids),
            )
            .group_by(CashbackTransaction.source_id)
            .all()
        )
        return {row[0]: float(abs(row[1])) for row in resgates}
    except Exception as exc:
        logger.warning(
            f"Erro ao buscar cashback por venda (tabela pode nao existir): {exc}"
        )
        return {}


def _carregar_cupons_por_venda(db: Session, tenant_id, venda_ids: list[int]) -> dict:
    if not venda_ids:
        return {}

    try:
        from app.campaigns.models import CouponRedemption

        resgates_cupons = (
            db.query(
                CouponRedemption.venda_id, func.sum(CouponRedemption.discount_applied)
            )
            .filter(
                CouponRedemption.tenant_id == tenant_id,
                CouponRedemption.venda_id.in_(venda_ids),
                CouponRedemption.voided_at.is_(None),
            )
            .group_by(CouponRedemption.venda_id)
            .all()
        )
        return {row[0]: float(row[1] or 0) for row in resgates_cupons}
    except Exception as exc:
        logger.warning(
            f"Erro ao buscar cupons por venda (tabela pode nao existir): {exc}"
        )
        return {}


def _carregar_entregadores_map(db: Session, tenant_id, vendas) -> dict:
    entregador_ids = {
        venda.entregador_id
        for venda in vendas
        if venda.tem_entrega and venda.entregador_id
    }
    if not entregador_ids:
        return {}

    try:
        entregadores = (
            db.query(Cliente.id, Cliente.taxa_fixa_entrega)
            .filter(
                and_(Cliente.tenant_id == tenant_id, Cliente.id.in_(entregador_ids))
            )
            .all()
        )
        return {
            entregador_id: float(taxa_fixa_entrega or 0)
            for entregador_id, taxa_fixa_entrega in entregadores
        }
    except Exception as exc:
        logger.warning(f"Erro ao buscar entregadores para rentabilidade: {exc}")
        return {}


def _carregar_estoque_custos_por_venda(
    db: Session, tenant_id, venda_ids: list[int]
) -> dict:
    estoque_custos_por_venda = {}
    if not venda_ids:
        return estoque_custos_por_venda

    try:
        movimentos_estoque = (
            db.query(EstoqueMovimentacao)
            .filter(
                and_(
                    EstoqueMovimentacao.tenant_id == tenant_id,
                    EstoqueMovimentacao.referencia_tipo == "venda",
                    EstoqueMovimentacao.referencia_id.in_(venda_ids),
                    EstoqueMovimentacao.tipo == "saida",
                )
            )
            .all()
        )

        for movimento in movimentos_estoque:
            mapa_venda = estoque_custos_por_venda.setdefault(
                movimento.referencia_id, {}
            )
            mapa_produto = mapa_venda.setdefault(
                movimento.produto_id, {"quantidade": 0.0, "valor_total": 0.0}
            )
            mapa_produto["quantidade"] += abs(float(movimento.quantidade or 0))
            mapa_produto["valor_total"] += abs(float(movimento.valor_total or 0))
    except Exception as exc:
        logger.warning(
            f"Erro ao buscar movimentacoes de estoque para rentabilidade: {exc}"
        )
    return estoque_custos_por_venda


def _montar_vendas_por_data(vendas, valores_operacionais_por_venda: dict) -> list[dict]:
    vendas_por_data = {}
    for venda in vendas:
        data_str = venda.data_venda.date().isoformat()
        if data_str not in vendas_por_data:
            vendas_por_data[data_str] = {
                "data": data_str,
                "quantidade": 0,
                "valor_bruto": 0,
                "taxa_entrega": 0,
                "desconto": 0,
                "valor_liquido": 0,
                "valor_recebido": 0,
                "saldo_aberto": 0,
            }

        valores_venda = valores_operacionais_por_venda[venda.id]
        vendas_por_data[data_str]["quantidade"] += 1
        vendas_por_data[data_str]["valor_bruto"] += valores_venda["valor_bruto"]
        vendas_por_data[data_str]["taxa_entrega"] += valores_venda["taxa_entrega"]
        vendas_por_data[data_str]["desconto"] += valores_venda["desconto"]
        vendas_por_data[data_str]["valor_liquido"] += valores_venda["valor_liquido"]
        vendas_por_data[data_str]["valor_recebido"] += valores_venda["valor_recebido"]
        vendas_por_data[data_str]["saldo_aberto"] += valores_venda["saldo_aberto"]

    for data_str, item in vendas_por_data.items():
        qtd = item["quantidade"]
        item["ticket_medio"] = round(item["valor_liquido"] / qtd if qtd > 0 else 0, 2)
        item["percentual_desconto"] = round(
            (item["desconto"] / item["valor_bruto"] * 100)
            if item["valor_bruto"] > 0
            else 0,
            1,
        )

    return sorted(vendas_por_data.values(), key=lambda item: item["data"])


def _montar_formas_recebimento(vendas) -> list[dict]:
    formas_recebimento = {}
    for venda in vendas:
        for pag in venda.pagamentos:
            forma_base = _normalizar_forma_pagamento_label(pag.forma_pagamento)
            if pag.numero_parcelas and pag.numero_parcelas > 1:
                forma_completa = f"{forma_base} {pag.numero_parcelas}x"
                parcelas = pag.numero_parcelas
            else:
                forma_completa = forma_base
                parcelas = 1

            if forma_completa not in formas_recebimento:
                formas_recebimento[forma_completa] = {
                    "forma_pagamento": forma_completa,
                    "valor_total": 0,
                    "ordem_forma": forma_base,
                    "ordem_parcelas": parcelas,
                }
            formas_recebimento[forma_completa]["valor_total"] += pag.valor

    formas_recebimento_lista = sorted(
        formas_recebimento.values(),
        key=lambda item: (item["ordem_forma"], item["ordem_parcelas"]),
    )
    for item in formas_recebimento_lista:
        item.pop("ordem_forma", None)
        item.pop("ordem_parcelas", None)
    return formas_recebimento_lista


def _montar_vendas_por_funcionario(
    vendas, valores_operacionais_por_venda: dict
) -> list[dict]:
    vendas_por_funcionario = {}
    for venda in vendas:
        funcionario_id = venda.user_id
        nome_func = (
            venda.usuario.nome
            if funcionario_id and venda.usuario
            else f"ID {funcionario_id}"
            if funcionario_id
            else "Sem funcionario"
        )
        if nome_func not in vendas_por_funcionario:
            vendas_por_funcionario[nome_func] = {
                "funcionario": nome_func,
                "quantidade": 0,
                "valor_bruto": 0,
                "desconto": 0,
                "valor_liquido": 0,
            }

        valores_venda = valores_operacionais_por_venda[venda.id]
        vendas_por_funcionario[nome_func]["quantidade"] += 1
        vendas_por_funcionario[nome_func]["valor_bruto"] += valores_venda["valor_bruto"]
        vendas_por_funcionario[nome_func]["desconto"] += valores_venda["desconto"]
        vendas_por_funcionario[nome_func]["valor_liquido"] += valores_venda[
            "valor_liquido"
        ]

    return sorted(
        vendas_por_funcionario.values(),
        key=lambda item: item["valor_liquido"],
        reverse=True,
    )


def _montar_vendas_por_tipo(vendas, valores_operacionais_por_venda: dict) -> list[dict]:
    vendas_por_tipo = {
        "Produto": {
            "tipo": "Produto",
            "quantidade": 0,
            "valor_bruto": 0,
            "desconto": 0,
            "valor_liquido": 0,
        }
    }

    for venda in vendas:
        valores_venda = valores_operacionais_por_venda[venda.id]
        vendas_por_tipo["Produto"]["quantidade"] += 1
        vendas_por_tipo["Produto"]["valor_bruto"] += valores_venda["valor_bruto"]
        vendas_por_tipo["Produto"]["desconto"] += valores_venda["desconto"]
        vendas_por_tipo["Produto"]["valor_liquido"] += valores_venda["valor_liquido"]

    return list(vendas_por_tipo.values())
