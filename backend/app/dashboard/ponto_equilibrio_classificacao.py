"""Classificacao e detalhe do Ponto de Equilibrio financeiro."""

import math
import re
import unicodedata
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Cliente
from ..financeiro_models import ContaPagar
from ..cargo_models import Cargo
from ..services.remuneracao_service import calcular_composicao_remuneracao


def _round_money(value) -> float:
    return round(float(value or 0), 2)


def _normalizar_texto_pe(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.replace("-", " ")
    return re.sub(r"\s+", " ", texto).strip()


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
