from __future__ import annotations

# ruff: noqa: E402

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import func

import app.db.base  # noqa: F401
from app.db import SessionLocal
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoKitComponente
from app.integracao_bling_pedido_payload import (
    _montar_payload_pedido,
    _resumir_ultima_nf_do_pedido_bling,
    _situacao_codigo_bling,
)
from app.integracao_bling_pedido_routes import (
    _SITUACOES_PEDIDO_ATENDIDO,
    _SITUACOES_PEDIDO_CANCELADO,
)
from app.services.bling_flow_monitor_diagnostics import (
    _nf_contexto_autorizado,
    _ultima_nf,
)
from app.services.bling_flow_monitor_service import (
    registrar_evento,
    resolver_incidentes_relacionados,
)
from app.services.bling_nf_service import (
    _obter_usuario_padrao_tenant,
    _sincronizar_cache_estoque_virtual,
    buscar_produto_do_item,
    movimento_documentado_por_nf,
    movimento_legado_pedido_para_nf,
    produto_usa_composicao_virtual,
)
from app.services.kit_estoque_service import KitEstoqueService
from app.services.pedido_status_reconciliation_service import (
    _consultar_pedido_bling,
)
from app.tenancy.context import tenant_context


MOTIVO_DOCUMENTACAO_BALANCO = "venda_bling_conciliada_balanco"
CONFIRMACAO_APLICACAO = "APLICAR_RESERVAS_BLING"
INCIDENTES_RESOLVIDOS = (
    "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
    "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
    "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audita e reconcilia reservas de pedidos Bling com NF autorizada. "
            "O modo padrao e somente leitura."
        )
    )
    parser.add_argument(
        "--tenant-id",
        default=os.getenv("BLING_WEBHOOK_TENANT_ID"),
        help="UUID do tenant. Usa BLING_WEBHOOK_TENANT_ID quando omitido.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Limita a quantidade de pedidos analisados.",
    )
    parser.add_argument(
        "--preservar-saldo",
        action="append",
        default=[],
        metavar="SKU=SALDO",
        help=(
            "Confirma um saldo fisico que deve permanecer inalterado. "
            "Pode ser repetido."
        ),
    )
    parser.add_argument(
        "--atualizar-do-bling",
        action="store_true",
        help=(
            "Consulta no Bling os pedidos pendentes sem NF autorizada local "
            "antes de planejar a conciliacao."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica a reconciliacao. Sem esta flag, apenas audita.",
    )
    parser.add_argument(
        "--confirmar",
        default=None,
        help=f"Obrigatorio com --apply: {CONFIRMACAO_APLICACAO}",
    )
    return parser.parse_args()


def _texto(valor: Any) -> str | None:
    texto = str(valor or "").strip()
    return texto or None


def _parse_preservar_saldos(valores: list[str]) -> dict[str, float]:
    saldos: dict[str, float] = {}
    for valor in valores:
        sku, separador, saldo = str(valor or "").partition("=")
        sku = sku.strip()
        if not separador or not sku:
            raise ValueError(
                f"Valor invalido em --preservar-saldo: {valor!r}. Use SKU=SALDO."
            )
        saldos[sku] = float(saldo.replace(",", "."))
    return saldos


def _carregar_produtos_preservados(
    db,
    tenant_id,
    saldos_esperados: dict[str, float],
) -> dict[int, dict[str, Any]]:
    preservados: dict[int, dict[str, Any]] = {}
    for sku, saldo_esperado in saldos_esperados.items():
        produto = buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=sku)
        if not produto:
            raise ValueError(f"Produto preservado nao encontrado: {sku}")
        saldo_atual = float(produto.estoque_atual or 0)
        if abs(saldo_atual - saldo_esperado) > 0.000001:
            raise ValueError(
                f"Saldo fisico de {sku} divergiu: esperado {saldo_esperado}, "
                f"encontrado {saldo_atual}. Nenhuma alteracao foi aplicada."
            )
        preservados[int(produto.id)] = {
            "sku": sku,
            "saldo_esperado": saldo_esperado,
            "produto": produto,
        }
    return preservados


