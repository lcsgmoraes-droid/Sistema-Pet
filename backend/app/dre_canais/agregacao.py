from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, extract, func
from sqlalchemy.orm import Session, selectinload

from app.comissoes_models import ComissaoItem
from app.dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.financeiro_models import ContaPagar, ContaReceber, FormaPagamento
from app.models import Cliente
from app.produtos_models import EstoqueMovimentacao, Produto
from app.vendas_models import Venda, VendaItem
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas.devolucao_dre import custo_original_item_devolvido
from app.services.venda_rentabilidade_snapshot_service import (
    _round_money,
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
    _periodo_meses,
    _separar_receita_produto_servico,
    _snapshot_pronto,
    _texto_conta,
)
from app.dre_canais.contas import (
    classificacoes_contas_pagar,
    eh_compra_estoque,
    filtros_contas_pagar_dre,
    ids_fretes_sobre_compras,
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
                    ComissaoItem.status != "estornado",
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
    return resultado


def _bulk_cashback_por_venda(
    db: Session, tenant_id: str, venda_ids: List[int]
) -> Dict[int, float]:
    if not venda_ids:
        return {}
    from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction

    rows = (
        db.query(
            CashbackTransaction.source_id,
            func.coalesce(func.sum(CashbackTransaction.amount), 0),
        )
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.amount < 0,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.redemption,
            CashbackTransaction.source_id.in_(venda_ids),
        )
        .group_by(CashbackTransaction.source_id)
        .all()
    )
    return {
        int(venda_id): abs(float(total or 0)) for venda_id, total in rows if venda_id
    }


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


def _moeda(valor: Any) -> Decimal:
    return _decimal(valor).quantize(Decimal("0.01"))


def _custo_confirmado_atual_item(
    item: VendaItem,
    estoque_custos_por_produto: Dict[int, Dict[str, float]],
) -> tuple[Decimal, str | None]:
    """Busca um custo real atual sem alterar a fotografia persistida da venda."""
    quantidade_item = _decimal(getattr(item, "quantidade", 0))
    if quantidade_item <= 0:
        return Decimal("0"), None

    produto_id = getattr(item, "produto_id", None)
    movimento = estoque_custos_por_produto.get(int(produto_id or 0), {})
    quantidade_movimento = _decimal(movimento.get("quantidade", 0))
    valor_movimento = _decimal(movimento.get("valor_total", 0))
    if quantidade_movimento > 0 and valor_movimento > 0:
        custo_unitario = valor_movimento / quantidade_movimento
        return _moeda(custo_unitario * quantidade_item), "movimentacao_estoque"

    produto = getattr(item, "produto", None)
    custo_unitario = _decimal(getattr(produto, "preco_custo", 0))
    if custo_unitario > 0:
        return _moeda(custo_unitario * quantidade_item), "cadastro_produto"

    return Decimal("0"), None


def _quantidade_snapshot_legado(valor: Any) -> Decimal:
    """Repete o arredondamento salvo pelo builder v5, inclusive em meios centavos."""
    return Decimal(str(_round_money(valor)))


def _indice_snapshot_item(
    item: VendaItem, itens_venda: list[VendaItem], itens_snapshot: list[dict]
) -> int | None:
    """Relaciona linha e fotografia sem depender da ordem da relacao ORM."""
    item_id = getattr(item, "id", None)
    if item_id is not None:
        indices = [
            indice
            for indice, fotografia in enumerate(itens_snapshot)
            if fotografia.get("venda_item_id") == item_id
        ]
        if len(indices) == 1:
            return indices[0]
    if any(
        fotografia.get("venda_item_id") is not None for fotografia in itens_snapshot
    ):
        return None

    def assinatura(linha):
        return (
            getattr(linha, "produto_id", None),
            # Snapshot v5 guarda a quantidade arredondada a centesimos.
            _quantidade_snapshot_legado(getattr(linha, "quantidade", 0)),
            _moeda(getattr(linha, "preco_unitario", 0)),
        )

    def assinatura_fotografia(fotografia):
        return (
            fotografia.get("produto_id"),
            _quantidade_snapshot_legado(fotografia.get("quantidade", 0)),
            _moeda(fotografia.get("preco_unitario", 0)),
        )

    chave = assinatura(item)
    if sum(assinatura(linha) == chave for linha in itens_venda) != 1:
        return None
    indices = [
        indice
        for indice, fotografia in enumerate(itens_snapshot)
        if assinatura_fotografia(fotografia) == chave
    ]
    if len(indices) == 1:
        return indices[0]
    if len(itens_venda) == len(itens_snapshot) == 1:
        return 0
    return None


