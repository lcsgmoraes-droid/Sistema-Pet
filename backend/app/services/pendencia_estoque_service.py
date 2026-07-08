"""
Serviço de Notificação de Pendências de Estoque
Verifica e notifica clientes quando produtos entram no estoque
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Dict
import logging
import requests

from app.pendencia_estoque_models import PendenciaEstoque
from app.produtos_models import Produto
from app.tenancy.rls import sync_rls_tenant

logger = logging.getLogger(__name__)
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def verificar_e_notificar_pendencias(
    db: Session, tenant_id: str, produto_id: int, quantidade_entrada: float
) -> Dict:
    """
    Verifica se há pendências para um produto que acabou de entrar no estoque
    e envia notificacao por push no app mobile e/ou WhatsApp para os clientes.

    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        produto_id: ID do produto que entrou no estoque
        quantidade_entrada: Quantidade que entrou

    Returns:
        Dict com resumo das notificações enviadas
    """
    logger.info(
        f"🔔 Verificando pendências para produto {produto_id} (qtd: {quantidade_entrada})"
    )

    sync_rls_tenant(db, tenant_id)

    # Buscar produto
    produto = (
        db.query(Produto)
        .filter(and_(Produto.id == produto_id, Produto.tenant_id == tenant_id))
        .first()
    )

    if not produto:
        logger.warning(f"❌ Produto {produto_id} não encontrado")
        return {"sucesso": False, "erro": "Produto não encontrado"}

    # Buscar pendências ativas ordenadas por prioridade e data
    pendencias = (
        db.query(PendenciaEstoque)
        .filter(
            and_(
                PendenciaEstoque.tenant_id == tenant_id,
                PendenciaEstoque.produto_id == produto_id,
                PendenciaEstoque.status == "pendente",
            )
        )
        .order_by(
            PendenciaEstoque.prioridade.desc(), PendenciaEstoque.data_registro.asc()
        )
        .all()
    )

    if not pendencias:
        logger.info(f"✅ Nenhuma pendência ativa para produto {produto.nome}")
        return {
            "sucesso": True,
            "produto_id": produto_id,
            "produto_nome": produto.nome,
            "pendencias_encontradas": 0,
            "notificacoes_enviadas": 0,
        }

    logger.info(f"📋 Encontradas {len(pendencias)} pendências para notificar")

    notificacoes_enviadas = 0
    notificacoes_falhas = 0

    for pendencia in pendencias:
        try:
            # Buscar cliente
            cliente = pendencia.cliente

            if not cliente:
                logger.warning(
                    f"❌ Cliente não encontrado para pendência {pendencia.id}"
                )
                continue

            telefone = cliente.celular or cliente.telefone
            push_sucesso = enviar_push_pendencia(
                db=db,
                tenant_id=tenant_id,
                cliente=cliente,
                produto=produto,
            )
            whatsapp_sucesso = False
            if telefone:
                mensagem = montar_mensagem_whatsapp(
                    cliente_nome=cliente.nome,
                    produto_nome=produto.nome,
                    produto_codigo=produto.codigo,
                    quantidade=pendencia.quantidade_desejada,
                    valor=produto.preco_venda,
                )
                whatsapp_sucesso = enviar_whatsapp_pendencia(
                    db=db,
                    tenant_id=tenant_id,
                    cliente_id=cliente.id,
                    telefone=telefone,
                    mensagem=mensagem,
                )
            else:
                logger.warning(f"Cliente {cliente.nome} nao tem telefone cadastrado")

            if push_sucesso or whatsapp_sucesso:
                pendencia.status = "notificado"
                pendencia.data_notificacao = datetime.utcnow()
                pendencia.whatsapp_enviado = bool(whatsapp_sucesso)
                notificacoes_enviadas += 1
                canais = []
                if push_sucesso:
                    canais.append("app mobile")
                if whatsapp_sucesso:
                    canais.append("WhatsApp")
                logger.info(
                    f"Notificacao enviada para {cliente.nome} via {', '.join(canais)}"
                )
            else:
                notificacoes_falhas += 1
                logger.error(f"Falha ao notificar {cliente.nome}")

        except Exception as e:
            logger.error(f"❌ Erro ao processar pendência {pendencia.id}: {str(e)}")
            notificacoes_falhas += 1
            continue

    db.commit()

    logger.info(
        f"✅ Notificações concluídas: {notificacoes_enviadas} enviadas, "
        f"{notificacoes_falhas} falhas"
    )

    return {
        "sucesso": True,
        "produto_id": produto_id,
        "produto_nome": produto.nome,
        "pendencias_encontradas": len(pendencias),
        "notificacoes_enviadas": notificacoes_enviadas,
        "notificacoes_falhas": notificacoes_falhas,
    }


def montar_mensagem_whatsapp(
    cliente_nome: str,
    produto_nome: str,
    produto_codigo: str,
    quantidade: float,
    valor: float,
) -> str:
    """
    Monta a mensagem de WhatsApp para notificação de produto disponível.
    """
    mensagem = f"""🎉 *Boa notícia, {cliente_nome}!*