def _carregar_referencias_pendentes_sem_nf_autorizada(
    db,
    tenant_id,
    limite: int | None,
) -> list[dict[str, Any]]:
    pedidos = (
        db.query(PedidoIntegrado)
        .join(
            PedidoIntegradoItem,
            PedidoIntegradoItem.pedido_integrado_id == PedidoIntegrado.id,
        )
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegradoItem.tenant_id == tenant_id,
            PedidoIntegradoItem.liberado_em.is_(None),
            PedidoIntegradoItem.vendido_em.is_(None),
            PedidoIntegrado.pedido_bling_id.isnot(None),
            PedidoIntegrado.status.in_(("aberto", "confirmado", "expirado")),
        )
        .distinct()
        .order_by(PedidoIntegrado.criado_em.asc(), PedidoIntegrado.id.asc())
        .all()
    )
    referencias = [
        {
            "pedido_id": int(pedido.id),
            "pedido_bling_id": _texto(pedido.pedido_bling_id),
        }
        for pedido in pedidos
        if not _nf_contexto_autorizado(_ultima_nf(pedido.payload))
    ]
    db.rollback()
    if limite:
        referencias = referencias[: max(int(limite), 1)]
    return referencias


def _consultar_referencias_no_bling(
    referencias: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for referencia in referencias:
        snapshot = dict(referencia)
        try:
            pedido_remoto = _consultar_pedido_bling(str(referencia["pedido_bling_id"]))
            situacao = _situacao_codigo_bling((pedido_remoto or {}).get("situacao"))
            resumo_nf = _resumir_ultima_nf_do_pedido_bling(pedido_remoto)
            if situacao in _SITUACOES_PEDIDO_CANCELADO:
                classificacao = "cancelado"
            elif _nf_contexto_autorizado(resumo_nf):
                classificacao = "nf_autorizada"
            elif resumo_nf:
                classificacao = "nf_nao_autorizada"
            elif situacao in _SITUACOES_PEDIDO_ATENDIDO:
                classificacao = "atendido_sem_nf"
            else:
                classificacao = "aberto_ou_outro_sem_nf"
            snapshot.update(
                {
                    "classificacao": classificacao,
                    "pedido_remoto": pedido_remoto,
                    "situacao": situacao,
                    "resumo_nf": resumo_nf,
                }
            )
        except Exception as exc:
            snapshot.update(
                {
                    "classificacao": "erro",
                    "erro": str(exc),
                }
            )
        snapshots.append(snapshot)
    return snapshots


def _pedido_possui_saida_estoque(db, pedido: PedidoIntegrado) -> bool:
    return (
        db.query(EstoqueMovimentacao.id)
        .filter(
            EstoqueMovimentacao.tenant_id == pedido.tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .first()
        is not None
    )


def _aplicar_snapshot_bling(
    db,
    *,
    snapshot: dict[str, Any],
    aplicar: bool,
) -> str:
    pedido = (
        db.query(PedidoIntegrado)
        .filter(PedidoIntegrado.id == snapshot["pedido_id"])
        .first()
    )
    if not pedido:
        raise ValueError(f"Pedido local nao encontrado: {snapshot['pedido_id']}")

    payload_atual = pedido.payload if isinstance(pedido.payload, dict) else {}
    webhook_atual = (
        payload_atual.get("webhook")
        if isinstance(payload_atual.get("webhook"), dict)
        else None
    )
    pedido.payload = _montar_payload_pedido(
        webhook_data=webhook_atual,
        pedido_completo=snapshot["pedido_remoto"],
        payload_atual=pedido.payload,
        ultima_nf=snapshot.get("resumo_nf"),
    )
    db.add(pedido)

    classificacao = snapshot["classificacao"]
    if classificacao == "cancelado":
        if _pedido_possui_saida_estoque(db, pedido):
            if aplicar:
                db.commit()
            return "cancelado_com_saida_estoque_requer_revisao"
        agora = datetime.utcnow()
        itens = (
            db.query(PedidoIntegradoItem)
            .filter(
                PedidoIntegradoItem.pedido_integrado_id == pedido.id,
                PedidoIntegradoItem.liberado_em.is_(None),
                PedidoIntegradoItem.vendido_em.is_(None),
            )
            .all()
        )
        for item in itens:
            item.liberado_em = agora
            db.add(item)
        pedido.status = "cancelado"
        pedido.cancelado_em = pedido.cancelado_em or agora
        db.add(pedido)
        acao = "cancelado_sem_saida_reserva_liberada"
    elif classificacao == "atendido_sem_nf":
        pedido.status = "confirmado"
        db.add(pedido)
        acao = "atendido_aguardando_nf"
    else:
        pedido.status = "aberto"
        db.add(pedido)
        acao = (
            "nf_autorizada_pronta_para_conciliar"
            if classificacao == "nf_autorizada"
            else "reserva_mantida_sem_nf_autorizada"
        )

    if aplicar:
        db.commit()
    return acao


def _atualizar_pendencias_do_bling(
    db,
    *,
    tenant_id,
    limite: int | None,
    aplicar: bool,
) -> dict[str, Any]:
    referencias = _carregar_referencias_pendentes_sem_nf_autorizada(
        db,
        tenant_id,
        limite,
    )
    snapshots = _consultar_referencias_no_bling(referencias)
    contagem_classificacao = Counter(
        snapshot["classificacao"] for snapshot in snapshots
    )
    contagem_acoes: Counter[str] = Counter()
    erros: list[dict[str, Any]] = []

    for snapshot in snapshots:
        if snapshot["classificacao"] == "erro":
            erros.append(
                {
                    "pedido_id": snapshot["pedido_id"],
                    "pedido_bling_id": snapshot["pedido_bling_id"],
                    "erro": snapshot["erro"],
                }
            )
            continue
        try:
            acao = _aplicar_snapshot_bling(
                db,
                snapshot=snapshot,
                aplicar=aplicar,
            )
            contagem_acoes[acao] += 1
        except Exception as exc:
            if aplicar:
                db.rollback()
            erros.append(
                {
                    "pedido_id": snapshot["pedido_id"],
                    "pedido_bling_id": snapshot["pedido_bling_id"],
                    "erro": str(exc),
                }
            )

    if not aplicar:
        db.flush()
    return {
        "pedidos_consultados": len(snapshots),
        "classificacoes": dict(contagem_classificacao),
        "acoes": dict(contagem_acoes),
        "pedidos_com_erro": len(erros),
        "erros": erros,
    }


def _carregar_pedidos_e_itens_ativos(db, tenant_id, limite: int | None):
    query = (
        db.query(PedidoIntegrado, PedidoIntegradoItem)
        .join(
            PedidoIntegradoItem,
            PedidoIntegradoItem.pedido_integrado_id == PedidoIntegrado.id,
        )
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegradoItem.tenant_id == tenant_id,
            PedidoIntegradoItem.liberado_em.is_(None),
            PedidoIntegradoItem.vendido_em.is_(None),
        )
        .order_by(PedidoIntegrado.criado_em.asc(), PedidoIntegrado.id.asc())
    )
    linhas = query.all()

    agrupados: dict[int, dict[str, Any]] = {}
    for pedido, item in linhas:
        if not _nf_contexto_autorizado(_ultima_nf(pedido.payload)):
            continue
        bucket = agrupados.setdefault(
            int(pedido.id),
            {"pedido": pedido, "itens": []},
        )
        bucket["itens"].append(item)

    pedidos = list(agrupados.values())
    if limite:
        pedidos = pedidos[: max(int(limite), 1)]
    return pedidos


def _ultimos_balancos_por_produto(db, tenant_id) -> dict[int, datetime]:
    rows = (
        db.query(
            EstoqueMovimentacao.produto_id,
            func.max(EstoqueMovimentacao.created_at),
        )
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.motivo == "balanco",
            EstoqueMovimentacao.status != "cancelado",
        )
        .group_by(EstoqueMovimentacao.produto_id)
        .all()
    )
    return {
        int(produto_id): criado_em
        for produto_id, criado_em in rows
        if produto_id and criado_em
    }


