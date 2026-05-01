"""
Endpoint DRE por Canal - Retorna dados estruturados com nome e cor por canal
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, and_, or_, extract
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.db import get_session
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User, Cliente
from app.vendas_models import Venda, VendaItem
from app.produtos_models import Produto, EstoqueMovimentacao
from app.financeiro_models import ContaPagar, FormaPagamento
from app.dre_plano_contas_models import DRESubcategoria
from app.comissoes_models import ComissaoItem
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.services.venda_rentabilidade_snapshot_service import (
    SNAPSHOT_VERSION,
    build_venda_rentabilidade_snapshot,
)

router = APIRouter(prefix="/financeiro/dre/canais", tags=["DRE por Canal"])


# ==================== CONFIGURAÇÃO DE CANAIS ====================

CANAIS_CONFIG = {
    'loja_fisica': {
        'nome': 'Loja Física',
        'cor': '#3b82f6',  # Azul
        'cor_bg': '#eff6ff'
    },
    'mercado_livre': {
        'nome': 'Mercado Livre',
        'cor': '#fbbf24',  # Amarelo
        'cor_bg': '#fef3c7'
    },
    'shopee': {
        'nome': 'Shopee',
        'cor': '#f97316',  # Laranja
        'cor_bg': '#ffedd5'
    },
    'amazon': {
        'nome': 'Amazon',
        'cor': '#16a34a',  # Verde
        'cor_bg': '#dcfce7'
    },
    'ecommerce': {
        'nome': 'E-commerce',
        'cor': '#9333ea',  # Roxo
        'cor_bg': '#faf5ff'
    },
    'app': {
        'nome': 'App',
        'cor': '#4f46e5',  # Índigo
        'cor_bg': '#eef2ff'
    }
}


# ==================== SCHEMAS ====================

class LinhaCanal(BaseModel):
    """Uma linha da DRE de um canal específico"""
    descricao: str  # Ex: "Faturamento Mercado Livre"
    valor: float
    percentual: float
    cor: str  # Cor do canal
    cor_bg: str  # Cor de fundo
    canal: str  # ID do canal
    canal_nome: str  # Nome do canal
    nivel: int  # 0=seção, 1=linha normal, 2=total
    tipo: str  # 'receita', 'deducao', 'custo', 'despesa', 'lucro'
    origem: Optional[str] = None
    campo: Optional[str] = None
    detalhavel: bool = False


class DREPorCanalResponse(BaseModel):
    """DRE completa com linhas separadas por canal"""
    periodo: str
    mes: int
    ano: int
    linhas: List[LinhaCanal]
    totais: Dict
    canais_encontrados: List[str]


class DREDetalheItem(BaseModel):
    id: str
    origem_tipo: str
    origem_label: str
    data: Optional[str] = None
    descricao: str
    contraparte: Optional[str] = None
    documento: Optional[str] = None
    status: Optional[str] = None
    valor: float
    valor_auxiliar: Optional[float] = None
    link: Optional[str] = None
    meta: Dict[str, Any] = {}


class DREDetalheResponse(BaseModel):
    campo: str
    canal: str
    canal_nome: str
    periodo: str
    origem: Optional[str] = None
    total: float
    total_itens: int
    page: int
    page_size: int
    pages: int
    items: List[DREDetalheItem]


# ==================== FUNÇÕES AUXILIARES ====================

def _obter_vendas_por_canal_legacy(db: Session, mes: int, ano: int, user_id: int) -> Dict:
    """Retorna vendas agrupadas por canal"""
    vendas = db.query(Venda).filter(
        and_(
            Venda.user_id == user_id,
            extract('month', Venda.data_venda) == mes,
            extract('year', Venda.data_venda) == ano,
            Venda.status.in_(['finalizada', 'pago_nf', 'baixa_parcial'])
        )
    ).all()
    
    # Agrupar por canal
    dados_por_canal = {}
    
    for venda in vendas:
        canal = venda.canal or 'loja_fisica'  # Default para loja física
        
        if canal not in dados_por_canal:
            dados_por_canal[canal] = {
                'receita_produtos': Decimal('0'),  # subtotal (só produtos)
                'taxa_entrega': Decimal('0'),  # frete cobrado do cliente
                'descontos': Decimal('0'),
                'cmv': Decimal('0'),
                'vendas': []
            }
        
        # Receita de Produtos (apenas subtotal, sem frete)
        dados_por_canal[canal]['receita_produtos'] += venda.subtotal
        
        # Taxa de Frete (o que o cliente pagou)
        if venda.taxa_entrega:
            dados_por_canal[canal]['taxa_entrega'] += venda.taxa_entrega
        
        dados_por_canal[canal]['descontos'] += (venda.desconto_valor or 0)
        dados_por_canal[canal]['vendas'].append(venda)
        
        # CMV
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        for item in itens:
            produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
            if produto and produto.preco_custo:
                custo = Decimal(str(produto.preco_custo)) * item.quantidade
                dados_por_canal[canal]['cmv'] += custo
    
    return dados_por_canal


def _periodo_mes(mes: int, ano: int) -> tuple[datetime, datetime]:
    inicio = datetime(ano, mes, 1)
    fim = datetime(ano + 1, 1, 1) if mes == 12 else datetime(ano, mes + 1, 1)
    return inicio, fim


def _decimal(valor) -> Decimal:
    return Decimal(str(valor or 0))


def _canal_expr():
    return func.coalesce(Venda.canal, 'loja_fisica')


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
    snapshot = _load_rentabilidade_snapshot(getattr(venda, "rentabilidade_snapshot", None))
    if not snapshot:
        return None
    try:
        version = int(snapshot.get("snapshot_version") or 0)
    except (TypeError, ValueError):
        version = 0
    return snapshot if version >= SNAPSHOT_VERSION else None


def _formas_pagamento_map(db: Session, tenant_id: str) -> Dict[str, FormaPagamento]:
    formas = db.query(FormaPagamento).filter(
        and_(FormaPagamento.tenant_id == tenant_id, FormaPagamento.ativo == True)
    ).all()
    return {_normalizar_forma_pagamento(forma.nome): forma for forma in formas}


def _impostos_percentual(db: Session, tenant_id: str) -> float:
    try:
        config_fiscal = db.query(EmpresaConfigFiscal).filter(
            EmpresaConfigFiscal.tenant_id == tenant_id
        ).first()
        return float(getattr(config_fiscal, "aliquota_simples_vigente", 0) or 0)
    except Exception:
        return 0.0


def _bulk_comissoes_por_venda(db: Session, tenant_id: str, venda_ids: List[int]) -> Dict[int, float]:
    if not venda_ids:
        return {}
    try:
        rows = (
            db.query(
                ComissaoItem.venda_id,
                func.coalesce(
                    func.sum(func.coalesce(ComissaoItem.valor_comissao, ComissaoItem.valor_comissao_gerada, 0)),
                    0,
                ),
            )
            .filter(and_(ComissaoItem.tenant_id == tenant_id, ComissaoItem.venda_id.in_(venda_ids)))
            .group_by(ComissaoItem.venda_id)
            .all()
        )
        return {int(venda_id): float(total or 0) for venda_id, total in rows}
    except Exception:
        return {}


def _bulk_cupons_por_venda(db: Session, tenant_id: str, vendas: List[Venda]) -> Dict[int, float]:
    resultado = {
        venda.id: float(_decimal(getattr(venda, "cupom_discount_applied", 0)))
        for venda in vendas
        if getattr(venda, "id", None)
    }
    ids_sem_valor = [venda.id for venda in vendas if getattr(venda, "id", None) and resultado.get(venda.id, 0) <= 0]
    if not ids_sem_valor:
        return resultado
    try:
        from app.campaigns.models import CouponRedemption

        rows = (
            db.query(CouponRedemption.venda_id, func.coalesce(func.sum(CouponRedemption.discount_applied), 0))
            .filter(
                CouponRedemption.tenant_id == tenant_id,
                CouponRedemption.venda_id.in_(ids_sem_valor),
                CouponRedemption.voided_at.is_(None),
            )
            .group_by(CouponRedemption.venda_id)
            .all()
        )
        for venda_id, total in rows:
            resultado[int(venda_id)] = float(total or 0)
    except Exception:
        pass
    return resultado


def _bulk_cashback_por_venda(db: Session, tenant_id: str, venda_ids: List[int]) -> Dict[int, float]:
    if not venda_ids:
        return {}
    try:
        from app.campaigns.models import CashbackTransaction

        rows = (
            db.query(CashbackTransaction.source_id, func.coalesce(func.sum(CashbackTransaction.amount), 0))
            .filter(
                CashbackTransaction.tenant_id == tenant_id,
                CashbackTransaction.amount < 0,
                CashbackTransaction.source_id.in_(venda_ids),
            )
            .group_by(CashbackTransaction.source_id)
            .all()
        )
        return {int(venda_id): abs(float(total or 0)) for venda_id, total in rows if venda_id}
    except Exception:
        return {}


def _bulk_taxa_operacional_por_venda(db: Session, tenant_id: str, vendas: List[Venda]) -> Dict[int, float]:
    entregador_ids = {
        venda.entregador_id
        for venda in vendas
        if getattr(venda, "tem_entrega", False) and getattr(venda, "entregador_id", None)
    }
    if not entregador_ids:
        return {}
    try:
        entregadores = db.query(Cliente.id, Cliente.taxa_fixa_entrega).filter(
            and_(Cliente.tenant_id == tenant_id, Cliente.id.in_(entregador_ids))
        ).all()
        taxas = {entregador_id: float(taxa or 0) for entregador_id, taxa in entregadores}
        return {
            venda.id: taxas.get(venda.entregador_id, 0.0)
            for venda in vendas
            if getattr(venda, "tem_entrega", False) and getattr(venda, "entregador_id", None)
        }
    except Exception:
        return {}


def _bulk_estoque_custos_por_venda(
    db: Session,
    tenant_id: str,
    venda_ids: List[int],
) -> Dict[int, Dict[int, Dict[str, float]]]:
    if not venda_ids:
        return {}
    try:
        movimentos = db.query(EstoqueMovimentacao).filter(
            and_(
                EstoqueMovimentacao.tenant_id == tenant_id,
                EstoqueMovimentacao.referencia_tipo == "venda",
                EstoqueMovimentacao.referencia_id.in_(venda_ids),
                EstoqueMovimentacao.tipo == "saida",
            )
        ).all()
    except Exception:
        return {}

    resultado: Dict[int, Dict[int, Dict[str, float]]] = {}
    for movimento in movimentos:
        if not getattr(movimento, "referencia_id", None) or not getattr(movimento, "produto_id", None):
            continue
        mapa_venda = resultado.setdefault(int(movimento.referencia_id), {})
        mapa_produto = mapa_venda.setdefault(
            int(movimento.produto_id),
            {"quantidade": 0.0, "valor_total": 0.0},
        )
        mapa_produto["quantidade"] += abs(float(getattr(movimento, "quantidade", 0) or 0))
        mapa_produto["valor_total"] += abs(float(getattr(movimento, "valor_total", 0) or 0))
    return resultado


def _campo_zero() -> Decimal:
    return Decimal("0")


def _novo_canal() -> Dict:
    return {
        'receita_produtos': _campo_zero(),
        'receita_servicos': _campo_zero(),
        'receita_frete': _campo_zero(),
        'descontos': _campo_zero(),
        'impostos': _campo_zero(),
        'cmv': _campo_zero(),
        'fretes_compras': _campo_zero(),
        'taxas_cartao': _campo_zero(),
        'taxas_marketplace': _campo_zero(),
        'repasse_entrega': _campo_zero(),
        'taxa_operacional_entrega': _campo_zero(),
        'comissoes': _campo_zero(),
        'campanhas': _campo_zero(),
        'despesas_pessoal': _campo_zero(),
        'despesas_administrativas': _campo_zero(),
        'despesas_comerciais': _campo_zero(),
        'despesas_financeiras': _campo_zero(),
        'outras_despesas': _campo_zero(),
        'vendas': [],
    }


def _valor_item_bruto(item: VendaItem) -> Decimal:
    subtotal = _decimal(getattr(item, "subtotal", 0))
    if subtotal:
        return subtotal
    return _decimal(getattr(item, "quantidade", 0)) * _decimal(getattr(item, "preco_unitario", 0))


def _separar_receita_produto_servico(venda: Venda, receita_bruta: Decimal) -> tuple[Decimal, Decimal]:
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


def _texto_conta(conta: ContaPagar, subcategoria: Optional[DRESubcategoria]) -> str:
    categoria_nome = getattr(getattr(subcategoria, "categoria", None), "nome", "") if subcategoria else ""
    partes = [
        getattr(conta, "descricao", "") or "",
        getattr(subcategoria, "nome", "") if subcategoria else "",
        categoria_nome or "",
    ]
    return " ".join(partes).lower()


def _eh_custo_de_venda_ja_vindo_da_venda(texto: str) -> bool:
    termos = [
        "taxa de cart",
        "taxas de cart",
        "taxa pix",
        "taxas pix",
        "pix/boleto",
        "frete operacional",
        "fretes sobre vendas",
        "taxa de entrega",
        "custo fixo entrega",
        "comissao entregador",
        "comissão entregador",
        "comissoes de vendas",
        "comissões de vendas",
    ]
    return any(termo in texto for termo in termos)


def _classificar_conta_dre(texto: str) -> str:
    if "marketplace" in texto or "mercado livre" in texto or "shopee" in texto or "amazon" in texto:
        return "taxas_marketplace"
    if any(t in texto for t in ["salario", "salário", "folha", "fgts", "inss", "vale ", "ferias", "férias", "13", "rescis"]):
        return "despesas_pessoal"
    if any(t in texto for t in ["aluguel", "condominio", "condomínio", "iptu", "energia", "eletrica", "elétrica", "agua", "água", "internet", "telefonia", "telefone", "seguranca", "segurança", "limpeza", "manutencao", "manutenção"]):
        return "despesas_administrativas"
    if any(t in texto for t in ["marketing", "ads", "propaganda", "anuncio", "anúncio", "brinde", "fidelidade", "campanha", "evento", "patrocin"]):
        return "despesas_comerciais"
    if any(t in texto for t in ["juros", "tarifa bancaria", "tarifa bancária", "iof", "financeir", "banco"]):
        return "despesas_financeiras"
    return "outras_despesas"


def obter_vendas_por_canal(db: Session, mes: int, ano: int, tenant_id: str) -> Dict:
    """Retorna vendas agrupadas por canal usando a fotografia de rentabilidade da venda."""
    inicio, fim = _periodo_mes(mes, ano)
    filtros_venda = [
        Venda.tenant_id == tenant_id,
        Venda.data_venda >= inicio,
        Venda.data_venda < fim,
        Venda.status.in_(['finalizada', 'pago_nf', 'baixa_parcial']),
    ]

    dados_por_canal: Dict[str, Dict] = {}

    vendas = (
        db.query(Venda)
        .options(
            selectinload(Venda.itens).selectinload(VendaItem.produto),
            selectinload(Venda.pagamentos),
        )
        .filter(and_(*filtros_venda))
        .all()
    )

    venda_ids = [venda.id for venda in vendas if getattr(venda, "id", None)]
    formas_pagamento = _formas_pagamento_map(db, tenant_id)
    impostos_percentual = _impostos_percentual(db, tenant_id)
    comissoes_por_venda = _bulk_comissoes_por_venda(db, tenant_id, venda_ids)
    cupons_por_venda = _bulk_cupons_por_venda(db, tenant_id, vendas)
    cashback_por_venda = _bulk_cashback_por_venda(db, tenant_id, venda_ids)
    taxa_operacional_por_venda = _bulk_taxa_operacional_por_venda(db, tenant_id, vendas)
    estoque_custos_por_venda = _bulk_estoque_custos_por_venda(db, tenant_id, venda_ids)

    for venda in vendas:
        canal = _normalizar_canal(getattr(venda, "canal", None))
        dados = dados_por_canal.setdefault(canal, _novo_canal())
        cupom_desconto = cupons_por_venda.get(venda.id, 0.0)
        custo_campanha = cupom_desconto + cashback_por_venda.get(venda.id, 0.0)
        snapshot = _snapshot_pronto(venda)
        if snapshot and custo_campanha > 0 and _decimal(snapshot.get("custo_campanha", 0)) <= 0:
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
                comissao_total=comissoes_por_venda.get(venda.id, 0.0),
                taxa_operacional_entrega=taxa_operacional_por_venda.get(venda.id, 0.0),
                estoque_custos_por_produto=estoque_custos_por_venda.get(venda.id, {}),
            )

        receita_bruta = _decimal(snapshot.get("venda_bruta", 0))
        receita_produtos, receita_servicos = _separar_receita_produto_servico(venda, receita_bruta)

        dados['receita_produtos'] += receita_produtos
        dados['receita_servicos'] += receita_servicos
        dados['receita_frete'] += _decimal(snapshot.get("taxa_loja", 0))
        dados['descontos'] += _decimal(snapshot.get("desconto", 0))
        dados['impostos'] += _decimal(snapshot.get("imposto", 0))
        dados['cmv'] += _decimal(snapshot.get("custo_produtos", 0))
        dados['taxas_cartao'] += _decimal(snapshot.get("taxa_cartao", 0))
        dados['repasse_entrega'] += _decimal(snapshot.get("taxa_entrega", 0))
        dados['taxa_operacional_entrega'] += _decimal(snapshot.get("taxa_operacional", 0))
        dados['comissoes'] += _decimal(snapshot.get("comissao", 0))
        dados['campanhas'] += _decimal(snapshot.get("custo_campanha", 0))
        dados['vendas'].append(venda)

    return dados_por_canal


def agregar_contas_pagar_por_canal(db: Session, mes: int, ano: int, tenant_id: str, dados_canais: Dict[str, Dict]) -> None:
    """Agrega despesas por competencia. Sem canal informado vai para Loja Fisica."""
    contas = (
        db.query(ContaPagar)
        .outerjoin(DRESubcategoria, ContaPagar.dre_subcategoria_id == DRESubcategoria.id)
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                extract('month', ContaPagar.data_emissao) == mes,
                extract('year', ContaPagar.data_emissao) == ano,
                ContaPagar.status != 'cancelado',
                ContaPagar.nota_entrada_id.is_(None),
            )
        )
        .all()
    )

    subcategoria_ids = {
        conta.dre_subcategoria_id
        for conta in contas
        if getattr(conta, "dre_subcategoria_id", None)
    }
    subcategorias = {}
    if subcategoria_ids:
        subcategorias = {
            subcategoria.id: subcategoria
            for subcategoria in db.query(DRESubcategoria)
            .options(selectinload(DRESubcategoria.categoria))
            .filter(
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.id.in_(subcategoria_ids),
            )
            .all()
        }

    for conta in contas:
        subcategoria = subcategorias.get(getattr(conta, "dre_subcategoria_id", None))

        texto = _texto_conta(conta, subcategoria)
        campo = _classificar_conta_dre(texto)
        if campo != "taxas_marketplace" and _eh_custo_de_venda_ja_vindo_da_venda(texto):
            continue

        canal = _normalizar_canal(getattr(conta, "canal", None))
        dados = dados_canais.setdefault(canal, _novo_canal())
        dados[campo] += _conta_valor(conta)


def agregar_fretes_sobre_compras(db: Session, mes: int, ano: int, tenant_id: str, dados_canais: Dict[str, Dict]) -> None:
    subcategoria_frete_compras = db.query(DRESubcategoria).filter(
        DRESubcategoria.tenant_id == tenant_id,
        DRESubcategoria.nome == "Fretes sobre Compras",
    ).first()

    if not subcategoria_frete_compras:
        return

    total = db.query(func.coalesce(func.sum(ContaPagar.valor_original), 0)).filter(
        and_(
            ContaPagar.tenant_id == tenant_id,
            extract('month', ContaPagar.data_emissao) == mes,
            extract('year', ContaPagar.data_emissao) == ano,
            ContaPagar.status != 'cancelado',
            ContaPagar.dre_subcategoria_id == subcategoria_frete_compras.id,
        )
    ).scalar()

    if total:
        dados_canais.setdefault("loja_fisica", _novo_canal())["fretes_compras"] += _decimal(total)


def _somar(dados_canais: Dict[str, Dict], campo: str) -> Decimal:
    return sum((_decimal(dados.get(campo, 0)) for dados in dados_canais.values()), Decimal("0"))


def _percentual(valor: Decimal, receita_bruta_total: Decimal) -> float:
    if receita_bruta_total <= 0:
        return 0.0
    return round(float(valor / receita_bruta_total * Decimal("100")), 2)


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
    "despesas_pessoal": "Contas a pagar de folha, salarios, encargos e beneficios pela data de emissao. Sem canal informado entra em Loja Fisica.",
    "despesas_administrativas": "Contas a pagar de aluguel, ocupacao, energia, agua, internet, manutencao e administrativo pela data de emissao.",
    "despesas_comerciais": "Contas a pagar de marketing, anuncios, brindes, eventos e acoes comerciais pela data de emissao.",
    "despesas_financeiras": "Contas a pagar de tarifas, juros, banco, IOF e despesas financeiras pela data de emissao.",
    "outras_despesas": "Demais contas a pagar classificadas para a DRE pela data de emissao.",
    "resultado_operacional_total": "Lucro bruto menos custos variaveis e despesas operacionais.",
    "lucro_liquido_total": "Resultado operacional do periodo. A DRE caixa sera tratada separadamente depois.",
}


def _linha_total(
    descricao: str,
    valor: Decimal,
    receita_bruta_total: Decimal,
    tipo: str,
    cor: str,
    cor_bg: str,
    origem: Optional[str] = None,
    campo: Optional[str] = None,
) -> LinhaCanal:
    percentual = Decimal("100") if descricao.startswith("(+)") and receita_bruta_total > 0 else Decimal(str(_percentual(valor, receita_bruta_total)))
    return LinhaCanal(
        descricao=descricao,
        valor=float(valor),
        percentual=float(percentual),
        cor=cor,
        cor_bg=cor_bg,
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo=tipo,
        origem=origem,
        campo=campo,
        detalhavel=False,
    )


def _linha_canal(
    canal: str,
    descricao: str,
    valor: Decimal,
    receita_bruta_total: Decimal,
    tipo: str,
    origem: Optional[str] = None,
    campo: Optional[str] = None,
) -> LinhaCanal:
    config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG["loja_fisica"])
    return LinhaCanal(
        descricao=f"{descricao} {config['nome']}",
        valor=float(valor),
        percentual=_percentual(valor, receita_bruta_total),
        cor=config["cor"],
        cor_bg="#ffffff",
        canal=canal,
        canal_nome=config["nome"],
        nivel=1,
        tipo=tipo,
        origem=origem,
        campo=campo,
        detalhavel=bool(campo),
    )


def _adicionar_linhas_campo(
    linhas: List[LinhaCanal],
    dados_canais: Dict[str, Dict],
    receita_bruta_total: Decimal,
    campo: str,
    descricao: str,
    tipo: str,
    origem: Optional[str] = None,
) -> None:
    origem_linha = origem or ORIGENS_DRE.get(campo)
    for canal in sorted(dados_canais.keys()):
        linhas.append(_linha_canal(canal, descricao, _decimal(dados_canais[canal].get(campo, 0)), receita_bruta_total, tipo, origem_linha, campo))


def montar_linhas_dre_competencia(dados_canais: Dict[str, Dict]) -> tuple[List[LinhaCanal], Dict[str, Any]]:
    receita_produtos_total = _somar(dados_canais, "receita_produtos")
    receita_servicos_total = _somar(dados_canais, "receita_servicos")
    receita_frete_total = _somar(dados_canais, "receita_frete")
    receita_bruta_total = receita_produtos_total + receita_servicos_total + receita_frete_total

    descontos_total = _somar(dados_canais, "descontos")
    impostos_total = _somar(dados_canais, "impostos")
    deducoes_total = descontos_total + impostos_total
    receita_liquida_total = receita_bruta_total - deducoes_total

    cmv_total = _somar(dados_canais, "cmv") + _somar(dados_canais, "fretes_compras")
    lucro_bruto_total = receita_liquida_total - cmv_total

    despesas_variaveis_total = (
        _somar(dados_canais, "taxas_cartao")
        + _somar(dados_canais, "taxas_marketplace")
        + _somar(dados_canais, "repasse_entrega")
        + _somar(dados_canais, "taxa_operacional_entrega")
        + _somar(dados_canais, "comissoes")
        + _somar(dados_canais, "campanhas")
    )
    despesas_fixas_total = (
        _somar(dados_canais, "despesas_pessoal")
        + _somar(dados_canais, "despesas_administrativas")
        + _somar(dados_canais, "despesas_comerciais")
        + _somar(dados_canais, "despesas_financeiras")
        + _somar(dados_canais, "outras_despesas")
    )
    despesas_operacionais_total = despesas_variaveis_total + despesas_fixas_total
    resultado_operacional_total = lucro_bruto_total - despesas_operacionais_total
    lucro_liquido_total = resultado_operacional_total

    linhas: List[LinhaCanal] = []

    linhas.append(_linha_total("(+) RECEITA BRUTA", receita_bruta_total, receita_bruta_total, "receita", "#111827", "#f3f4f6", ORIGENS_DRE["receita_bruta_total"]))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "receita_produtos", "Vendas de Produtos", "receita")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "receita_servicos", "Vendas de Servicos", "receita")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "receita_frete", "Receita de Frete", "receita")

    linhas.append(_linha_total("(-) DEDUCOES DA RECEITA", deducoes_total, receita_bruta_total, "deducao", "#dc2626", "#fef2f2", ORIGENS_DRE["deducoes_total"]))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "descontos", "Descontos Concedidos", "deducao")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "impostos", "Impostos sobre Vendas", "deducao")

    linhas.append(_linha_total("(=) RECEITA LIQUIDA", receita_liquida_total, receita_bruta_total, "receita", "#059669", "#d1fae5", ORIGENS_DRE["receita_liquida_total"]))

    linhas.append(_linha_total("(-) CUSTO DAS MERCADORIAS VENDIDAS (CMV)", cmv_total, receita_bruta_total, "custo", "#dc2626", "#fef2f2", ORIGENS_DRE["cmv_total"]))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "cmv", "CMV", "custo")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "fretes_compras", "Fretes sobre Compras", "custo")

    linhas.append(_linha_total("(=) LUCRO BRUTO", lucro_bruto_total, receita_bruta_total, "lucro", "#059669", "#d1fae5", ORIGENS_DRE["lucro_bruto_total"]))

    linhas.append(_linha_total("(-) CUSTOS E DESPESAS VARIAVEIS DE VENDA", despesas_variaveis_total, receita_bruta_total, "despesa", "#dc2626", "#fff7ed", ORIGENS_DRE["despesas_variaveis_total"]))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "taxas_cartao", "Taxas de Cartao/Meios de Pagamento", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "taxas_marketplace", "Taxas de Marketplace", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "repasse_entrega", "Repasse/Custo de Entrega", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "taxa_operacional_entrega", "Custo Operacional de Entrega", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "comissoes", "Comissoes de Venda", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "campanhas", "Campanhas, Cupons e Cashback", "despesa")

    linhas.append(_linha_total("(-) DESPESAS OPERACIONAIS FIXAS/ADMINISTRATIVAS", despesas_fixas_total, receita_bruta_total, "despesa", "#dc2626", "#fef2f2", ORIGENS_DRE["despesas_fixas_total"]))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "despesas_pessoal", "Folha, Salarios e Encargos", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "despesas_administrativas", "Aluguel/Ocupacao e Administrativo", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "despesas_comerciais", "Marketing e Comercial", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "despesas_financeiras", "Despesas Financeiras", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "outras_despesas", "Outras Despesas", "despesa")

    linhas.append(_linha_total("(=) RESULTADO OPERACIONAL", resultado_operacional_total, receita_bruta_total, "lucro", "#059669", "#d1fae5", ORIGENS_DRE["resultado_operacional_total"]))
    linhas.append(_linha_total("(=) LUCRO/PREJUIZO LIQUIDO", lucro_liquido_total, receita_bruta_total, "lucro", "#059669", "#d1fae5", ORIGENS_DRE["lucro_liquido_total"]))

    totais = {
        "receita_bruta": float(receita_bruta_total),
        "vendas_produtos": float(receita_produtos_total),
        "vendas_servicos": float(receita_servicos_total),
        "receita_frete": float(receita_frete_total),
        "descontos": float(descontos_total),
        "impostos": float(impostos_total),
        "deducoes_total": float(deducoes_total),
        "receita_liquida": float(receita_liquida_total),
        "cmv": float(cmv_total),
        "lucro_bruto": float(lucro_bruto_total),
        "despesas_variaveis": float(despesas_variaveis_total),
        "despesas_operacionais": float(despesas_operacionais_total),
        "resultado_operacional": float(resultado_operacional_total),
        "resultado_financeiro": 0.0,
        "lucro_liquido": float(lucro_liquido_total),
        "margem_bruta": round((float(lucro_bruto_total) / float(receita_liquida_total) * 100) if receita_liquida_total > 0 else 0, 2),
        "margem_liquida": round((float(lucro_liquido_total) / float(receita_liquida_total) * 100) if receita_liquida_total > 0 else 0, 2),
    }

    return linhas, totais


def obter_despesas_operacionais(db: Session, mes: int, ano: int, tenant_id: str) -> Decimal:
    """
    Calcula o total de despesas operacionais do período
    Inclui: TODAS as despesas operacionais (salários, fretes, comissões, administrativas, etc.)
    Exclui: Apenas compras de mercadorias (que vão para CMV)
    """
    from app.produtos_models import NotaEntrada
    
    # Buscar contas a pagar do período (TODAS, exceto compras de mercadorias)
    # ✅ USA DATA_EMISSAO (regime de competência)
    contas_pagar = db.query(ContaPagar).filter(
        and_(
            ContaPagar.tenant_id == tenant_id,
            extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
            extract('year', ContaPagar.data_emissao) == ano,
            ContaPagar.nota_entrada_id.is_(None)  # Exclui compras de mercadorias (CMV)
        )
    ).all()
    
    total_despesas = Decimal('0')
    for conta in contas_pagar:
        total_despesas += conta.valor_original
    
    # Adicionar fretes de notas de entrada (despesa operacional, não CMV)
    notas = db.query(NotaEntrada).filter(
        and_(
            NotaEntrada.tenant_id == tenant_id,
            extract('month', NotaEntrada.data_emissao) == mes,
            extract('year', NotaEntrada.data_emissao) == ano
        )
    ).all()
    
    for nota in notas:
        if nota.valor_frete:
            total_despesas += Decimal(str(nota.valor_frete))
    
    return total_despesas


def _periodo_label(mes: int, ano: int) -> str:
    meses = ['', 'Janeiro', 'Fevereiro', 'MarÃ§o', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    return f"{meses[mes]}/{ano}" if 1 <= mes <= 12 else f"{mes}/{ano}"


def _data_iso(valor: Any) -> Optional[str]:
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)


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
    return items[inicio:inicio + page_size], page_size, pages


def _preparar_snapshots_vendas(
    db: Session,
    tenant_id: str,
    vendas: List[Venda],
) -> Dict[int, Dict[str, Any]]:
    venda_ids = [venda.id for venda in vendas if getattr(venda, "id", None)]
    formas_pagamento = _formas_pagamento_map(db, tenant_id)
    impostos_percentual = _impostos_percentual(db, tenant_id)
    comissoes_por_venda = _bulk_comissoes_por_venda(db, tenant_id, venda_ids)
    cupons_por_venda = _bulk_cupons_por_venda(db, tenant_id, vendas)
    cashback_por_venda = _bulk_cashback_por_venda(db, tenant_id, venda_ids)
    taxa_operacional_por_venda = _bulk_taxa_operacional_por_venda(db, tenant_id, vendas)
    estoque_custos_por_venda = _bulk_estoque_custos_por_venda(db, tenant_id, venda_ids)

    snapshots: Dict[int, Dict[str, Any]] = {}
    for venda in vendas:
        cupom_desconto = cupons_por_venda.get(venda.id, 0.0)
        custo_campanha = cupom_desconto + cashback_por_venda.get(venda.id, 0.0)
        snapshot = _snapshot_pronto(venda)
        if snapshot and custo_campanha > 0 and _decimal(snapshot.get("custo_campanha", 0)) <= 0:
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
                comissao_total=comissoes_por_venda.get(venda.id, 0.0),
                taxa_operacional_entrega=taxa_operacional_por_venda.get(venda.id, 0.0),
                estoque_custos_por_produto=estoque_custos_por_venda.get(venda.id, {}),
            )
        snapshots[int(venda.id)] = snapshot
    return snapshots


def _valor_snapshot_campo(campo: str, venda: Venda, snapshot: Dict[str, Any]) -> Decimal:
    if campo in {"receita_produtos", "receita_servicos"}:
        receita_produtos, receita_servicos = _separar_receita_produto_servico(
            venda,
            _decimal(snapshot.get("venda_bruta", 0)),
        )
        return receita_produtos if campo == "receita_produtos" else receita_servicos

    mapa_snapshot = {
        "receita_frete": "taxa_loja",
        "descontos": "desconto",
        "impostos": "imposto",
        "cmv": "custo_produtos",
        "taxas_cartao": "taxa_cartao",
        "repasse_entrega": "taxa_entrega",
        "taxa_operacional_entrega": "taxa_operacional",
        "comissoes": "comissao",
        "campanhas": "custo_campanha",
    }
    chave = mapa_snapshot.get(campo)
    return _decimal(snapshot.get(chave, 0)) if chave else Decimal("0")


CAMPOS_DETALHE_VENDAS = {
    "receita_produtos",
    "receita_servicos",
    "receita_frete",
    "descontos",
    "impostos",
    "cmv",
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


def _detalhes_vendas_campo(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    canal: str,
    campo: str,
) -> List[DREDetalheItem]:
    inicio, fim = _periodo_mes(mes, ano)
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
                Venda.status.in_(['finalizada', 'pago_nf', 'baixa_parcial']),
            )
        )
        .all()
    )
    vendas = [venda for venda in vendas if _normalizar_canal(getattr(venda, "canal", None)) == canal]
    snapshots = _preparar_snapshots_vendas(db, tenant_id, vendas)

    detalhes: List[DREDetalheItem] = []
    for venda in vendas:
        snapshot = snapshots.get(int(venda.id), {})
        valor = _valor_snapshot_campo(campo, venda, snapshot)
        if abs(valor) <= Decimal("0.004"):
            continue

        pagamentos = []
        for pagamento in list(getattr(venda, "pagamentos", []) or []):
            forma = getattr(pagamento, "forma_pagamento", None) or getattr(pagamento, "tipo", None)
            if forma:
                pagamentos.append(str(forma))

        cliente_nome = getattr(getattr(venda, "cliente", None), "nome", None) or "Sem cliente"
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

    detalhes.sort(key=lambda item: item.data or "", reverse=True)
    return detalhes


def _subcategorias_contas_map(
    db: Session,
    tenant_id: str,
    contas: List[ContaPagar],
) -> Dict[int, DRESubcategoria]:
    ids = {
        conta.dre_subcategoria_id
        for conta in contas
        if getattr(conta, "dre_subcategoria_id", None)
    }
    if not ids:
        return {}
    return {
        subcategoria.id: subcategoria
        for subcategoria in db.query(DRESubcategoria)
        .options(selectinload(DRESubcategoria.categoria))
        .filter(
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.id.in_(ids),
        )
        .all()
    }


def _detalhes_contas_campo(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    canal: str,
    campo: str,
) -> List[DREDetalheItem]:
    if campo == "fretes_compras":
        if canal != "loja_fisica":
            return []
        subcategoria_frete_compras = db.query(DRESubcategoria).filter(
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.nome == "Fretes sobre Compras",
        ).first()
        if not subcategoria_frete_compras:
            return []
        contas = (
            db.query(ContaPagar)
            .options(selectinload(ContaPagar.fornecedor))
            .filter(
                and_(
                    ContaPagar.tenant_id == tenant_id,
                    extract('month', ContaPagar.data_emissao) == mes,
                    extract('year', ContaPagar.data_emissao) == ano,
                    ContaPagar.status != 'cancelado',
                    ContaPagar.dre_subcategoria_id == subcategoria_frete_compras.id,
                )
            )
            .all()
        )
        subcategorias = {subcategoria_frete_compras.id: subcategoria_frete_compras}
    else:
        contas_base = (
            db.query(ContaPagar)
            .options(selectinload(ContaPagar.fornecedor))
            .filter(
                and_(
                    ContaPagar.tenant_id == tenant_id,
                    extract('month', ContaPagar.data_emissao) == mes,
                    extract('year', ContaPagar.data_emissao) == ano,
                    ContaPagar.status != 'cancelado',
                    ContaPagar.nota_entrada_id.is_(None),
                )
            )
            .all()
        )
        subcategorias = _subcategorias_contas_map(db, tenant_id, contas_base)
        contas = []
        for conta in contas_base:
            if _normalizar_canal(getattr(conta, "canal", None)) != canal:
                continue
            subcategoria = subcategorias.get(getattr(conta, "dre_subcategoria_id", None))
            texto = _texto_conta(conta, subcategoria)
            campo_conta = _classificar_conta_dre(texto)
            if campo_conta != "taxas_marketplace" and _eh_custo_de_venda_ja_vindo_da_venda(texto):
                continue
            if campo_conta == campo:
                contas.append(conta)

    detalhes: List[DREDetalheItem] = []
    for conta in contas:
        fornecedor_nome = getattr(getattr(conta, "fornecedor", None), "nome", None)
        documento = getattr(conta, "documento", None) or getattr(conta, "nfe_numero", None)
        subcategoria = subcategorias.get(getattr(conta, "dre_subcategoria_id", None))
        valor = _decimal(getattr(conta, "valor_original", 0)) if campo == "fretes_compras" else _conta_valor(conta)
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

    detalhes.sort(key=lambda item: item.data or "", reverse=True)
    return detalhes


# ==================== ENDPOINT PRINCIPAL ====================

@router.get("/detalhes", response_model=DREDetalheResponse)
def detalhar_linha_dre_por_canal(
    ano: int = Query(..., description="Ano do DRE"),
    mes: int = Query(..., description="MÃªs do DRE (1-12)"),
    canal: str = Query(..., description="Canal da linha"),
    campo: str = Query(..., description="Campo da DRE"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="MÃªs deve estar entre 1 e 12")

    campo = (campo or "").strip()
    canal = _normalizar_canal(canal)
    if campo not in CAMPOS_DETALHE_VENDAS and campo not in CAMPOS_DETALHE_CONTAS:
        raise HTTPException(status_code=400, detail="Linha da DRE sem detalhamento disponivel")

    _, tenant_id = user_and_tenant
    if campo in CAMPOS_DETALHE_VENDAS:
        detalhes = _detalhes_vendas_campo(db, mes, ano, tenant_id, canal, campo)
    else:
        detalhes = _detalhes_contas_campo(db, mes, ano, tenant_id, canal, campo)

    total = sum((_decimal(item.valor) for item in detalhes), Decimal("0"))
    pagina_items, page_size_final, pages = _paginar_detalhes(detalhes, page, page_size)
    config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG["loja_fisica"])

    return DREDetalheResponse(
        campo=campo,
        canal=canal,
        canal_nome=config["nome"],
        periodo=_periodo_label(mes, ano),
        origem=ORIGENS_DRE.get(campo),
        total=float(total),
        total_itens=len(detalhes),
        page=max(int(page or 1), 1),
        page_size=page_size_final,
        pages=pages,
        items=pagina_items,
    )

@router.get("", response_model=DREPorCanalResponse)
def gerar_dre_por_canais(
    ano: int = Query(..., description="Ano do DRE"),
    mes: int = Query(..., description="Mês do DRE (1-12)"),
    canais: str = Query("loja_fisica", description="Canais selecionados separados por vírgula (ex: loja_fisica,mercado_livre)"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Gera DRE com cada canal em linhas separadas
    
    Cada linha terá:
    - Nome do canal na descrição (ex: "Descontos Concedidos Loja Física")
    - Cor específica do canal
    - Valores individuais
    """
    
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Mês deve estar entre 1 e 12")
    
    # Processar canais selecionados
    canais_selecionados = [_normalizar_canal(c.strip()) for c in canais.split(',') if c.strip()]
    if not canais_selecionados:
        canais_selecionados = list(CANAIS_CONFIG.keys())
    
    meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    periodo = f"{meses[mes]}/{ano}"
    
    # Extrair user e tenant
    _, tenant_id = user_and_tenant

    dados_canais_calculados = obter_vendas_por_canal(db, mes, ano, tenant_id)
    agregar_contas_pagar_por_canal(db, mes, ano, tenant_id, dados_canais_calculados)
    agregar_fretes_sobre_compras(db, mes, ano, tenant_id, dados_canais_calculados)

    dados_canais_resultado = {
        canal_id: dados_canais_calculados.get(canal_id, _novo_canal())
        for canal_id in canais_selecionados
    }

    linhas, totais = montar_linhas_dre_competencia(dados_canais_resultado)

    return DREPorCanalResponse(
        periodo=periodo,
        mes=mes,
        ano=ano,
        linhas=linhas,
        totais=totais,
        canais_encontrados=list(dados_canais_resultado.keys())
    )
    
    # Obter dados por canal
    dados_canais = obter_vendas_por_canal(db, mes, ano, tenant_id)
    
    # Filtrar apenas os canais selecionados e garantir que existam
    dados_canais_filtrados = {}
    for canal_id in canais_selecionados:
        if canal_id in dados_canais:
            dados_canais_filtrados[canal_id] = dados_canais[canal_id]
        else:
            # Canal selecionado mas sem vendas - adicionar com valores zerados
            dados_canais_filtrados[canal_id] = {
                'receita_produtos': Decimal('0'),
                'taxa_entrega': Decimal('0'),
                'descontos': Decimal('0'),
                'cmv': Decimal('0'),
                'vendas': []
            }
    
    # Usar apenas os canais filtrados
    dados_canais = dados_canais_filtrados
    
    # Calcular totais
    receita_produtos_total = sum(d['receita_produtos'] for d in dados_canais.values())
    taxa_entrega_total = sum(d['taxa_entrega'] for d in dados_canais.values())
    receita_bruta_total = receita_produtos_total + taxa_entrega_total
    descontos_total = sum(d['descontos'] for d in dados_canais.values())
    cmv_total = sum(d['cmv'] for d in dados_canais.values())
    receita_liquida_total = receita_bruta_total - descontos_total
    lucro_bruto_total = receita_liquida_total - cmv_total
    
    # Montar linhas
    linhas = []
    
    # ========== RECEITA BRUTA ==========
    linhas.append(LinhaCanal(
        descricao="(+) RECEITA BRUTA",
        valor=float(receita_bruta_total),
        percentual=100.0,
        cor="#000000",
        cor_bg="#f3f4f6",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="receita"
    ))
    
    # Linhas por canal - Vendas de Produtos (apenas subtotal, sem frete)
    for canal, dados in sorted(dados_canais.items()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        receita_produtos = float(dados['receita_produtos'])
        percentual = (receita_produtos / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
        
        linhas.append(LinhaCanal(
            descricao=f"Vendas de Produtos {config['nome']}",
            valor=receita_produtos,
            percentual=round(percentual, 2),
            cor=config['cor'],
            cor_bg="#ffffff",
            canal=canal,
            canal_nome=config['nome'],
            nivel=1,
            tipo="receita"
        ))
    
    # ========== TAXA DE FRETE (RECEITA) POR CANAL ==========
    # Taxa de frete paga pelo cliente, entra como receita
    # Vem diretamente do campo taxa_entrega das vendas
    
    from app.dre_plano_contas_models import DRESubcategoria
    
    for canal in sorted(dados_canais.keys()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        taxa_frete_canal = float(dados_canais[canal]['taxa_entrega'])
        
        if taxa_frete_canal > 0:
            percentual = (taxa_frete_canal / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
            
            linhas.append(LinhaCanal(
                descricao=f"Taxa de Frete {config['nome']}",
                valor=taxa_frete_canal,
                percentual=round(percentual, 2),
                cor=config['cor'],
                cor_bg="#ffffff",
                canal=canal,
                canal_nome=config['nome'],
                nivel=1,
                tipo="receita"
            ))
    
    # Vendas de Serviços por canal (REMOVIDO - será adicionado apenas se houver valores reais)
    
    # ========== DEDUÇÕES ==========
    linhas.append(LinhaCanal(
        descricao="(-) DEDUÇÕES DA RECEITA",
        valor=float(descontos_total),
        percentual=round((float(descontos_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#dc2626",
        cor_bg="#fef2f2",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="deducao"
    ))
    
    # Descontos por canal
    for canal, dados in sorted(dados_canais.items()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        desconto = float(dados['descontos'])
        percentual = (desconto / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
        
        linhas.append(LinhaCanal(
            descricao=f"Descontos Concedidos {config['nome']}",  # ← Nome do canal na descrição
            valor=desconto,
            percentual=round(percentual, 2),
            cor=config['cor'],
            cor_bg="#ffffff",
            canal=canal,
            canal_nome=config['nome'],
            nivel=1,
            tipo="deducao"
        ))
    
    # Devoluções por canal (REMOVIDO - será adicionado apenas se houver valores reais)
    
    # ========== RECEITA LÍQUIDA ==========
    linhas.append(LinhaCanal(
        descricao="(=) RECEITA LÍQUIDA",
        valor=float(receita_liquida_total),
        percentual=round((float(receita_liquida_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#059669",
        cor_bg="#d1fae5",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="receita"
    ))
    
    # ========== CMV ==========
    linhas.append(LinhaCanal(
        descricao="(-) CUSTO DAS MERCADORIAS VENDIDAS (CMV)",
        valor=float(cmv_total),
        percentual=round((float(cmv_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#dc2626",
        cor_bg="#fef2f2",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="custo"
    ))
    
    # CMV por canal
    for canal, dados in sorted(dados_canais.items()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        cmv = float(dados['cmv'])
        percentual = (cmv / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
        
        linhas.append(LinhaCanal(
            descricao=f"CMV {config['nome']}",  # ← Nome do canal na descrição
            valor=cmv,
            percentual=round(percentual, 2),
            cor=config['cor'],
            cor_bg="#ffffff",
            canal=canal,
            canal_nome=config['nome'],
            nivel=1,
            tipo="custo"
        ))
    
    # ========== FRETES SOBRE COMPRAS (CMV) ==========
    # Frete pago na compra de mercadorias
    
    subcategoria_frete_compras = db.query(DRESubcategoria).filter(
        DRESubcategoria.tenant_id == tenant_id,
        DRESubcategoria.nome == "Fretes sobre Compras"
    ).first()
    
    if subcategoria_frete_compras:
        contas_frete_compras = db.query(ContaPagar).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                extract('year', ContaPagar.data_emissao) == ano,
                ContaPagar.dre_subcategoria_id == subcategoria_frete_compras.id
            )
        ).all()
        
        total_frete_compras = sum(conta.valor_original for conta in contas_frete_compras)
        
        if total_frete_compras > 0:
            cmv_total += total_frete_compras
            percentual = (float(total_frete_compras) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
            
            linhas.append(LinhaCanal(
                descricao="   Fretes sobre Compras",
                valor=float(total_frete_compras),
                percentual=round(percentual, 2),
                cor="#6b7280",
                cor_bg="#ffffff",
                canal="total",
                canal_nome="Total",
                nivel=1,
                tipo="custo"
            ))
    
    # Recalcular lucro bruto com frete de compras
    lucro_bruto_total = receita_liquida_total - cmv_total
    
    # ========== LUCRO BRUTO ==========
    linhas.append(LinhaCanal(
        descricao="(=) LUCRO BRUTO",
        valor=float(lucro_bruto_total),
        percentual=round((float(lucro_bruto_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#059669",
        cor_bg="#d1fae5",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="lucro"
    ))
    
    # ========== DESPESAS OPERACIONAIS ==========
    # Primeiro, buscar subcategoria antiga "Fretes sobre Vendas" para contas legadas
    subcategoria_antiga = db.query(DRESubcategoria).filter(
        DRESubcategoria.tenant_id == tenant_id,
        DRESubcategoria.nome.like('Fretes sobre Vendas%')
    ).first()
    
    # Calcular Frete Operacional por canal
    total_frete_op_geral = Decimal('0')
    detalhes_frete_op = []
    
    for canal in sorted(dados_canais.keys()):
            config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
            total_frete_op_canal = Decimal('0')
            
            # Buscar subcategoria específica do canal (nova, sem acentos)
            nome_canal = config['nome'].replace('í', 'i')
            subcategoria_frete_op = db.query(DRESubcategoria).filter(
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.nome == f"Frete Operacional - {nome_canal}"
            ).first()
            
            # Buscar contas com a subcategoria nova
            if subcategoria_frete_op:
                contas_frete_op = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id == subcategoria_frete_op.id,
                        ContaPagar.canal == canal
                    )
                ).all()
                total_frete_op_canal += sum(conta.valor_original for conta in contas_frete_op)
            
            # ✅ INCLUIR contas antigas com "Fretes sobre Vendas" que sejam "Custo fixo entrega"
            # (apenas no canal loja_fisica, pois vendas antigas não tinham campo canal preenchido)
            if subcategoria_antiga and canal == 'loja_fisica':
                contas_antigas_frete = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id == subcategoria_antiga.id,
                        or_(
                            ContaPagar.descricao.like('Custo fixo entrega%'),
                            ContaPagar.descricao.like('Controla RH entrega%')
                        ),
                        ContaPagar.canal.is_(None)  # Apenas contas sem canal (antigas)
                    )
                ).all()
                total_frete_op_canal += sum(conta.valor_original for conta in contas_antigas_frete)
            
            total_frete_op_geral += total_frete_op_canal
            
            if total_frete_op_canal > 0:
                percentual = (float(total_frete_op_canal) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
                
                detalhes_frete_op.append(LinhaCanal(
                    descricao=f"   Frete Operacional {config['nome']}",
                    valor=float(total_frete_op_canal),
                    percentual=round(percentual, 2),
                    cor=config['cor'],
                    cor_bg="#ffffff",
                    canal=canal,
                    canal_nome=config['nome'],
                    nivel=1,
                    tipo="despesa"
                ))
    
    # Calcular Comissão Entregador por canal
    total_comissao_geral = Decimal('0')
    detalhes_comissao = []
    
    for canal in sorted(dados_canais.keys()):
            config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
            total_comissao_canal = Decimal('0')
            
            # Buscar subcategoria específica do canal (nova, sem acentos)
            nome_canal = config['nome'].replace('í', 'i')
            subcategoria_comissao = db.query(DRESubcategoria).filter(
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.nome == f"Comissao Entregador - {nome_canal}"
            ).first()
            
            # Buscar contas com a subcategoria nova
            if subcategoria_comissao:
                contas_comissao = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id == subcategoria_comissao.id,
                        ContaPagar.canal == canal
                    )
                ).all()
                total_comissao_canal += sum(conta.valor_original for conta in contas_comissao)
            
            # ✅ INCLUIR contas antigas com "Fretes sobre Vendas" que sejam "Taxa de entrega"
            # (apenas no canal loja_fisica, pois vendas antigas não tinham campo canal preenchido)
            if subcategoria_antiga and canal == 'loja_fisica':
                contas_antigas_comissao = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id == subcategoria_antiga.id,
                        ContaPagar.descricao.like('Taxa de entrega%'),
                        ContaPagar.canal.is_(None)  # Apenas contas sem canal (antigas)
                    )
                ).all()
                total_comissao_canal += sum(conta.valor_original for conta in contas_antigas_comissao)
            
            total_comissao_geral += total_comissao_canal
            
            if total_comissao_canal > 0:
                percentual = (float(total_comissao_canal) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
                
                detalhes_comissao.append(LinhaCanal(
                    descricao=f"   Comissão Entregador {config['nome']}",
                    valor=float(total_comissao_canal),
                    percentual=round(percentual, 2),
                    cor=config['cor'],
                    cor_bg="#ffffff",
                    canal=canal,
                    canal_nome=config['nome'],
                    nivel=1,
                    tipo="despesa"
                ))
    
    # Calcular Comissões de Vendas - Vendedores por canal
    total_comissao_vendedores_geral = Decimal('0')
    detalhes_comissao_vendedores = []
    
    for canal in sorted(dados_canais.keys()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        total_comissao_vendedores_canal = Decimal('0')
        
        # Buscar subcategoria "Comissões de Vendas - Vendedores"
        subcategoria_comissao_vendedores = db.query(DRESubcategoria).filter(
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.nome.like('Comiss%es de Vendas - Vendedores')
        ).first()
        
        # Buscar contas
        if subcategoria_comissao_vendedores:
            contas_comissao_vendedores = db.query(ContaPagar).filter(
                and_(
                    ContaPagar.tenant_id == tenant_id,
                    extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência (data da venda)
                    extract('year', ContaPagar.data_emissao) == ano,
                    ContaPagar.dre_subcategoria_id == subcategoria_comissao_vendedores.id,
                    or_(ContaPagar.canal == canal, ContaPagar.canal.is_(None))
                )
            ).all()
            total_comissao_vendedores_canal += sum(conta.valor_original for conta in contas_comissao_vendedores)
        
        total_comissao_vendedores_geral += total_comissao_vendedores_canal
        
        if total_comissao_vendedores_canal > 0:
            percentual = (float(total_comissao_vendedores_canal) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
            
            detalhes_comissao_vendedores.append(LinhaCanal(
                descricao=f"   Comissões de Vendas {config['nome']}",
                valor=float(total_comissao_vendedores_canal),
                percentual=round(percentual, 2),
                cor=config['cor'],
                cor_bg="#ffffff",
                canal=canal,
                canal_nome=config['nome'],
                nivel=1,
                tipo="despesa"
            ))
    
    # Calcular Taxas de Cartao/PIX por canal e tipo
    total_taxas_cartao_geral = Decimal('0')
    detalhes_taxas_cartao = []

    tipos_taxas = [
        ("Taxas de Cartão de Crédito", "Taxas de Cartão de Crédito"),
        ("Taxas de Cartão de Débito", "Taxas de Cartão de Débito"),
        ("Taxa de PIX", "Taxa de PIX")
    ]

    for canal in sorted(dados_canais.keys()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])

        for nome_base, label in tipos_taxas:
            total_taxa_tipo = Decimal('0')

            nomes_taxas = [
                f"{nome_base} - {config['nome']}",
                nome_base
            ]

            subcategorias_taxas = db.query(DRESubcategoria).filter(
                and_(
                    DRESubcategoria.tenant_id == tenant_id,
                    DRESubcategoria.nome.in_(nomes_taxas)
                )
            ).all()

            if subcategorias_taxas:
                ids_taxas = [s.id for s in subcategorias_taxas]
                contas_taxas = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id.in_(ids_taxas),
                        or_(ContaPagar.canal == canal, ContaPagar.canal.is_(None))
                    )
                ).all()
                total_taxa_tipo += sum(conta.valor_original for conta in contas_taxas)

            if total_taxa_tipo > 0:
                total_taxas_cartao_geral += total_taxa_tipo
                percentual = (float(total_taxa_tipo) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
                detalhes_taxas_cartao.append(LinhaCanal(
                    descricao=f"   {label} {config['nome']}",
                    valor=float(total_taxa_tipo),
                    percentual=round(percentual, 2),
                    cor=config['cor'],
                    cor_bg="#ffffff",
                    canal=canal,
                    canal_nome=config['nome'],
                    nivel=1,
                    tipo="despesa"
                ))

    # Calcular total de despesas operacionais (soma dos detalhes)
    despesas_operacionais_total = (
        total_frete_op_geral +
        total_comissao_geral +
        total_comissao_vendedores_geral +
        total_taxas_cartao_geral
    )
    
    # Calcular resultado operacional e lucro líquido
    resultado_operacional_total = lucro_bruto_total - despesas_operacionais_total
    lucro_liquido_total = resultado_operacional_total  # Por enquanto, sem resultado financeiro
    
    # Inserir linha principal de DESPESAS OPERACIONAIS
    if despesas_operacionais_total > 0:
        linhas.append(LinhaCanal(
            descricao="(-) DESPESAS OPERACIONAIS",
            valor=float(despesas_operacionais_total),
            percentual=round((float(despesas_operacionais_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
            cor="#dc2626",
            cor_bg="#fef2f2",
            canal="total",
            canal_nome="Total",
            nivel=0,
            tipo="despesa"
        ))
        
        # Adicionar detalhes de Frete Operacional
        for detalhe in detalhes_frete_op:
            linhas.append(detalhe)
        
        # Adicionar detalhes de Comissão Entregador
        for detalhe in detalhes_comissao:
            linhas.append(detalhe)
        
        # Adicionar detalhes de Comissões de Vendas - Vendedores
        for detalhe in detalhes_comissao_vendedores:
            linhas.append(detalhe)

        # Adicionar detalhes de Taxas de Cartao
        for detalhe in detalhes_taxas_cartao:
            linhas.append(detalhe)
    
    # ========== RESULTADO OPERACIONAL ==========
    linhas.append(LinhaCanal(
        descricao="(=) RESULTADO OPERACIONAL",
        valor=float(resultado_operacional_total),
        percentual=round((float(resultado_operacional_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#059669",
        cor_bg="#d1fae5",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="lucro"
    ))
    
    # ========== RESULTADO FINANCEIRO ==========
    # TODO: Buscar receitas/despesas financeiras de contas_receber/pagar
    # Por enquanto, não exibir seção se não houver valores
    
    # ========== LUCRO LÍQUIDO ==========
    linhas.append(LinhaCanal(
        descricao="(=) LUCRO/PREJUÍZO LÍQUIDO",
        valor=float(lucro_liquido_total),
        percentual=round((float(lucro_liquido_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#059669",
        cor_bg="#d1fae5",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="lucro"
    ))
    
    # Totais
    totais = {
        'receita_bruta': float(receita_bruta_total),
        'descontos': float(descontos_total),
        'receita_liquida': float(receita_liquida_total),
        'cmv': float(cmv_total),
        'lucro_bruto': float(lucro_bruto_total),
        'despesas_operacionais': float(despesas_operacionais_total),
        'resultado_operacional': float(resultado_operacional_total),
        'resultado_financeiro': 0.0,
        'lucro_liquido': float(lucro_liquido_total),
        'margem_bruta': round((float(lucro_bruto_total) / float(receita_liquida_total) * 100) if receita_liquida_total > 0 else 0, 2),
        'margem_liquida': round((float(lucro_liquido_total) / float(receita_liquida_total) * 100) if receita_liquida_total > 0 else 0, 2)
    }
    
    return DREPorCanalResponse(
        periodo=periodo,
        mes=mes,
        ano=ano,
        linhas=linhas,
        totais=totais,
        canais_encontrados=list(dados_canais.keys())
    )
