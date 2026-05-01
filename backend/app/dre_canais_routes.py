"""
Endpoint DRE por Canal - Retorna dados estruturados com nome e cor por canal
"""
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
from app.models import User
from app.vendas_models import Venda, VendaItem
from app.produtos_models import Produto
from app.financeiro_models import ContaPagar
from app.dre_plano_contas_models import DRESubcategoria
from app.services.venda_rentabilidade_snapshot_service import get_or_build_venda_rentabilidade_snapshot

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


class DREPorCanalResponse(BaseModel):
    """DRE completa com linhas separadas por canal"""
    periodo: str
    mes: int
    ano: int
    linhas: List[LinhaCanal]
    totais: Dict
    canais_encontrados: List[str]


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

    for venda in vendas:
        canal = _normalizar_canal(getattr(venda, "canal", None))
        dados = dados_por_canal.setdefault(canal, _novo_canal())
        snapshot = get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant_id,
            persist_if_missing=False,
            force_refresh=False,
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

    for conta in contas:
        subcategoria = None
        if getattr(conta, "dre_subcategoria_id", None):
            subcategoria = db.query(DRESubcategoria).filter(
                DRESubcategoria.id == conta.dre_subcategoria_id,
                DRESubcategoria.tenant_id == tenant_id,
            ).first()

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


def _linha_total(descricao: str, valor: Decimal, receita_bruta_total: Decimal, tipo: str, cor: str, cor_bg: str) -> LinhaCanal:
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
    )


def _linha_canal(canal: str, descricao: str, valor: Decimal, receita_bruta_total: Decimal, tipo: str) -> LinhaCanal:
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
    )


def _adicionar_linhas_campo(
    linhas: List[LinhaCanal],
    dados_canais: Dict[str, Dict],
    receita_bruta_total: Decimal,
    campo: str,
    descricao: str,
    tipo: str,
) -> None:
    for canal in sorted(dados_canais.keys()):
        linhas.append(_linha_canal(canal, descricao, _decimal(dados_canais[canal].get(campo, 0)), receita_bruta_total, tipo))


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

    linhas.append(_linha_total("(+) RECEITA BRUTA", receita_bruta_total, receita_bruta_total, "receita", "#111827", "#f3f4f6"))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "receita_produtos", "Vendas de Produtos", "receita")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "receita_servicos", "Vendas de Servicos", "receita")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "receita_frete", "Receita de Frete", "receita")

    linhas.append(_linha_total("(-) DEDUCOES DA RECEITA", deducoes_total, receita_bruta_total, "deducao", "#dc2626", "#fef2f2"))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "descontos", "Descontos Concedidos", "deducao")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "impostos", "Impostos sobre Vendas", "deducao")

    linhas.append(_linha_total("(=) RECEITA LIQUIDA", receita_liquida_total, receita_bruta_total, "receita", "#059669", "#d1fae5"))

    linhas.append(_linha_total("(-) CUSTO DAS MERCADORIAS VENDIDAS (CMV)", cmv_total, receita_bruta_total, "custo", "#dc2626", "#fef2f2"))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "cmv", "CMV", "custo")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "fretes_compras", "Fretes sobre Compras", "custo")

    linhas.append(_linha_total("(=) LUCRO BRUTO", lucro_bruto_total, receita_bruta_total, "lucro", "#059669", "#d1fae5"))

    linhas.append(_linha_total("(-) CUSTOS E DESPESAS VARIAVEIS DE VENDA", despesas_variaveis_total, receita_bruta_total, "despesa", "#dc2626", "#fff7ed"))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "taxas_cartao", "Taxas de Cartao/Meios de Pagamento", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "taxas_marketplace", "Taxas de Marketplace", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "repasse_entrega", "Repasse/Custo de Entrega", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "taxa_operacional_entrega", "Custo Operacional de Entrega", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "comissoes", "Comissoes de Venda", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "campanhas", "Campanhas, Cupons e Cashback", "despesa")

    linhas.append(_linha_total("(-) DESPESAS OPERACIONAIS FIXAS/ADMINISTRATIVAS", despesas_fixas_total, receita_bruta_total, "despesa", "#dc2626", "#fef2f2"))
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "despesas_pessoal", "Folha, Salarios e Encargos", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "despesas_administrativas", "Aluguel/Ocupacao e Administrativo", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "despesas_comerciais", "Marketing e Comercial", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "despesas_financeiras", "Despesas Financeiras", "despesa")
    _adicionar_linhas_campo(linhas, dados_canais, receita_bruta_total, "outras_despesas", "Outras Despesas", "despesa")

    linhas.append(_linha_total("(=) RESULTADO OPERACIONAL", resultado_operacional_total, receita_bruta_total, "lucro", "#059669", "#d1fae5"))
    linhas.append(_linha_total("(=) LUCRO/PREJUIZO LIQUIDO", lucro_liquido_total, receita_bruta_total, "lucro", "#059669", "#d1fae5"))

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


# ==================== ENDPOINT PRINCIPAL ====================

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
