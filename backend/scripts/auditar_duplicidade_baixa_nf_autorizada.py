from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import func

from app.db import SessionLocal
from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao, Produto
from app.services.bling_nf_service import (
    _obter_usuario_padrao_tenant,
    _restaurar_lotes_consumidos,
    _sincronizar_cache_estoque_virtual,
    movimento_documentado_por_nf,
)
from app.services.kit_estoque_service import KitEstoqueService
from app.services.nfe_authorized_reconciliation_service import (
    _garantir_registry_sqlalchemy_reconciliacao,
    _extrair_referencias_nf_cache,
    reconciliar_nf_autorizada_cache,
)


OBSERVACAO_GENERICA = "baixa automatica via nf autorizada do bling"
STATUS_NF_AUTORIZADA = "autorizada"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audita e corrige duplicidades de baixa de estoque geradas pela "
            "reconciliacao de NF autorizada do Bling."
        )
    )
    parser.add_argument(
        "--tenant-id",
        dest="tenant_id",
        default=None,
        help="UUID do tenant. Se omitido, processa todos os tenants encontrados.",
    )
    parser.add_argument(
        "--dias-nf",
        dest="dias_nf",
        type=int,
        default=15,
        help="Janela maxima para procurar NFs autorizadas relacionadas ao pedido.",
    )
    parser.add_argument(
        "--max-grupos",
        dest="max_grupos",
        type=int,
        default=None,
        help="Limita a quantidade de grupos suspeitos processados.",
    )
    parser.add_argument(
        "--apply",
        dest="apply_changes",
        action="store_true",
        help="Aplica a correcao. Sem esta flag o script roda apenas em modo leitura.",
    )
    parser.add_argument(
        "--backup-file",
        dest="backup_file",
        default=None,
        help="Arquivo JSON para snapshot previo dos movimentos afetados.",
    )
    return parser.parse_args()


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _observacao_normalizada(valor: str | None) -> str:
    return str(valor or "").strip().lower()


def _movimento_generico_duplicado(mov: EstoqueMovimentacao) -> bool:
    return (
        getattr(mov, "tipo", None) == "saida"
        and getattr(mov, "status", None) != "cancelado"
        and getattr(mov, "motivo", None) == "venda_bling"
        and getattr(mov, "referencia_tipo", None) == "pedido_integrado"
        and not str(getattr(mov, "documento", None) or "").strip()
        and _observacao_normalizada(getattr(mov, "observacao", None)) == OBSERVACAO_GENERICA
    )


def _serializar_movimentacao(mov: EstoqueMovimentacao) -> dict[str, Any]:
    return {
        "id": mov.id,
        "tenant_id": str(getattr(mov, "tenant_id", None) or ""),
        "produto_id": mov.produto_id,
        "tipo": mov.tipo,
        "motivo": mov.motivo,
        "quantidade": float(mov.quantidade or 0),
        "quantidade_anterior": float(mov.quantidade_anterior or 0),
        "quantidade_nova": float(mov.quantidade_nova or 0),
        "documento": mov.documento,
        "referencia_id": mov.referencia_id,
        "referencia_tipo": mov.referencia_tipo,
        "status": mov.status,
        "observacao": mov.observacao,
        "user_id": mov.user_id,
        "created_at": mov.created_at,
        "updated_at": mov.updated_at,
        "lotes_consumidos": mov.lotes_consumidos,
    }