def _alvos_fisicos_item(
    db,
    *,
    tenant_id,
    item: PedidoIntegradoItem,
    cache_componentes: dict[int, list[ProdutoKitComponente]],
    cache_produtos: dict[int, Produto],
) -> tuple[Produto | None, list[dict[str, Any]]]:
    produto_item = buscar_produto_do_item(
        db=db,
        tenant_id=tenant_id,
        sku=item.sku,
    )
    if not produto_item:
        return None, []

    quantidade_item = float(item.quantidade or 0)
    if not produto_usa_composicao_virtual(produto_item):
        return produto_item, [
            {
                "produto": produto_item,
                "quantidade": quantidade_item,
                "origem": "direta",
            }
        ]

    componentes = cache_componentes.get(int(produto_item.id))
    if componentes is None:
        componentes = (
            db.query(ProdutoKitComponente)
            .filter(
                ProdutoKitComponente.tenant_id == tenant_id,
                ProdutoKitComponente.kit_id == produto_item.id,
            )
            .all()
        )
        cache_componentes[int(produto_item.id)] = componentes

    alvos: list[dict[str, Any]] = []
    for componente in componentes:
        produto_id = int(componente.produto_componente_id)
        produto_componente = cache_produtos.get(produto_id)
        if produto_componente is None:
            produto_componente = (
                db.query(Produto)
                .filter(
                    Produto.tenant_id == tenant_id,
                    Produto.id == produto_id,
                )
                .first()
            )
            if produto_componente:
                cache_produtos[produto_id] = produto_componente
        if not produto_componente:
            return produto_item, []
        alvos.append(
            {
                "produto": produto_componente,
                "quantidade": quantidade_item * float(componente.quantidade or 0),
                "origem": "componente_kit_virtual",
                "kit_id": int(produto_item.id),
            }
        )
    return produto_item, alvos


