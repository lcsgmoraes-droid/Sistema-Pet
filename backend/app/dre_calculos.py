"""Calculos e agregacoes financeiras da DRE."""

from decimal import Decimal

from sqlalchemy import and_, extract, or_
from sqlalchemy.orm import Session

from .dre_canais.contas import (
    classificacoes_contas_pagar,
    eh_compra_estoque,
    ids_fretes_sobre_compras,
)
from .dre_plano_contas_models import DRESubcategoria
from .financeiro_models import ContaPagar
from .vendas_models import Venda, VendaItem


def _calcular_custo_itens_por_natureza(
    db: Session, mes: int, ano: int, tenant_id: str, *, servicos: bool
) -> Decimal:
    """Separa custos de mercadorias e serviços sem alterar o custo total da venda."""
    # Busca todas as vendas do período
    vendas = (
        db.query(Venda)
        .filter(
            and_(
                extract("month", Venda.data_venda) == mes,
                extract("year", Venda.data_venda) == ano,
                Venda.tenant_id == tenant_id,
                Venda.status.in_(["finalizada", "pago_nf", "baixa_parcial"]),
            )
        )
        .all()
    )

    custo_total = Decimal("0")

    for venda in vendas:
        # Soma o custo de cada item vendido
        itens = (
            db.query(VendaItem)
            .filter(
                VendaItem.tenant_id == tenant_id,
                VendaItem.venda_id == venda.id,
            )
            .all()
        )

        for item in itens:
            if (str(item.tipo or "").lower() == "servico") != servicos:
                continue
            if item.produto and item.produto.preco_custo:
                custo_item = Decimal(str(item.produto.preco_custo)) * item.quantidade
                custo_total += custo_item

    return custo_total


def calcular_cmv(db: Session, mes: int, ano: int, tenant_id: str) -> Decimal:
    """Custo das mercadorias vendidas; não inclui itens de serviço."""
    return _calcular_custo_itens_por_natureza(db, mes, ano, tenant_id, servicos=False)


def calcular_custo_servicos(db: Session, mes: int, ano: int, tenant_id: str) -> Decimal:
    """Custo direto dos serviços vendidos no período."""
    return _calcular_custo_itens_por_natureza(db, mes, ano, tenant_id, servicos=True)


def calcular_frete_notas_entrada(
    db: Session, mes: int, ano: int, tenant_id: str
) -> Decimal:
    """
    Calcula o total de frete das notas de entrada do período
    Consulta informativa. O frete integra o custo de aquisição dos produtos
    e não deve ser somado novamente às despesas da DRE.
    """
    from .produtos_models import NotaEntrada

    notas = (
        db.query(NotaEntrada)
        .filter(
            and_(
                extract("month", NotaEntrada.data_emissao) == mes,
                extract("year", NotaEntrada.data_emissao) == ano,
                NotaEntrada.tenant_id == tenant_id,
            )
        )
        .all()
    )

    frete_total = Decimal("0")
    for nota in notas:
        if nota.valor_frete:
            frete_total += Decimal(str(nota.valor_frete))

    return frete_total


