"""
Serviço de Notificação de Pendências de Estoque
Verifica e notifica clientes quando produtos entram no estoque
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Dict
import logging

from app.pendencia_estoque_models import PendenciaEstoque
from app.produtos_models import Produto
from app.tenancy.rls import sync_rls_tenant

logger = logging.getLogger(__name__)


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
            if _notificar_pendencia(db, tenant_id, produto, pendencia):
                notificacoes_enviadas += 1
            else:
                notificacoes_falhas += 1
        except Exception:
            logger.exception("Erro ao processar pendencia %s", pendencia.id)
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


def _notificar_pendencia(
    db: Session, tenant_id: str, produto: Produto, pendencia: PendenciaEstoque
) -> bool:
    cliente = pendencia.cliente
    if not cliente:
        logger.warning("Cliente nao encontrado para pendencia %s", pendencia.id)
        return False

    push_sucesso = enviar_push_pendencia(
        db=db,
        tenant_id=tenant_id,
        cliente=cliente,
        produto=produto,
        pendencia=pendencia,
    )
    whatsapp_sucesso = _enviar_whatsapp_pendencia_cliente(
        db=db,
        tenant_id=tenant_id,
        produto=produto,
        pendencia=pendencia,
        cliente=cliente,
    )

    if not (push_sucesso or whatsapp_sucesso):
        logger.error("Falha ao notificar %s", cliente.nome)
        return False

    pendencia.status = "notificado"
    pendencia.data_notificacao = datetime.utcnow()
    pendencia.whatsapp_enviado = bool(whatsapp_sucesso)
    canais = _nomes_canais_notificacao(push_sucesso, whatsapp_sucesso)
    logger.info("Notificacao enviada para %s via %s", cliente.nome, canais)
    return True


def _enviar_whatsapp_pendencia_cliente(
    db: Session,
    tenant_id: str,
    produto: Produto,
    pendencia: PendenciaEstoque,
    cliente,
) -> bool:
    telefone = cliente.celular or cliente.telefone
    if not telefone:
        logger.warning("Cliente %s nao tem telefone cadastrado", cliente.nome)
        return False

    mensagem = montar_mensagem_whatsapp(
        cliente_nome=cliente.nome,
        produto_nome=produto.nome,
        produto_codigo=produto.codigo,
        quantidade=pendencia.quantidade_desejada,
        valor=produto.preco_venda,
    )
    return enviar_whatsapp_pendencia(
        db=db,
        tenant_id=tenant_id,
        cliente_id=cliente.id,
        telefone=telefone,
        mensagem=mensagem,
    )


def _nomes_canais_notificacao(push_sucesso: bool, whatsapp_sucesso: bool) -> str:
    canais = []
    if push_sucesso:
        canais.append("app mobile")
    if whatsapp_sucesso:
        canais.append("WhatsApp")
    return ", ".join(canais)


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
    pendencia=None,
) -> bool:
    """Envia push mobile de produto disponivel para cliente da lista de espera."""
    try:
        from app.services.app_notifications import (
            criar_notificacao_estoque_app,
            registrar_resultado_push_notificacao_app,
        )
        from app.services.push_devices import (
            load_customer_push_targets,
            mark_push_target_result,
        )
        from app.services.order_push_notifications import send_expo_push

        app_notification = None
        try:
            app_notification = criar_notificacao_estoque_app(
                db=db,
                tenant_id=tenant_id,
                cliente=cliente,
                produto=produto,
                pendencia=pendencia,
            )
        except Exception:
            logger.exception(
                "[LISTA-ESPERA-PDV] Falha ao gravar notificacao no app tenant_id=%s cliente_id=%s produto_id=%s",
                tenant_id,
                getattr(cliente, "id", None),
                getattr(produto, "id", None),
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
            registrar_resultado_push_notificacao_app(
                app_notification,
                sent=False,
                error="Cliente sem dispositivo push",
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
                "pendencia_id": getattr(pendencia, "id", None),
            },
        }

        any_sent = False
        last_ticket_id = None
        last_error = None
        for target in targets:
            try:
                sent, ticket_id, error = send_expo_push(target.token, content)
            except Exception as exc:
                sent, ticket_id, error = False, None, str(exc)
            any_sent = any_sent or sent
            if sent and ticket_id:
                last_ticket_id = ticket_id
            if error:
                last_error = error
            mark_push_target_result(target, sent=sent, ticket_id=ticket_id, error=error)
        registrar_resultado_push_notificacao_app(
            app_notification,
            sent=any_sent,
            ticket_id=last_ticket_id,
            error=last_error,
        )
        return any_sent
    except Exception:
        logger.exception("Erro ao enviar push de pendencia")
        return False


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

    except Exception:
        logger.exception("Erro ao enviar WhatsApp")
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
