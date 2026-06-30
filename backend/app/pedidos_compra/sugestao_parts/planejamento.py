"""Planejamento e resposta da sugestao de compra."""

from datetime import datetime

from app.pedidos_compra.sugestao_parts.base import (
    MARGEM_SEGURANCA_COMPRA_DIAS,
    MAX_MULTIPLICADOR_AJUSTE_RUPTURA,
    MIN_DIAS_COM_ESTOQUE_AJUSTE_RUPTURA,
    MIN_VENDAS_AJUSTE_RUPTURA,
    _datetime_naive_utc_sugestao,
    _float_seguro_sugestao,
    _round_seguro_sugestao,
    _sanitizar_json_sugestao,
)


def _selecionar_produtos_fornecedor_sugestao(
    produtos_fornecedor_raw,
    fornecedor_id: int,
) -> list:
    produtos_por_id = {}
    for produto, produto_fornecedor, marca in produtos_fornecedor_raw:
        score = (
            0 if produto_fornecedor.fornecedor_id == fornecedor_id else 1,
            0 if produto_fornecedor.e_principal else 1,
            0 if produto_fornecedor.fornecedor_id == produto.fornecedor_id else 1,
            _float_seguro_sugestao(produto_fornecedor.preco_custo, 999999999),
            produto_fornecedor.id,
        )
        atual = produtos_por_id.get(produto.id)
        if not atual or score < atual["score"]:
            produtos_por_id[produto.id] = {
                "score": score,
                "linha": (produto, produto_fornecedor, marca),
            }

    return [item["linha"] for item in produtos_por_id.values()]


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


def _calcular_planejamento_compra_sugestao(
    *,
    vendas_periodo: float,
    vendas_30: float,
    periodo_dias: int,
    estoque_atual: float,
    estoque_minimo: float,
    dias_com_estoque: float,
    dias_cobertura: float,
    lead_time: float,
    ruptura_ativa: bool,
    teve_ruptura: bool,
) -> dict:
    periodo_dias = max(1, int(periodo_dias or 0))
    vendas_periodo = _float_seguro_sugestao(vendas_periodo)
    vendas_30 = _float_seguro_sugestao(vendas_30)
    estoque_atual = _float_seguro_sugestao(estoque_atual)
    estoque_minimo = _float_seguro_sugestao(estoque_minimo)
    dias_com_estoque = _float_seguro_sugestao(dias_com_estoque)

    consumo_observado = vendas_periodo / periodo_dias if vendas_periodo > 0 else 0
    consumo_recente = vendas_30 / 30 if vendas_30 > 0 else 0
    consumo_base = max(consumo_observado, consumo_recente)
    consumo_ajustado = consumo_observado
    ajuste_ruptura_aplicado = False
    motivo_ajuste_ruptura = None

    pode_ajustar_por_ruptura = (
        teve_ruptura
        and dias_com_estoque >= 1
        and dias_com_estoque < periodo_dias * 0.95
    )
    if pode_ajustar_por_ruptura and vendas_periodo > 0:
        if vendas_periodo < MIN_VENDAS_AJUSTE_RUPTURA:
            motivo_ajuste_ruptura = (
                "Ruptura detectada, mas sem ajuste: apenas "
                f"{vendas_periodo:g} venda(s) no periodo."
            )
        elif dias_com_estoque < MIN_DIAS_COM_ESTOQUE_AJUSTE_RUPTURA:
            motivo_ajuste_ruptura = (
                "Ruptura detectada, mas sem ajuste: somente "
                f"{dias_com_estoque:.1f} dia(s) com estoque."
            )
        else:
            consumo_ajustado_bruto = vendas_periodo / max(dias_com_estoque, 1.0)
            limite_ajuste = (
                consumo_base * MAX_MULTIPLICADOR_AJUSTE_RUPTURA
                if consumo_base > 0
                else consumo_ajustado_bruto
            )
            consumo_ajustado = min(consumo_ajustado_bruto, limite_ajuste)
            ajuste_ruptura_aplicado = consumo_ajustado > consumo_base * 1.05
            if consumo_ajustado_bruto > consumo_ajustado:
                motivo_ajuste_ruptura = (
                    "Media ajustada por ruptura, limitada a "
                    f"{MAX_MULTIPLICADOR_AJUSTE_RUPTURA:g}x o giro observado."
                )
            else:
                motivo_ajuste_ruptura = (
                    "Media ajustada pelos dias em que havia estoque."
                )
    elif teve_ruptura and vendas_periodo <= 0:
        motivo_ajuste_ruptura = (
            "Ruptura detectada, mas sem vendas no periodo para projetar demanda."
        )

    consumo_diario = max(consumo_base, consumo_ajustado)
    estoque_para_calculo = max(0.0, estoque_atual)
    dias_estoque = (
        estoque_para_calculo / consumo_diario
        if consumo_diario > 0 and estoque_para_calculo > 0
        else (0 if consumo_diario > 0 and estoque_atual <= 0 else 999)
    )

    margem_seguranca_dias = MARGEM_SEGURANCA_COMPRA_DIAS
    dias_reposicao = _float_seguro_sugestao(lead_time) + _float_seguro_sugestao(
        margem_seguranca_dias
    )
    lead_time_incluido_no_alvo = bool(
        ruptura_ativa
        or estoque_atual <= estoque_minimo
        or dias_estoque < dias_reposicao
    )
    dias_total_cobertura = _float_seguro_sugestao(dias_cobertura) + (
        dias_reposicao if lead_time_incluido_no_alvo else 0.0
    )
    quantidade_ideal = consumo_diario * dias_total_cobertura
    quantidade_sugerida = max(0, quantidade_ideal - estoque_para_calculo)

    if estoque_atual <= 0 and (vendas_periodo > 0 or estoque_minimo > 0):
        prioridade = "CR\u00cdTICO"
    elif dias_estoque < 7:
        prioridade = "CR\u00cdTICO"
    elif estoque_atual <= estoque_minimo:
        prioridade = "ALERTA"
    elif dias_estoque < dias_reposicao:
        prioridade = "ATEN\u00c7\u00c3O"
    else:
        prioridade = "NORMAL"

    return {
        "consumo_observado": consumo_observado,
        "consumo_recente": consumo_recente,
        "consumo_base": consumo_base,
        "consumo_ajustado": consumo_ajustado,
        "ajuste_ruptura_aplicado": ajuste_ruptura_aplicado,
        "motivo_ajuste_ruptura": motivo_ajuste_ruptura,
        "consumo_diario": consumo_diario,
        "estoque_para_calculo": estoque_para_calculo,
        "dias_estoque": dias_estoque,
        "margem_seguranca_dias": margem_seguranca_dias,
        "dias_reposicao": dias_reposicao,
        "lead_time_incluido_no_alvo": lead_time_incluido_no_alvo,
        "dias_total_cobertura": dias_total_cobertura,
        "quantidade_ideal": quantidade_ideal,
        "quantidade_sugerida": quantidade_sugerida,
        "prioridade": prioridade,
    }