def obter_despesas_por_categoria(
    db: Session, mes: int, ano: int, tenant_id: str
) -> dict:
    """
    Agrupa despesas por categoria
    Categorias principais:
    - Despesas com Pessoal (salários, encargos)
    - Despesas Administrativas (água, luz, internet, telefone)
    - Despesas com Ocupação (aluguel, condomínio, IPTU)
    - Despesas com Vendas (marketing, frete)
    - Outras Despesas

    IMPORTANTE: Exclui compras de mercadorias (CMV) e Taxas Financeiras
    (categoria_id=7), que já são tratadas por calcular_taxas_cartao.
    """

    # IDs de subcategorias de Taxas Financeiras para excluir (evitar dupla contagem)
    subcategorias_taxas_ids = [
        s.id
        for s in db.query(DRESubcategoria)
        .filter(
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.categoria_id == 7,
            DRESubcategoria.ativo.is_(True),
        )
        .all()
    ]

    # Busca contas a pagar do período excluindo CMV e Taxas Financeiras
    filtros = [
        extract("month", ContaPagar.data_emissao) == mes,
        extract("year", ContaPagar.data_emissao) == ano,
        ContaPagar.tenant_id == tenant_id,
        ContaPagar.nota_entrada_id.is_(None),  # EXCLUI compras de mercadorias (CMV)
        ContaPagar.status != "cancelado",
        ContaPagar.status != "parcelado",
        ContaPagar.afeta_dre.is_(True),
    ]
    if subcategorias_taxas_ids:
        filtros.append(
            or_(
                ContaPagar.dre_subcategoria_id.is_(None),
                ~ContaPagar.dre_subcategoria_id.in_(subcategorias_taxas_ids),
            )
        )

    contas_pagar = db.query(ContaPagar).filter(and_(*filtros)).all()
    tipos, categorias_estoque = classificacoes_contas_pagar(db, tenant_id, contas_pagar)
    frete_ids = ids_fretes_sobre_compras(db, tenant_id)

    categorias = {
        "Despesas com Pessoal": Decimal("0"),
        "Despesas Administrativas": Decimal("0"),
        "Despesas com Ocupação": Decimal("0"),
        "Despesas com Vendas": Decimal("0"),
        "Outras Despesas": Decimal("0"),
    }

    # Palavras-chave para categorização automática
    # Nota: 'taxa' foi removido — taxas financeiras são tratadas por calcular_taxas_cartao
    palavras_pessoal = [
        "salário",
        "salario",
        "folha",
        "inss",
        "fgts",
        "vale",
        "funcionario",
        "funcionário",
        "comissão",
        "comissao",
        "férias",
        "ferias",
        "décimo",
        "decimo",
        "13º",
        "rescisão",
        "rescisao",
        "abono",
        "provisão de",
        "provisao de",
    ]
    palavras_admin = [
        "luz",
        "água",
        "agua",
        "internet",
        "telefone",
        "material",
        "limpeza",
    ]
    palavras_ocupacao = ["aluguel", "condomínio", "condominio", "iptu"]
    palavras_vendas = [
        "marketing",
        "propaganda",
        "anúncio",
        "anuncio",
        "frete",
        "entrega",
        "entregador",
    ]

    for conta in contas_pagar:
        if conta.dre_subcategoria_id not in frete_ids and eh_compra_estoque(
            conta, tipos, categorias_estoque
        ):
            continue
        descricao_lower = (conta.descricao or "").lower()
        valor = conta.valor_original

        # Categorização inteligente baseada em palavras-chave
        if any(palavra in descricao_lower for palavra in palavras_pessoal):
            categorias["Despesas com Pessoal"] += valor
        elif any(palavra in descricao_lower for palavra in palavras_admin):
            categorias["Despesas Administrativas"] += valor
        elif any(palavra in descricao_lower for palavra in palavras_ocupacao):
            categorias["Despesas com Ocupação"] += valor
        elif any(palavra in descricao_lower for palavra in palavras_vendas):
            categorias["Despesas com Vendas"] += valor
        else:
            categorias["Outras Despesas"] += valor

    return categorias


def calcular_taxas_cartao(db: Session, mes: int, ano: int, tenant_id: str) -> Decimal:
    """
    Calcula o total de taxas de cartão/PIX do período a partir das contas a pagar.
    Usa a categoria_id=7 (Taxas Financeiras) para identificar as subcategorias corretas.
    """
    # Buscar todas as subcategorias de Taxas Financeiras (categoria_id=7)
    subcategorias_taxas = (
        db.query(DRESubcategoria)
        .filter(
            and_(
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.categoria_id == 7,
                DRESubcategoria.ativo.is_(True),
            )
        )
        .all()
    )

    subcategoria_ids = [s.id for s in subcategorias_taxas]

    if not subcategoria_ids:
        return Decimal("0")

    # Buscar contas a pagar de taxas do período (regime de competência)
    taxas = (
        db.query(ContaPagar)
        .filter(
            and_(
                extract("month", ContaPagar.data_emissao) == mes,
                extract("year", ContaPagar.data_emissao) == ano,
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.dre_subcategoria_id.in_(subcategoria_ids),
                ContaPagar.status != "cancelado",
                ContaPagar.status != "parcelado",
                ContaPagar.afeta_dre.is_(True),
                ContaPagar.nota_entrada_id.is_(None),
            )
        )
        .all()
    )

    taxas_total = sum([Decimal(str(t.valor_original or 0)) for t in taxas])

    return taxas_total


# ==================== ENDPOINTS ====================