def _buscar_grupos_suspeitos(db, tenant_id: str | None, max_grupos: int | None) -> list[dict[str, Any]]:
    query = (
        db.query(
            EstoqueMovimentacao.tenant_id.label("tenant_id"),
            EstoqueMovimentacao.referencia_id.label("pedido_integrado_id"),
            EstoqueMovimentacao.produto_id.label("produto_id"),
            func.count(EstoqueMovimentacao.id).label("qtd_movs"),
            func.sum(EstoqueMovimentacao.quantidade).label("qtd_total"),
            func.min(EstoqueMovimentacao.created_at).label("primeira_baixa"),
            func.max(EstoqueMovimentacao.created_at).label("ultima_baixa"),
        )
        .filter(
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
            EstoqueMovimentacao.motivo == "venda_bling",
            func.coalesce(EstoqueMovimentacao.documento, "") == "",
            func.lower(func.coalesce(EstoqueMovimentacao.observacao, "")) == OBSERVACAO_GENERICA,
        )
    )

    if tenant_id:
        query = query.filter(EstoqueMovimentacao.tenant_id == tenant_id)

    query = (
        query.group_by(
            EstoqueMovimentacao.tenant_id,
            EstoqueMovimentacao.referencia_id,
            EstoqueMovimentacao.produto_id,
        )
        .having(func.count(EstoqueMovimentacao.id) > 1)
        .order_by(func.count(EstoqueMovimentacao.id).desc(), func.max(EstoqueMovimentacao.created_at).desc())
    )

    if max_grupos:
        query = query.limit(int(max_grupos))

    grupos: list[dict[str, Any]] = []
    for row in query.all():
        pedido = db.query(PedidoIntegrado).filter(PedidoIntegrado.id == row.pedido_integrado_id).first()
        produto = db.query(Produto).filter(Produto.id == row.produto_id).first()
        grupos.append(
            {
                "tenant_id": str(row.tenant_id),
                "pedido_integrado_id": int(row.pedido_integrado_id),
                "pedido_bling_id": getattr(pedido, "pedido_bling_id", None),
                "pedido_bling_numero": getattr(pedido, "pedido_bling_numero", None),
                "produto_id": int(row.produto_id),
                "produto_codigo": getattr(produto, "codigo", None),
                "produto_nome": getattr(produto, "nome", None),
                "qtd_movs_genericos": int(row.qtd_movs or 0),
                "qtd_total_generica": float(row.qtd_total or 0),
                "primeira_baixa": row.primeira_baixa,
                "ultima_baixa": row.ultima_baixa,
            }
        )
    return grupos


def _buscar_movimentos_saida_pedido_produto(db, tenant_id: str, pedido_id: int, produto_id: int) -> list[EstoqueMovimentacao]:
    return (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido_id,
            EstoqueMovimentacao.produto_id == produto_id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )


def _buscar_registro_nf_para_pedido(
    db,
    *,
    tenant_id: str,
    pedido: PedidoIntegrado,
    dias_nf: int,
) -> BlingNotaFiscalCache | None:
    limite_data = datetime.utcnow() - timedelta(days=max(int(dias_nf or 15), 1))
    candidatos = (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            func.lower(BlingNotaFiscalCache.status) == STATUS_NF_AUTORIZADA,
            func.coalesce(BlingNotaFiscalCache.data_emissao, BlingNotaFiscalCache.last_synced_at) >= limite_data,
        )
        .order_by(
            BlingNotaFiscalCache.data_emissao.desc().nullslast(),
            BlingNotaFiscalCache.last_synced_at.desc().nullslast(),
            BlingNotaFiscalCache.id.desc(),
        )
        .all()
    )

    pedido_bling_id = str(getattr(pedido, "pedido_bling_id", None) or "").strip()
    pedido_bling_numero = str(getattr(pedido, "pedido_bling_numero", None) or "").strip()

    for registro in candidatos:
        refs = _extrair_referencias_nf_cache(registro)
        if pedido_bling_id and str(refs.get("pedido_bling_id") or "").strip() == pedido_bling_id:
            return registro
        if pedido_bling_numero and str(refs.get("pedido_bling_numero") or "").strip() == pedido_bling_numero:
            return registro
    return None