def _rateio_grupo_snapshot_sem_ids(
    item: VendaItem, itens_venda: list[VendaItem], itens_snapshot: list[dict]
) -> tuple[Decimal, Decimal] | None:
    """Rateia apenas na DRE custo agregado de linhas legadas indistinguiveis."""
    if any(
        fotografia.get("venda_item_id") is not None for fotografia in itens_snapshot
    ):
        return None
    chave = (
        getattr(item, "produto_id", None),
        _quantidade_snapshot_legado(getattr(item, "quantidade", 0)),
        _moeda(getattr(item, "preco_unitario", 0)),
    )
    grupo_itens = sorted(
        (
            linha
            for linha in itens_venda
            if (
                getattr(linha, "produto_id", None),
                _quantidade_snapshot_legado(getattr(linha, "quantidade", 0)),
                _moeda(getattr(linha, "preco_unitario", 0)),
            )
            == chave
        ),
        key=lambda linha: getattr(linha, "id", 0) or 0,
    )
    grupo_fotografias = [
        fotografia
        for fotografia in itens_snapshot
        if (
            fotografia.get("produto_id"),
            _quantidade_snapshot_legado(fotografia.get("quantidade", 0)),
            _moeda(fotografia.get("preco_unitario", 0)),
        )
        == chave
    ]
    if len(grupo_itens) < 2 or len(grupo_itens) != len(grupo_fotografias):
        return None
    custo_grupo = sum(
        (_moeda(fotografia.get("custo_total", 0)) for fotografia in grupo_fotografias),
        Decimal("0"),
    )
    indice = grupo_itens.index(item)
    quantidade_linhas = Decimal(len(grupo_itens))
    parcela = _moeda(custo_grupo * (indice + 1) / quantidade_linhas) - _moeda(
        custo_grupo * indice / quantidade_linhas
    )
    return parcela, custo_grupo


def _rateio_cmv_agregado_legado(
    venda: Venda, snapshot: Dict[str, Any]
) -> Dict[int, Decimal] | None:
    """Atribui apenas na DRE um total legado sem custo suficiente por linha.

    Nao comprova custo historico para entrada no estoque. O total ja integra o
    CMV da venda; distribui-lo evita somar uma segunda estimativa e permite
    estorno cumulativo por item, inclusive em devolucoes de outro mes.
    """
    itens = list(getattr(venda, "itens", []) or [])
    if not itens or any(
        str(getattr(item, "tipo", "") or "").lower() == "servico" for item in itens
    ):
        return None
    custo_total = _moeda(snapshot.get("custo_produtos", 0))
    if custo_total <= 0:
        return None
    fotografias = snapshot.get("itens")
    fotografias_validas = (
        isinstance(fotografias, list)
        and len(fotografias) == len(itens)
        and all(isinstance(fotografia, dict) for fotografia in fotografias)
    )
    custo_itens = (
        sum(
            (_moeda(fotografia.get("custo_total", 0)) for fotografia in fotografias),
            Decimal("0"),
        )
        if fotografias_validas
        else Decimal("0")
    )
    if fotografias_validas and custo_itens >= custo_total:
        return None

    ordenados = sorted(itens, key=lambda item: getattr(item, "id", 0) or 0)
    pesos = [
        max(
            _decimal(getattr(item, "subtotal", 0)),
            _decimal(getattr(item, "quantidade", 0))
            * _decimal(getattr(item, "preco_unitario", 0)),
            Decimal("0"),
        )
        for item in ordenados
    ]
    if sum(pesos) <= 0:
        pesos = [Decimal("1") for _ in ordenados]
    total_pesos = sum(pesos)
    acumulado = Decimal("0")
    anterior = Decimal("0")
    atribuicoes = {}
    for item, peso in zip(ordenados, pesos):
        acumulado += peso
        atual = _moeda(custo_total * acumulado / total_pesos)
        atribuicoes[id(item)] = atual - anterior
        anterior = atual
    return atribuicoes


