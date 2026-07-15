import json
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import func, or_

from app.dre_plano_contas_models import DRESubcategoria
from app.financeiro_models import ContaPagar
from app.vendas_models import Venda, VendaItem
from app.services.venda_rentabilidade_snapshot_service import SNAPSHOT_VERSION


CANAIS_CONFIG = {
    "loja_fisica": {
        "nome": "Loja Física",
        "cor": "#3b82f6",  # Azul
        "cor_bg": "#eff6ff",
    },
    "mercado_livre": {
        "nome": "Mercado Livre",
        "cor": "#fbbf24",  # Amarelo
        "cor_bg": "#fef3c7",
    },
    "shopee": {
        "nome": "Shopee",
        "cor": "#f97316",  # Laranja
        "cor_bg": "#ffedd5",
    },
    "amazon": {
        "nome": "Amazon",
        "cor": "#16a34a",  # Verde
        "cor_bg": "#dcfce7",
    },
    "ecommerce": {
        "nome": "E-commerce",
        "cor": "#9333ea",  # Roxo
        "cor_bg": "#faf5ff",
    },
    "app": {
        "nome": "App",
        "cor": "#4f46e5",  # Índigo
        "cor_bg": "#eef2ff",
    },
}


def _periodo_mes(mes: int, ano: int) -> tuple[datetime, datetime]:
    inicio = datetime(ano, mes, 1)
    fim = datetime(ano + 1, 1, 1) if mes == 12 else datetime(ano, mes + 1, 1)
    return inicio, fim


def _filtro_status_venda_dre():
    return or_(Venda.status.is_(None), Venda.status != "cancelada")


def _decimal(valor) -> Decimal:
    return Decimal(str(valor or 0))


def _canal_expr():
    return func.coalesce(Venda.canal, "loja_fisica")


CANAL_ALIASES = {
    "": "loja_fisica",
    "pdv": "loja_fisica",
    "fisica": "loja_fisica",
    "loja": "loja_fisica",
    "loja física": "loja_fisica",
    "loja fisica": "loja_fisica",
    "mercadolivre": "mercado_livre",
    "mercado livre": "mercado_livre",
    "ml": "mercado_livre",
    "site": "ecommerce",
    "web": "ecommerce",
    "e-commerce": "ecommerce",
    "ecommerce": "ecommerce",
    "app_mobile": "app",
    "mobile": "app",
}


def _normalizar_canal(canal: Optional[str]) -> str:
    chave = (canal or "loja_fisica").strip().lower()
    return CANAL_ALIASES.get(chave, chave if chave in CANAIS_CONFIG else "loja_fisica")


def _normalizar_forma_pagamento(valor: Optional[str]) -> str:
    return (valor or "").strip().lower()


def _load_rentabilidade_snapshot(snapshot_raw: Any) -> Optional[Dict[str, Any]]:
    if isinstance(snapshot_raw, dict):
        return snapshot_raw
    if isinstance(snapshot_raw, str) and snapshot_raw.strip():
        try:
            parsed = json.loads(snapshot_raw)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _snapshot_pronto(venda: Venda) -> Optional[Dict[str, Any]]:
    snapshot = _load_rentabilidade_snapshot(
        getattr(venda, "rentabilidade_snapshot", None)
    )
    if not snapshot:
        return None
    try:
        version = int(snapshot.get("snapshot_version") or 0)
    except (TypeError, ValueError):
        version = 0
    return snapshot if version >= SNAPSHOT_VERSION else None


def _campo_zero() -> Decimal:
    return Decimal("0")


def _novo_canal() -> Dict:
    return {
        "receita_produtos": _campo_zero(),
        "receita_servicos": _campo_zero(),
        "receita_frete": _campo_zero(),
        "descontos": _campo_zero(),
        "impostos": _campo_zero(),
        "cmv": _campo_zero(),
        "fretes_compras": _campo_zero(),
        "taxas_cartao": _campo_zero(),
        "taxas_marketplace": _campo_zero(),
        "repasse_entrega": _campo_zero(),
        "taxa_operacional_entrega": _campo_zero(),
        "comissoes": _campo_zero(),
        "campanhas": _campo_zero(),
        "despesas_pessoal": _campo_zero(),
        "despesas_administrativas": _campo_zero(),
        "despesas_comerciais": _campo_zero(),
        "despesas_financeiras": _campo_zero(),
        "outras_despesas": _campo_zero(),
        "vendas": [],
    }