def _movimentos_nf_pedido(
    db,
    *,
    pedido: PedidoIntegrado,
    nf_numero: str | None,
    nf_bling_id: str | None,
) -> tuple[dict[int, list[EstoqueMovimentacao]], dict[int, list[EstoqueMovimentacao]]]:
    movimentos = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == pedido.tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )
    documentados: dict[int, list[EstoqueMovimentacao]] = defaultdict(list)
    legados: dict[int, list[EstoqueMovimentacao]] = defaultdict(list)
    for movimento in movimentos:
        produto_id = int(movimento.produto_id)
        if movimento_documentado_por_nf(
            movimento,
            nf_numero=nf_numero,
            nf_bling_id=nf_bling_id,
        ):
            documentados[produto_id].append(movimento)
        elif movimento_legado_pedido_para_nf(
            movimento,
            pedido_bling_numero=pedido.pedido_bling_numero,
            nf_numero=nf_numero,
            nf_bling_id=nf_bling_id,
        ):
            legados[produto_id].append(movimento)
    return documentados, legados


def _consumir_movimento(
    filas: dict[int, list[EstoqueMovimentacao]],
    produto_id: int,
) -> EstoqueMovimentacao | None:
    fila = filas.get(produto_id) or []
    return fila.pop(0) if fila else None


def _planejar_pedido(
    db,
    *,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    ultimos_balancos: dict[int, datetime],
    produtos_preservados: dict[int, dict[str, Any]],
    cache_componentes: dict[int, list[ProdutoKitComponente]],
    cache_produtos: dict[int, Produto],
) -> dict[str, Any]:
    nf = _ultima_nf(pedido.payload)
    nf_bling_id = _texto(nf.get("id") or nf.get("nfe_id"))
    nf_numero = _texto(nf.get("numero"))
    documentados, legados = _movimentos_nf_pedido(
        db,
        pedido=pedido,
        nf_numero=nf_numero,
        nf_bling_id=nf_bling_id,
    )

    plano = {
        "pedido": pedido,
        "itens": itens,
        "nf_bling_id": nf_bling_id,
        "nf_numero": nf_numero,
        "acoes": [],
        "erros": [],
    }
    for item in itens:
        produto_item, alvos = _alvos_fisicos_item(
            db,
            tenant_id=pedido.tenant_id,
            item=item,
            cache_componentes=cache_componentes,
            cache_produtos=cache_produtos,
        )
        if not produto_item:
            plano["erros"].append(f"SKU sem produto local: {item.sku}")
            continue
        if not alvos:
            plano["erros"].append(
                f"SKU sem alvos fisicos validos: {item.sku} ({produto_item.id})"
            )
            continue

        for alvo in alvos:
            produto = alvo["produto"]
            produto_id = int(produto.id)
            movimento = _consumir_movimento(documentados, produto_id)
            origem_movimento = "existente_nf"
            if not movimento:
                movimento = _consumir_movimento(legados, produto_id)
                origem_movimento = "existente_legado"

            if movimento:
                plano["acoes"].append(
                    {
                        "acao": origem_movimento,
                        "item": item,
                        "produto": produto,
                        "quantidade": float(alvo["quantidade"]),
                        "movimento": movimento,
                    }
                )
                continue

            ultimo_balanco = ultimos_balancos.get(produto_id)
            preservar = produto_id in produtos_preservados or bool(
                ultimo_balanco
                and pedido.criado_em
                and ultimo_balanco >= pedido.criado_em
            )
            plano["acoes"].append(
                {
                    "acao": (
                        "documentar_por_balanco" if preservar else "baixar_estoque"
                    ),
                    "item": item,
                    "produto": produto,
                    "quantidade": float(alvo["quantidade"]),
                    "ultimo_balanco": ultimo_balanco,
                    "preservacao_explicita": produto_id in produtos_preservados,
                }
            )
    return plano