def _complementar_snapshot_com_custos_reais(
    venda: Venda,
    snapshot: Dict[str, Any],
    estoque_custos_por_produto: Dict[int, Dict[str, float]],
    tenant_id: str | None = None,
) -> Dict[str, Any]:
    """Prefere o comprovante da baixa e completa custos zerados na DRE."""
    itens_venda = list(getattr(venda, "itens", []) or [])
    itens_snapshot_originais = snapshot.get("itens")
    if (
        not isinstance(itens_snapshot_originais, list)
        or not itens_venda
        or len(itens_snapshot_originais) != len(itens_venda)
    ):
        return snapshot

    itens_snapshot = [
        dict(item) if isinstance(item, dict) else {}
        for item in itens_snapshot_originais
    ]
    custo_original = _moeda(snapshot.get("custo_produtos", 0))
    custo_itens_originais = sum(
        (_moeda(item.get("custo_total", 0)) for item in itens_snapshot), Decimal("0")
    )
    if custo_original > custo_itens_originais and not any(
        getattr(item, "custo_original_saida", None) for item in itens_venda
    ):
        # Um total agregado legado ja integra a DRE. O custo atual do cadastro
        # nao pode substitui-lo retroativamente nem justificar custo de estoque.
        return snapshot
    custo_adicional = Decimal("0")
    custo_comprovado_ajustado = False

    for item in itens_venda:
        indice = _indice_snapshot_item(item, itens_venda, itens_snapshot)
        if indice is None:
            continue
        item_snapshot = itens_snapshot[indice]
        if tenant_id is not None and getattr(item, "custo_original_saida", None):
            custo_comprovado, _origem, pendente = custo_original_item_devolvido(
                None,
                venda,
                item,
                _decimal(getattr(item, "quantidade", 0)),
                tenant_id,
            )
            if not pendente and custo_comprovado > 0:
                quantidade = _decimal(getattr(item, "quantidade", 0))
                item_snapshot["custo_total"] = float(custo_comprovado)
                item_snapshot["custo_unitario"] = float(
                    _moeda(custo_comprovado / quantidade)
                )
                item_snapshot["custo_origem_complemento_dre"] = "baixa_estoque_venda"
                custo_comprovado_ajustado = True
                continue
        if _decimal(item_snapshot.get("custo_total", 0)) > Decimal("0.004"):
            continue

        custo_real, origem = _custo_confirmado_atual_item(
            item, estoque_custos_por_produto
        )
        if custo_real <= Decimal("0.004"):
            continue

        quantidade = _decimal(getattr(item, "quantidade", 0))
        item_snapshot["custo_total"] = float(custo_real)
        item_snapshot["custo_unitario"] = (
            float(_moeda(custo_real / quantidade)) if quantidade > 0 else 0.0
        )
        item_snapshot["custo_origem_complemento_dre"] = origem
        custo_adicional += custo_real

    custo_itens = sum(
        (_moeda(item.get("custo_total", 0)) for item in itens_snapshot),
        Decimal("0"),
    )
    if custo_itens <= 0 or (
        custo_adicional <= 0
        and not custo_comprovado_ajustado
        and custo_itens == custo_original
    ):
        return snapshot

    snapshot_ajustado = dict(snapshot)
    snapshot_ajustado["itens"] = itens_snapshot
    # Fotografias antigas podem ter custo nos itens e total zerado. A soma dos
    # itens é a mesma base usada ao criar a fotografia e evita omitir esse CMV.
    snapshot_ajustado["custo_produtos"] = float(custo_itens)
    snapshot_ajustado["custo_complementado_dre"] = float(
        _moeda(custo_itens - custo_original)
    )
    return snapshot_ajustado


def _conciliar_custo_campanha_snapshot(
    snapshot: Dict[str, Any] | None,
    custo_campanha: float,
    cupom_desconto: float,
    desconto_bruto: Any,
) -> Dict[str, Any] | None:
    """Reclassifica desconto/campanha sem recalcular outros custos historicos."""
    if snapshot is None:
        return None
    custo_ledger = _moeda(custo_campanha)
    cupom_atual = _moeda(cupom_desconto)
    desconto_total = _moeda(
        max(
            _moeda(desconto_bruto) - min(cupom_atual, _moeda(desconto_bruto)),
            Decimal("0"),
        )
    )
    if (
        _moeda(snapshot.get("custo_campanha", 0)) == custo_ledger
        and _moeda(snapshot.get("cupom_desconto", 0)) == cupom_atual
        and _moeda(snapshot.get("desconto", 0)) == desconto_total
    ):
        return snapshot
    ajustado = dict(snapshot)
    ajustado["custo_campanha"] = float(custo_ledger)
    ajustado["cupom_desconto"] = float(cupom_atual)
    ajustado["desconto"] = float(desconto_total)
    ajustado["custo_campanha_origem_dre"] = "ledger_campanha_cupom"
    return ajustado


