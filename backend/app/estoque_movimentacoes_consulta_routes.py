"""
Rotas de consulta de movimentacoes de estoque.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque_movimentacoes_context import (
    _contexto_venda_pedido_integrado,
    _detalhar_reservas_ativas_produto,
    _label_canal_movimentacao,
    _observacao_exibicao_movimentacao_bling,
)
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.vendas_models import Venda


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque", tags=["Estoque"])


@router.get("/movimentacoes/produto/{produto_id}")
def listar_movimentacoes_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as movimentacoes de um produto especifico.
    """
    _current_user, tenant_id = user_and_tenant
    logger.info("Listando movimentacoes do produto %s", produto_id)

    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    movimentacoes = db.query(EstoqueMovimentacao).filter(
        EstoqueMovimentacao.produto_id == produto_id,
        EstoqueMovimentacao.tenant_id == tenant_id,
    ).order_by(EstoqueMovimentacao.created_at).all()

    pedido_integrado_ids = sorted(
        {
            int(mov.referencia_id)
            for mov in movimentacoes
            if mov.referencia_tipo == "pedido_integrado" and mov.referencia_id
        }
    )
    pedidos_integrados = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.id.in_(pedido_integrado_ids),
        )
        .all()
        if pedido_integrado_ids
        else []
    )
    pedidos_integrados_por_id = {pedido.id: pedido for pedido in pedidos_integrados}

    resultado = []
    custo_anterior_entrada = None
    consumo_por_lote = {}
    saldo_estimado = 0.0

    for mov in movimentacoes:
        if mov.quantidade_nova is not None:
            saldo_apos_lancamento = float(mov.quantidade_nova)
            saldo_estimado = saldo_apos_lancamento
        else:
            quantidade_movimento = float(mov.quantidade or 0)
            if mov.status != "cancelado":
                if mov.tipo == "entrada":
                    saldo_estimado += quantidade_movimento
                elif mov.tipo == "saida":
                    saldo_estimado -= quantidade_movimento
            saldo_apos_lancamento = saldo_estimado

        lote_nome = None
        lote_info = None

        if mov.tipo == "entrada" and mov.lote_id:
            lote = db.query(ProdutoLote).filter(ProdutoLote.id == mov.lote_id).first()
            if lote:
                lote_nome = lote.nome_lote
                lote_info = {
                    "nome": lote_nome,
                    "total_lote": lote.quantidade_inicial,
                    "tipo": "entrada",
                }

        elif mov.tipo == "saida" and mov.lotes_consumidos:
            try:
                lotes = json.loads(mov.lotes_consumidos)
                if lotes and len(lotes) > 0:
                    primeiro_lote = lotes[0]
                    lote_id = primeiro_lote.get("lote_id")

                    if lote_id:
                        if lote_id not in consumo_por_lote:
                            consumo_por_lote[lote_id] = 0
                        consumo_por_lote[lote_id] += primeiro_lote.get("quantidade", 0)

                        lote = db.query(ProdutoLote).filter(ProdutoLote.id == lote_id).first()
                        if lote:
                            lote_info = {
                                "nome": lote.nome_lote,
                                "consumido_acumulado": consumo_por_lote[lote_id],
                                "total_lote": lote.quantidade_inicial,
                                "quantidade_movimento": primeiro_lote.get("quantidade", 0),
                                "tipo": "saida",
                            }
            except Exception:
                pass

        variacao_custo = None
        if mov.tipo == "entrada" and mov.custo_unitario:
            if custo_anterior_entrada and custo_anterior_entrada > 0:
                diferenca_valor = mov.custo_unitario - custo_anterior_entrada
                diferenca_percentual = (diferenca_valor / custo_anterior_entrada) * 100

                variacao_custo = {
                    "custo_anterior": custo_anterior_entrada,
                    "custo_atual": mov.custo_unitario,
                    "diferenca_valor": diferenca_valor,
                    "diferenca_percentual": diferenca_percentual,
                    "tipo": "aumento" if diferenca_valor > 0 else "reducao" if diferenca_valor < 0 else "estavel",
                }

            custo_anterior_entrada = mov.custo_unitario

        canal_venda = None
        preco_venda_unitario = None
        nf_numero = None
        documento_exibicao = mov.documento
        observacao_exibicao = mov.observacao
        if mov.referencia_tipo == "venda" and mov.referencia_id:
            venda = db.query(Venda.canal, Venda.total).filter(Venda.id == mov.referencia_id).first()
            if venda:
                canal_venda = venda.canal
                if mov.quantidade and mov.quantidade > 0:
                    preco_venda_unitario = float(venda.total) / float(mov.quantidade) if venda.total else None
        elif mov.referencia_tipo == "pedido_integrado" and mov.referencia_id:
            pedido_integrado = pedidos_integrados_por_id.get(int(mov.referencia_id))
            if pedido_integrado:
                contexto_venda = _contexto_venda_pedido_integrado(db, pedido_integrado, produto_id)
                canal_venda = contexto_venda.get("canal")
                nf_numero = contexto_venda.get("nf_numero")
                nf_id = contexto_venda.get("nf_id")
                try:
                    from app.services.bling_nf_service import movimento_documentado_por_nf
                except Exception:
                    movimento_documentado_por_nf = None

                movimento_usa_nf = bool(
                    movimento_documentado_por_nf
                    and movimento_documentado_por_nf(
                        mov,
                        nf_numero=nf_numero,
                        nf_bling_id=nf_id,
                    )
                )

                if movimento_usa_nf:
                    preco_venda_unitario = contexto_venda.get("preco_venda_unitario")
                    documento_exibicao = nf_numero or mov.documento
                    observacao_exibicao = _observacao_exibicao_movimentacao_bling(
                        canal=canal_venda,
                        nf_numero=nf_numero,
                        observacao_original=mov.observacao,
                    )
                else:
                    nf_numero = None

        resultado.append({
            "id": mov.id,
            "tipo": mov.tipo,
            "status": mov.status,
            "motivo": mov.motivo,
            "quantidade": mov.quantidade,
            "quantidade_anterior": mov.quantidade_anterior,
            "quantidade_nova": mov.quantidade_nova,
            "saldo_apos_lancamento": saldo_apos_lancamento,
            "custo_unitario": mov.custo_unitario,
            "valor_total": mov.valor_total,
            "documento": documento_exibicao,
            "documento_original": mov.documento,
            "referencia_id": mov.referencia_id,
            "referencia_tipo": mov.referencia_tipo,
            "observacao": mov.observacao,
            "observacao_exibicao": observacao_exibicao,
            "lote_id": mov.lote_id,
            "lote_nome": lote_nome,
            "lote_info": lote_info,
            "variacao_custo": variacao_custo,
            "canal": canal_venda,
            "canal_label": _label_canal_movimentacao(canal_venda),
            "nf_numero": nf_numero,
            "preco_venda_unitario": preco_venda_unitario,
            "created_at": mov.created_at.isoformat() if mov.created_at else None,
            "user_id": mov.user_id,
        })

    resultado.reverse()

    return resultado


@router.get("/produto/{produto_id}/reservas-ativas")
def listar_reservas_ativas_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    logger.info("Listando reservas ativas do produto %s", produto_id)

    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    reservas = _detalhar_reservas_ativas_produto(
        db,
        tenant_id=tenant_id,
        produto_id=produto_id,
    )

    return {
        "produto_id": produto_id,
        "produto_nome": produto.nome,
        "total_pedidos": len(reservas),
        "quantidade_reservada": round(
            sum(float(item.get("quantidade_reservada") or 0) for item in reservas),
            4,
        ),
        "pedidos": reservas,
    }