def _normalizar_movimento_legado(
    db,
    movimento: EstoqueMovimentacao,
    *,
    nf_numero: str | None,
    nf_bling_id: str | None,
) -> None:
    if nf_numero:
        movimento.documento = nf_numero
        movimento.observacao = f"Baixa automatica via NF {nf_numero}"
    elif nf_bling_id:
        movimento.observacao = f"Baixa automatica via NF Bling #{nf_bling_id}"
    db.add(movimento)


def _documentar_saida_ja_absorvida_por_balanco(
    db,
    *,
    pedido: PedidoIntegrado,
    produto: Produto,
    quantidade: float,
    user_id: int,
    nf_numero: str | None,
    nf_bling_id: str | None,
    ultimo_balanco: datetime | None,
) -> EstoqueMovimentacao:
    saldo_atual = float(produto.estoque_atual or 0)
    documento = nf_numero or nf_bling_id
    movimento = EstoqueMovimentacao(
        tenant_id=pedido.tenant_id,
        produto_id=produto.id,
        tipo="saida",
        motivo=MOTIVO_DOCUMENTACAO_BALANCO,
        quantidade=float(quantidade),
        quantidade_anterior=saldo_atual,
        quantidade_nova=saldo_atual,
        custo_unitario=float(produto.preco_custo or 0),
        valor_total=float(quantidade) * float(produto.preco_custo or 0),
        documento=documento,
        referencia_id=pedido.id,
        referencia_tipo="pedido_integrado",
        status="confirmado",
        observacao=(
            f"Venda da NF {documento or 'sem numero'} documentada sem nova baixa: "
            "o saldo fisico ja foi consolidado por balanco posterior"
            + (
                f" em {ultimo_balanco.isoformat()}"
                if ultimo_balanco
                else " confirmado explicitamente"
            )
        ),
        user_id=user_id,
    )
    db.add(movimento)
    db.flush()
    return movimento


def _baixar_produto_fisico(
    db,
    *,
    pedido: PedidoIntegrado,
    produto: Produto,
    quantidade: float,
    user_id: int,
    nf_numero: str | None,
    nf_bling_id: str | None,
) -> None:
    from app.estoque.service import EstoqueService

    documento = nf_numero or nf_bling_id
    EstoqueService.baixar_estoque(
        produto_id=produto.id,
        quantidade=float(quantidade),
        motivo="venda_bling",
        referencia_id=pedido.id,
        referencia_tipo="pedido_integrado",
        user_id=user_id,
        db=db,
        tenant_id=pedido.tenant_id,
        documento=documento,
        observacao=(
            f"Baixa reconciliada via NF {nf_numero}"
            if nf_numero
            else f"Baixa reconciliada via NF Bling #{nf_bling_id}"
        ),
    )
    for kit_id in KitEstoqueService.recalcular_kits_que_usam_produto(db, produto.id):
        _sincronizar_cache_estoque_virtual(db, pedido.tenant_id, int(kit_id))