def _valor_item_bruto(item: VendaItem) -> Decimal:
    subtotal = _decimal(getattr(item, "subtotal", 0))
    if subtotal:
        return subtotal
    return _decimal(getattr(item, "quantidade", 0)) * _decimal(
        getattr(item, "preco_unitario", 0)
    )


def _separar_receita_produto_servico(
    venda: Venda, receita_bruta: Decimal
) -> tuple[Decimal, Decimal]:
    total_produtos = Decimal("0")
    total_servicos = Decimal("0")

    for item in list(getattr(venda, "itens", []) or []):
        valor_item = _valor_item_bruto(item)
        if str(getattr(item, "tipo", "") or "").lower() == "servico":
            total_servicos += valor_item
        else:
            total_produtos += valor_item

    total_itens = total_produtos + total_servicos
    if total_itens <= 0:
        return receita_bruta, Decimal("0")

    fator = receita_bruta / total_itens
    return total_produtos * fator, total_servicos * fator


def _conta_valor(conta: ContaPagar) -> Decimal:
    valor_final = _decimal(getattr(conta, "valor_final", 0))
    return valor_final if valor_final else _decimal(getattr(conta, "valor_original", 0))


def _normalizar_texto_dre(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[-_/]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _texto_conta(conta: ContaPagar, subcategoria: Optional[DRESubcategoria]) -> str:
    categoria_nome = (
        getattr(getattr(subcategoria, "categoria", None), "nome", "")
        if subcategoria
        else ""
    )
    partes = [
        getattr(conta, "descricao", "") or "",
        getattr(subcategoria, "nome", "") if subcategoria else "",
        categoria_nome or "",
    ]
    return _normalizar_texto_dre(" ".join(partes))


def _eh_custo_de_venda_ja_vindo_da_venda(texto: str) -> bool:
    texto = _normalizar_texto_dre(texto)
    termos = [
        "taxa de cart",
        "taxas de cart",
        "taxa pix",
        "taxas pix",
        "pix boleto",
        "frete operacional",
        "fretes sobre vendas",
        "taxa de entrega",
        "custo fixo entrega",
        "comissao entregador",
        "comissoes de vendas",
    ]
    return any(termo in texto for termo in termos)


def _eh_folha_funcionarios_dre(texto: str) -> bool:
    """Identifica folha de empregados sem confundir pro-labore de socios."""
    texto = _normalizar_texto_dre(texto)
    termos = (
        "salario",
        "folha",
        "funcionario",
        "encargo",
        "fgts",
        "inss",
        "ferias",
        "decimo terceiro",
        "13o salario",
        "13º salario",
        "complemento salarial",
    )
    return any(termo in texto for termo in termos) and "pro labore" not in texto


def _classificar_conta_dre(texto: str) -> str:
    texto = _normalizar_texto_dre(texto)
    if (
        "marketplace" in texto
        or "mercado livre" in texto
        or "shopee" in texto
        or "amazon" in texto
    ):
        return "taxas_marketplace"
    if any(
        t in texto
        for t in [
            "salario",
            "folha",
            "pessoal",
            "funcionario",
            "encargo",
            "fgts",
            "inss",
            "vale transporte",
            "vale alimentacao",
            "vale refeicao",
            "ferias",
            "decimo terceiro",
            "13o salario",
            "13º salario",
            "rescis",
            "pro labore",
            "plano odontologico",
            "plano de saude",
            "beneficios trabalhistas",
            "beneficios funcionarios",
        ]
    ):
        return "despesas_pessoal"
    if any(
        t in texto
        for t in [
            "aluguel",
            "condominio",
            "iptu",
            "energia",
            "eletrica",
            "agua",
            "internet",
            "telefonia",
            "telefone",
            "seguranca",
            "limpeza",
            "manutencao",
            "ocupacao",
            "administrativ",
            "software",
            "sistema",
            "erp",
            "escritorio",
            "contabil",
            "honorario",
            "licenca",
        ]
    ):
        return "despesas_administrativas"
    if any(
        t in texto
        for t in [
            "marketing",
            "ads",
            "propaganda",
            "anuncio",
            "brinde",
            "fidelidade",
            "campanha",
            "evento",
            "patrocin",
        ]
    ):
        return "despesas_comerciais"
    if any(
        t in texto
        for t in [
            "juros",
            "tarifa bancaria",
            "iof",
            "financeir",
            "banco",
        ]
    ):
        return "despesas_financeiras"
    return "outras_despesas"


ORIGENS_DRE = {
    "receita_bruta_total": "Soma de produtos, servicos e frete das vendas do periodo nos canais selecionados. Usa a data da venda no regime de competencia.",
    "receita_produtos": "Vem dos itens de produto vendidos no periodo. Frete, servicos e descontos ficam em linhas separadas.",
    "receita_servicos": "Vem dos itens marcados como servico nas vendas do periodo.",
    "receita_frete": "Frete/taxa de entrega cobrada do cliente na venda, tratado como receita do periodo.",
    "deducoes_total": "Soma dos descontos comerciais e dos impostos estimados sobre as vendas.",
    "descontos": "Descontos concedidos na venda. Cupons/cashback identificados como campanha sao reclassificados na linha de campanhas.",
    "impostos": "Imposto por competencia, calculado pela aliquota fiscal configurada sobre venda bruta e frete.",
    "receita_liquida_total": "Receita bruta menos deducoes da receita.",
    "cmv_total": "Soma do CMV e dos fretes sobre compras classificados no periodo.",
    "cmv": "Custo dos produtos vendidos. Prioriza movimentacao de estoque/FIFO e usa custo do cadastro do produto quando nao houver movimento.",
    "fretes_compras": "Contas a pagar classificadas como Fretes sobre Compras pela data de emissao.",
    "lucro_bruto_total": "Receita liquida menos CMV e fretes sobre compras.",
    "despesas_variaveis_total": "Soma dos custos variaveis ligados a venda: cartao, marketplace, entrega, operacional, comissoes e campanhas.",
    "taxas_cartao": "Taxas das formas de pagamento configuradas, calculadas sobre os pagamentos das vendas.",
    "taxas_marketplace": "Contas a pagar classificadas como taxas de marketplace pela data de emissao.",
    "repasse_entrega": "Valor repassado ao entregador nas vendas com entrega.",
    "taxa_operacional_entrega": "Custo operacional fixo do entregador configurado no cadastro.",
    "comissoes": "Comissoes apuradas no modulo de comissoes para as vendas do periodo.",
    "campanhas": "Cupons, cashback e beneficios de campanha aplicados nas vendas do periodo.",
    "despesas_fixas_total": "Soma das contas a pagar administrativas, pessoal, comerciais, financeiras e outras no regime de competencia.",
    "despesas_pessoal": "Contas a pagar, provisoes trabalhistas e complemento da remuneracao cadastrada para funcionarios ativos, sem duplicar valores ja lancados. Sem canal informado entra em Loja Fisica.",
    "despesas_administrativas": "Contas a pagar de aluguel, ocupacao, energia, agua, internet, manutencao e administrativo pela data de emissao.",
    "despesas_comerciais": "Contas a pagar de marketing, anuncios, brindes, eventos e acoes comerciais pela data de emissao.",
    "despesas_financeiras": "Contas a pagar de tarifas, juros, banco, IOF e despesas financeiras pela data de emissao.",
    "outras_despesas": "Demais contas a pagar classificadas para a DRE pela data de emissao.",
    "resultado_operacional_total": "Lucro bruto menos custos variaveis e despesas operacionais.",
    "lucro_liquido_total": "Resultado operacional do periodo. A DRE caixa sera tratada separadamente depois.",
}


def _periodo_label(mes: int, ano: int) -> str:
    meses = [
        "",
        "Janeiro",
        "Fevereiro",
        "MarÃ§o",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    return f"{meses[mes]}/{ano}" if 1 <= mes <= 12 else f"{mes}/{ano}"


def _data_iso(valor: Any) -> Optional[str]:
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)
