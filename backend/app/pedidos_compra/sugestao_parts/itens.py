"""Montagem de itens da sugestao de compra."""

from math import ceil
from typing import Optional

from app.pedidos_compra.sugestao_parts.base import (
    _float_seguro_sugestao,
    _round_seguro_sugestao,
)
from app.pedidos_compra.quantidades import (
    UNIDADE_COMPRA_PADRAO,
    normalizar_quantidade_por_embalagem,
    normalizar_unidade_compra,
)


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


def _resolver_embalagem_sugestao(produto, embalagem_historica: Optional[dict] = None) -> dict:
    if embalagem_historica:
        unidade_historica = normalizar_unidade_compra(
            embalagem_historica.get("unidade_compra")
        )
        return {
            "unidade_compra": unidade_historica,
            "quantidade_por_embalagem": normalizar_quantidade_por_embalagem(
                unidade_historica,
                embalagem_historica.get("quantidade_por_embalagem"),
            ),
            "origem": "historico",
        }

    itens_por_caixa = normalizar_quantidade_por_embalagem(
        "CX", getattr(produto, "itens_por_caixa", None)
    )
    if itens_por_caixa and itens_por_caixa > 1:
        return {
            "unidade_compra": "CX",
            "quantidade_por_embalagem": itens_por_caixa,
            "origem": "cadastro_produto",
        }

    return {
        "unidade_compra": UNIDADE_COMPRA_PADRAO,
        "quantidade_por_embalagem": 1,
        "origem": "unitario",
    }


def _converter_quantidade_sugerida_por_embalagem(
    quantidade_sugerida: float,
    unidade_compra: str,
    quantidade_por_embalagem: Optional[float],
) -> dict:
    quantidade_base = max(0, _float_seguro_sugestao(quantidade_sugerida))
    quantidade_compra = ceil(quantidade_base)

    if unidade_compra == UNIDADE_COMPRA_PADRAO:
        return {
            "quantidade_compra": quantidade_compra,
            "quantidade_total_unidades": quantidade_compra,
        }

    if quantidade_por_embalagem and quantidade_por_embalagem > 1:
        quantidade_compra = ceil(quantidade_base / quantidade_por_embalagem)
        return {
            "quantidade_compra": quantidade_compra,
            "quantidade_total_unidades": quantidade_compra * quantidade_por_embalagem,
        }

    return {
        "quantidade_compra": quantidade_compra,
        "quantidade_total_unidades": None,
    }