def _resumo_planos(planos: list[dict[str, Any]]) -> dict[str, Any]:
    resumo = {
        "pedidos": len(planos),
        "itens": sum(len(plano["itens"]) for plano in planos),
        "quantidade_itens": sum(
            float(item.quantidade or 0) for plano in planos for item in plano["itens"]
        ),
        "acoes": defaultdict(int),
        "quantidades": defaultdict(float),
        "produtos": {},
        "pedidos_com_erro": 0,
    }
    for plano in planos:
        if plano["erros"]:
            resumo["pedidos_com_erro"] += 1
        for acao in plano["acoes"]:
            nome_acao = acao["acao"]
            quantidade = float(acao["quantidade"] or 0)
            resumo["acoes"][nome_acao] += 1
            resumo["quantidades"][nome_acao] += quantidade
            produto = acao["produto"]
            produto_id = int(produto.id)
            produto_resumo = resumo["produtos"].setdefault(
                produto_id,
                {
                    "produto_id": produto_id,
                    "codigo": produto.codigo,
                    "nome": produto.nome,
                    "saldo_atual": float(produto.estoque_atual or 0),
                    "acoes": defaultdict(int),
                    "quantidades": defaultdict(float),
                },
            )
            produto_resumo["acoes"][nome_acao] += 1
            produto_resumo["quantidades"][nome_acao] += quantidade

    resumo["acoes"] = dict(resumo["acoes"])
    resumo["quantidades"] = {
        chave: round(valor, 6) for chave, valor in resumo["quantidades"].items()
    }
    produtos = []
    for produto in resumo["produtos"].values():
        produto["acoes"] = dict(produto["acoes"])
        produto["quantidades"] = {
            chave: round(valor, 6) for chave, valor in produto["quantidades"].items()
        }
        produtos.append(produto)
    resumo["produtos"] = sorted(
        produtos,
        key=lambda item: (
            -sum(item["quantidades"].values()),
            str(item["codigo"] or ""),
        ),
    )
    return resumo


