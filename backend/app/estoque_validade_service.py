from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.estoque.service import EstoqueService
from app.estoque_validade_models import EstoqueValidadeBloqueio
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote


STATUS_ABERTOS = {"pendente"}


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _tenant_str(tenant_id) -> str:
    return str(tenant_id)


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def _is_vencido(data_validade, agora: datetime) -> bool:
    if not data_validade:
        return False
    validade = data_validade
    referencia = agora
    if validade.tzinfo is None and referencia.tzinfo is not None:
        referencia = referencia.replace(tzinfo=None)
    if validade.tzinfo is not None and referencia.tzinfo is None:
        validade = validade.replace(tzinfo=None)
    return validade <= referencia


class EstoqueValidadeService:
    @staticmethod
    def bloquear_lote(
        *,
        db: Session,
        tenant_id: str,
        user_id: int | None,
        produto: Produto,
        lote: ProdutoLote,
        agora: datetime | None = None,
        origem: str = "rotina",
    ) -> EstoqueValidadeBloqueio:
        agora = agora or _agora_utc()
        quantidade_lote = max(_to_float(getattr(lote, "quantidade_disponivel", 0)), 0)
        quantidade_vendavel = max(_to_float(getattr(produto, "estoque_atual", 0)), 0)
        quantidade_bloquear = min(quantidade_lote, quantidade_vendavel)
        custo_unitario = _to_float(
            getattr(lote, "custo_unitario", None),
            _to_float(getattr(produto, "preco_custo", 0)),
        )

        produto.estoque_atual = quantidade_vendavel - quantidade_bloquear
        lote.status = (
            "vencido_bloqueado"
            if _is_vencido(getattr(lote, "data_validade", None), agora)
            else "bloqueado_validade"
        )

        user_id_movimentacao = EstoqueService._resolver_user_id_operacao(
            db=db,
            tenant_id=_tenant_str(tenant_id),
            user_id=user_id,
        )

        movimentacao = EstoqueMovimentacao(
            produto_id=produto.id,
            tipo="saida",
            motivo="validade_bloqueio",
            quantidade=quantidade_bloquear,
            quantidade_anterior=quantidade_vendavel,
            quantidade_nova=produto.estoque_atual,
            custo_unitario=custo_unitario,
            valor_total=quantidade_bloquear * custo_unitario,
            lote_id=lote.id,
            referencia_id=lote.id,
            referencia_tipo="validade_lote",
            observacao=f"Lote {getattr(lote, 'nome_lote', lote.id)} retirado do estoque vendavel por validade",
            user_id=user_id_movimentacao,
            tenant_id=tenant_id,
        )
        db.add(movimentacao)
        db.flush()

        bloqueio = EstoqueValidadeBloqueio(
            tenant_id=tenant_id,
            produto_id=produto.id,
            lote_id=lote.id,
            user_id=user_id_movimentacao,
            status="pendente",
            origem=origem,
            data_referencia=agora,
            data_validade=getattr(lote, "data_validade", None),
            quantidade_bloqueada=quantidade_bloquear,
            quantidade_resolvida=0,
            custo_unitario=custo_unitario,
            custo_total_estimado=quantidade_bloquear * custo_unitario,
            movimentacao_bloqueio_id=movimentacao.id,
        )
        db.add(bloqueio)
        db.flush()
        return bloqueio

    @staticmethod
    def descartar_bloqueio(
        *,
        db: Session,
        tenant_id: str,
        user_id: int,
        bloqueio: EstoqueValidadeBloqueio,
        observacao: str | None = None,
        agora: datetime | None = None,
    ) -> EstoqueValidadeBloqueio:
        agora = agora or _agora_utc()
        lote = bloqueio.lote
        produto = bloqueio.produto
        quantidade = max(
            _to_float(bloqueio.quantidade_bloqueada)
            - _to_float(bloqueio.quantidade_resolvida),
            0,
        )
        custo_unitario = _to_float(
            bloqueio.custo_unitario, _to_float(getattr(produto, "preco_custo", 0))
        )
        estoque_vendavel = _to_float(getattr(produto, "estoque_atual", 0))

        lote.quantidade_disponivel = max(
            _to_float(getattr(lote, "quantidade_disponivel", 0)) - quantidade, 0
        )
        lote.status = "descartado"

        user_id_movimentacao = EstoqueService._resolver_user_id_operacao(
            db=db,
            tenant_id=_tenant_str(tenant_id),
            user_id=user_id,
        )

        movimentacao = EstoqueMovimentacao(
            produto_id=bloqueio.produto_id,
            tipo="saida",
            motivo="validade_descarte",
            quantidade=quantidade,
            quantidade_anterior=estoque_vendavel,
            quantidade_nova=estoque_vendavel,
            custo_unitario=custo_unitario,
            valor_total=quantidade * custo_unitario,
            lote_id=bloqueio.lote_id,
            referencia_id=bloqueio.id,
            referencia_tipo="validade_bloqueio",
            observacao=observacao or "Descarte por validade",
            user_id=user_id_movimentacao,
            tenant_id=tenant_id,
        )
        db.add(movimentacao)
        db.flush()

        bloqueio.status = "descartado"
        bloqueio.decisao = "descartado"
        bloqueio.quantidade_resolvida = _to_float(bloqueio.quantidade_bloqueada)
        bloqueio.movimentacao_resolucao_id = movimentacao.id
        bloqueio.decidido_por_user_id = user_id_movimentacao
        bloqueio.decidido_em = agora
        bloqueio.observacao = observacao
        db.flush()
        return bloqueio

    @staticmethod
    def processar_lotes_em_risco(
        *,
        db: Session,
        tenant,
        user_id: int | None,
        agora: datetime | None = None,
        origem: str = "rotina",
    ) -> dict:
        agora = agora or _agora_utc()
        if not bool(getattr(tenant, "protecao_validade_ativa", False)):
            return {"processados": 0, "bloqueios": []}

        from datetime import timedelta

        limite = agora + timedelta(
            days=int(getattr(tenant, "dias_alerta_validade", 15) or 15)
        )
        lotes = (
            db.query(ProdutoLote)
            .join(Produto, Produto.id == ProdutoLote.produto_id)
            .filter(
                ProdutoLote.tenant_id == tenant.id,
                ProdutoLote.status == "ativo",
                ProdutoLote.quantidade_disponivel > 0,
                ProdutoLote.data_validade.isnot(None),
                ProdutoLote.data_validade <= limite,
                Produto.situacao.isnot(False),
            )
            .all()
        )

        bloqueios = []
        for lote in lotes:
            existente = (
                db.query(EstoqueValidadeBloqueio)
                .filter(
                    EstoqueValidadeBloqueio.tenant_id == tenant.id,
                    EstoqueValidadeBloqueio.lote_id == lote.id,
                    EstoqueValidadeBloqueio.status.in_(list(STATUS_ABERTOS)),
                )
                .first()
            )
            if existente:
                continue
            bloqueios.append(
                EstoqueValidadeService.bloquear_lote(
                    db=db,
                    tenant_id=tenant.id,
                    user_id=user_id,
                    produto=lote.produto,
                    lote=lote,
                    agora=agora,
                    origem=origem,
                )
            )

        return {"processados": len(bloqueios), "bloqueios": bloqueios}

    @staticmethod
    def trocar_com_fornecedor(
        *,
        db: Session,
        tenant_id: str,
        user_id: int,
        bloqueio: EstoqueValidadeBloqueio,
        observacao: str | None = None,
        agora: datetime | None = None,
    ) -> EstoqueValidadeBloqueio:
        agora = agora or _agora_utc()
        lote = bloqueio.lote
        lote.quantidade_disponivel = 0
        lote.status = "trocado_fornecedor"

        bloqueio.status = "trocado_fornecedor"
        bloqueio.decisao = "trocado_fornecedor"
        bloqueio.quantidade_resolvida = _to_float(bloqueio.quantidade_bloqueada)
        bloqueio.decidido_por_user_id = user_id
        bloqueio.decidido_em = agora
        bloqueio.observacao = observacao
        db.flush()
        return bloqueio

    @staticmethod
    def retornar_ao_vendavel(
        *,
        db: Session,
        tenant_id: str,
        user_id: int,
        bloqueio: EstoqueValidadeBloqueio,
        observacao: str | None = None,
        agora: datetime | None = None,
    ) -> EstoqueValidadeBloqueio:
        agora = agora or _agora_utc()
        produto = bloqueio.produto
        lote = bloqueio.lote
        quantidade = max(
            _to_float(bloqueio.quantidade_bloqueada)
            - _to_float(bloqueio.quantidade_resolvida),
            0,
        )

        produto.estoque_atual = (
            _to_float(getattr(produto, "estoque_atual", 0)) + quantidade
        )
        lote.status = "ativo"

        bloqueio.status = "retornado_vendavel"
        bloqueio.decisao = "retornado_vendavel"
        bloqueio.quantidade_resolvida = _to_float(bloqueio.quantidade_bloqueada)
        bloqueio.decidido_por_user_id = user_id
        bloqueio.decidido_em = agora
        bloqueio.observacao = observacao
        db.flush()
        return bloqueio
