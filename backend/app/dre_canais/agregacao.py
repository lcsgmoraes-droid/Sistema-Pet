from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy import and_, extract, func
from sqlalchemy.orm import Session, selectinload

from app.comissoes_models import ComissaoItem
from app.dre_plano_contas_models import DRESubcategoria
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.financeiro_models import ContaPagar, FormaPagamento
from app.models import Cliente
from app.produtos_models import EstoqueMovimentacao, Produto
from app.vendas_models import Venda, VendaItem
from app.services.venda_rentabilidade_snapshot_service import (
    build_venda_rentabilidade_snapshot,
)
from app.dre_canais.base import (
    _classificar_conta_dre,
    _conta_valor,
    _decimal,
    _eh_custo_de_venda_ja_vindo_da_venda,
    _filtro_status_venda_dre,
    _normalizar_canal,
    _normalizar_forma_pagamento,
    _novo_canal,
    _periodo_mes,
    _separar_receita_produto_servico,
    _snapshot_pronto,
    _texto_conta,
)
from app.dre_canais.folha import calcular_resumo_folha_gerencial


def _obter_vendas_por_canal_legacy(
    db: Session, mes: int, ano: int, user_id: int
) -> Dict:
    """Retorna vendas agrupadas por canal"""
    vendas = (
        db.query(Venda)
        .filter(
            and_(
                Venda.user_id == user_id,
                extract("month", Venda.data_venda) == mes,
                extract("year", Venda.data_venda) == ano,
                _filtro_status_venda_dre(),
            )
        )
        .all()
    )

    # Agrupar por canal
    dados_por_canal = {}

    for venda in vendas:
        canal = venda.canal or "loja_fisica"  # Default para loja física

        if canal not in dados_por_canal:
            dados_por_canal[canal] = {
                "receita_produtos": Decimal("0"),  # subtotal (só produtos)
                "taxa_entrega": Decimal("0"),  # frete cobrado do cliente
                "descontos": Decimal("0"),
                "cmv": Decimal("0"),
                "vendas": [],
            }

        # Receita de Produtos (apenas subtotal, sem frete)
        dados_por_canal[canal]["receita_produtos"] += venda.subtotal

        # Taxa de Frete (o que o cliente pagou)
        if venda.taxa_entrega:
            dados_por_canal[canal]["taxa_entrega"] += venda.taxa_entrega

        dados_por_canal[canal]["descontos"] += venda.desconto_valor or 0
        dados_por_canal[canal]["vendas"].append(venda)

        # CMV
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        for item in itens:
            produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
            if produto and produto.preco_custo:
                custo = Decimal(str(produto.preco_custo)) * item.quantidade
                dados_por_canal[canal]["cmv"] += custo

    return dados_por_canal


def _formas_pagamento_map(db: Session, tenant_id: str) -> Dict[str, FormaPagamento]:
    formas = (
        db.query(FormaPagamento)
        .filter(
            and_(FormaPagamento.tenant_id == tenant_id, FormaPagamento.ativo.is_(True))
        )
        .all()
    )
    return {_normalizar_forma_pagamento(forma.nome): forma for forma in formas}


def _impostos_percentual(db: Session, tenant_id: str) -> float:
    try:
        config_fiscal = (
            db.query(EmpresaConfigFiscal)
            .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
            .first()
        )
        return float(getattr(config_fiscal, "aliquota_simples_vigente", 0) or 0)
    except Exception:
        return 0.0


def _bulk_comissoes_por_venda(
    db: Session, tenant_id: str, venda_ids: List[int]
) -> Dict[int, float]:
    if not venda_ids:
        return {}
    try:
        rows = (
            db.query(
                ComissaoItem.venda_id,
                func.coalesce(
                    func.sum(
                        func.coalesce(
                            ComissaoItem.valor_comissao,
                            ComissaoItem.valor_comissao_gerada,
                            0,
                        )
                    ),
                    0,
                ),
            )
            .filter(
                and_(
                    ComissaoItem.tenant_id == tenant_id,
                    ComissaoItem.venda_id.in_(venda_ids),
                )
            )
            .group_by(ComissaoItem.venda_id)
            .all()
        )
        return {int(venda_id): float(total or 0) for venda_id, total in rows}
    except Exception:
        return {}


