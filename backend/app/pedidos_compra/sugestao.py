from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional


JANELAS_GIRO_SUGESTAO = (7, 15, 30, 60, 90)
MIN_VENDAS_AJUSTE_RUPTURA = 3
MIN_DIAS_COM_ESTOQUE_AJUSTE_RUPTURA = 7
MAX_MULTIPLICADOR_AJUSTE_RUPTURA = 2.0
MARGEM_SEGURANCA_COMPRA_DIAS = 7


def _float_seguro_sugestao(valor, padrao: float = 0.0) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return padrao
    return numero if math.isfinite(numero) else padrao


def _round_seguro_sugestao(valor, casas: int = 2, padrao: float = 0.0) -> float:
    return round(_float_seguro_sugestao(valor, padrao), casas)


def _sanitizar_json_sugestao(valor):
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else 0.0
    if isinstance(valor, dict):
        return {chave: _sanitizar_json_sugestao(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_sanitizar_json_sugestao(item) for item in valor]
    return valor


def _datetime_naive_utc_sugestao(valor: Optional[datetime]) -> Optional[datetime]:
    if not valor:
        return None

    if valor.tzinfo is not None and valor.utcoffset() is not None:
        return valor.astimezone(timezone.utc).replace(tzinfo=None)

    return valor


def _formatar_origem_venda(canal: Optional[str]) -> str:
    canal_normalizado = str(canal or "loja_fisica").strip().lower()
    nomes = {
        "loja_fisica": "Loja",
        "pdv": "Loja",
        "mercado_livre": "Mercado Livre",
        "shopee": "Shopee",
        "amazon": "Amazon",
        "site": "Site",
        "instagram": "Instagram",
        "bling": "Bling/online",
        "venda_bling": "Bling/online",
        "granel": "Granel",
        "granel_kit": "Granel/kit",
        "kit_virtual": "Granel/kit",
        "movimentacao": "Mov. estoque",
    }
    return nomes.get(canal_normalizado, canal_normalizado.replace("_", " ").title())


def _nova_stats_venda_sugestao() -> dict:
    return {
        "vendas_periodo": 0.0,
        "janelas": {str(dias): 0.0 for dias in JANELAS_GIRO_SUGESTAO},
        "granel_kg_periodo": 0.0,
        "granel_pacotes_periodo": 0.0,
        "granel_janelas_kg": {str(dias): 0.0 for dias in JANELAS_GIRO_SUGESTAO},
        "granel_janelas_pacotes": {str(dias): 0.0 for dias in JANELAS_GIRO_SUGESTAO},
        "granel_itens": defaultdict(lambda: {"kg": 0.0, "pacotes": 0.0}),
        "origens": defaultdict(float),
        "fontes": set(),
        "pares_venda_produto": set(),
    }


def _somar_venda_sugestao(
    stats_por_produto: dict,
    produto_id: int,
    quantidade: float,
    data_ref: Optional[datetime],
    data_inicio_periodo: datetime,
    data_fim: datetime,
    origem: str,
    fonte: str,
):
    if not produto_id or not data_ref:
        return

    data_ref = _datetime_naive_utc_sugestao(data_ref)
    data_inicio_periodo = _datetime_naive_utc_sugestao(data_inicio_periodo)
    data_fim = _datetime_naive_utc_sugestao(data_fim)
    if not data_ref or not data_inicio_periodo or not data_fim:
        return

    quantidade = _float_seguro_sugestao(quantidade)
    if quantidade <= 0:
        return

    stats = stats_por_produto[produto_id]
    if data_ref >= data_inicio_periodo:
        stats["vendas_periodo"] += quantidade

    dias_decorridos = max(0.0, (data_fim - data_ref).total_seconds() / 86400)
    for dias in JANELAS_GIRO_SUGESTAO:
        if dias_decorridos <= dias:
            stats["janelas"][str(dias)] += quantidade

    stats["origens"][_formatar_origem_venda(origem)] += quantidade
    stats["fontes"].add(fonte)


def _somar_vendas_rows_sugestao(
    stats_por_produto: dict,
    produto_ids: list[int],
    vendas_rows,
    data_inicio_periodo: datetime,
    data_fim: datetime,
) -> set[tuple[int, int]]:
    produto_ids_set = {int(produto_id) for produto_id in produto_ids or []}
    pares_venda_produto = set()

    for produto_id, venda_id, canal, data_ref, quantidade in vendas_rows:
        produto_id = int(produto_id)
        if venda_id:
            par = (int(venda_id), produto_id)
            pares_venda_produto.add(par)
            if produto_id in produto_ids_set:
                stats_por_produto[produto_id]["pares_venda_produto"].add(par)

        if produto_id in produto_ids_set:
            _somar_venda_sugestao(
                stats_por_produto,
                produto_id,
                quantidade,
                data_ref,
                data_inicio_periodo,
                data_fim,
                canal or "loja_fisica",
                "vendas",
            )

    return pares_venda_produto


def _somar_conversao_granel_sugestao(
    stats_por_produto: dict,
    produto_pai_id: int,
    produto_granel_id: int,
    produto_granel_nome: str | None,
    quantidade_kg: float,
    quantidade_pacotes: float,
    peso_pacote_kg: float,
    data_ref: Optional[datetime],
    data_inicio_periodo: datetime,
    data_fim: datetime,
):
    data_ref = _datetime_naive_utc_sugestao(data_ref)
    data_inicio_periodo = _datetime_naive_utc_sugestao(data_inicio_periodo)
    data_fim = _datetime_naive_utc_sugestao(data_fim)

    quantidade_kg = _float_seguro_sugestao(quantidade_kg)
    quantidade_pacotes = _float_seguro_sugestao(quantidade_pacotes)
    peso_pacote_kg = _float_seguro_sugestao(peso_pacote_kg)
    produto_pai_id = int(produto_pai_id or 0)
    if quantidade_kg <= 0 or quantidade_pacotes <= 0 or not produto_pai_id:
        return

    _somar_venda_sugestao(
        stats_por_produto,
        produto_pai_id,
        quantidade_pacotes,
        data_ref,
        data_inicio_periodo,
        data_fim,
        "granel",
        "conversao_granel",
    )

    if not data_ref or not data_inicio_periodo or not data_fim:
        return

    stats = stats_por_produto[produto_pai_id]
    if data_ref >= data_inicio_periodo:
        stats["granel_kg_periodo"] += quantidade_kg
        stats["granel_pacotes_periodo"] += quantidade_pacotes

    dias_decorridos = max(0.0, (data_fim - data_ref).total_seconds() / 86400)
    for dias in JANELAS_GIRO_SUGESTAO:
        if dias_decorridos <= dias:
            stats["granel_janelas_kg"][str(dias)] += quantidade_kg
            stats["granel_janelas_pacotes"][str(dias)] += quantidade_pacotes

    produto_granel_id = int(produto_granel_id or 0)
    item = stats["granel_itens"][produto_granel_id]
    item["produto_id"] = produto_granel_id
    item["produto_nome"] = produto_granel_nome
    item["peso_pacote_kg"] = peso_pacote_kg
    item["kg"] += quantidade_kg
    item["pacotes"] += quantidade_pacotes


def _somar_conversoes_granel_rows_sugestao(
    stats_por_produto: dict,
    conversoes_rows,
    data_inicio_periodo: datetime,
    data_fim: datetime,
) -> None:
    for conversao, produto_granel in conversoes_rows:
        _somar_conversao_granel_sugestao(
            stats_por_produto,
            conversao.produto_origem_id,
            conversao.produto_granel_id,
            produto_granel.nome if produto_granel else None,
            conversao.quantidade_granel_kg,
            conversao.quantidade_origem,
            conversao.peso_por_unidade_kg,
            conversao.created_at,
            data_inicio_periodo,
            data_fim,
        )


def _somar_movimentacoes_complementares_sugestao(
    stats_por_produto: dict,
    movimentos_rows,
    pares_venda_produto,
    vendas_referenciadas_validas,
    data_inicio_periodo: datetime,
    data_fim: datetime,
) -> None:
    pares_venda_produto = set(pares_venda_produto or [])
    vendas_referenciadas_validas = {
        int(venda_id) for venda_id in vendas_referenciadas_validas or []
    }

    for row in movimentos_rows:
        produto_id = int(row.produto_id)
        referencia_tipo = str(row.referencia_tipo or "").strip().lower()
        motivo = str(row.motivo or "").strip().lower()
        referencia_id = int(row.referencia_id) if row.referencia_id else None
        tem_item_direto = bool(
            referencia_id and (referencia_id, produto_id) in pares_venda_produto
        )
        venda_referenciada_valida = bool(
            referencia_id
            and referencia_tipo == "venda"
            and referencia_id in vendas_referenciadas_validas
        )
        origem_externa = (
            referencia_tipo == "venda_bling"
            or "bling" in referencia_tipo
            or "bling" in motivo
            or "online" in motivo
        )
        consumo_derivado = bool(venda_referenciada_valida and not tem_item_direto)

        if tem_item_direto:
            continue
        if not (consumo_derivado or origem_externa):
            continue

        origem = "granel_kit" if consumo_derivado else "bling"
        _somar_venda_sugestao(
            stats_por_produto,
            produto_id,
            row.quantidade,
            row.created_at,
            data_inicio_periodo,
            data_fim,
            origem,
            "estoque_componentes" if consumo_derivado else "estoque_externo",
        )


def _montar_resultado_vendas_sugestao(stats_por_produto: dict) -> dict:
    resultado = {}
    for produto_id, stats in stats_por_produto.items():
        origens = [
            {"canal": canal, "quantidade": _round_seguro_sugestao(quantidade, 3)}
            for canal, quantidade in sorted(
                stats["origens"].items(),
                key=lambda item: item[1],
                reverse=True,
            )
            if _float_seguro_sugestao(quantidade) > 0
        ]
        resultado[produto_id] = {
            "vendas_periodo": _round_seguro_sugestao(stats["vendas_periodo"], 3),
            "janelas": {
                chave: _round_seguro_sugestao(valor, 3)
                for chave, valor in stats["janelas"].items()
            },
            "origens": origens,
            "fontes": sorted(stats["fontes"]),
            "granel_consumo": {
                "kg_periodo": _round_seguro_sugestao(stats["granel_kg_periodo"], 3),
                "pacotes_equivalentes_periodo": _round_seguro_sugestao(
                    stats["granel_pacotes_periodo"], 3
                ),
                "janelas_kg": {
                    chave: _round_seguro_sugestao(valor, 3)
                    for chave, valor in stats["granel_janelas_kg"].items()
                },
                "janelas_pacotes": {
                    chave: _round_seguro_sugestao(valor, 3)
                    for chave, valor in stats["granel_janelas_pacotes"].items()
                },
                "itens": [
                    {
                        "produto_id": item.get("produto_id"),
                        "produto_nome": item.get("produto_nome"),
                        "peso_pacote_kg": _round_seguro_sugestao(
                            item.get("peso_pacote_kg"), 3
                        ),
                        "kg": _round_seguro_sugestao(item.get("kg"), 3),
                        "pacotes_equivalentes": _round_seguro_sugestao(
                            item.get("pacotes"), 3
                        ),
                    }
                    for item in sorted(
                        stats["granel_itens"].values(),
                        key=lambda valor: _float_seguro_sugestao(valor.get("kg")),
                        reverse=True,
                    )
                    if _float_seguro_sugestao(item.get("kg")) > 0
                ],
            },
        }

    return resultado


def _calcular_dias_com_estoque(
    movimentacoes: list,
    estoque_atual: float,
    data_inicio: datetime,
    data_fim: datetime,
) -> dict:
    data_inicio = _datetime_naive_utc_sugestao(data_inicio) or datetime.utcnow()
    data_fim = _datetime_naive_utc_sugestao(data_fim) or data_inicio
    total_dias = max(0.0, (data_fim - data_inicio).total_seconds() / 86400)
    if total_dias <= 0:
        return {
            "dias_com_estoque": 0.0,
            "dias_sem_estoque": 0.0,
            "teve_ruptura": estoque_atual <= 0,
            "ruptura_ativa": estoque_atual <= 0,
        }

    movimentos = sorted(
        [
            (_datetime_naive_utc_sugestao(mov.created_at), mov)
            for mov in movimentacoes
            if mov.created_at
        ],
        key=lambda item: item[0],
    )

    if not movimentos:
        dias_com_estoque = total_dias if estoque_atual > 0 else 0.0
        dias_sem_estoque = max(0.0, total_dias - dias_com_estoque)
        return {
            "dias_com_estoque": round(dias_com_estoque, 1),
            "dias_sem_estoque": round(dias_sem_estoque, 1),
            "teve_ruptura": dias_sem_estoque > 0 or estoque_atual <= 0,
            "ruptura_ativa": estoque_atual <= 0,
        }

    primeiro = movimentos[0][1]
    estoque_corrente = (
        _float_seguro_sugestao(primeiro.quantidade_anterior)
        if primeiro.quantidade_anterior is not None
        else _float_seguro_sugestao(estoque_atual)
    )
    cursor = data_inicio
    dias_com_estoque = 0.0

    for momento_mov, mov in movimentos:
        if not momento_mov:
            continue

        momento = min(max(momento_mov, data_inicio), data_fim)
        if momento > cursor:
            if estoque_corrente > 0:
                dias_com_estoque += (momento - cursor).total_seconds() / 86400
            cursor = momento

        if mov.quantidade_nova is not None:
            estoque_corrente = _float_seguro_sugestao(mov.quantidade_nova)
        else:
            quantidade = _float_seguro_sugestao(mov.quantidade)
            if mov.tipo == "entrada":
                estoque_corrente += quantidade
            elif mov.tipo == "saida":
                estoque_corrente -= quantidade

    if data_fim > cursor and estoque_corrente > 0:
        dias_com_estoque += (data_fim - cursor).total_seconds() / 86400

    dias_com_estoque = min(max(dias_com_estoque, 0.0), total_dias)
    dias_sem_estoque = max(0.0, total_dias - dias_com_estoque)

    return {
        "dias_com_estoque": round(dias_com_estoque, 1),
        "dias_sem_estoque": round(dias_sem_estoque, 1),
        "teve_ruptura": dias_sem_estoque >= 1 or estoque_atual <= 0,
        "ruptura_ativa": estoque_atual <= 0,
    }


def _gerar_observacao(
    prioridade: str,
    dias_estoque: float,
    tendencia: str,
    consumo_diario: float,
    estoque_atual: float = 0,
    teve_ruptura: bool = False,
    ruptura_ativa: bool = False,
    dias_sem_estoque: float = 0,
    consumo_ajustado: float = 0,
    consumo_observado: float = 0,
    ajuste_ruptura_aplicado: bool = False,
    motivo_ajuste_ruptura: Optional[str] = None,
) -> str:
    observacoes = []

    if ruptura_ativa:
        observacoes.append("Ruptura ativa: estoque zerado/negativo")
    elif prioridade == "CR\u00cdTICO":
        if dias_estoque < 3:
            observacoes.append("Urgente: estoque cobre menos de 3 dias")
        else:
            observacoes.append(f"Critico: estoque para {dias_estoque:.1f} dias")
    elif prioridade == "ALERTA":
        observacoes.append("Estoque abaixo do minimo configurado")

    if ajuste_ruptura_aplicado and teve_ruptura and dias_sem_estoque > 0:
        observacoes.append(
            f"Media ajustada por {dias_sem_estoque:.1f} dia(s) sem estoque"
        )
    elif teve_ruptura and motivo_ajuste_ruptura:
        observacoes.append(motivo_ajuste_ruptura)

    if (
        ajuste_ruptura_aplicado
        and consumo_ajustado > consumo_observado * 1.1
        and consumo_observado > 0
    ):
        observacoes.append("Demanda recalculada pelos dias em que havia estoque")

    if tendencia == "CRESCIMENTO":
        observacoes.append("Vendas em crescimento")
    elif tendencia == "QUEDA":
        observacoes.append("Vendas em queda")

    if consumo_diario == 0:
        observacoes.append("Sem vendas no periodo analisado")

    return " | ".join(observacoes) if observacoes else "Estoque adequado"