def _cancelar_movimento_duplicado(
    db,
    *,
    tenant_id: str,
    pedido_id: int,
    produto_id: int,
    nf_numero: str | None,
    nf_bling_id: str | None,
    movimento: EstoqueMovimentacao,
) -> dict[str, Any]:
    from app.estoque.service import EstoqueService

    usuario_execucao = getattr(movimento, "user_id", None) or getattr(
        _obter_usuario_padrao_tenant(db=db, tenant_id=tenant_id),
        "id",
        None,
    )
    if not usuario_execucao:
        raise ValueError(
            f"Sem usuario valido para estornar a movimentacao {movimento.id} "
            f"do pedido {pedido_id}."
        )

    lotes_restaurados = _restaurar_lotes_consumidos(db, movimento)
    resultado_estorno = EstoqueService.estornar_estoque(
        produto_id=produto_id,
        quantidade=float(movimento.quantidade or 0),
        motivo="correcao_dup_nf_autorizada_bling",
        referencia_id=pedido_id,
        referencia_tipo="pedido_integrado",
        user_id=usuario_execucao,
        db=db,
        tenant_id=tenant_id,
        documento=nf_numero or nf_bling_id,
        observacao=(
            f"Estorno automatico por duplicidade de baixa via NF autorizada "
            f"{nf_numero or nf_bling_id or 'sem_numero'}"
        ),
    )

    for kit_id, _estoque_virtual in KitEstoqueService.recalcular_kits_que_usam_produto(db, produto_id).items():
        _sincronizar_cache_estoque_virtual(db, tenant_id, kit_id)

    observacao_original = str(getattr(movimento, "observacao", None) or "").strip()
    complemento = (
        f"Cancelada automaticamente por duplicidade de baixa NF {nf_numero or nf_bling_id or 'sem_numero'}"
    )
    movimento.status = "cancelado"
    movimento.observacao = (
        f"{observacao_original} | {complemento}"
        if observacao_original and complemento not in observacao_original
        else complemento
    )
    db.add(movimento)

    return {
        "movimento_id_cancelado": movimento.id,
        "movimento_estorno_id": resultado_estorno.get("movimentacao_id"),
        "quantidade_estornada": float(movimento.quantidade or 0),
        "lotes_restaurados": int(lotes_restaurados or 0),
    }


def _processar_grupo(
    db,
    *,
    grupo: dict[str, Any],
    dias_nf: int,
    apply_changes: bool,
) -> dict[str, Any]:
    tenant_id = grupo["tenant_id"]
    pedido_id = grupo["pedido_integrado_id"]
    produto_id = grupo["produto_id"]

    pedido = db.query(PedidoIntegrado).filter(PedidoIntegrado.id == pedido_id).first()
    if not pedido:
        return {
            **grupo,
            "status": "pedido_nao_encontrado",
        }

    movimentos_antes = _buscar_movimentos_saida_pedido_produto(db, tenant_id, pedido_id, produto_id)
    snapshot_movimentos = [_serializar_movimentacao(mov) for mov in movimentos_antes]

    registro_nf = _buscar_registro_nf_para_pedido(
        db,
        tenant_id=tenant_id,
        pedido=pedido,
        dias_nf=dias_nf,
    )
    nf_refs = _extrair_referencias_nf_cache(registro_nf) if registro_nf else {}

    resultado = {
        **grupo,
        "status": "dry_run",
        "pedido_status": getattr(pedido, "status", None),
        "nf_bling_id": nf_refs.get("nf_bling_id"),
        "nf_numero": nf_refs.get("nf_numero"),
        "movimentos_antes": snapshot_movimentos,
        "movimentos_genericos_antes": sum(1 for mov in movimentos_antes if _movimento_generico_duplicado(mov)),
        "movimentos_documentados_antes": sum(
            1
            for mov in movimentos_antes
            if movimento_documentado_por_nf(
                mov,
                nf_numero=nf_refs.get("nf_numero"),
                nf_bling_id=nf_refs.get("nf_bling_id"),
            )
        ),
    }

    if not apply_changes:
        return resultado

    if not registro_nf:
        resultado["status"] = "nf_nao_encontrada"
        return resultado

    reconciliacao = reconciliar_nf_autorizada_cache(
        db,
        tenant_id=tenant_id,
        registro=registro_nf,
    )
    resultado["reconciliacao"] = reconciliacao
    if not reconciliacao.get("success"):
        db.rollback()
        resultado["status"] = "falha_reconciliacao"
        return resultado

    db.expire_all()
    movimentos_depois_reconciliacao = _buscar_movimentos_saida_pedido_produto(db, tenant_id, pedido_id, produto_id)
    nf_numero = reconciliacao.get("nf_numero") or nf_refs.get("nf_numero")
    nf_bling_id = reconciliacao.get("nf_bling_id") or nf_refs.get("nf_bling_id")

    documentados = [
        mov
        for mov in movimentos_depois_reconciliacao
        if movimento_documentado_por_nf(mov, nf_numero=nf_numero, nf_bling_id=nf_bling_id)
    ]
    genericos = [mov for mov in movimentos_depois_reconciliacao if _movimento_generico_duplicado(mov)]

    if not documentados:
        db.rollback()
        resultado["status"] = "sem_movimento_canonico_nf"
        resultado["movimentos_pos_reconciliacao"] = [_serializar_movimentacao(mov) for mov in movimentos_depois_reconciliacao]
        return resultado

    cancelamentos = []
    for mov in genericos:
        cancelamentos.append(
            _cancelar_movimento_duplicado(
                db,
                tenant_id=tenant_id,
                pedido_id=pedido_id,
                produto_id=produto_id,
                nf_numero=nf_numero,
                nf_bling_id=nf_bling_id,
                movimento=mov,
            )
        )

    db.commit()

    movimentos_finais = _buscar_movimentos_saida_pedido_produto(db, tenant_id, pedido_id, produto_id)
    resultado["status"] = "corrigido"
    resultado["movimentos_cancelados"] = cancelamentos
    resultado["movimentos_genericos_restantes"] = sum(1 for mov in movimentos_finais if _movimento_generico_duplicado(mov))
    resultado["movimentos_documentados_finais"] = sum(
        1
        for mov in movimentos_finais
        if movimento_documentado_por_nf(mov, nf_numero=nf_numero, nf_bling_id=nf_bling_id)
    )
    resultado["movimentos_finais"] = [_serializar_movimentacao(mov) for mov in movimentos_finais]
    return resultado