def _separar_custo_produto_servico(
    venda: Venda, snapshot: Dict[str, Any]
) -> tuple[Decimal, Decimal]:
    """Classifica o custo da venda sem alterar sua fotografia financeira."""
    custo_total = _moeda(snapshot.get("custo_produtos", 0))
    itens_venda = list(getattr(venda, "itens", []) or [])
    if not itens_venda:
        return custo_total, Decimal("0")

    tipos = [str(getattr(item, "tipo", "") or "").lower() for item in itens_venda]
    if all(tipo == "servico" for tipo in tipos):
        return Decimal("0"), custo_total
    if "servico" not in tipos:
        return custo_total, Decimal("0")

    itens_snapshot = snapshot.get("itens")
    if not isinstance(itens_snapshot, list) or len(itens_snapshot) != len(itens_venda):
        return custo_total, Decimal("0")

    # Fotografias antigas não guardam o tipo. Prefere a ordem original dos
    # itens; se a consulta vier em outra ordem, usa o produto quando seu tipo
    # for inequívoco nesta venda.
    if any(not isinstance(item_snapshot, dict) for item_snapshot in itens_snapshot):
        return custo_total, Decimal("0")
    if any(
        item_snapshot.get("produto_id") != getattr(item, "produto_id", None)
        for item, item_snapshot in zip(itens_venda, itens_snapshot)
    ):
        tipos_por_produto: Dict[int | None, set[str]] = {}
        for item, tipo in zip(itens_venda, tipos):
            tipos_por_produto.setdefault(getattr(item, "produto_id", None), set()).add(
                tipo
            )
        tipos_snapshot = [
            tipos_por_produto.get(item_snapshot.get("produto_id"), set())
            for item_snapshot in itens_snapshot
        ]
        if any(len(tipos_item) != 1 for tipos_item in tipos_snapshot):
            return custo_total, Decimal("0")
        tipos = [next(iter(tipos_item)) for tipos_item in tipos_snapshot]

    custo_servicos = sum(
        (
            _moeda(item_snapshot.get("custo_total", 0))
            for tipo, item_snapshot in zip(tipos, itens_snapshot)
            if tipo == "servico"
        ),
        Decimal("0"),
    )
    custo_servicos = min(max(custo_servicos, Decimal("0")), custo_total)
    return custo_total - custo_servicos, custo_servicos


def _registrar_base_estimativa_cmv(
    venda: Venda,
    canal: str,
    snapshot: Dict[str, Any],
    bases_por_canal: Dict[str, Dict[str, Decimal]],
    pendencias_por_canal: Dict[str, List[Dict[str, Any]]],
    custos_atribuidos: List[Dict[str, Any]],
) -> None:
    """Separa itens com custo confirmado dos produtos que ainda precisam de estimativa."""
    itens_venda = list(getattr(venda, "itens", []) or [])
    itens_snapshot = snapshot.get("itens")
    if not isinstance(itens_snapshot, list):
        itens_snapshot = []
    snapshot_completo = len(itens_snapshot) == len(itens_venda) and all(
        isinstance(fotografia, dict) for fotografia in itens_snapshot
    )
    custo_agregado = _rateio_cmv_agregado_legado(venda, snapshot)
    custo_itens = (
        sum(
            (_moeda(fotografia.get("custo_total", 0)) for fotografia in itens_snapshot),
            Decimal("0"),
        )
        if snapshot_completo
        else Decimal("0")
    )
    custo_sem_rateio = (
        custo_agregado is None
        and _moeda(snapshot.get("custo_produtos", 0)) > custo_itens
        and any(
            str(getattr(item, "tipo", "") or "").lower() != "servico"
            for item in itens_venda
        )
    )

    base = bases_por_canal.setdefault(
        canal,
        {"receita_confirmada": Decimal("0"), "custo_confirmado": Decimal("0")},
    )
    pendencias = pendencias_por_canal.setdefault(canal, [])
    if custo_sem_rateio:
        custos_atribuidos.append(
            {
                "venda_id": getattr(venda, "id", None),
                "venda_item_id": None,
                "valor_cmv_atribuido": 0.0,
                "custo_total_sem_rateio": float(
                    _moeda(snapshot.get("custo_produtos", 0)) - custo_itens
                ),
                "conciliacao_pendente": True,
            }
        )

    for item in itens_venda:
        if str(getattr(item, "tipo", "") or "").lower() == "servico":
            continue

        indice = (
            _indice_snapshot_item(item, itens_venda, itens_snapshot)
            if snapshot_completo and custo_agregado is None
            else None
        )
        rateio_ambiguo = False
        if custo_agregado is not None:
            custo_rateado = custo_agregado[id(item)]
            item_snapshot = {
                "venda_bruta": getattr(item, "subtotal", 0),
                "custo_total": custo_rateado,
            }
            custo_grupo = _moeda(snapshot.get("custo_produtos", 0))
            rateio_ambiguo = True
        elif indice is None and snapshot_completo:
            grupo = _rateio_grupo_snapshot_sem_ids(item, itens_venda, itens_snapshot)
            if grupo is None:
                if not custo_sem_rateio:
                    continue
                item_snapshot = {"venda_bruta": getattr(item, "subtotal", 0)}
                custo_grupo = Decimal("0")
            else:
                custo_rateado, custo_grupo = grupo
                item_snapshot = {
                    "venda_bruta": getattr(item, "subtotal", None)
                    or _decimal(getattr(item, "quantidade", 0))
                    * _decimal(getattr(item, "preco_unitario", 0)),
                    "custo_total": custo_rateado,
                }
                rateio_ambiguo = True
        elif indice is not None:
            item_snapshot = itens_snapshot[indice]
            custo_grupo = Decimal("0")
        else:
            # Fotografia incompleta sem CMV agregado: ainda estimar o produto
            # vendido pela linha real, sem inventar custo historico.
            item_snapshot = {"venda_bruta": getattr(item, "subtotal", 0)}
            custo_grupo = Decimal("0")

        valor_venda = _moeda(
            item_snapshot.get("venda_bruta", getattr(item, "subtotal", 0))
        )
        produto = getattr(item, "produto", None)
        data_venda = getattr(venda, "data_venda", None)
        data_iso = None
        if data_venda:
            data_iso = (
                data_venda.date().isoformat()
                if hasattr(data_venda, "date")
                else data_venda.isoformat()
            )
        identificacao = {
            "venda_id": getattr(venda, "id", None),
            "venda_item_id": getattr(item, "id", None),
            "numero_venda": getattr(venda, "numero_venda", None),
            "data": data_iso,
            "produto_id": getattr(item, "produto_id", None),
            "produto_codigo": getattr(produto, "codigo", None),
            "produto_nome": getattr(produto, "nome", None) or "Produto removido",
            "quantidade": float(_decimal(getattr(item, "quantidade", 0))),
            "valor_venda": float(valor_venda),
            "canal": canal,
            "rateio_ambiguo": rateio_ambiguo,
        }
        custo_confirmado = _moeda(item_snapshot.get("custo_total", 0))
        if custo_sem_rateio and custo_confirmado <= 0:
            continue
        if custo_confirmado > Decimal("0.004") or (rateio_ambiguo and custo_grupo > 0):
            custos_atribuidos.append(
                {
                    **identificacao,
                    "valor_cmv_atribuido": float(custo_confirmado),
                    "rateio_ambiguo": rateio_ambiguo,
                }
            )
            if valor_venda > 0 and not rateio_ambiguo:
                base["receita_confirmada"] += valor_venda
                base["custo_confirmado"] += custo_confirmado
            continue

        pendencias.append({**identificacao, "valor_estimado": 0.0})


