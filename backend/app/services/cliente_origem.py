"""Origem de aquisicao do cliente, independente do canal de cada venda."""

import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import BeforeValidator
from sqlalchemy import func

ORIGENS_CLIENTE = {
    "loja_fisica": "Loja Física",
    "ecommerce": "E-commerce",
    "app": "App",
    "ifood": "iFood",
    "whatsapp": "WhatsApp",
    "instagram": "Instagram",
    "indicacao": "Indicação",
}


def normalizar_origem_cliente(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Informe uma origem válida.")
    key = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    key = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
    aliases = {
        "loja": "loja_fisica",
        "pdv": "loja_fisica",
        "balcao": "loja_fisica",
        "site": "ecommerce",
        "web": "ecommerce",
        "e_commerce": "ecommerce",
        "aplicativo": "app",
        "i_food": "ifood",
        "whats_app": "whatsapp",
        "nao_identificada": None,
    }
    if not key or len(key) > 50:
        raise ValueError("A origem deve ter entre 1 e 50 caracteres.")
    return aliases.get(key, key)


OrigemCliente = Annotated[str | None, BeforeValidator(normalizar_origem_cliente)]


def nome_origem_cliente(value):
    return (
        ORIGENS_CLIENTE.get(value, value.replace("_", " ").capitalize())
        if value
        else "Não identificada"
    )


def opcoes_origem_cliente(db, model, tenant_ids):
    rows = (
        db.query(model.origem_cliente)
        .filter(
            model.tenant_id.in_(tenant_ids),
            model.origem_cliente.is_not(None),
        )
        .distinct()
        .all()
    )
    keys = list(ORIGENS_CLIENTE)
    keys.extend(sorted({origem for (origem,) in rows} - set(keys)))
    return [{"value": key, "label": nome_origem_cliente(key)} for key in keys]


def filtrar_origem_periodo(
    query, model, *, origem=None, inicio: date | None = None, fim: date | None = None
):
    """Datas de cadastro inclusivas no horario de Brasilia, comparadas em UTC."""
    if inicio and fim and inicio > fim:
        raise ValueError("A data inicial deve ser anterior ou igual à data final.")
    if origem is not None:
        query = query.filter(model.origem_cliente == normalizar_origem_cliente(origem))
    brasilia = ZoneInfo("America/Sao_Paulo")
    if inicio:
        query = query.filter(
            model.created_at
            >= datetime.combine(inicio, time.min, brasilia).astimezone(timezone.utc)
        )
    if fim:
        query = query.filter(
            model.created_at
            < datetime.combine(fim + timedelta(days=1), time.min, brasilia).astimezone(
                timezone.utc
            )
        )
    return query


def resumir_origens(query, model):
    rows = (
        query.with_entities(model.origem_cliente, func.count(model.id))
        .group_by(model.origem_cliente)
        .all()
    )
    return sorted(
        [
            {"origem": origem, "nome": nome_origem_cliente(origem), "total": total}
            for origem, total in rows
        ],
        key=lambda item: (-item["total"], item["nome"]),
    )
