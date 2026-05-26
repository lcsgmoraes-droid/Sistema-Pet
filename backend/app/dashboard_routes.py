"""
Rotas para Dashboard Financeiro
Endpoints para dados consolidados do sistema
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import Float, cast, func, and_, or_
from datetime import datetime, date, time, timedelta
from typing import Optional
import logging
import math
import calendar
import re
import unicodedata

from uuid import UUID
from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User, Cliente
from app.tenancy.context import get_current_tenant
from .vendas_models import Venda, VendaPagamento, VendaItem
from .financeiro_models import ContaReceber, ContaPagar, CategoriaFinanceira, TipoDespesa
from .caixa_models import Caixa
from .produtos_models import Produto
from .cargo_models import Cargo
from .dre_plano_contas_models import DRESubcategoria
from .ia.aba7_dre_detalhada_models import DREDetalheCanal
from .services.remuneracao_service import calcular_composicao_remuneracao
from .services.venda_rentabilidade_snapshot_service import build_venda_rentabilidade_snapshot
from .dre_canais_routes import (
    _bulk_cashback_por_venda,
    _bulk_comissoes_por_venda,
    _bulk_cupons_por_venda,
    _bulk_estoque_custos_por_venda,
    _bulk_taxa_operacional_por_venda,
    _formas_pagamento_map,
    _impostos_percentual,
    _snapshot_pronto,
)
from .utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)

router = APIRouter()


def _dashboard_fetchone(db: Session, sql: str, tenant_id, params=None):
    return execute_tenant_safe(db, sql, params or {}, tenant_id=tenant_id).fetchone()


def _round_money(value) -> float:
    return round(float(value or 0), 2)


def _filtro_status_venda_relatorio():
    return or_(Venda.status.is_(None), Venda.status != "cancelada")


MARGEM_PONTO_EQUILIBRIO_PADRAO = "media_12_meses_fechados"
MARGEM_PONTO_EQUILIBRIO_OPCOES = {
    "periodo_atual": {"label": "Periodo atual", "meses_fechados": 0},
    "mes_anterior_fechado": {"label": "Mes anterior fechado", "meses_fechados": 1},
    "media_3_meses_fechados": {"label": "Media 3 meses fechados", "meses_fechados": 3},
    "media_6_meses_fechados": {"label": "Media 6 meses fechados", "meses_fechados": 6},
    "media_12_meses_fechados": {"label": "Media 12 meses fechados", "meses_fechados": 12},
}

MODO_CUSTO_FISCAL_PE_PADRAO = "gerencial_completo"
MODO_CUSTO_FISCAL_PE_OPCOES = {
    "gerencial_completo": {
        "label": "Visao gerencial completa",
        "descricao": "Considera o custo fiscal estimado em todas as vendas para uma leitura conservadora.",
    },
    "documentos_emitidos": {
        "label": "Somente documentos emitidos",
        "descricao": "Aplica o custo fiscal apenas nas vendas com NF/NFC-e emitida.",
    },
}


def _conta_eh_compra_estoque_para_pe(conta: ContaPagar, tipo_nome: str = "", categoria_nome: str = "") -> bool:
    texto = f"{tipo_nome or ''} {categoria_nome or ''} {conta.descricao or ''}".lower()
    return bool(conta.nota_entrada_id) or (
        "produto" in texto and "revenda" in texto
    )


def _normalizar_texto_pe(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.replace("-", " ")
    return re.sub(r"\s+", " ", texto).strip()


def _venda_tem_documento_fiscal_pe(venda: Venda) -> bool:
    nfe_status = _normalizar_texto_pe(getattr(venda, "nfe_status", None))
    if nfe_status in {"cancelada", "cancelado", "denegada", "rejeitada"}:
        return False

    return bool(
        getattr(venda, "nfe_bling_id", None)
        or getattr(venda, "nfe_chave", None)
        or getattr(venda, "nfe_numero", None)
        or _normalizar_texto_pe(getattr(venda, "status", None)) == "pago_nf"
    )


def _snapshot_float(snapshot: dict, campo: str) -> float:
    return _round_money(float((snapshot or {}).get(campo, 0) or 0))


def _detalhe_venda_margem_pe(
    snapshot: dict,
    *,
    campo: str,
    valor: float,
    nf_emitida: bool,
    observacao: str = "",
) -> dict:
    return {
        "id": snapshot.get("venda_id"),
        "venda_id": snapshot.get("venda_id"),
        "numero_venda": snapshot.get("numero_venda"),
        "descricao": f"Venda {snapshot.get('numero_venda') or snapshot.get('venda_id') or ''}".strip(),
        "cliente_nome": snapshot.get("cliente_nome") or "Sem cliente",
        "data_venda": snapshot.get("data_venda"),
        "valor": _round_money(valor),
        "campo": campo,
        "nf_emitida": bool(nf_emitida),
        "observacao": observacao,
    }


def _ajustar_snapshot_custo_fiscal_pe(
    snapshot: dict,
    *,
    venda_tem_documento: bool,
    modo_custo_fiscal: str,
) -> dict:
    ajustado = dict(snapshot or {})
    imposto_original = _snapshot_float(ajustado, "imposto")
    ajustado["custo_fiscal_original"] = imposto_original
    ajustado["custo_fiscal_desconsiderado"] = 0.0

    if modo_custo_fiscal == "documentos_emitidos" and not venda_tem_documento and imposto_original > 0:
        ajustado["imposto"] = 0.0
        ajustado["custo_fiscal_desconsiderado"] = imposto_original
        ajustado["venda_liquida"] = _round_money(_snapshot_float(ajustado, "venda_liquida") + imposto_original)
        ajustado["lucro"] = _round_money(_snapshot_float(ajustado, "lucro") + imposto_original)

    return ajustado


def _conta_variavel_ja_coberta_pelo_snapshot_pe(
    conta: ContaPagar,
    tipo_nome: str = "",
    categoria_nome: str = "",
    dre_subcategoria_nome: str = "",
) -> bool:
    texto = _normalizar_texto_pe(
        f"{getattr(conta, 'descricao', '') or ''} {tipo_nome or ''} {categoria_nome or ''} {dre_subcategoria_nome or ''}"
    )
    termos_custos_venda = (
        "taxa credito",
        "taxa debito",
        "taxa cartao",
        "taxas cartao",
        "taxa pix",
        "pix boleto",
        "comissao venda",
        "comissoes venda",
        "comissao de venda",
        "comissoes de venda",
        "comissao entregador",
        "taxa de entrega",
        "frete operacional",
        "fretes sobre vendas",
        "custo operacional entrega",
        "campanha",
        "cashback",
        "cupom",
    )
    if any(termo in texto for termo in termos_custos_venda):
        return True

    return "venda" in texto and any(
        termo in texto
        for termo in (
            "cartao",
            "credito",
            "debito",
            "comissao",
            "entrega",
            "operacional",
            "desconto",
        )
    )


def _somar_componentes_margem_vendas_pe(
    vendas_snapshot: list[dict],
    *,
    outros_variaveis: float = 0.0,
    detalhes_outros_variaveis: Optional[list[dict]] = None,
    incluir_detalhes: bool = True,
) -> dict:
    campos = {
        "receita_produtos_servicos": 0.0,
        "receita_entrega": 0.0,
        "descontos": 0.0,
        "beneficios_campanhas": 0.0,
        "taxas_cartao": 0.0,
        "repasse_entrega": 0.0,
        "custo_operacional_entrega": 0.0,
        "comissoes": 0.0,
        "custo_fiscal": 0.0,
        "cmv_estimado": 0.0,
    }
    componentes = {campo: [] for campo in campos}
    componentes["outros_variaveis"] = list(detalhes_outros_variaveis or []) if incluir_detalhes else []

    for venda_info in vendas_snapshot or []:
        snapshot = dict(venda_info.get("snapshot") or venda_info)
        nf_emitida = bool(venda_info.get("nf_emitida", False))
        mapa = {
            "receita_produtos_servicos": ("venda_bruta", ""),
            "receita_entrega": ("taxa_loja", ""),
            "descontos": ("desconto", ""),
            "beneficios_campanhas": ("custo_campanha", ""),
            "taxas_cartao": ("taxa_cartao", ""),
            "repasse_entrega": ("taxa_entrega", ""),
            "custo_operacional_entrega": ("taxa_operacional", ""),
            "comissoes": ("comissao", ""),
            "custo_fiscal": (
                "imposto",
                "Custo fiscal estimado desconsiderado nesta visao"
                if _snapshot_float(snapshot, "custo_fiscal_desconsiderado") > 0
                else "",
            ),
            "cmv_estimado": ("custo_produtos", ""),
        }
        for campo_total, (campo_snapshot, observacao) in mapa.items():
            valor = _snapshot_float(snapshot, campo_snapshot)
            campos[campo_total] = _round_money(campos[campo_total] + valor)
            custo_fiscal_omitido = campo_total == "custo_fiscal" and _snapshot_float(snapshot, "custo_fiscal_desconsiderado") > 0
            if incluir_detalhes and (valor > 0 or custo_fiscal_omitido):
                componentes[campo_total].append(
                    _detalhe_venda_margem_pe(
                        snapshot,
                        campo=campo_total,
                        valor=valor,
                        nf_emitida=nf_emitida,
                        observacao=observacao,
                    )
                )

    receita_produtos_servicos = _round_money(campos["receita_produtos_servicos"])
    receita_entrega = _round_money(campos["receita_entrega"])
    faturamento = _round_money(receita_produtos_servicos + receita_entrega)
    outros_variaveis = _round_money(outros_variaveis)
    despesas_variaveis = _round_money(
        campos["descontos"]
        + campos["beneficios_campanhas"]
        + campos["taxas_cartao"]
        + campos["repasse_entrega"]
        + campos["custo_operacional_entrega"]
        + campos["comissoes"]
        + campos["custo_fiscal"]
        + outros_variaveis
    )
    cmv_estimado = _round_money(campos["cmv_estimado"])
    custos_variaveis = _round_money(cmv_estimado + despesas_variaveis)
    margem_contribuicao = _round_money(faturamento - custos_variaveis)
    margem_decimal = margem_contribuicao / faturamento if faturamento > 0 else 0

    subtotais = [
        {"id": "receita_produtos_servicos", "label": "Receita de produtos/servicos", "tipo": "receita", "valor": receita_produtos_servicos},
        {"id": "receita_entrega", "label": "Receita de entrega", "tipo": "receita", "valor": receita_entrega},
        {"id": "descontos", "label": "Descontos comerciais", "tipo": "deducao", "valor": _round_money(campos["descontos"])},
        {"id": "beneficios_campanhas", "label": "Campanhas, cupons e cashback", "tipo": "deducao", "valor": _round_money(campos["beneficios_campanhas"])},
        {"id": "taxas_cartao", "label": "Taxas de cartao/meios de pagamento", "tipo": "deducao", "valor": _round_money(campos["taxas_cartao"])},
        {"id": "repasse_entrega", "label": "Repasse/custo de entrega", "tipo": "deducao", "valor": _round_money(campos["repasse_entrega"])},
        {"id": "custo_operacional_entrega", "label": "Custo operacional de entrega", "tipo": "deducao", "valor": _round_money(campos["custo_operacional_entrega"])},
        {"id": "comissoes", "label": "Comissoes de venda", "tipo": "deducao", "valor": _round_money(campos["comissoes"])},
        {"id": "custo_fiscal", "label": "Custo fiscal gerencial", "tipo": "deducao", "valor": _round_money(campos["custo_fiscal"])},
        {"id": "cmv_estimado", "label": "CMV", "tipo": "custo", "valor": cmv_estimado},
        {"id": "outros_variaveis", "label": "Outros custos variaveis", "tipo": "deducao", "valor": outros_variaveis},
    ]

    return {
        "faturamento": faturamento,
        "receita_produtos_servicos": receita_produtos_servicos,
        "receita_entrega": receita_entrega,
        "descontos": _round_money(campos["descontos"]),
        "beneficios_campanhas": _round_money(campos["beneficios_campanhas"]),
        "taxas_cartao": _round_money(campos["taxas_cartao"]),
        "repasse_entrega": _round_money(campos["repasse_entrega"]),
        "custo_operacional_entrega": _round_money(campos["custo_operacional_entrega"]),
        "comissoes": _round_money(campos["comissoes"]),
        "custo_fiscal": _round_money(campos["custo_fiscal"]),
        "cmv_estimado": cmv_estimado,
        "outros_variaveis": outros_variaveis,
        "despesas_variaveis": despesas_variaveis,
        "custos_variaveis": custos_variaveis,
        "margem_contribuicao": margem_contribuicao,
        "margem_contribuicao_percentual": round(margem_decimal * 100, 2),
        "margem_decimal": margem_decimal,
        "detalhes_margem": {
            "subtotais": subtotais,
            "componentes": componentes,
        },
    }


PE_TERMOS_FIXOS = (
    "pro labore",
    "prolabore",
    "salario",
    "salarios",
    "folha",
    "funcionario",
    "funcionarios",
    "encargo",
    "fgts",
    "inss",
    "ferias",
    "decimo",
    "13o salario",
    "13 salario",
    "vale transporte",
    "aluguel",
    "condominio",
    "iptu",
    "agua",
    "energia",
    "eletrica",
    "luz",
    "internet",
    "telefone",
    "celular",
    "escritorio",
    "contabilidade",
    "honorario",
    "software",
    "sistema",
    "erp",
    "licenca",
    "plano odontologico",
    "seguro",
    "limpeza",
    "material de uso interno",
)

PE_TERMOS_VARIAVEIS = (
    "taxa credito",
    "taxa debito",
    "taxa cartao",
    "cartao de credito",
    "cartao de debito",
    "tarifa envio",
    "frete",
    "entrega",
    "envio",
    "comissao",
    "marketplace",
    "abastecimento moto",
    "combustivel",
    "motoboy",
    "pagarme",
    "mercado livre",
    "shopee",
    "amazon",
)

PE_TERMOS_FOLHA = (
    "salario",
    "salarios",
    "folha",
    "funcionario",
    "funcionarios",
    "encargo",
    "fgts",
    "inss",
    "ferias",
    "decimo",
    "13o salario",
    "13 salario",
)


def _classificar_texto_ponto_equilibrio(texto: str) -> Optional[str]:
    texto_normalizado = _normalizar_texto_pe(texto)
    if not texto_normalizado:
        return None
    if any(termo in texto_normalizado for termo in PE_TERMOS_FIXOS):
        return "fixo"
    if any(termo in texto_normalizado for termo in PE_TERMOS_VARIAVEIS):
        return "variavel"
    return None


def _normalizar_tipo_custo_dre(valor) -> str:
    if valor is None:
        return ""
    tipo = getattr(valor, "value", valor)
    return _normalizar_texto_pe(str(tipo).split(".")[-1])


def _classificar_conta_ponto_equilibrio(
    conta: ContaPagar,
    *,
    tipo_e_custo_fixo=None,
    tipo_despesa_nome: Optional[str] = None,
    categoria_tipo_custo: Optional[str] = None,
    categoria_nome: Optional[str] = None,
    dre_custo_pe: Optional[str] = None,
    dre_subcategoria_nome: Optional[str] = None,
    dre_tipo_custo=None,
) -> tuple[Optional[str], str]:
    dre_custo_pe_normalizado = _normalizar_texto_pe(dre_custo_pe)
    if dre_custo_pe_normalizado in {"fixo", "variavel"}:
        return dre_custo_pe_normalizado, f"PE na subcategoria DRE: {dre_subcategoria_nome or '-'}"

    if tipo_e_custo_fixo is not None:
        classificacao = "fixo" if bool(tipo_e_custo_fixo) else "variavel"
        return classificacao, f"Tipo de despesa: {tipo_despesa_nome or '-'}"

    categoria_tipo_normalizado = _normalizar_texto_pe(categoria_tipo_custo)
    if categoria_tipo_normalizado in {"fixo", "variavel"}:
        return categoria_tipo_normalizado, f"Categoria financeira: {categoria_nome or '-'}"

    texto_lancamento = " ".join(
        str(parte or "")
        for parte in (conta.descricao, tipo_despesa_nome, categoria_nome)
    )
    classificacao_por_lancamento = _classificar_texto_ponto_equilibrio(texto_lancamento)
    if classificacao_por_lancamento:
        return classificacao_por_lancamento, "Classificacao automatica pelo lancamento"

    dre_tipo_normalizado = _normalizar_tipo_custo_dre(dre_tipo_custo)
    if dre_tipo_normalizado in {"corporativo", "indireto_rateavel", "indireto rateavel"}:
        return "fixo", f"Tipo DRE: {dre_subcategoria_nome or '-'}"
    if dre_tipo_normalizado == "direto":
        return "variavel", f"Tipo DRE: {dre_subcategoria_nome or '-'}"

    classificacao_por_dre = _classificar_texto_ponto_equilibrio(dre_subcategoria_nome or "")
    if classificacao_por_dre:
        return classificacao_por_dre, f"Subcategoria DRE: {dre_subcategoria_nome or '-'}"

    return None, "Sem classificacao"


def _conta_eh_folha_para_pe(
    conta: ContaPagar,
    tipo_despesa_nome: Optional[str],
    categoria_nome: Optional[str],
    dre_subcategoria_nome: Optional[str],
) -> bool:
    texto = _normalizar_texto_pe(
        " ".join(
            str(parte or "")
            for parte in (conta.descricao, tipo_despesa_nome, categoria_nome, dre_subcategoria_nome)
        )
    )
    return any(termo in texto for termo in PE_TERMOS_FOLHA)


def _calcular_complemento_folha_gerencial(
    *,
    total_estimado,
    total_lancado,
    total_provisoes_dre,
) -> float:
    complemento = float(total_estimado or 0) - float(total_lancado or 0) - float(total_provisoes_dre or 0)
    return _round_money(max(0, complemento))


def _calcular_folha_gerencial_estimada(db: Session, tenant_id) -> dict:
    funcionarios = (
        db.query(Cliente, Cargo)
        .join(Cargo, Cliente.cargo_id == Cargo.id)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
            Cliente.ativo.is_(True),
            Cliente.cargo_id.isnot(None),
            Cargo.tenant_id == tenant_id,
            Cargo.ativo.is_(True),
        )
        .all()
    )

    total = 0.0
    quantidade = 0
    for funcionario, cargo in funcionarios:
        composicao = calcular_composicao_remuneracao(cargo, funcionario)
        total += float(composicao.get("custo_total_empresa") or 0)
        quantidade += 1

    return {
        "total": _round_money(total),
        "quantidade_funcionarios": quantidade,
    }


def _detalhe_sintetico_pe(
    *,
    item_id,
    descricao: str,
    valor: float,
    data_vencimento: date,
    classificacao: str,
    origem_classificacao: str,
) -> dict:
    return {
        "id": item_id,
        "descricao": descricao,
        "valor": _round_money(valor),
        "data_vencimento": data_vencimento,
        "fornecedor_nome": None,
        "canal": None,
        "classificacao": classificacao,
        "origem_classificacao": origem_classificacao,
        "tipo_despesa_nome": None,
        "categoria_nome": None,
        "dre_subcategoria_nome": None,
        "nota_entrada_id": None,
    }


def _detalhe_conta_pe(
    conta: ContaPagar,
    *,
    valor: float,
    classificacao: str,
    origem_classificacao: str,
    fornecedor_nome: Optional[str],
    tipo_despesa_nome: Optional[str],
    categoria_nome: Optional[str],
    dre_subcategoria_nome: Optional[str],
) -> dict:
    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "valor": _round_money(valor),
        "data_vencimento": conta.data_vencimento,
        "fornecedor_nome": fornecedor_nome,
        "canal": conta.canal,
        "classificacao": classificacao,
        "origem_classificacao": origem_classificacao,
        "tipo_despesa_nome": tipo_despesa_nome,
        "categoria_nome": categoria_nome,
        "dre_subcategoria_nome": dre_subcategoria_nome,
        "nota_entrada_id": conta.nota_entrada_id,
    }


PONTO_EQUILIBRIO_GRUPOS_CLASSIFICACAO = {
    "fixas": {
        "label": "Despesas fixas",
        "origem": "Contas a pagar, provisoes da DRE e complemento gerencial de folha.",
    },
    "variaveis": {
        "label": "Outros custos variaveis",
        "origem": "Contas a pagar e provisoes variaveis que nao nasceram do snapshot da venda.",
    },
    "custos_venda_snapshot": {
        "label": "Custos de venda ja no snapshot",
        "origem": "Contas a pagar que foram separadas para evitar duplicidade com custos gerados pela venda.",
    },
    "sem_classificacao": {
        "label": "Sem classificacao",
        "origem": "Contas a pagar ainda sem regra suficiente para entrar no ponto de equilibrio.",
    },
    "estoque_excluido": {
        "label": "Fora do PE: compras de estoque",
        "origem": "Compras de produto para revenda ficam fora do PE porque entram no resultado pelo CMV quando vendidas.",
    },
}


def _paginar_detalhes_ponto_equilibrio(items: list[dict], *, page: int = 1, page_size: int = 30) -> dict:
    page_size = max(1, min(int(page_size or 30), 100))
    total_itens = len(items or [])
    pages = max(1, math.ceil(total_itens / page_size))
    page = max(1, min(int(page or 1), pages))
    inicio = (page - 1) * page_size
    fim = inicio + page_size

    return {
        "items": list(items or [])[inicio:fim],
        "total_itens": total_itens,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


def _normalizar_item_detalhe_ponto_equilibrio(item: dict, origem_label: str) -> dict:
    data = item.get("data_venda") or item.get("data_vencimento")
    descricao = item.get("descricao") or item.get("numero_venda") or item.get("id") or "-"
    contraparte = item.get("cliente_nome") or item.get("fornecedor_nome") or item.get("canal")
    return {
        **item,
        "data": data,
        "descricao": descricao,
        "contraparte": contraparte,
        "origem_label": origem_label,
    }


def _formatar_data_br_ponto_equilibrio(valor) -> str:
    if isinstance(valor, datetime):
        valor = valor.date()
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor or "-")


def _adicionar_meses(data_base: date, meses: int) -> date:
    indice_mes = data_base.year * 12 + data_base.month - 1 + meses
    ano = indice_mes // 12
    mes = indice_mes % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def _periodo_meses_fechados_para_margem(data_referencia: date, meses: int) -> tuple[date, date]:
    inicio_mes_referencia = data_referencia.replace(day=1)
    fim = inicio_mes_referencia - timedelta(days=1)
    inicio = _adicionar_meses(fim.replace(day=1), -(meses - 1))
    return inicio, fim


def _calcular_despesas_variaveis_margem_pe(
    db: Session,
    tenant_id,
    inicio: date,
    fim: date,
    canais_lista: list[str],
) -> float:
    contas_query = db.query(
        ContaPagar,
        TipoDespesa.e_custo_fixo.label("tipo_e_custo_fixo"),
        TipoDespesa.nome.label("tipo_despesa_nome"),
        CategoriaFinanceira.tipo_custo.label("categoria_tipo_custo"),
        CategoriaFinanceira.nome.label("categoria_nome"),
        DRESubcategoria.custo_pe.label("dre_custo_pe"),
        DRESubcategoria.tipo_custo.label("dre_tipo_custo"),
        DRESubcategoria.nome.label("dre_subcategoria_nome"),
    ).outerjoin(
        TipoDespesa,
        ContaPagar.tipo_despesa_id == TipoDespesa.id,
    ).outerjoin(
        CategoriaFinanceira,
        ContaPagar.categoria_id == CategoriaFinanceira.id,
    ).outerjoin(
        DRESubcategoria,
        ContaPagar.dre_subcategoria_id == DRESubcategoria.id,
    ).filter(
        ContaPagar.tenant_id == tenant_id,
        ContaPagar.data_vencimento >= inicio,
        ContaPagar.data_vencimento <= fim,
        ContaPagar.status != "cancelado",
    )
    if canais_lista:
        contas_query = contas_query.filter(
            or_(ContaPagar.canal.in_(canais_lista), ContaPagar.canal.is_(None))
        )

    despesas_variaveis = 0.0
    for (
        conta,
        tipo_e_custo_fixo,
        tipo_despesa_nome,
        categoria_tipo_custo,
        categoria_nome,
        dre_custo_pe,
        dre_tipo_custo,
        dre_subcategoria_nome,
    ) in contas_query.all():
        if _conta_eh_compra_estoque_para_pe(conta, tipo_despesa_nome, categoria_nome):
            continue
        if _conta_variavel_ja_coberta_pelo_snapshot_pe(
            conta,
            tipo_despesa_nome,
            categoria_nome,
            dre_subcategoria_nome,
        ):
            continue

        classificacao, _ = _classificar_conta_ponto_equilibrio(
            conta,
            tipo_e_custo_fixo=tipo_e_custo_fixo,
            tipo_despesa_nome=tipo_despesa_nome,
            categoria_tipo_custo=categoria_tipo_custo,
            categoria_nome=categoria_nome,
            dre_custo_pe=dre_custo_pe,
            dre_subcategoria_nome=dre_subcategoria_nome,
            dre_tipo_custo=dre_tipo_custo,
        )
        if classificacao == "variavel":
            despesas_variaveis += float(conta.valor_final or conta.valor_original or 0)

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
            or_(DREDetalheCanal.canal.in_(canais_lista), DREDetalheCanal.canal == "provisao")
        )

    for provisao in provisoes_dre_query.all():
        despesas_variaveis += float(provisao.despesas_vendas or 0)

    return _round_money(despesas_variaveis)


def _preparar_snapshots_margem_vendas_pe(
    db: Session,
    tenant_id,
    vendas: list[Venda],
    modo_custo_fiscal: str,
) -> list[dict]:
    venda_ids = [venda.id for venda in vendas if getattr(venda, "id", None)]
    formas_pagamento = _formas_pagamento_map(db, tenant_id)
    impostos_percentual = _impostos_percentual(db, tenant_id)
    comissoes_por_venda = _bulk_comissoes_por_venda(db, tenant_id, venda_ids)
    cupons_por_venda = _bulk_cupons_por_venda(db, tenant_id, vendas)
    cashback_por_venda = _bulk_cashback_por_venda(db, tenant_id, venda_ids)
    taxa_operacional_por_venda = _bulk_taxa_operacional_por_venda(db, tenant_id, vendas)
    estoque_custos_por_venda = _bulk_estoque_custos_por_venda(db, tenant_id, venda_ids)

    vendas_snapshot = []
    for venda in vendas:
        venda_id = getattr(venda, "id", None)
        nf_emitida = _venda_tem_documento_fiscal_pe(venda)
        cupom_desconto = cupons_por_venda.get(venda_id, 0.0)
        custo_campanha = cupom_desconto + cashback_por_venda.get(venda_id, 0.0)

        snapshot = _snapshot_pronto(venda)
        if snapshot and custo_campanha > 0 and _snapshot_float(snapshot, "custo_campanha") <= 0:
            snapshot = None

        if snapshot is None:
            snapshot = build_venda_rentabilidade_snapshot(
                venda,
                db,
                tenant_id,
                impostos_percentual=impostos_percentual,
                formas_pagamento_map=formas_pagamento,
                custo_campanha=custo_campanha,
                cupom_desconto=cupom_desconto,
                comissao_total=comissoes_por_venda.get(venda_id, 0.0),
                taxa_operacional_entrega=taxa_operacional_por_venda.get(venda_id, 0.0),
                estoque_custos_por_produto=estoque_custos_por_venda.get(venda_id, {}),
            )

        snapshot = _ajustar_snapshot_custo_fiscal_pe(
            snapshot,
            venda_tem_documento=nf_emitida,
            modo_custo_fiscal=modo_custo_fiscal,
        )
        vendas_snapshot.append({"snapshot": snapshot, "nf_emitida": nf_emitida})

    return vendas_snapshot


def _calcular_margem_periodo_ponto_equilibrio(
    db: Session,
    tenant_id,
    inicio: date,
    fim: date,
    canais_lista: list[str],
    modo_custo_fiscal: str = MODO_CUSTO_FISCAL_PE_PADRAO,
    outros_variaveis: Optional[float] = None,
    detalhes_outros_variaveis: Optional[list[dict]] = None,
    incluir_detalhes: bool = True,
) -> dict:
    inicio_dt = datetime.combine(inicio, time.min)
    fim_dt = datetime.combine(fim, time.max)

    vendas_query = (
        db.query(Venda)
        .options(
            selectinload(Venda.cliente),
            selectinload(Venda.itens).selectinload(VendaItem.produto),
            selectinload(Venda.pagamentos),
        )
        .filter(
            Venda.tenant_id == tenant_id,
            _filtro_status_venda_relatorio(),
            Venda.data_venda >= inicio_dt,
            Venda.data_venda <= fim_dt,
        )
    )
    if canais_lista:
        vendas_query = vendas_query.filter(Venda.canal.in_(canais_lista))

    vendas = vendas_query.all()
    vendas_snapshot = _preparar_snapshots_margem_vendas_pe(
        db,
        tenant_id,
        vendas,
        modo_custo_fiscal,
    )

    if outros_variaveis is None:
        outros_variaveis = _calcular_despesas_variaveis_margem_pe(
            db,
            tenant_id,
            inicio,
            fim,
            canais_lista,
        )

    resultado = _somar_componentes_margem_vendas_pe(
        vendas_snapshot,
        outros_variaveis=outros_variaveis,
        detalhes_outros_variaveis=detalhes_outros_variaveis,
        incluir_detalhes=incluir_detalhes,
    )
    quantidade_vendas = len(vendas)
    ticket_medio = _round_money(resultado["faturamento"] / quantidade_vendas) if quantidade_vendas else 0

    return {
        **resultado,
        "inicio": inicio,
        "fim": fim,
        "quantidade_vendas": quantidade_vendas,
        "ticket_medio": ticket_medio,
    }


def _calcular_margem_referencia_ponto_equilibrio(
    db: Session,
    tenant_id,
    inicio: date,
    fim: date,
    canais_lista: list[str],
    fonte_margem: str,
    margem_periodo: dict,
    modo_custo_fiscal: str = MODO_CUSTO_FISCAL_PE_PADRAO,
) -> dict:
    opcao = MARGEM_PONTO_EQUILIBRIO_OPCOES[fonte_margem]
    if fonte_margem == "periodo_atual":
        return {
            **margem_periodo,
            "fonte": fonte_margem,
            "label": opcao["label"],
        }

    meses = opcao["meses_fechados"]
    inicio_referencia, fim_referencia = _periodo_meses_fechados_para_margem(inicio, meses)
    margem = _calcular_margem_periodo_ponto_equilibrio(
        db,
        tenant_id,
        inicio_referencia,
        fim_referencia,
        canais_lista,
        modo_custo_fiscal=modo_custo_fiscal,
        incluir_detalhes=False,
    )
    return {
        **margem,
        "fonte": fonte_margem,
        "label": opcao["label"],
    }


@router.get("/financeiro/ponto-equilibrio")
async def obter_ponto_equilibrio(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    canais: Optional[str] = None,
    fonte_margem: Optional[str] = MARGEM_PONTO_EQUILIBRIO_PADRAO,
    modo_custo_fiscal: Optional[str] = MODO_CUSTO_FISCAL_PE_PADRAO,
    incluir_detalhes: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """Calcula o ponto de equilibrio pela margem de contribuicao."""
    _, tenant_id = user_and_tenant

    hoje = datetime.now().date()
    inicio = data_inicio or hoje.replace(day=1)
    fim_padrao = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])
    fim = data_fim or fim_padrao
    if fim < inicio:
        raise HTTPException(status_code=422, detail="Data final deve ser maior ou igual a data inicial")

    inicio_dt = datetime.combine(inicio, time.min)
    fim_dt = datetime.combine(fim, time.max)
    canais_lista = [canal.strip() for canal in (canais or "").split(",") if canal.strip()]
    fonte_margem = (fonte_margem or MARGEM_PONTO_EQUILIBRIO_PADRAO).strip()
    if fonte_margem not in MARGEM_PONTO_EQUILIBRIO_OPCOES:
        opcoes = ", ".join(MARGEM_PONTO_EQUILIBRIO_OPCOES.keys())
        raise HTTPException(status_code=422, detail=f"Fonte da margem invalida. Use: {opcoes}")
    modo_custo_fiscal = (modo_custo_fiscal or MODO_CUSTO_FISCAL_PE_PADRAO).strip()
    if modo_custo_fiscal not in MODO_CUSTO_FISCAL_PE_OPCOES:
        opcoes = ", ".join(MODO_CUSTO_FISCAL_PE_OPCOES.keys())
        raise HTTPException(status_code=422, detail=f"Modo de custo invalido. Use: {opcoes}")

    produtos_sem_custo = db.query(
        func.count(func.distinct(VendaItem.produto_id))
    ).join(
        Venda,
        VendaItem.venda_id == Venda.id,
    ).outerjoin(
        Produto,
        VendaItem.produto_id == Produto.id,
    ).filter(
        Venda.tenant_id == tenant_id,
        _filtro_status_venda_relatorio(),
        Venda.data_venda >= inicio_dt,
        Venda.data_venda <= fim_dt,
        VendaItem.tipo == "produto",
        VendaItem.produto_id.isnot(None),
        or_(Produto.preco_custo.is_(None), Produto.preco_custo <= 0),
    )
    if canais_lista:
        produtos_sem_custo = produtos_sem_custo.filter(Venda.canal.in_(canais_lista))
    produtos_sem_custo = int(produtos_sem_custo.scalar() or 0)

    contas_query = db.query(
        ContaPagar,
        TipoDespesa.e_custo_fixo.label("tipo_e_custo_fixo"),
        TipoDespesa.nome.label("tipo_despesa_nome"),
        CategoriaFinanceira.tipo_custo.label("categoria_tipo_custo"),
        CategoriaFinanceira.nome.label("categoria_nome"),
        DRESubcategoria.custo_pe.label("dre_custo_pe"),
        DRESubcategoria.tipo_custo.label("dre_tipo_custo"),
        DRESubcategoria.nome.label("dre_subcategoria_nome"),
        Cliente.nome.label("fornecedor_nome"),
    ).outerjoin(
        TipoDespesa,
        ContaPagar.tipo_despesa_id == TipoDespesa.id,
    ).outerjoin(
        CategoriaFinanceira,
        ContaPagar.categoria_id == CategoriaFinanceira.id,
    ).outerjoin(
        DRESubcategoria,
        ContaPagar.dre_subcategoria_id == DRESubcategoria.id,
    ).outerjoin(
        Cliente,
        and_(ContaPagar.fornecedor_id == Cliente.id, Cliente.tenant_id == tenant_id),
    ).filter(
        ContaPagar.tenant_id == tenant_id,
        ContaPagar.data_vencimento >= inicio,
        ContaPagar.data_vencimento <= fim,
        ContaPagar.status != "cancelado",
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

        if _conta_eh_folha_para_pe(conta, tipo_despesa_nome, categoria_nome, dre_subcategoria_nome):
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
            or_(DREDetalheCanal.canal.in_(canais_lista), DREDetalheCanal.canal == "provisao")
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
        detalhes_outros_variaveis=detalhes_classificacao["variaveis"] if incluir_detalhes else None,
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
    ticket_medio_usado = ticket_medio if ticket_medio > 0 else _round_money(margem_referencia.get("ticket_medio"))

    ponto_equilibrio = None
    falta_faturar = None
    percentual_atingido = 0
    vendas_necessarias = None
    status_pe = "sem_faturamento"

    if margem_usada_decimal > 0:
        ponto_equilibrio = despesas_fixas / margem_usada_decimal
        falta_faturar = max(0, ponto_equilibrio - faturamento)
        percentual_atingido = (faturamento / ponto_equilibrio) * 100 if ponto_equilibrio > 0 else 100
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
        "margem_contribuicao_percentual": round(margem_contribuicao_percentual * 100, 2),
        "margem_periodo_percentual": round(margem_contribuicao_percentual * 100, 2),
        "margem_periodo_valor": _round_money(margem_contribuicao),
        "margem_usada_percentual": margem_usada_percentual,
        "margem_usada_valor": _round_money(margem_referencia.get("margem_contribuicao")),
        "margem_usada_label": margem_referencia.get("label"),
        "margem_referencia": margem_referencia,
        "detalhes_margem": margem_periodo.get("detalhes_margem", {}),
        "ponto_equilibrio": _round_money(ponto_equilibrio) if ponto_equilibrio is not None else None,
        "falta_faturar": _round_money(falta_faturar) if falta_faturar is not None else None,
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
    user_and_tenant = Depends(get_current_user_and_tenant),
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
            "variaveis": dados.get("outros_variaveis", dados.get("despesas_variaveis_contas")),
            "custos_venda_snapshot": dados.get("despesas_variaveis_ja_cobertas"),
            "sem_classificacao": dados.get("despesas_sem_classificacao"),
            "estoque_excluido": dados.get("despesas_estoque_excluidas"),
        }
        total = _round_money(total_por_grupo.get(grupo) or 0)
    else:
        raise HTTPException(status_code=404, detail="Grupo de detalhes nao encontrado")

    paginacao = _paginar_detalhes_ponto_equilibrio(items, page=page, page_size=page_size)
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


@router.get("/dashboard/resumo")
async def obter_resumo_dashboard(
    periodo_dias: int = 30,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna resumo consolidado para o dashboard financeiro
    """
    current_user, tenant_id = user_and_tenant
    try:
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)
        
        # ========================================
        # 1. SALDO ATUAL (Baseado em vendas pagas)
        # ========================================
        vendas_pagas = db.query(
            func.sum(Venda.total)
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.status == 'finalizada'
            )
        ).scalar() or 0
        
        contas_pagas_total = db.query(
            func.sum(ContaPagar.valor_pago)
        ).filter(
            ContaPagar.tenant_id == tenant_id
        ).scalar() or 0
        
        saldo_atual = vendas_pagas - contas_pagas_total
        
        # ========================================
        # 2. CONTAS A RECEBER
        # ========================================
        contas_receber_total = db.query(
            func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido)
        ).filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status.in_(['pendente', 'parcial', 'vencida'])
            )
        ).scalar() or 0
        
        # Contas vencidas a receber
        contas_receber_vencidas = db.query(
            func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido)
        ).filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status.in_(['pendente', 'parcial', 'vencida']),
                ContaReceber.data_vencimento < hoje
            )
        ).scalar() or 0
        
        # ========================================
        # 3. CONTAS A PAGAR
        # ========================================
        contas_pagar_total = db.query(
            func.sum(ContaPagar.valor_final - ContaPagar.valor_pago)
        ).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status.in_(['pendente', 'parcial', 'vencida'])
            )
        ).scalar() or 0
        
        # Contas vencidas a pagar
        contas_pagar_vencidas = db.query(
            func.sum(ContaPagar.valor_final - ContaPagar.valor_pago)
        ).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status.in_(['pendente', 'parcial', 'vencida']),
                ContaPagar.data_vencimento < hoje
            )
        ).scalar() or 0
        
        # ========================================
        # 4. VENDAS DO PERÍODO
        # ========================================
        vendas_periodo = db.query(
            func.count(Venda.id).label('quantidade'),
            func.sum(Venda.total).label('valor_total'),
            func.sum(Venda.subtotal).label('faturamento_bruto')
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo
            )
        ).first()
        
        total_vendas_periodo = vendas_periodo.valor_total or 0
        quantidade_vendas_periodo = vendas_periodo.quantidade or 0
        faturamento_bruto_periodo = vendas_periodo.faturamento_bruto or 0
        
        # Vendas finalizadas
        vendas_finalizadas = db.query(
            func.sum(Venda.total)
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo,
                Venda.status == 'finalizada'
            )
        ).scalar() or 0
        
        # ========================================
        # 5. ENTRADAS E SAÍDAS DO PERÍODO (baseado em vendas e contas)
        # ========================================
        entradas_periodo = db.query(
            func.sum(Venda.total)
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo,
                Venda.status == 'finalizada'
            )
        ).scalar() or 0
        
        saidas_periodo = db.query(
            func.sum(ContaPagar.valor_pago)
        ).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.data_pagamento >= inicio_periodo
            )
        ).scalar() or 0
        
        # ========================================
        # 6. LUCRO DO PERÍODO
        # ========================================
        lucro_periodo = entradas_periodo - saidas_periodo
        
        # ========================================
        # 7. TICKET MÉDIO
        # ========================================
        ticket_medio = (total_vendas_periodo / quantidade_vendas_periodo) if quantidade_vendas_periodo > 0 else 0
        
        # ========================================
        # RETORNO
        # ========================================
        return {
            "saldo_atual": round(saldo_atual, 2),
            "contas_receber": {
                "total": round(contas_receber_total, 2),
                "vencidas": round(contas_receber_vencidas, 2)
            },
            "contas_pagar": {
                "total": round(contas_pagar_total, 2),
                "vencidas": round(contas_pagar_vencidas, 2)
            },
            "vendas_periodo": {
                "quantidade": quantidade_vendas_periodo,
                "valor_total": round(total_vendas_periodo, 2),
                "faturamento_bruto": round(float(faturamento_bruto_periodo), 2),
                "finalizadas": round(vendas_finalizadas, 2),
                "ticket_medio": round(ticket_medio, 2)
            },
            "fluxo_periodo": {
                "entradas": round(entradas_periodo, 2),
                "saidas": round(saidas_periodo, 2),
                "lucro": round(lucro_periodo, 2)
            },
            "periodo_dias": periodo_dias
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter resumo do dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/entradas-saidas")
async def obter_entradas_saidas_por_dia(
    periodo_dias: int = 30,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna entradas e saídas agrupadas por dia para gráfico
    """
    current_user, tenant_id = user_and_tenant
    try:
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)
        
        # Buscar vendas por dia
        vendas = db.query(
            func.date(Venda.data_venda).label('data'),
            func.sum(Venda.total).label('total')
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo,
                Venda.status == 'finalizada'
            )
        ).group_by(
            func.date(Venda.data_venda)
        ).all()
        
        # Buscar pagamentos por dia
        pagamentos = db.query(
            func.date(ContaPagar.data_pagamento).label('data'),
            func.sum(ContaPagar.valor_pago).label('total')
        ).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.data_pagamento >= inicio_periodo
            )
        ).group_by(
            func.date(ContaPagar.data_pagamento)
        ).all()
        
        # Organizar por data
        dados_por_dia = {}
        
        # Inicializar todos os dias com zero
        for i in range(periodo_dias + 1):
            data = (inicio_periodo + timedelta(days=i)).strftime('%Y-%m-%d')
            dados_por_dia[data] = {
                'data': data,
                'entradas': 0,
                'saidas': 0
            }
        
        # Preencher com vendas
        for venda in vendas:
            data_obj = venda[0] if isinstance(venda, tuple) else venda.data
            data_str = data_obj.strftime('%Y-%m-%d') if hasattr(data_obj, 'strftime') else str(data_obj)
            if data_str in dados_por_dia:
                dados_por_dia[data_str]['entradas'] = float(venda.total or 0)
        
        # Preencher com pagamentos
        for pagamento in pagamentos:
            data_obj = pagamento[0] if isinstance(pagamento, tuple) else pagamento.data
            data_str = data_obj.strftime('%Y-%m-%d') if hasattr(data_obj, 'strftime') else str(data_obj)
            if data_str in dados_por_dia:
                dados_por_dia[data_str]['saidas'] = float(pagamento.total or 0)
        
        # Converter para lista ordenada
        resultado = sorted(dados_por_dia.values(), key=lambda x: x['data'])
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao obter entradas/saídas por dia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/vendas-por-dia")
async def obter_vendas_por_dia(
    periodo_dias: int = 30,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna vendas agrupadas por dia para gráfico
    """
    current_user, tenant_id = user_and_tenant
    try:
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)
        
        # Buscar vendas do período
        vendas = db.query(
            func.date(Venda.data_venda).label('data'),
            func.count(Venda.id).label('quantidade'),
            func.sum(Venda.total).label('valor_total')
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo
            )
        ).group_by(
            func.date(Venda.data_venda)
        ).all()
        
        # Organizar por data
        dados_por_dia = {}
        
        # Inicializar todos os dias com zero
        for i in range(periodo_dias + 1):
            data = (inicio_periodo + timedelta(days=i)).strftime('%Y-%m-%d')
            dados_por_dia[data] = {
                'data': data,
                'quantidade': 0,
                'valor_total': 0
            }
        
        # Preencher com dados reais
        for venda in vendas:
            # venda é um resultado de query com labels, não um objeto Venda
            data_obj = venda[0] if isinstance(venda, tuple) else venda.data
            data_str = data_obj.strftime('%Y-%m-%d') if hasattr(data_obj, 'strftime') else str(data_obj)
            if data_str in dados_por_dia:
                dados_por_dia[data_str]['quantidade'] = int(venda.quantidade) if venda.quantidade else 0
                dados_por_dia[data_str]['valor_total'] = float(venda.valor_total or 0)
        
        # Converter para lista ordenada
        resultado = sorted(dados_por_dia.values(), key=lambda x: x['data'])
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao obter vendas por dia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/contas-vencidas")
async def obter_contas_vencidas(
    limite: int = 10,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna contas a receber e pagar vencidas (não pagas)
    """
    current_user, tenant_id = user_and_tenant
    
    try:
        hoje = datetime.now().date()
        logger.info(f"[contas-vencidas] Buscando contas vencidas para tenant {tenant_id}")
        
        # Contas a receber vencidas
        try:
            contas_receber = db.query(ContaReceber).filter(
                and_(
                    ContaReceber.tenant_id == tenant_id,
                    ContaReceber.status.in_(['pendente', 'parcial', 'vencido']),
                    ContaReceber.data_vencimento < hoje
                )
            ).order_by(ContaReceber.data_vencimento.asc()).limit(limite).all()
            logger.info(f"[contas-vencidas] Encontradas {len(contas_receber)} contas a receber vencidas")
        except Exception as e:
            logger.error(f"[contas-vencidas] Erro ao buscar contas a receber: {e}")
            contas_receber = []
        
        # Contas a pagar vencidas
        try:
            contas_pagar = db.query(ContaPagar).filter(
                and_(
                    ContaPagar.tenant_id == tenant_id,
                    ContaPagar.status.in_(['pendente', 'parcial', 'vencido']),
                    ContaPagar.data_vencimento < hoje
                )
            ).order_by(ContaPagar.data_vencimento.asc()).limit(limite).all()
            logger.info(f"[contas-vencidas] Encontradas {len(contas_pagar)} contas a pagar vencidas")
        except Exception as e:
            logger.error(f"[contas-vencidas] Erro ao buscar contas a pagar: {e}")
            contas_pagar = []
        
        #Serializar contas a receber
        contas_receber_list = []
        for c in contas_receber:
            try:
                # Acessar relacionamentos com segurança
                cliente_nome = None
                try:
                    if hasattr(c, 'cliente') and c.cliente:
                        cliente_nome = c.cliente.nome
                except Exception:
                    pass
                
                valor_final = float(c.valor_final) if c.valor_final else 0
                valor_recebido = float(c.valor_recebido) if c.valor_recebido else 0
                
                contas_receber_list.append({
                    "id": c.id,
                    "descricao": c.descricao or "Sem descrição",
                    "cliente": cliente_nome,
                    "valor_total": valor_final,
                    "valor_pago": valor_recebido,
                    "saldo": valor_final - valor_recebido,
                    "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
                    "dias_vencido": (hoje - c.data_vencimento).days if c.data_vencimento else 0,
                    "status": c.status
                })
            except Exception as e:
                logger.error(f"[contas-vencidas] Erro ao serializar conta a receber {c.id}: {e}")
                continue
        
        # Serializar contas a pagar
        contas_pagar_list = []
        for c in contas_pagar:
            try:
                # Acessar relacionamentos com segurança
                fornecedor_nome = None
                try:
                    if hasattr(c, 'fornecedor') and c.fornecedor:
                        fornecedor_nome = c.fornecedor.nome
                except Exception:
                    pass
                
                valor_final = float(c.valor_final) if c.valor_final else 0
                valor_pago = float(c.valor_pago) if c.valor_pago else 0
                
                contas_pagar_list.append({
                    "id": c.id,
                    "descricao": c.descricao or "Sem descrição",
                    "fornecedor": fornecedor_nome,
                    "valor_total": valor_final,
                    "valor_pago": valor_pago,
                    "saldo": valor_final - valor_pago,
                    "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
                    "dias_vencido": (hoje - c.data_vencimento).days if c.data_vencimento else 0,
                    "status": c.status
                })
            except Exception as e:
                logger.error(f"[contas-vencidas] Erro ao serializar conta a pagar {c.id}: {e}")
                continue
        
        return {
            "contas_receber": contas_receber_list,
            "contas_pagar": contas_pagar_list
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter contas vencidas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/gerencial")
async def obter_metricas_gerencial(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna métricas consolidadas para o Dashboard Gerencial.
    Calcula diretamente do banco, sem depender de client-side logic.
    """
    current_user, tenant_id = user_and_tenant
    try:
        # 1. VIPs inativos — segmento VIP com mais de 20 dias sem compra
        vips_result = _dashboard_fetchone(db, """
            SELECT
                COUNT(*) AS qtd,
                COALESCE(SUM(CAST(cs.metricas->>'total_compras_90d' AS FLOAT)), 0) AS impacto
            FROM cliente_segmentos cs
            JOIN clientes c ON c.id = cs.cliente_id AND c.{tenant_filter}
            WHERE cs.{tenant_filter}
              AND cs.segmento = 'VIP'
              AND CAST(cs.metricas->>'ultima_compra_dias' AS INTEGER) > 20
              AND c.ativo = true
        """, tenant_id)

        # 2. Clientes inativos — sem compra há mais de 90 dias
        inativos_result = _dashboard_fetchone(db, """
            SELECT COUNT(DISTINCT c.id) AS qtd
            FROM clientes c
            LEFT JOIN (
                SELECT cliente_id, MAX(data_venda) AS ultima_venda
                FROM vendas
                WHERE {tenant_filter} AND status = 'finalizada'
                GROUP BY cliente_id
            ) v ON v.cliente_id = c.id
            WHERE c.{tenant_filter}
              AND c.tipo_cadastro = 'cliente'
              AND c.ativo = true
              AND (v.ultima_venda IS NULL OR v.ultima_venda < NOW() - INTERVAL '90 days')
        """, tenant_id)

        # 3. Clientes endividados — contas a receber em aberto com saldo > 0
        endividados_result = _dashboard_fetchone(db, """
            SELECT
                COUNT(DISTINCT cr.cliente_id) AS qtd,
                COALESCE(SUM(cr.valor_final - COALESCE(cr.valor_recebido, 0)), 0) AS total_dividas
            FROM contas_receber cr
            WHERE cr.{tenant_filter}
              AND cr.status IN ('pendente', 'vencido', 'parcial')
              AND cr.cliente_id IS NOT NULL
              AND (cr.valor_final - COALESCE(cr.valor_recebido, 0)) > 0
        """, tenant_id)

        # 4. Novos promissores — segmento Novo com ticket médio > R$ 200
        novos_result = _dashboard_fetchone(db, """
            SELECT
                COUNT(*) AS qtd,
                COALESCE(SUM(CAST(cs.metricas->>'ticket_medio' AS FLOAT)), 0) AS potencial
            FROM cliente_segmentos cs
            JOIN clientes c ON c.id = cs.cliente_id AND c.{tenant_filter}
            WHERE cs.{tenant_filter}
              AND cs.segmento = 'Novo'
              AND CAST(cs.metricas->>'ticket_medio' AS FLOAT) > 200
              AND c.ativo = true
        """, tenant_id)

        # 5. WhatsApp faltando — clientes sem celular cadastrado
        sem_whatsapp_result = _dashboard_fetchone(db, """
            SELECT COUNT(*) AS qtd
            FROM clientes
            WHERE {tenant_filter}
              AND tipo_cadastro = 'cliente'
              AND ativo = true
              AND (celular IS NULL OR TRIM(celular) = '')
        """, tenant_id)

        # 6. Total de clientes ativos (tipo cliente)
        total_result = _dashboard_fetchone(db, """
            SELECT COUNT(*) AS qtd
            FROM clientes
            WHERE {tenant_filter}
              AND tipo_cadastro = 'cliente'
              AND ativo = true
        """, tenant_id)

        def fmt_brl(value: float) -> str:
            return f"R$ {value:_.2f}".replace('.', ',').replace('_', '.')

        total_dividas = float(endividados_result.total_dividas or 0)
        potencial_novos = float(novos_result.potencial or 0)
        impacto_vips = float(vips_result.impacto or 0)

        return {
            'vips_inativos': {
                'quantidade': int(vips_result.qtd or 0),
                'impacto': fmt_brl(impacto_vips)
            },
            'clientes_inativos': {
                'quantidade': int(inativos_result.qtd or 0),
                'impacto': 'Reativação pendente'
            },
            'clientes_endividados': {
                'quantidade': int(endividados_result.qtd or 0),
                'impacto': fmt_brl(total_dividas)
            },
            'oportunidades_novos': {
                'quantidade': int(novos_result.qtd or 0),
                'impacto': f"~R$ {potencial_novos:_.0f}/mês".replace('_', '.')
            },
            'pets_sem_eventos': {
                'quantidade': 0,
                'impacto': 'Em breve'
            },
            'whatsapp_inativo': {
                'quantidade': int(sem_whatsapp_result.qtd or 0),
                'impacto': 'Canal perdido'
            },
            'total_clientes': int(total_result.qtd or 0)
        }

    except Exception as e:
        logger.error(f"Erro ao obter métricas gerenciais: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/top-produtos")
async def obter_top_produtos(
    periodo_dias: int = 30,
    limite: int = 10,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna os produtos mais vendidos no período
    """
    current_user, tenant_id = user_and_tenant
    try:
        from .vendas_models import VendaItem
        from .produtos_models import Produto
        
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)
        
        # Buscar produtos mais vendidos
        top_produtos = db.query(
            Produto.nome,
            func.sum(VendaItem.quantidade).label('total_vendido'),
            func.sum(VendaItem.subtotal).label('receita_total')
        ).join(
            VendaItem, Produto.id == VendaItem.produto_id
        ).join(
            Venda, VendaItem.venda_id == Venda.id
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Produto.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo
            )
        ).group_by(
            Produto.id, Produto.nome
        ).order_by(
            func.sum(VendaItem.quantidade).desc()
        ).limit(limite).all()
        
        return [
            {
                "nome": p.nome,
                "quantidade_vendida": int(p.total_vendido),
                "receita_total": float(p.receita_total or 0)
            }
            for p in top_produtos
        ]
        
    except Exception as e:
        logger.error(f"Erro ao obter top produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