def _aplicar_estimativas_cmv(
    dados_por_canal: Dict[str, Dict],
    bases_por_canal: Dict[str, Dict[str, Decimal]],
    pendencias_por_canal: Dict[str, List[Dict[str, Any]]],
) -> None:
    """Estima somente na DRE usando a proporção ponderada de custos confirmados."""
    receita_global = sum(
        (base["receita_confirmada"] for base in bases_por_canal.values()),
        Decimal("0"),
    )
    custo_global = sum(
        (base["custo_confirmado"] for base in bases_por_canal.values()),
        Decimal("0"),
    )

    for canal, pendencias in pendencias_por_canal.items():
        if not pendencias:
            continue
        dados = dados_por_canal.setdefault(canal, _novo_canal())
        base = bases_por_canal.get(canal, {})
        receita_base = _decimal(base.get("receita_confirmada", 0))
        custo_base = _decimal(base.get("custo_confirmado", 0))
        origem_percentual = "mesmo_canal"

        if receita_base <= 0 or custo_base <= 0:
            receita_base = receita_global
            custo_base = custo_global
            origem_percentual = "todos_canais_periodo"

        percentual = (
            custo_base / receita_base
            if receita_base > 0 and custo_base > 0
            else Decimal("0")
        )
        if percentual <= 0:
            origem_percentual = "sem_base"

        total_estimado = Decimal("0")
        itens_estimados: List[Dict[str, Any]] = []
        for pendencia in pendencias:
            item_estimado = dict(pendencia)
            valor_estimado = _moeda(
                _decimal(pendencia.get("valor_venda", 0)) * percentual
            )
            item_estimado["valor_estimado"] = float(valor_estimado)
            item_estimado["percentual_custo"] = float(percentual * Decimal("100"))
            item_estimado["origem_percentual"] = origem_percentual
            itens_estimados.append(item_estimado)
            total_estimado += valor_estimado

        dados["cmv_estimado"] = _moeda(total_estimado)
        dados["itens_cmv_estimado"] = itens_estimados
        dados["percentual_cmv_estimado"] = percentual * Decimal("100")
        dados["origem_percentual_cmv_estimado"] = origem_percentual


