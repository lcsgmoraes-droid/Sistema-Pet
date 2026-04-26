"""Enfileiramento de campanhas de retorno do Banho & Tosa."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.banho_tosa_retornos import listar_sugestoes_retorno
from app.banho_tosa_retornos_templates import (
    normalizar_canal,
    obter_template_retorno,
    renderizar_template_retorno,
    template_aplicavel,
)
from app.campaigns.models import NotificationChannelEnum, NotificationQueue
from app.models import Cliente


def enfileirar_notificacoes_retorno(
    db: Session,
    tenant_id,
    *,
    tipos: list[str] | None = None,
    dias_antecedencia: int = 7,
    limit: int = 100,
    canal: str = "app",
    template_id: int | None = None,
) -> dict:
    template = obter_template_retorno(db, tenant_id, template_id, ativo=True) if template_id else None
    canal = template.canal if template else normalizar_canal(canal)
    sugestoes = listar_sugestoes_retorno(db, tenant_id, dias=max(dias_antecedencia, 0), limit=limit)["itens"]
    emails = _emails_clientes(db, tenant_id, sugestoes) if canal == "email" else {}
    tipos_set = set(tipos or [])
    resultado = {"processados": 0, "enfileirados": 0, "ignorados": 0, "sem_destino": 0}
    agora = datetime.now()

    for item in sugestoes:
        if not _deve_processar(item, tipos_set, dias_antecedencia, template):
            continue
        resultado["processados"] += 1
        email = emails.get(item["cliente_id"]) if canal == "email" else None
        if canal == "email" and not email:
            resultado["sem_destino"] += 1
            continue
        keys = _idempotency_keys(tenant_id, item, canal, template_id)
        if db.query(NotificationQueue.id).filter(NotificationQueue.idempotency_key.in_(keys)).first():
            resultado["ignorados"] += 1
            continue
        assunto, mensagem = renderizar_template_retorno(template, item)
        db.add(NotificationQueue(
            tenant_id=tenant_id,
            idempotency_key=keys[0],
            customer_id=item["cliente_id"],
            channel=_canal_fila(canal),
            subject=assunto,
            body=mensagem,
            email_address=email,
            scheduled_at=agora,
        ))
        resultado["enfileirados"] += 1

    db.commit()
    return resultado


def _deve_processar(item: dict, tipos_set: set[str], dias_antecedencia: int, template) -> bool:
    if tipos_set and item["tipo"] not in tipos_set:
        return False
    if not template_aplicavel(template, item["tipo"]):
        return False
    if item.get("dias_para_acao") is not None and item["dias_para_acao"] > dias_antecedencia:
        return False
    return True


def _canal_fila(canal: str):
    return NotificationChannelEnum.email if canal == "email" else NotificationChannelEnum.push


def _emails_clientes(db: Session, tenant_id, sugestoes: list[dict]) -> dict[int, str]:
    ids = {item["cliente_id"] for item in sugestoes if item.get("cliente_id")}
    if not ids:
        return {}
    rows = db.query(Cliente.id, Cliente.email).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.id.in_(ids),
    ).all()
    return {cliente_id: email for cliente_id, email in rows if email}


def _idempotency_keys(tenant_id, item: dict, canal: str, template_id: int | None) -> list[str]:
    ref = item.get("referencia_id") or item["id"]
    data = item.get("data_referencia")
    base = f"bt-retorno:{tenant_id}:{item['tipo']}:{ref}:{data}"
    key = f"{base}:{canal}:{template_id or 'padrao'}"
    return [key, base] if canal == "app" and not template_id else [key]