def _default_backup_path() -> Path:
    return ROOT_DIR / "tmp_relatorios" / f"duplicidade_nf_autorizada_{_now_tag()}.json"


def main() -> int:
    args = parse_args()
    db = SessionLocal()

    try:
        _garantir_registry_sqlalchemy_reconciliacao()
        grupos = _buscar_grupos_suspeitos(
            db,
            tenant_id=args.tenant_id,
            max_grupos=args.max_grupos,
        )

        if not grupos:
            print(
                json.dumps(
                    {
                        "mode": "apply" if args.apply_changes else "dry_run",
                        "tenant_id": args.tenant_id,
                        "grupos_suspeitos": 0,
                        "message": "Nenhuma duplicidade generica encontrada.",
                    },
                    ensure_ascii=False,
                    indent=2,
                    default=_json_default,
                )
            )
            return 0

        backup_path = None
        preview_resultados = [
            _processar_grupo(
                db,
                grupo=grupo,
                dias_nf=args.dias_nf,
                apply_changes=False,
            )
            for grupo in grupos
        ]

        if args.apply_changes:
            backup_path = Path(args.backup_file) if args.backup_file else _default_backup_path()
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_payload = {
                "generated_at": datetime.now(),
                "tenant_id": args.tenant_id,
                "mode": "pre_apply_backup",
                "grupos": preview_resultados,
            }
            backup_path.write_text(
                json.dumps(backup_payload, ensure_ascii=False, indent=2, default=_json_default),
                encoding="utf-8",
            )

        resultados = []
        if args.apply_changes:
            for grupo in grupos:
                try:
                    resultados.append(
                        _processar_grupo(
                            db,
                            grupo=grupo,
                            dias_nf=args.dias_nf,
                            apply_changes=True,
                        )
                    )
                except Exception as exc:
                    db.rollback()
                    resultados.append(
                        {
                            **grupo,
                            "status": "erro",
                            "erro": str(exc),
                        }
                    )
        else:
            resultados = preview_resultados

        resumo_status = defaultdict(int)
        for resultado in resultados:
            resumo_status[str(resultado.get("status") or "desconhecido")] += 1

        payload = {
            "generated_at": datetime.now(),
            "mode": "apply" if args.apply_changes else "dry_run",
            "tenant_id": args.tenant_id,
            "grupos_suspeitos": len(grupos),
            "resumo_status": dict(resumo_status),
            "backup_file": str(backup_path) if backup_path else None,
            "resultados": resultados,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
