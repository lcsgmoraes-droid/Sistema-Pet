"""Retorno do cancelamento vinculado as saidas e aos lotes originais.

Nao escolhe o FIFO atual, nao usa o custo atual e nao commita. O cancelamento
total trava a venda antes de preparar os produtos, movimentos e lotes.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import HTTPException

from app.estoque.devolucao_lotes import (
    _composicao,
    preparar_devolucao_lotes,
    recompor_lotes_devolucao,
)
from app.estoque.service import EstoqueService
from app.grupo_comercial_estoque_compartilhado_service import (
    contexto_tenant_estoque,
    resolver_tenant_estoque_item,
)
from app.produtos.tipos import tipo_controla_estoque
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.services.sales_channel import is_online_sales_channel
from app.vendas.fiscal_status import nota_fiscal_cancelada
from app.vendas.kit_estoque import tipo_kit_estoque

MOTIVO = "cancelamento_venda"
EPSILON = Decimal("0.000001")
CENTAVO = Decimal("0.01")


def _inconsistente():
    raise HTTPException(
        409,
        "A baixa original, os lotes ou um retorno anterior precisam de conciliacao antes de cancelar a venda.",
    )


def _numero(value, *, positivo=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        _inconsistente()
    if not result.is_finite() or result < 0 or (positivo and result <= 0):
        _inconsistente()
    return result


def _validar_saldo_fisico(value):
    """Um saldo negativo conhecido e real; ausencia e nao finitos nao sao zero."""
    try:
        saldo = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        _inconsistente()
    if not saldo.is_finite():
        _inconsistente()


def _moeda(value):
    return value.quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass
class RetornoItem:
    tenant_estoque: object
    produto_id: int
    quantidade: Decimal
    custo_total: Decimal | None
    plano_lotes: object = None
    compartilhado: bool = False


def _prova_item(venda, item, saidas_por_id, tenant_estoque):
    proof = getattr(item, "custo_original_saida", None)
    if proof is None:
        return None, None
    if not isinstance(proof, dict) or any(
        type(proof.get(key)) is not int
        for key in (
            "versao",
            "venda_id",
            "venda_item_id",
            "produto_id",
            "movimentacao_id",
        )
    ):
        _inconsistente()
    if (
        proof["versao"] != 1
        or proof.get("origem") != "baixa_estoque_venda"
        or proof["venda_id"] != venda.id
        or proof["venda_item_id"] != item.id
        or proof["produto_id"] != item.produto_id
        or str(proof.get("tenant_estoque_id")) != str(tenant_estoque)
    ):
        _inconsistente()
    captured = proof.get("capturado_em")
    try:
        if not isinstance(captured, str) or "T" not in captured:
            raise ValueError
        datetime.fromisoformat(captured.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        _inconsistente()
    saida = saidas_por_id.get(proof["movimentacao_id"])
    if (
        saida is None
        or _numero(proof.get("quantidade"), positivo=True)
        != _numero(item.quantidade, positivo=True)
        or abs(_numero(saida.quantidade, positivo=True) - _numero(item.quantidade))
        > EPSILON
    ):
        _inconsistente()
    custo = proof.get("custo_total")
    return saida, _numero(custo) if custo is not None else None


def _custo_saida(saida, comprovado=None):
    """Zero sem comprovante e desconhecido; custo atual nunca e um fallback."""
    total = getattr(saida, "valor_total", None)
    unitario = getattr(saida, "custo_unitario", None)
    total = _numero(total) if total is not None else None
    unitario = _numero(unitario) if unitario is not None else None
    quantidade = _numero(saida.quantidade, positivo=True)
    if total is not None and unitario is not None:
        if abs(_moeda(unitario * quantidade) - _moeda(total)) > CENTAVO:
            _inconsistente()
    if comprovado is not None:
        if total is not None and _moeda(total) != _moeda(comprovado):
            _inconsistente()
        if (
            unitario is not None
            and abs(_moeda(unitario * quantidade) - _moeda(comprovado)) > CENTAVO
        ):
            _inconsistente()
        return _moeda(comprovado)
    if total is not None and total > 0:
        return _moeda(total)
    # A baixa legada convertia custo ausente em zero. Esse zero nao comprova
    # gratuidade nem pode ser convertido no novo custo do cadastro.
    return None


def _custos_sem_prova(itens, saidas):
    """Atribui apenas origens inequivocas; total do produto nao prova a linha."""
    custos_saidas = {saida.id: _custo_saida(saida) for saida in saidas}
    if len(itens) == 1:
        known = all(value is not None for value in custos_saidas.values())
        return {
            itens[0].id: sum(custos_saidas.values(), Decimal("0")) if known else None
        }
    if len(saidas) == 1 and saidas[0].custo_unitario is not None:
        # Uma unica saida com custo unitario congelado descreve a mesma unidade
        # para todas as parcelas; cotas cumulativas preservam o ultimo centavo.
        total = custos_saidas[saidas[0].id]
        quantidade = _numero(saidas[0].quantidade, positivo=True)
        acumulado = Decimal("0")
        custos = {}
        for item in sorted(itens, key=lambda row: row.id):
            anterior = acumulado
            acumulado += _numero(item.quantidade)
            custos[item.id] = (
                _moeda(total * acumulado / quantidade)
                - _moeda(total * anterior / quantidade)
                if total is not None
                else None
            )
        return custos
    candidatos = {}
    for item in itens:
        lote = getattr(item, "lote_id", None)
        candidatos[item.id] = [
            saida.id
            for saida in saidas
            if abs(_numero(saida.quantidade) - _numero(item.quantidade)) <= EPSILON
            and (lote is None or set(_composicao(saida)) == {lote})
        ]
    usos = defaultdict(int)
    for ids in candidatos.values():
        for saida_id in ids:
            usos[saida_id] += 1
    return {
        item.id: custos_saidas[candidatos[item.id][0]]
        if len(candidatos[item.id]) == 1 and usos[candidatos[item.id][0]] == 1
        else None
        for item in itens
    }


def _preparar_grupo(db, venda, itens, tenant_venda, tenant_estoque, produto_id):
    produto = (
        db.query(Produto)
        .filter_by(tenant_id=tenant_estoque, id=produto_id)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )
    if produto is None or not produto.controlar_estoque:
        _inconsistente()
    _validar_saldo_fisico(getattr(produto, "estoque_atual", None))
    tipo_kit = tipo_kit_estoque(produto)
    if produto.tipo_produto == "PAI" or (tipo_kit and tipo_kit != "FISICO"):
        # A composicao atual de um kit virtual nao e prova do consumo passado.
        _inconsistente()
    movimentos = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_estoque,
            EstoqueMovimentacao.produto_id == produto_id,
            EstoqueMovimentacao.referencia_id == venda.id,
            EstoqueMovimentacao.referencia_tipo.in_(("venda", "venda_bling")),
        )
        .order_by(EstoqueMovimentacao.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    if any(m.tipo == "entrada" and m.status != "cancelado" for m in movimentos):
        _inconsistente()
    cancelados_fiscais = [
        m
        for m in movimentos
        if m.tipo == "saida"
        and m.status == "cancelado"
        and m.referencia_tipo == "venda_bling"
    ]
    saidas = [m for m in movimentos if m.tipo == "saida" and m.status != "cancelado"]
    tem_prova = any(
        getattr(item, "custo_original_saida", None) is not None for item in itens
    )
    tem_lote_item = any(getattr(item, "lote_id", None) is not None for item in itens)
    tem_lote_historico = any(
        m.lote_id is not None or m.lotes_consumidos for m in movimentos
    )

    def tem_lotes_atuais():
        return (
            db.query(ProdutoLote.id)
            .filter_by(tenant_id=tenant_estoque, produto_id=produto_id)
            .first()
            is not None
        )

    if (
        cancelados_fiscais
        and nota_fiscal_cancelada(venda)
        and isinstance(getattr(venda, "nfe_bling_id", None), (str, int))
    ):
        # Compatibilidade com webhook fiscal antigo que ja devolveu o agregado.
        # O servico consumidor abate esse saldo uma unica vez. Nao inventar uma
        # segunda entrada nem presumir reparo de lote de um retorno sem prova.
        if tem_prova or tem_lote_item or tem_lote_historico or tem_lotes_atuais():
            _inconsistente()
        return {}
    if not saidas:
        if (
            bool(getattr(venda, "canal", None))
            and is_online_sales_channel(venda.canal)
            and not tem_prova
            and not tem_lote_item
            and not movimentos
        ):
            # Um lote existente hoje nao comprova uma saida no pedido online.
            return {
                item.id: RetornoItem(tenant_estoque, produto_id, Decimal("0"), None)
                for item in itens
            }
        tem_lote = tem_lotes_atuais()
        if tem_prova or tem_lote_item or tem_lote_historico or tem_lote or movimentos:
            _inconsistente()
        # Historico offline sem provas/saidas/lotes: manter a devolucao agregada
        # ja existente, identificando o custo como desconhecido no movimento.
        return {}
    if (
        not tem_prova
        and not tem_lote_item
        and not tem_lote_historico
        and tem_lotes_atuais()
    ):
        # Um historico legado sem composicao nao prova quais lotes consumiu.
        # Nao deixar uma entrada agregada ocultar uma divergencia ja existente.
        _inconsistente()
    quantidade = sum(
        (_numero(item.quantidade, positivo=True) for item in itens), Decimal("0")
    )
    if (
        abs(
            sum((_numero(m.quantidade, positivo=True) for m in saidas), Decimal("0"))
            - quantidade
        )
        > EPSILON
    ):
        _inconsistente()
    if any(m.motivo not in {"venda", "venda_bling"} for m in saidas):
        _inconsistente()
    saidas_por_id = {m.id: m for m in saidas}
    provas = {
        item.id: _prova_item(venda, item, saidas_por_id, tenant_estoque)
        for item in itens
    }
    ids_provados = [saida.id for saida, _ in provas.values() if saida is not None]
    if len(set(ids_provados)) != len(ids_provados):
        _inconsistente()
    if tem_prova and (
        len(ids_provados) != len(itens) or set(ids_provados) != set(saidas_por_id)
    ):
        _inconsistente()
    plano = preparar_devolucao_lotes(
        db,
        produto_id=produto_id,
        tenant_id=tenant_estoque,
        venda_id=venda.id,
        saidas=saidas,
        itens_venda=itens,
        quantidades_por_item={item.id: _numero(item.quantidade) for item in itens},
        bloquear=True,
        motivo_entrada=MOTIVO,
    )
    custos = {}
    if tem_prova:
        for item in itens:
            saida, prova_custo = provas[item.id]
            custos[item.id] = _custo_saida(saida, prova_custo)
    else:
        custos = _custos_sem_prova(itens, saidas)
    compartilhado = str(tenant_estoque) != str(tenant_venda)
    return {
        item.id: RetornoItem(
            tenant_estoque,
            produto_id,
            _numero(item.quantidade),
            custos[item.id],
            plano,
            compartilhado,
        )
        for item in itens
    }


def preparar_cancelamento_estoque(db, venda, itens, tenant_id):
    """Prepara todos os grupos antes da primeira alteracao de estoque/financeiro."""
    grupos = defaultdict(list)
    for item in itens:
        if item.produto_id and tipo_controla_estoque(item.tipo):
            # Validar antes dos caminhos legado, fiscal ou somente reserva: uma
            # quantidade corrompida nunca pode transformar entrada em saida.
            _numero(item.quantidade, positivo=True)
            if str(item.tenant_id) != str(tenant_id) or item.venda_id != venda.id:
                _inconsistente()
            tenant_estoque, _ = resolver_tenant_estoque_item(item, tenant_id)
            produto_id = getattr(item, "product_variation_id", None) or item.produto_id
            if produto_id != item.produto_id:
                # O modelo antigo pode apontar para o pai em vez da variacao.
                # Sem vinculo individual da baixa, nao atribuir estoque ao pai.
                _inconsistente()
            grupos[(str(tenant_estoque), produto_id)].append(item)
    resultados = {}
    for (tenant_estoque, produto_id), grupo in sorted(grupos.items()):
        with contexto_tenant_estoque(tenant_estoque, tenant_id) as tenant_estoque_uuid:
            resultados.update(
                _preparar_grupo(
                    db, venda, grupo, tenant_id, tenant_estoque_uuid, produto_id
                )
            )
    return resultados


def estornar_item_cancelamento(db, venda, item, plano, user_id, motivo):
    """Executa o retorno comprovado na transacao ja bloqueada do cancelamento."""
    if plano.quantidade == 0:
        return None
    with contexto_tenant_estoque(
        plano.tenant_estoque, venda.tenant_id
    ) as tenant_estoque:
        result = EstoqueService.estornar_estoque(
            produto_id=plano.produto_id,
            quantidade=plano.quantidade,
            motivo=MOTIVO,
            referencia_id=venda.id,
            referencia_tipo="venda",
            user_id=0 if plano.compartilhado else user_id,
            tenant_id=tenant_estoque,
            db=db,
            documento=venda.numero_venda,
            observacao=f"Cancelamento: {motivo}. Retorno vinculado a baixa original; tenant da venda {venda.tenant_id}.",
            custo_unitario_override=float(plano.custo_total / plano.quantidade)
            if plano.custo_total is not None
            else None,
            valor_total_override=float(plano.custo_total)
            if plano.custo_total is not None
            else None,
            preservar_custo_desconhecido=plano.custo_total is None,
        )
        recompor_lotes_devolucao(
            db,
            plano.plano_lotes,
            item.id,
            plano.quantidade,
            result["movimentacao_id"],
            motivo_entrada=MOTIVO,
        )
    return result