def _bulk_cupons_por_venda(
    db: Session, tenant_id: str, vendas: List[Venda]
) -> Dict[int, float]:
    resultado = {
        venda.id: float(_decimal(getattr(venda, "cupom_discount_applied", 0)))
        for venda in vendas
        if getattr(venda, "id", None)
    }
    ids_sem_valor = [
        venda.id
        for venda in vendas
        if getattr(venda, "id", None) and resultado.get(venda.id, 0) <= 0
    ]
    if not ids_sem_valor:
        return resultado
    try:
        from app.campaigns.models import CouponRedemption

        rows = (
            db.query(
                CouponRedemption.venda_id,
                func.coalesce(func.sum(CouponRedemption.discount_applied), 0),
            )
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


def _bulk_cashback_por_venda(
    db: Session, tenant_id: str, venda_ids: List[int]
) -> Dict[int, float]:
    if not venda_ids:
        return {}
    try:
        from app.campaigns.models import CashbackTransaction

        rows = (
            db.query(
                CashbackTransaction.source_id,
                func.coalesce(func.sum(CashbackTransaction.amount), 0),
            )
            .filter(
                CashbackTransaction.tenant_id == tenant_id,
                CashbackTransaction.amount < 0,
                CashbackTransaction.source_id.in_(venda_ids),
            )
            .group_by(CashbackTransaction.source_id)
            .all()
        )
        return {
            int(venda_id): abs(float(total or 0))
            for venda_id, total in rows
            if venda_id
        }
    except Exception:
        return {}


def _bulk_taxa_operacional_por_venda(
    db: Session, tenant_id: str, vendas: List[Venda]
) -> Dict[int, float]:
    entregador_ids = {
        venda.entregador_id
        for venda in vendas
        if getattr(venda, "tem_entrega", False)
        and getattr(venda, "entregador_id", None)
    }
    if not entregador_ids:
        return {}
    try:
        entregadores = (
            db.query(Cliente.id, Cliente.taxa_fixa_entrega)
            .filter(
                and_(Cliente.tenant_id == tenant_id, Cliente.id.in_(entregador_ids))
            )
            .all()
        )
        taxas = {
            entregador_id: float(taxa or 0) for entregador_id, taxa in entregadores
        }
        return {
            venda.id: taxas.get(venda.entregador_id, 0.0)
            for venda in vendas
            if getattr(venda, "tem_entrega", False)
            and getattr(venda, "entregador_id", None)
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
        movimentos = (
            db.query(EstoqueMovimentacao)
            .filter(
                and_(
                    EstoqueMovimentacao.tenant_id == tenant_id,
                    EstoqueMovimentacao.referencia_tipo == "venda",
                    EstoqueMovimentacao.referencia_id.in_(venda_ids),
                    EstoqueMovimentacao.tipo == "saida",
                )
            )
            .all()
        )
    except Exception:
        return {}

    resultado: Dict[int, Dict[int, Dict[str, float]]] = {}
    for movimento in movimentos:
        if not getattr(movimento, "referencia_id", None) or not getattr(
            movimento, "produto_id", None
        ):
            continue
        mapa_venda = resultado.setdefault(int(movimento.referencia_id), {})
        mapa_produto = mapa_venda.setdefault(
            int(movimento.produto_id),
            {"quantidade": 0.0, "valor_total": 0.0},
        )
        mapa_produto["quantidade"] += abs(
            float(getattr(movimento, "quantidade", 0) or 0)
        )
        mapa_produto["valor_total"] += abs(
            float(getattr(movimento, "valor_total", 0) or 0)
        )
    return resultado


def obter_vendas_por_canal(db: Session, mes: int, ano: int, tenant_id: str) -> Dict:
    """Retorna vendas agrupadas por canal usando a fotografia de rentabilidade da venda."""
    inicio, fim = _periodo_mes(mes, ano)
    filtros_venda = [
        Venda.tenant_id == tenant_id,
        Venda.data_venda >= inicio,
        Venda.data_venda < fim,
        _filtro_status_venda_dre(),
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
        if (
            snapshot
            and custo_campanha > 0
            and _decimal(snapshot.get("custo_campanha", 0)) <= 0
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
                comissao_total=comissoes_por_venda.get(venda.id, 0.0),
                taxa_operacional_entrega=taxa_operacional_por_venda.get(venda.id, 0.0),
                estoque_custos_por_produto=estoque_custos_por_venda.get(venda.id, {}),
            )

        receita_bruta = _decimal(snapshot.get("venda_bruta", 0))
        receita_produtos, receita_servicos = _separar_receita_produto_servico(
            venda, receita_bruta
        )

        dados["receita_produtos"] += receita_produtos
        dados["receita_servicos"] += receita_servicos
        dados["receita_frete"] += _decimal(snapshot.get("taxa_loja", 0))
        dados["descontos"] += _decimal(snapshot.get("desconto", 0))
        dados["impostos"] += _decimal(snapshot.get("imposto", 0))
        dados["cmv"] += _decimal(snapshot.get("custo_produtos", 0))
        dados["taxas_cartao"] += _decimal(snapshot.get("taxa_cartao", 0))
        dados["repasse_entrega"] += _decimal(snapshot.get("taxa_entrega", 0))
        dados["taxa_operacional_entrega"] += _decimal(
            snapshot.get("taxa_operacional", 0)
        )
        dados["comissoes"] += _decimal(snapshot.get("comissao", 0))
        dados["campanhas"] += _decimal(snapshot.get("custo_campanha", 0))
        dados["vendas"].append(venda)

    return dados_por_canal


def agregar_contas_pagar_por_canal(
    db: Session, mes: int, ano: int, tenant_id: str, dados_canais: Dict[str, Dict]
) -> None:
    """Agrega despesas por competencia. Sem canal informado vai para Loja Fisica."""
    contas = (
        db.query(ContaPagar)
        .outerjoin(
            DRESubcategoria, ContaPagar.dre_subcategoria_id == DRESubcategoria.id
        )
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                extract("month", ContaPagar.data_emissao) == mes,
                extract("year", ContaPagar.data_emissao) == ano,
                ContaPagar.status != "cancelado",
                ContaPagar.afeta_dre.is_(True),
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

    resumo_folha = calcular_resumo_folha_gerencial(
        db, mes, ano, tenant_id, contas, subcategorias
    )
    for canal, valor in resumo_folha["ajustes_por_canal"].items():
        if valor:
            dados_canais.setdefault(canal, _novo_canal())["despesas_pessoal"] += valor


def agregar_fretes_sobre_compras(
    db: Session, mes: int, ano: int, tenant_id: str, dados_canais: Dict[str, Dict]
) -> None:
    subcategoria_frete_compras = (
        db.query(DRESubcategoria)
        .filter(
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.nome == "Fretes sobre Compras",
        )
        .first()
    )

    if not subcategoria_frete_compras:
        return

    total = (
        db.query(func.coalesce(func.sum(ContaPagar.valor_original), 0))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                extract("month", ContaPagar.data_emissao) == mes,
                extract("year", ContaPagar.data_emissao) == ano,
                ContaPagar.status != "cancelado",
                ContaPagar.dre_subcategoria_id == subcategoria_frete_compras.id,
            )
        )
        .scalar()
    )

    if total:
        dados_canais.setdefault("loja_fisica", _novo_canal())["fretes_compras"] += (
            _decimal(total)
        )


def obter_despesas_operacionais(
    db: Session, mes: int, ano: int, tenant_id: str
) -> Decimal:
    """
    Calcula o total de despesas operacionais do período
    Inclui: TODAS as despesas operacionais (salários, fretes, comissões, administrativas, etc.)
    Exclui: Apenas compras de mercadorias (que vão para CMV)
    """
    from app.produtos_models import NotaEntrada

    # Buscar contas a pagar do período (TODAS, exceto compras de mercadorias)
    # ✅ USA DATA_EMISSAO (regime de competência)
    contas_pagar = (
        db.query(ContaPagar)
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                extract("month", ContaPagar.data_emissao) == mes,  # ✅ Competência
                extract("year", ContaPagar.data_emissao) == ano,
                ContaPagar.nota_entrada_id.is_(
                    None
                ),  # Exclui compras de mercadorias (CMV)
            )
        )
        .all()
    )

    total_despesas = Decimal("0")
    for conta in contas_pagar:
        total_despesas += conta.valor_original

    # Adicionar fretes de notas de entrada (despesa operacional, não CMV)
    notas = (
        db.query(NotaEntrada)
        .filter(
            and_(
                NotaEntrada.tenant_id == tenant_id,
                extract("month", NotaEntrada.data_emissao) == mes,
                extract("year", NotaEntrada.data_emissao) == ano,
            )
        )
        .all()
    )

    for nota in notas:
        if nota.valor_frete:
            total_despesas += Decimal(str(nota.valor_frete))

    return total_despesas


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
        if (
            snapshot
            and custo_campanha > 0
            and _decimal(snapshot.get("custo_campanha", 0)) <= 0
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
                comissao_total=comissoes_por_venda.get(venda.id, 0.0),
                taxa_operacional_entrega=taxa_operacional_por_venda.get(venda.id, 0.0),
                estoque_custos_por_produto=estoque_custos_por_venda.get(venda.id, {}),
            )
        snapshots[int(venda.id)] = snapshot
    return snapshots


def _valor_snapshot_campo(
    campo: str, venda: Venda, snapshot: Dict[str, Any]
) -> Decimal:
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