def obter_vendas_por_canal(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> Dict:
    """Retorna vendas agrupadas por canal usando a fotografia de rentabilidade da venda."""
    inicio, fim = _periodo_meses(mes_inicial or mes, mes, ano, data_final)
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

    bases_estimativa: Dict[str, Dict[str, Decimal]] = {}
    pendencias_estimativa: Dict[str, List[Dict[str, Any]]] = {}

    for venda in vendas:
        canal = _normalizar_canal(getattr(venda, "canal", None))
        dados = dados_por_canal.setdefault(canal, _novo_canal())
        cupom_desconto = cupons_por_venda.get(venda.id, 0.0)
        custo_campanha = cupom_desconto + cashback_por_venda.get(venda.id, 0.0)
        snapshot = _conciliar_custo_campanha_snapshot(
            _snapshot_pronto(venda),
            custo_campanha,
            cupom_desconto,
            getattr(venda, "desconto_valor", 0),
        )
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
        snapshot = _complementar_snapshot_com_custos_reais(
            venda,
            snapshot,
            estoque_custos_por_venda.get(venda.id, {}),
            tenant_id,
        )
        _registrar_base_estimativa_cmv(
            venda,
            canal,
            snapshot,
            bases_estimativa,
            pendencias_estimativa,
            dados["itens_cmv_atribuido"],
        )

        receita_bruta = _decimal(snapshot.get("venda_bruta", 0))
        receita_produtos, receita_servicos = _separar_receita_produto_servico(
            venda, receita_bruta
        )
        cmv_produtos, custo_servicos = _separar_custo_produto_servico(venda, snapshot)

        dados["receita_produtos"] += receita_produtos
        dados["receita_servicos"] += receita_servicos
        dados["receita_frete"] += _decimal(snapshot.get("taxa_loja", 0))
        dados["descontos"] += _decimal(snapshot.get("desconto", 0))
        dados["impostos"] += _decimal(snapshot.get("imposto", 0))
        dados["cmv"] += cmv_produtos
        dados["custo_servicos"] += custo_servicos
        dados["taxas_cartao"] += _decimal(snapshot.get("taxa_cartao", 0))
        dados["repasse_entrega"] += _decimal(snapshot.get("taxa_entrega", 0))
        dados["taxa_operacional_entrega"] += _decimal(
            snapshot.get("taxa_operacional", 0)
        )
        dados["comissoes"] += _decimal(snapshot.get("comissao", 0))
        dados["campanhas"] += _decimal(snapshot.get("custo_campanha", 0))
        dados["vendas"].append(venda)

    _aplicar_estimativas_cmv(dados_por_canal, bases_estimativa, pendencias_estimativa)
    return dados_por_canal


def _devolucoes_periodo_query(db: Session, tenant_id: str, inicio, fim):
    return db.query(VendaDevolucao).filter(
        VendaDevolucao.tenant_id == tenant_id,
        VendaDevolucao.data_competencia >= inicio.date(),
        VendaDevolucao.data_competencia < fim.date(),
    )


def _estimativas_por_item(dados_canais: Dict[str, Dict]) -> Dict[tuple, Dict]:
    """Indexa o CMV exibido pela DRE quando a linha da venda é inequívoca."""
    estimativas = {}
    for dados in dados_canais.values():
        for campo, origem in (
            ("itens_cmv_estimado", "estimativa"),
            ("itens_cmv_atribuido", "custo_atribuido_sem_comprovante"),
        ):
            for item in dados.get(campo, []) or []:
                venda_id = item.get("venda_id")
                venda_item_id = item.get("venda_item_id")
                if venda_id is not None and venda_item_id is not None:
                    estimativas[(venda_id, venda_item_id)] = {
                        **item,
                        "origem_cmv_estornado": origem,
                    }
    return estimativas


def _estornar_cmv_estimado_devolucoes(
    db: Session,
    tenant_id: str,
    inicio,
    fim,
    dados_canais: Dict[str, Dict],
    eventos_periodo: list[VendaDevolucao],
) -> None:
    """Estorna no mês da devolução o CMV provisório da linha original.

    A estimativa é dinâmica na DRE, então o estorno usa a mesma estimativa da
    venda. O rateio cumulativo fecha os centavos em devoluções parciais.
    """
    venda_ids = {
        evento.venda_id
        for evento in eventos_periodo
        if any(
            item.get("venda_item_id") is not None
            and item.get("custo_pendente")
            and item.get("tipo") == "produto"
            and not item.get("is_componente_kit")
            for item in (getattr(evento, "itens", None) or [])
        )
    }
    if not venda_ids:
        return

    vendas = (
        db.query(Venda)
        .filter(Venda.tenant_id == tenant_id, Venda.id.in_(venda_ids))
        .all()
    )
    vendas_por_id = {venda.id: venda for venda in vendas}
    estimativas_periodo = _estimativas_por_item(dados_canais)
    estimativas_por_mes = {}

    def estimativa_original(venda_id, venda_item_id):
        venda = vendas_por_id.get(venda_id)
        if venda is None or venda.data_venda is None:
            return None
        data_venda = (
            venda.data_venda.date()
            if hasattr(venda.data_venda, "date")
            else venda.data_venda
        )
        if inicio.date() <= data_venda < fim.date():
            return estimativas_periodo.get((venda_id, venda_item_id))
        chave_mes = (data_venda.year, data_venda.month)
        if chave_mes not in estimativas_por_mes:
            dados_mes = obter_vendas_por_canal(
                db, data_venda.month, data_venda.year, tenant_id
            )
            estimativas_por_mes[chave_mes] = _estimativas_por_item(dados_mes)
        return estimativas_por_mes[chave_mes].get((venda_id, venda_item_id))

    eventos_vendas = (
        db.query(VendaDevolucao)
        .filter(
            VendaDevolucao.tenant_id == tenant_id,
            VendaDevolucao.venda_id.in_(venda_ids),
        )
        .all()
    )
    ids_periodo = {evento.id for evento in eventos_periodo}
    quantidades_anteriores: Dict[tuple, Decimal] = {}
    for evento in sorted(
        eventos_vendas, key=lambda atual: (atual.data_competencia, atual.id)
    ):
        for item in evento.itens or []:
            venda_item_id = item.get("venda_item_id")
            if venda_item_id is None or item.get("is_componente_kit"):
                continue
            chave = (evento.venda_id, venda_item_id)
            quantidade = _decimal(item.get("quantidade", 0))
            anterior = quantidades_anteriores.get(chave, Decimal("0"))
            quantidades_anteriores[chave] = anterior + quantidade
            if (
                evento.id not in ids_periodo
                or item.get("tipo") != "produto"
                or not item.get("custo_pendente")
                or quantidade <= 0
            ):
                continue
            estimativa = estimativa_original(*chave)
            if not estimativa:
                continue
            quantidade_original = _decimal(estimativa.get("quantidade", 0))
            if quantidade_original <= 0 or anterior + quantidade > quantidade_original:
                continue
            custo_original_estimado = _moeda(
                estimativa.get(
                    "valor_estimado", estimativa.get("valor_cmv_atribuido", 0)
                )
            )
            estorno = _moeda(
                custo_original_estimado * (anterior + quantidade) / quantidade_original
            ) - _moeda(custo_original_estimado * anterior / quantidade_original)
            if estorno <= 0:
                continue
            canal = _normalizar_canal(evento.canal)
            dados = dados_canais.setdefault(canal, _novo_canal())
            dados["cmv_estimado"] -= estorno
            dados.setdefault("itens_cmv_estornado", []).append(
                {
                    **estimativa,
                    "devolucao_id": evento.id,
                    "data": evento.data_competencia.isoformat(),
                    "valor_estimado": -float(estorno),
                    "valor_venda": -float(_decimal(item.get("valor_devolvido", 0))),
                }
            )


def agregar_devolucoes_por_canal(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    dados_canais: Dict[str, Dict],
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> None:
    inicio, fim = _periodo_meses(mes_inicial or mes, mes, ano, data_final)
    devolucoes = _devolucoes_periodo_query(db, tenant_id, inicio, fim).all()
    for devolucao in devolucoes:
        canal = _normalizar_canal(devolucao.canal)
        dados = dados_canais.setdefault(canal, _novo_canal())
        dados["devolucoes"] += _moeda(devolucao.valor_devolvido)
        dados["cmv"] -= _moeda(devolucao.custo_produtos_estornado)
        dados["custo_servicos"] -= _moeda(devolucao.custo_servicos_estornado)
        if devolucao.custo_pendente:
            dados.setdefault("devolucoes_custo_pendente", []).append(devolucao)
    _estornar_cmv_estimado_devolucoes(
        db, tenant_id, inicio, fim, dados_canais, devolucoes
    )


def _contas_receber_manuais_query(db: Session, tenant_id: str, inicio, fim):
    """Receitas sem venda vinculada, para não duplicar o faturamento do PDV."""
    return (
        db.query(ContaReceber)
        .join(DRESubcategoria, ContaReceber.dre_subcategoria_id == DRESubcategoria.id)
        .join(DRECategoria, DRESubcategoria.categoria_id == DRECategoria.id)
        .filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.data_emissao >= inicio,
            ContaReceber.data_emissao < fim,
            ContaReceber.venda_id.is_(None),
            ContaReceber.status.notin_(("cancelado", "cancelada", "parcelado")),
            DRESubcategoria.tenant_id == tenant_id,
            DRECategoria.tenant_id == tenant_id,
            DRECategoria.natureza == NaturezaDRE.RECEITA,
        )
    )


def _valor_recebivel_competencia(conta: ContaReceber) -> Decimal:
    """Mantém a receita na emissão, sem juros ou descontos aplicados na baixa."""
    return _moeda(getattr(conta, "valor_original", 0))


def agregar_contas_receber_manuais_por_canal(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    dados_canais: Dict[str, Dict],
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> None:
    inicio, fim = _periodo_meses(mes_inicial or mes, mes, ano, data_final)
    for conta in _contas_receber_manuais_query(db, tenant_id, inicio, fim).all():
        canal = _normalizar_canal(getattr(conta, "canal", None))
        dados_canais.setdefault(canal, _novo_canal())["receita_outras"] += (
            _valor_recebivel_competencia(conta)
        )


def agregar_contas_pagar_por_canal(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    dados_canais: Dict[str, Dict],
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> None:
    """Agrega despesas por competencia. Sem canal informado vai para Loja Fisica."""
    inicio, fim = _periodo_meses(mes_inicial or mes, mes, ano, data_final)
    contas = (
        db.query(ContaPagar)
        .filter(*filtros_contas_pagar_dre(tenant_id, inicio, fim))
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

    tipos, categorias = classificacoes_contas_pagar(db, tenant_id, contas)
    frete_ids = ids_fretes_sobre_compras(db, tenant_id)
    contas_folha = []
    for conta in contas:
        if conta.dre_subcategoria_id in frete_ids or eh_compra_estoque(
            conta, tipos, categorias
        ):
            continue
        contas_folha.append(conta)
        subcategoria = subcategorias.get(getattr(conta, "dre_subcategoria_id", None))

        texto = _texto_conta(conta, subcategoria)
        campo = _classificar_conta_dre(texto)
        if campo != "taxas_marketplace" and _eh_custo_de_venda_ja_vindo_da_venda(texto):
            continue

        canal = _normalizar_canal(getattr(conta, "canal", None))
        dados = dados_canais.setdefault(canal, _novo_canal())
        dados[campo] += _conta_valor(conta)

    resumo_folha = calcular_resumo_folha_gerencial(
        db,
        mes,
        ano,
        tenant_id,
        contas_folha,
        subcategorias,
        mes_inicial=mes_inicial,
        data_final=data_final,
    )
    for canal, valor in resumo_folha["ajustes_por_canal"].items():
        if valor:
            dados_canais.setdefault(canal, _novo_canal())["despesas_pessoal"] += valor


def agregar_fretes_sobre_compras(
    db: Session,
    mes: int,
    ano: int,
    tenant_id: str,
    dados_canais: Dict[str, Dict],
    mes_inicial: Optional[int] = None,
    data_final: Optional[date] = None,
) -> None:
    inicio, fim = _periodo_meses(mes_inicial or mes, mes, ano, data_final)
    frete_ids = ids_fretes_sobre_compras(db, tenant_id)
    if not frete_ids:
        return

    contas = (
        db.query(ContaPagar)
        .filter(
            *filtros_contas_pagar_dre(tenant_id, inicio, fim),
            ContaPagar.dre_subcategoria_id.in_(frete_ids),
        )
        .all()
    )
    for conta in contas:
        canal = _normalizar_canal(getattr(conta, "canal", None))
        dados_canais.setdefault(canal, _novo_canal())["fretes_compras"] += _decimal(
            conta.valor_original
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
        snapshot = _conciliar_custo_campanha_snapshot(
            _snapshot_pronto(venda),
            custo_campanha,
            cupom_desconto,
            getattr(venda, "desconto_valor", 0),
        )
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
        snapshot = _complementar_snapshot_com_custos_reais(
            venda,
            snapshot,
            estoque_custos_por_venda.get(venda.id, {}),
            tenant_id,
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

    if campo in {"cmv", "custo_servicos"}:
        cmv_produtos, custo_servicos = _separar_custo_produto_servico(venda, snapshot)
        return cmv_produtos if campo == "cmv" else custo_servicos

    mapa_snapshot = {
        "receita_frete": "taxa_loja",
        "descontos": "desconto",
        "impostos": "imposto",
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