def _aplicar_planos(
    db,
    *,
    planos: list[dict[str, Any]],
    tenant_id,
    produtos_preservados: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    usuario = _obter_usuario_padrao_tenant(db=db, tenant_id=tenant_id)
    user_id = int(getattr(usuario, "id", 0) or 0)
    if not user_id:
        raise ValueError("Nenhum usuario valido para registrar movimentos de estoque.")

    aplicados = 0
    erros: list[dict[str, Any]] = []
    for plano in planos:
        pedido = plano["pedido"]
        if plano["erros"]:
            erros.append(
                {
                    "pedido_id": pedido.id,
                    "erros": list(plano["erros"]),
                }
            )
            continue
        try:
            for acao in plano["acoes"]:
                nome_acao = acao["acao"]
                if nome_acao == "existente_legado":
                    _normalizar_movimento_legado(
                        db,
                        acao["movimento"],
                        nf_numero=plano["nf_numero"],
                        nf_bling_id=plano["nf_bling_id"],
                    )
                elif nome_acao == "documentar_por_balanco":
                    _documentar_saida_ja_absorvida_por_balanco(
                        db,
                        pedido=pedido,
                        produto=acao["produto"],
                        quantidade=acao["quantidade"],
                        user_id=user_id,
                        nf_numero=plano["nf_numero"],
                        nf_bling_id=plano["nf_bling_id"],
                        ultimo_balanco=acao.get("ultimo_balanco"),
                    )
                elif nome_acao == "baixar_estoque":
                    _baixar_produto_fisico(
                        db,
                        pedido=pedido,
                        produto=acao["produto"],
                        quantidade=acao["quantidade"],
                        user_id=user_id,
                        nf_numero=plano["nf_numero"],
                        nf_bling_id=plano["nf_bling_id"],
                    )

            agora = datetime.utcnow()
            for item in plano["itens"]:
                item.vendido_em = agora
                db.add(item)
            pedido.status = "confirmado"
            pedido.confirmado_em = pedido.confirmado_em or agora
            db.add(pedido)
            registrar_evento(
                tenant_id=tenant_id,
                source="manutencao",
                event_type="reservas.reconciliadas",
                entity_type="pedido",
                status="ok",
                severity="info",
                message=(
                    "Reserva reconciliada com NF autorizada e protecao de "
                    "balancos fisicos posteriores."
                ),
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido.pedido_bling_id,
                nf_bling_id=plano["nf_bling_id"],
                payload={
                    "nf_numero": plano["nf_numero"],
                    "acoes": [acao["acao"] for acao in plano["acoes"]],
                },
                auto_fix_applied=True,
                db=db,
            )
            resolver_incidentes_relacionados(
                db,
                tenant_id=tenant_id,
                codes=INCIDENTES_RESOLVIDOS,
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido.pedido_bling_id,
                nf_bling_id=plano["nf_bling_id"],
                resolution_note=(
                    "Reserva e estoque reconciliados considerando balancos "
                    "fisicos posteriores."
                ),
            )
            for preservado in produtos_preservados.values():
                saldo_atual = float(preservado["produto"].estoque_atual or 0)
                saldo_esperado = float(preservado["saldo_esperado"])
                if abs(saldo_atual - saldo_esperado) > 0.000001:
                    raise RuntimeError(
                        f"Saldo preservado de {preservado['sku']} mudaria para "
                        f"{saldo_atual}; esperado {saldo_esperado}."
                    )
            db.commit()
            aplicados += 1
        except Exception as exc:
            db.rollback()
            erros.append(
                {
                    "pedido_id": pedido.id,
                    "erro": str(exc),
                }
            )
    return {
        "pedidos_aplicados": aplicados,
        "pedidos_com_erro": len(erros),
        "erros": erros,
    }


def executar(args: argparse.Namespace) -> dict[str, Any]:
    if not args.tenant_id:
        raise ValueError(
            "Tenant nao informado e BLING_WEBHOOK_TENANT_ID nao configurado."
        )
    tenant_id = UUID(str(args.tenant_id))
    saldos_esperados = _parse_preservar_saldos(args.preservar_saldo)
    if args.apply and args.confirmar != CONFIRMACAO_APLICACAO:
        raise ValueError(f"Para aplicar, informe --confirmar {CONFIRMACAO_APLICACAO}.")

    with tenant_context(tenant_id):
        db = SessionLocal()
        try:
            produtos_preservados = _carregar_produtos_preservados(
                db,
                tenant_id,
                saldos_esperados,
            )
            atualizacao_bling = None
            if args.atualizar_do_bling:
                atualizacao_bling = _atualizar_pendencias_do_bling(
                    db,
                    tenant_id=tenant_id,
                    limite=args.limite,
                    aplicar=args.apply,
                )
            pedidos = _carregar_pedidos_e_itens_ativos(
                db,
                tenant_id,
                args.limite,
            )
            ultimos_balancos = _ultimos_balancos_por_produto(db, tenant_id)
            cache_componentes: dict[int, list[ProdutoKitComponente]] = {}
            cache_produtos: dict[int, Produto] = {}
            planos = [
                _planejar_pedido(
                    db,
                    pedido=bucket["pedido"],
                    itens=bucket["itens"],
                    ultimos_balancos=ultimos_balancos,
                    produtos_preservados=produtos_preservados,
                    cache_componentes=cache_componentes,
                    cache_produtos=cache_produtos,
                )
                for bucket in pedidos
            ]
            resultado = {
                "modo": "apply" if args.apply else "dry_run",
                "tenant_id": str(tenant_id),
                "saldos_preservados": {
                    item["sku"]: item["saldo_esperado"]
                    for item in produtos_preservados.values()
                },
                "resumo": _resumo_planos(planos),
            }
            if atualizacao_bling is not None:
                resultado["atualizacao_bling"] = atualizacao_bling
            if args.apply:
                resultado["aplicacao"] = _aplicar_planos(
                    db,
                    planos=planos,
                    tenant_id=tenant_id,
                    produtos_preservados=produtos_preservados,
                )
                for item in produtos_preservados.values():
                    db.refresh(item["produto"])
                    saldo_final = float(item["produto"].estoque_atual or 0)
                    if abs(saldo_final - item["saldo_esperado"]) > 0.000001:
                        raise RuntimeError(
                            f"Saldo preservado de {item['sku']} mudou para "
                            f"{saldo_final}; esperado {item['saldo_esperado']}."
                        )
                resultado["saldos_preservados_finais"] = {
                    item["sku"]: float(item["produto"].estoque_atual or 0)
                    for item in produtos_preservados.values()
                }
            else:
                db.rollback()
            return resultado
        finally:
            db.close()


def main() -> int:
    try:
        resultado = executar(parse_args())
        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {"success": False, "erro": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