def _montar_item_sugestao_compra(
    *,
    produto,
    produto_fornecedor,
    marca,
    fornecedor_grupo,
    fornecedores_por_id: dict,
    estoque_info: dict,
    vendas_stats: dict,
    vendas_janelas: dict,
    vendas_periodo: float,
    estoque_atual: float,
    estoque_minimo: float,
    dias_com_estoque: float,
    dias_sem_estoque: float,
    teve_ruptura: bool,
    ruptura_ativa: bool,
    lead_time: float,
    dias_cobertura: float,
    planejamento: dict,
    tendencia: str,
    preco_unitario: float,
    valor_sugestao: float,
    embalagem_historica: Optional[dict] = None,
) -> dict:
    vendas_janelas = vendas_janelas or {}
    vendas_stats = vendas_stats or {}
    estoque_info = estoque_info or {}

    prioridade = planejamento["prioridade"]
    consumo_diario = planejamento["consumo_diario"]
    consumo_observado = planejamento["consumo_observado"]
    consumo_ajustado = planejamento["consumo_ajustado"]
    consumo_base = planejamento["consumo_base"]
    dias_estoque = planejamento["dias_estoque"]
    ajuste_ruptura_aplicado = planejamento["ajuste_ruptura_aplicado"]
    motivo_ajuste_ruptura = planejamento["motivo_ajuste_ruptura"]
    quantidade_sugerida = _round_seguro_sugestao(planejamento["quantidade_sugerida"], 2)
    embalagem_sugestao = _resolver_embalagem_sugestao(produto, embalagem_historica)
    unidade_compra_sugerida = embalagem_sugestao["unidade_compra"]
    quantidade_por_embalagem_sugerida = embalagem_sugestao["quantidade_por_embalagem"]
    quantidade_convertida = _converter_quantidade_sugerida_por_embalagem(
        quantidade_sugerida,
        unidade_compra_sugerida,
        quantidade_por_embalagem_sugerida,
    )

    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "produto_sku": produto.codigo,
        "produto_codigo_barras": produto.codigo_barras,
        "fornecedor_id": produto_fornecedor.fornecedor_id,
        "fornecedor_nome": fornecedores_por_id.get(produto_fornecedor.fornecedor_id),
        "fornecedor_grupo_id": fornecedor_grupo.id if fornecedor_grupo else None,
        "fornecedor_grupo_nome": fornecedor_grupo.nome if fornecedor_grupo else None,
        "marca_id": produto.marca_id,
        "marca_nome": marca.nome if marca else None,
        "estoque_atual": _float_seguro_sugestao(estoque_atual),
        "estoque_minimo": _float_seguro_sugestao(estoque_minimo),
        "consumo_diario": _round_seguro_sugestao(consumo_diario, 2),
        "consumo_diario_observado": _round_seguro_sugestao(consumo_observado, 3),
        "consumo_diario_ajustado": _round_seguro_sugestao(consumo_ajustado, 3),
        "consumo_diario_base": _round_seguro_sugestao(consumo_base, 3),
        "vendas_periodo": _float_seguro_sugestao(vendas_periodo),
        "vendas_janelas": vendas_janelas,
        "vendas_7d": _float_seguro_sugestao(vendas_janelas.get("7")),
        "vendas_15d": _float_seguro_sugestao(vendas_janelas.get("15")),
        "vendas_30d": _float_seguro_sugestao(vendas_janelas.get("30")),
        "vendas_60d": _float_seguro_sugestao(vendas_janelas.get("60")),
        "vendas_90d": _float_seguro_sugestao(vendas_janelas.get("90")),
        "origens_venda": vendas_stats.get("origens") or [],
        "fontes_calculo": vendas_stats.get("fontes") or [],
        "granel_consumo": vendas_stats.get("granel_consumo") or {},
        "dias_estoque": _round_seguro_sugestao(dias_estoque, 1)
        if dias_estoque < 999
        else None,
        "dias_com_estoque": dias_com_estoque,
        "dias_sem_estoque": dias_sem_estoque,
        "teve_ruptura": teve_ruptura,
        "ruptura_ativa": ruptura_ativa,
        "ruptura_ajuste_aplicado": ajuste_ruptura_aplicado,
        "ruptura_ajuste_motivo": motivo_ajuste_ruptura,
        "lead_time": lead_time,
        "dias_planejamento": _float_seguro_sugestao(dias_cobertura),
        "dias_reposicao": _round_seguro_sugestao(planejamento["dias_reposicao"], 1),
        "margem_seguranca_dias": planejamento["margem_seguranca_dias"],
        "lead_time_incluido_no_alvo": planejamento["lead_time_incluido_no_alvo"],
        "dias_total_cobertura": planejamento["dias_total_cobertura"],
        "estoque_para_calculo": _round_seguro_sugestao(
            planejamento["estoque_para_calculo"], 3
        ),
        "quantidade_sugerida": quantidade_sugerida,
        "unidade_compra_sugerida": unidade_compra_sugerida,
        "quantidade_por_embalagem_sugerida": quantidade_por_embalagem_sugerida,
        "quantidade_compra_sugerida": quantidade_convertida["quantidade_compra"],
        "quantidade_total_unidades_sugerida": quantidade_convertida[
            "quantidade_total_unidades"
        ],
        "embalagem_sugestao_origem": embalagem_sugestao["origem"],
        "preco_unitario": _float_seguro_sugestao(preco_unitario),
        "valor_total": _round_seguro_sugestao(valor_sugestao, 2),
        "peso_bruto": _float_seguro_sugestao(
            produto.peso_embalagem or produto.peso_bruto or produto.peso_liquido
        ),
        "estoque_derivado": bool(estoque_info.get("estoque_derivado")),
        "tipo_produto": estoque_info.get("tipo_produto"),
        "tipo_kit": estoque_info.get("tipo_kit"),
        "prioridade": prioridade,
        "tendencia": tendencia,
        "observacao": _gerar_observacao(
            prioridade,
            dias_estoque,
            tendencia,
            consumo_diario,
            estoque_atual=estoque_atual,
            teve_ruptura=teve_ruptura,
            ruptura_ativa=ruptura_ativa,
            dias_sem_estoque=dias_sem_estoque,
            consumo_ajustado=consumo_ajustado,
            consumo_observado=consumo_observado,
            ajuste_ruptura_aplicado=ajuste_ruptura_aplicado,
            motivo_ajuste_ruptura=motivo_ajuste_ruptura,
        ),
    }


def _calcular_tendencia_vendas_sugestao(
    periodo_dias: int,
    consumo_observado: float,
    consumo_recente: float,
) -> str:
    if periodo_dias < 60 or consumo_observado <= 0:
        return "N/A"
    if consumo_recente > consumo_observado * 1.2:
        return "CRESCIMENTO"
    if consumo_recente < consumo_observado * 0.8:
        return "QUEDA"
    return "EST\u00c1VEL"
