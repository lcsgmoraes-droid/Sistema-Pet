"""Rotas de rastreio de entrega do App Mobile."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Cliente, User
from app.routes.ecommerce_auth import (
    _activate_user_tenant_context,
    _get_current_ecommerce_user,
)

router = APIRouter()


@router.get("/pedidos/{pedido_id}/rastreio")
def rastreio_entrega(
    pedido_id: str,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna o status de rastreio de entrega de um pedido do cliente.
    Busca a rota de entrega associada à venda gerada pelo pedido.
    """
    from app.pedido_models import Pedido
    from app.vendas_models import Venda
    from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada

    tenant_id = _activate_user_tenant_context(current_user)

    # Verificar se o pedido pertence ao cliente
    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.tenant_id == tenant_id,
            Pedido.cliente_id == current_user.id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    # Buscar venda associada ao pedido (via observações ou canal+cliente)
    venda = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.canal.in_(["ecommerce", "app", "aplicativo"]),
            Venda.observacoes.contains(pedido_id),
        )
        .first()
    )

    if not venda:
        # Pedido ainda não gerou venda (aguardando pagamento)
        return {
            "status_pedido": pedido.status,
            "tem_entrega": False,
            "mensagem": _rastreio_mensagem_status(pedido.status),
            "rota": None,
        }

    if not venda.tem_entrega:
        return {
            "status_pedido": pedido.status,
            "tem_entrega": False,
            "mensagem": "Seu pedido é para retirada na loja.",
            "tipo_retirada": venda.tipo_retirada,
            "palavra_chave_retirada": venda.palavra_chave_retirada,
            "rota": None,
        }

    # Buscar parada de entrega associada a esta venda
    parada = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.venda_id == venda.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .first()
    )

    if not parada:
        return {
            "status_pedido": pedido.status,
            "tem_entrega": True,
            "mensagem": "Entrega em preparação — em breve será despachada.",
            "rota": None,
        }

    rota = (
        db.query(RotaEntrega)
        .filter(
            RotaEntrega.id == parada.rota_id,
            RotaEntrega.tenant_id == tenant_id,
        )
        .first()
    )
    if not rota:
        return {
            "status_pedido": pedido.status,
            "tem_entrega": True,
            "mensagem": "Entrega em preparação.",
            "rota": None,
        }

    # Buscar todas as paradas da rota para calcular progresso
    todas_paradas = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .order_by(RotaEntregaParada.ordem)
        .all()
    )
    entregues = sum(1 for p in todas_paradas if p.status == "entregue")
    posicao_cliente = None
    for i, p in enumerate(todas_paradas):
        if p.id == parada.id:
            posicao_cliente = i + 1
            break

    # Última posição GPS do entregador.
    # Prioridade:
    # 1) posição atual contínua da rota (lat_atual/lon_atual)
    # 2) fallback para última parada entregue com GPS
    ultima_posicao = None
    try:
        rota_posicao = db.execute(
            text(
                """
                SELECT lat_atual, lon_atual, localizacao_atualizada_em
                FROM rotas_entrega
                WHERE id = :rid AND tenant_id = :tenant
                """
            ),
            {"rid": rota.id, "tenant": tenant_id},
        ).fetchone()

        if rota_posicao and rota_posicao[0] is not None and rota_posicao[1] is not None:
            ultima_posicao = {
                "lat": float(rota_posicao[0]),
                "lon": float(rota_posicao[1]),
                "atualizada_em": rota_posicao[2].isoformat()
                if rota_posicao[2]
                else None,
                "fonte": "rota_atual",
            }
        else:
            for p in reversed(todas_paradas):
                result = db.execute(
                    text(
                        "SELECT lat_entrega, lon_entrega "
                        "FROM rotas_entrega_paradas "
                        "WHERE id = :pid AND tenant_id = :tenant"
                    ),
                    {"pid": p.id, "tenant": tenant_id},
                ).fetchone()
                if result and result[0] is not None and result[1] is not None:
                    ultima_posicao = {
                        "lat": float(result[0]),
                        "lon": float(result[1]),
                        "atualizada_em": p.data_entrega.isoformat()
                        if p.data_entrega
                        else None,
                        "fonte": "ultima_parada",
                    }
                    break
    except Exception:
        pass

    entregador_nome = None
    if rota.entregador_id:
        entregador = (
            db.query(Cliente)
            .filter(
                Cliente.id == rota.entregador_id,
                Cliente.tenant_id == tenant_id,
            )
            .first()
        )
        if entregador:
            entregador_nome = entregador.nome

    return {
        "status_pedido": pedido.status,
        "tem_entrega": True,
        "rota": {
            "numero": rota.numero,
            "status": rota.status,
            "token_rastreio": rota.token_rastreio,
            "entregador_nome": entregador_nome or "Entregador",
            "total_paradas": len(todas_paradas),
            "entregues": entregues,
            "posicao_cliente": posicao_cliente,
            "paradas_antes": max(0, (posicao_cliente or 1) - 1 - entregues),
            "status_parada": parada.status,
            "endereco_entrega": parada.endereco or venda.endereco_entrega,
            "data_entrega": parada.data_entrega.isoformat()
            if parada.data_entrega
            else None,
            "ultima_posicao_gps": ultima_posicao,
        },
        "mensagem": _rastreio_mensagem_parada(parada.status, rota.status),
    }


def _rastreio_mensagem_status(status: str) -> str:
    mapa = {
        "carrinho": "Carrinho ainda ativo.",
        "pendente": "Aguardando confirmação de pagamento.",
        "aprovado": "Pagamento confirmado! Preparando seu pedido.",
        "recusado": "Pagamento recusado. Entre em contato com a loja.",
        "cancelado": "Pedido cancelado.",
        "criado": "Pedido recebido, em preparação.",
    }
    return mapa.get(status, "Pedido em processamento.")


def _rastreio_mensagem_parada(status_parada: str, status_rota: str) -> str:
    if status_parada == "entregue":
        return "✅ Entregue! Aproveite seu pedido."
    if status_rota in ("em_rota", "em_andamento"):
        return "🛵 Entregador saiu para entrega!"
    if status_parada == "pendente":
        return "📦 Pedido separado, aguardando saída para entrega."
    return "Entrega em preparação."