O produto que você aguardava chegou! 📦

*Produto:* {produto_nome}
*Código:* {produto_codigo}
*Quantidade disponível:* {quantidade}
*Valor:* R$ {valor:.2f}

✅ O produto já está disponível em nossa loja!

Venha garantir o seu antes que acabe! 😊

_Esta é uma notificação automática do nosso sistema de lista de espera._"""

    return mensagem


def enviar_push_pendencia(
    db: Session,
    tenant_id: str,
    cliente,
    produto: Produto,
) -> bool:
    """Envia push mobile de produto disponivel para cliente da lista de espera."""
    try:
        from app.services.push_devices import (
            load_customer_push_targets,
            mark_push_target_result,
        )

        targets = load_customer_push_targets(
            db,
            tenant_id=tenant_id,
            customer_id=getattr(cliente, "id", None),
        )
        if not targets:
            logger.warning(
                "[LISTA-ESPERA-PDV] Cliente sem dispositivo push tenant_id=%s cliente_id=%s produto_id=%s",
                tenant_id,
                getattr(cliente, "id", None),
                getattr(produto, "id", None),
            )
            return False

        content = {
            "title": "Produto disponivel",
            "body": f"{produto.nome} voltou ao estoque. Confira no app antes que acabe.",
            "data": {
                "source": "stock_waitlist",
                "kind": "stock_available",
                "produto_id": getattr(produto, "id", None),
                "product_id": getattr(produto, "id", None),
            },
        }

        any_sent = False
        for target in targets:
            try:
                sent, ticket_id, error = _send_expo_push(target.token, content)
            except Exception as exc:
                sent, ticket_id, error = False, None, str(exc)
            any_sent = any_sent or sent
            mark_push_target_result(target, sent=sent, ticket_id=ticket_id, error=error)
        return any_sent
    except Exception as e:
        logger.error(f"Erro ao enviar push de pendencia: {str(e)}")
        return False


def _send_expo_push(
    push_token: str, content: dict
) -> tuple[bool, str | None, str | None]:
    payload = {
        "to": push_token,
        "sound": "default",
        "priority": "high",
        "channelId": "default",
        "title": content["title"],
        "body": content["body"],
        "data": content["data"],
    }
    response = requests.post(
        EXPO_PUSH_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    try:
        response_body = response.json()
    except Exception:
        return True, None, None
    data = response_body.get("data") if isinstance(response_body, dict) else None
    if isinstance(data, dict) and data.get("status") not in (None, "ok"):
        logger.warning("[LISTA-ESPERA-PDV] Expo retornou falha: %s", data)
        return False, None, str(data)
    ticket_id = data.get("id") if isinstance(data, dict) else None
    return True, ticket_id, None


def enviar_whatsapp_pendencia(
    db: Session, tenant_id: str, cliente_id: int, telefone: str, mensagem: str
) -> bool:
    """
    Envia mensagem de WhatsApp para o cliente.

    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        cliente_id: ID do cliente
        telefone: Telefone do cliente
        mensagem: Mensagem a enviar

    Returns:
        True se enviado com sucesso, False caso contrário
    """
    try:
        # Importar serviço de WhatsApp
        from app.whatsapp.whatsapp_service import enviar_mensagem_texto

        # Enviar mensagem
        resultado = enviar_mensagem_texto(
            db=db,
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            telefone=telefone,
            mensagem=mensagem,
            tipo_mensagem="notificacao_pendencia",
        )

        return resultado.get("sucesso", False)

    except Exception as e:
        logger.error(f"❌ Erro ao enviar WhatsApp: {str(e)}")
        return False


def marcar_pendencia_finalizada(
    db: Session, pendencia_id: int, venda_id: int, *, tenant_id: str
) -> bool:
    """
    Marca uma pendência como finalizada quando o cliente efetua a compra.

    Args:
        db: Sessão do banco
        pendencia_id: ID da pendência
        venda_id: ID da venda que finalizou a pendência

    Returns:
        True se atualizado com sucesso
    """
    try:
        sync_rls_tenant(db, tenant_id)

        pendencia = (
            db.query(PendenciaEstoque)
            .filter(
                and_(
                    PendenciaEstoque.id == pendencia_id,
                    PendenciaEstoque.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not pendencia:
            return False

        pendencia.status = "finalizado"
        pendencia.data_finalizacao = datetime.utcnow()
        pendencia.venda_id = venda_id

        db.commit()

        logger.info(f"✅ Pendência {pendencia_id} finalizada com venda {venda_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Erro ao finalizar pendência: {str(e)}")
        db.rollback()
        return False
