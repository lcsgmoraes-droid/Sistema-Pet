"""Calculos e classificacoes do Ponto de Equilibrio financeiro."""

import calendar
import math
import re
import unicodedata
from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from ..models import Cliente
from ..vendas_models import Venda, VendaItem
from ..financeiro_models import ContaPagar, CategoriaFinanceira, TipoDespesa
from ..cargo_models import Cargo
from ..dre_plano_contas_models import DRESubcategoria
from ..ia.aba7_dre_detalhada_models import DREDetalheCanal
from ..services.remuneracao_service import calcular_composicao_remuneracao
from ..services.venda_rentabilidade_snapshot_service import (
    build_venda_rentabilidade_snapshot,
)
from ..dre_canais_routes import (
    _bulk_cashback_por_venda,
    _bulk_comissoes_por_venda,
    _bulk_cupons_por_venda,
    _bulk_estoque_custos_por_venda,
    _bulk_taxa_operacional_por_venda,
    _formas_pagamento_map,
    _impostos_percentual,
    _snapshot_pronto,
)

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
    "media_12_meses_fechados": {
        "label": "Media 12 meses fechados",
        "meses_fechados": 12,
    },
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


def _conta_eh_compra_estoque_para_pe(
    conta: ContaPagar, tipo_nome: str = "", categoria_nome: str = ""
) -> bool:
    texto = f"{tipo_nome or ''} {categoria_nome or ''} {conta.descricao or ''}".lower()
    return bool(conta.nota_entrada_id) or ("produto" in texto and "revenda" in texto)


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

    if (
        modo_custo_fiscal == "documentos_emitidos"
        and not venda_tem_documento
        and imposto_original > 0
    ):
        ajustado["imposto"] = 0.0
        ajustado["custo_fiscal_desconsiderado"] = imposto_original
        ajustado["venda_liquida"] = _round_money(
            _snapshot_float(ajustado, "venda_liquida") + imposto_original
        )
        ajustado["lucro"] = _round_money(
            _snapshot_float(ajustado, "lucro") + imposto_original
        )

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
    componentes["outros_variaveis"] = (
        list(detalhes_outros_variaveis or []) if incluir_detalhes else []
    )

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
            custo_fiscal_omitido = (
                campo_total == "custo_fiscal"
                and _snapshot_float(snapshot, "custo_fiscal_desconsiderado") > 0
            )
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
        {
            "id": "receita_produtos_servicos",
            "label": "Receita de produtos/servicos",
            "tipo": "receita",
            "valor": receita_produtos_servicos,
        },
        {
            "id": "receita_entrega",
            "label": "Receita de entrega",
            "tipo": "receita",
            "valor": receita_entrega,
        },
        {
            "id": "descontos",
            "label": "Descontos comerciais",
            "tipo": "deducao",
            "valor": _round_money(campos["descontos"]),
        },
        {
            "id": "beneficios_campanhas",
            "label": "Campanhas, cupons e cashback",
            "tipo": "deducao",
            "valor": _round_money(campos["beneficios_campanhas"]),
        },
        {
            "id": "taxas_cartao",
            "label": "Taxas de cartao/meios de pagamento",
            "tipo": "deducao",
            "valor": _round_money(campos["taxas_cartao"]),
        },
        {
            "id": "repasse_entrega",
            "label": "Repasse/custo de entrega",
            "tipo": "deducao",
            "valor": _round_money(campos["repasse_entrega"]),
        },
        {
            "id": "custo_operacional_entrega",
            "label": "Custo operacional de entrega",
            "tipo": "deducao",
            "valor": _round_money(campos["custo_operacional_entrega"]),
        },
        {
            "id": "comissoes",
            "label": "Comissoes de venda",
            "tipo": "deducao",
            "valor": _round_money(campos["comissoes"]),
        },
        {
            "id": "custo_fiscal",
            "label": "Custo fiscal gerencial",
            "tipo": "deducao",
            "valor": _round_money(campos["custo_fiscal"]),
        },
        {"id": "cmv_estimado", "label": "CMV", "tipo": "custo", "valor": cmv_estimado},
        {
            "id": "outros_variaveis",
            "label": "Outros custos variaveis",
            "tipo": "deducao",
            "valor": outros_variaveis,
        },
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
        return (
            dre_custo_pe_normalizado,
            f"PE na subcategoria DRE: {dre_subcategoria_nome or '-'}",
        )

    if tipo_e_custo_fixo is not None:
        classificacao = "fixo" if bool(tipo_e_custo_fixo) else "variavel"
        return classificacao, f"Tipo de despesa: {tipo_despesa_nome or '-'}"

    categoria_tipo_normalizado = _normalizar_texto_pe(categoria_tipo_custo)
    if categoria_tipo_normalizado in {"fixo", "variavel"}:
        return (
            categoria_tipo_normalizado,
            f"Categoria financeira: {categoria_nome or '-'}",
        )

    texto_lancamento = " ".join(
        str(parte or "")
        for parte in (conta.descricao, tipo_despesa_nome, categoria_nome)
    )
    classificacao_por_lancamento = _classificar_texto_ponto_equilibrio(texto_lancamento)
    if classificacao_por_lancamento:
        return classificacao_por_lancamento, "Classificacao automatica pelo lancamento"

    dre_tipo_normalizado = _normalizar_tipo_custo_dre(dre_tipo_custo)
    if dre_tipo_normalizado in {
        "corporativo",
        "indireto_rateavel",
        "indireto rateavel",
    }:
        return "fixo", f"Tipo DRE: {dre_subcategoria_nome or '-'}"
    if dre_tipo_normalizado == "direto":
        return "variavel", f"Tipo DRE: {dre_subcategoria_nome or '-'}"

    classificacao_por_dre = _classificar_texto_ponto_equilibrio(
        dre_subcategoria_nome or ""
    )
    if classificacao_por_dre:
        return (
            classificacao_por_dre,
            f"Subcategoria DRE: {dre_subcategoria_nome or '-'}",
        )

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
            for parte in (
                conta.descricao,
                tipo_despesa_nome,
                categoria_nome,
                dre_subcategoria_nome,
            )
        )
    )
    return any(termo in texto for termo in PE_TERMOS_FOLHA)


def _calcular_complemento_folha_gerencial(
    *,
    total_estimado,
    total_lancado,
    total_provisoes_dre,
) -> float:
    complemento = (
        float(total_estimado or 0)
        - float(total_lancado or 0)
        - float(total_provisoes_dre or 0)
    )
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


def _paginar_detalhes_ponto_equilibrio(
    items: list[dict], *, page: int = 1, page_size: int = 30
) -> dict:
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
    descricao = (
        item.get("descricao") or item.get("numero_venda") or item.get("id") or "-"
    )
    contraparte = (
        item.get("cliente_nome") or item.get("fornecedor_nome") or item.get("canal")
    )
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


def _periodo_meses_fechados_para_margem(
    data_referencia: date, meses: int
) -> tuple[date, date]:
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
            or_(
                DREDetalheCanal.canal.in_(canais_lista),
                DREDetalheCanal.canal == "provisao",
            )
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
        if (
            snapshot
            and custo_campanha > 0
            and _snapshot_float(snapshot, "custo_campanha") <= 0
        ):
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
    ticket_medio = (
        _round_money(resultado["faturamento"] / quantidade_vendas)
        if quantidade_vendas
        else 0
    )

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
    inicio_referencia, fim_referencia = _periodo_meses_fechados_para_margem(
        inicio, meses
    )
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