def _montar_resposta_sugestao_compra(
    *,
    fornecedor,
    fornecedor_ids: list[int],
    fornecedor_grupo,
    periodo_dias: int,
    dias_cobertura: int,
    apenas_fornecedor_principal: bool,
    data_inicio: datetime,
    data_fim: datetime,
    sugestoes: list[dict],
    total_criticos: int,
    total_alerta: int,
    valor_total: float,
) -> dict:
    ordem_prioridade = {
        "CR\u00cdTICO": 0,
        "ALERTA": 1,
        "ATEN\u00c7\u00c3O": 2,
        "NORMAL": 3,
    }
    sugestoes.sort(
        key=lambda item: (
            ordem_prioridade.get(item["prioridade"], 4),
            -float(item.get("valor_total") or 0),
        )
    )

    return _sanitizar_json_sugestao(
        {
            "fornecedor": {
                "id": fornecedor.id,
                "nome": fornecedor.nome,
                "ids_considerados": fornecedor_ids,
                "grupo": {
                    "id": fornecedor_grupo.id,
                    "nome": fornecedor_grupo.nome,
                }
                if fornecedor_grupo
                else None,
            },
            "periodo_dias": periodo_dias,
            "dias_cobertura": dias_cobertura,
            "apenas_fornecedor_principal": apenas_fornecedor_principal,
            "data_analise_inicio": data_inicio.isoformat(),
            "data_analise_fim": data_fim.isoformat(),
            "sugestoes": sugestoes,
            "resumo": {
                "total_produtos": len(sugestoes),
                "produtos_criticos": total_criticos,
                "produtos_alerta": total_alerta,
                "produtos_atencao": len(
                    [s for s in sugestoes if s["prioridade"] == "ATEN\u00c7\u00c3O"]
                ),
                "valor_total_estimado": _round_seguro_sugestao(valor_total, 2),
            },
        }
    )
