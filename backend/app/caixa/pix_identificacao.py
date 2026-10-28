"""Identificação manual de Pix, independente da quitação e do saldo do caixa."""

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import JSON, cast, func, or_
from sqlalchemy.orm import contains_eager

from app.caixa.auditoria import assinatura_item
from app.caixa.escopo import buscar_caixa_acessivel
from app.caixa.recebimentos import filtro_pagamentos_validos
from app.caixa_models import Caixa
from app.models import AuditLog
from app.vendas_models import Venda, VendaPagamento

ACAO_PIX = "caixa_pix_identificacao"
ENTIDADE_PIX = "pix_pagamento"


class AlteracaoIdentificacaoPixSchema(BaseModel):
    assinatura: str = Field(min_length=64, max_length=64)
    registro_id: int | None = Field(default=None, gt=0)
    estado: Literal["identificado", "nao_identificado"]
    justificativa: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validar_justificativa(self):
        self.justificativa = self.justificativa.strip()
        if not self.justificativa:
            raise ValueError("Informe a justificativa da identificação do Pix.")
        return self


class IdentificacaoPixSchema(AlteracaoIdentificacaoPixSchema):
    pagamento_id: int = Field(gt=0)


def item_pagamento_auditoria(pagamento):
    """O mesmo conteúdo financeiro é assinado no caixa e na central do gestor."""
    item = {
        **pagamento.to_dict(),
        "venda_id": pagamento.venda_id,
        "venda_numero": pagamento.venda.numero_venda,
        "data_movimento": pagamento.data_pagamento.isoformat()
        if pagamento.data_pagamento
        else None,
        "tipo": "estorno" if pagamento.valor < 0 else "recebimento",
        "descricao": (
            f"Estorno do recebimento da venda {pagamento.venda.numero_venda}"
            if pagamento.valor < 0
            else f"Recebimento da venda {pagamento.venda.numero_venda}"
        ),
        "natureza": "saida" if pagamento.valor < 0 else "entrada",
    }
    if str(pagamento.venda.status or "").strip().casefold() in {
        "cancelada",
        "cancelado",
    }:
        # A consulta histórica pode incluir o pagamento original de uma venda
        # cancelada. O controle só se aplica a recebimentos ainda ativos.
        item["identificacao_pix"] = None
    return item


def _filtro_pix_ativo():
    return (
        filtro_pagamentos_validos(),
        func.lower(func.trim(VendaPagamento.forma_pagamento)) == "pix",
        VendaPagamento.valor > 0,
        VendaPagamento.caixa_id.is_not(None),
        or_(
            Venda.status.is_(None),
            func.lower(func.trim(Venda.status)).notin_(["cancelada", "cancelado"]),
        ),
    )


def _dados_evento(evento):
    return json.loads(evento.new_value or "{}")


def _registro(evento):
    dados = _dados_evento(evento)
    data = evento.timestamp
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
    return {
        "registro_id": evento.id,
        "estado": dados["estado"],
        "justificativa": evento.details,
        "usuario_id": evento.user_id,
        "usuario_nome": dados.get("usuario_nome"),
        "data": data.isoformat(),
        "assinatura": dados.get("assinatura"),
    }


def _metadados(logs, assinatura=None):
    historico = [_registro(evento) for evento in logs]
    if not historico:
        return {
            "estado": "nao_conferido",
            "registro_id": None,
            "justificativa": None,
            "usuario_nome": None,
            "data": None,
            "pagamento_alterado": False,
            "historico": [],
        }
    atual = historico[0]
    alterado = assinatura is not None and atual["assinatura"] != assinatura
    return {
        **atual,
        "estado": "nao_conferido" if alterado else atual["estado"],
        "pagamento_alterado": alterado,
        "historico": historico,
    }


def carregar_identificacoes_pix(db, tenant_id, pagamentos):
    elegiveis = {
        item["id"]: item
        for item in pagamentos
        if str(item.get("forma_pagamento") or "").strip().casefold() == "pix"
        and item.get("valor", 0) > 0
        and item.get("identificacao_pix", True) is not None
    }
    if not elegiveis:
        return
    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.action == ACAO_PIX,
            AuditLog.entity_type == ENTIDADE_PIX,
            AuditLog.entity_id.in_(elegiveis),
        )
        .order_by(AuditLog.id.desc())
        .all()
    )
    por_pagamento = {}
    for evento in logs:
        por_pagamento.setdefault(evento.entity_id, []).append(evento)
    for pagamento_id, item in elegiveis.items():
        item["identificacao_pix"] = _metadados(
            por_pagamento.get(pagamento_id, []), item["assinatura"]
        )


def registrar_identificacao_pix(
    db, usuario_e_tenant, dados, *, caixa_id=None, acesso_gerencial=False
):
    usuario, tenant_id = usuario_e_tenant
    query = (
        db.query(VendaPagamento)
        .join(Venda, Venda.id == VendaPagamento.venda_id)
        .join(Caixa, Caixa.id == VendaPagamento.caixa_id)
        .options(contains_eager(VendaPagamento.venda).lazyload(Venda.contas_receber))
        .filter(
            VendaPagamento.id == dados.pagamento_id,
            VendaPagamento.tenant_id == tenant_id,
            Venda.tenant_id == tenant_id,
            Caixa.tenant_id == tenant_id,
            *_filtro_pix_ativo(),
        )
    )
    if caixa_id is not None:
        query = query.filter(VendaPagamento.caixa_id == caixa_id)
    pagamento = query.populate_existing().with_for_update(of=VendaPagamento).first()
    if pagamento is None:
        raise HTTPException(404, "Pagamento Pix ativo não encontrado neste caixa.")
    if not acesso_gerencial:
        caixa, _ = buscar_caixa_acessivel(
            db,
            caixa_id=pagamento.caixa_id,
            tenant_id=tenant_id,
            usuario_id=usuario.id,
        )
        if not caixa:
            raise HTTPException(404, "Caixa não encontrado")
    assinatura = assinatura_item(item_pagamento_auditoria(pagamento))
    if dados.assinatura != assinatura:
        raise HTTPException(
            409, "O pagamento mudou. Atualize os detalhes antes de identificar o Pix."
        )
    ultimo = (
        db.query(AuditLog)
        .filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.action == ACAO_PIX,
            AuditLog.entity_type == ENTIDADE_PIX,
            AuditLog.entity_id == pagamento.id,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    if dados.registro_id != (ultimo.id if ultimo else None):
        raise HTTPException(
            409, "A identificação do Pix mudou. Atualize antes de salvar."
        )
    anterior = _dados_evento(ultimo) if ultimo else None
    if (
        not anterior
        or anterior["estado"] != dados.estado
        or anterior.get("assinatura") != assinatura
    ):
        nome = (
            getattr(usuario, "nome", None)
            or getattr(usuario, "username", None)
            or getattr(usuario, "email", None)
        )
        novo = {
            "estado": dados.estado,
            "assinatura": assinatura,
            "caixa_id": pagamento.caixa_id,
            "pagamento_id": pagamento.id,
            "venda_id": pagamento.venda_id,
            "usuario_nome": nome,
        }
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                user_id=usuario.id,
                action=ACAO_PIX,
                entity_type=ENTIDADE_PIX,
                entity_id=pagamento.id,
                timestamp=datetime.now(timezone.utc),
                old_value=json.dumps(anterior, ensure_ascii=False)
                if anterior
                else None,
                new_value=json.dumps(novo, ensure_ascii=False),
                details=dados.justificativa,
            )
        )
    db.commit()
    item = {
        "id": pagamento.id,
        "forma_pagamento": pagamento.forma_pagamento,
        "valor": float(pagamento.valor),
        "assinatura": assinatura,
    }
    carregar_identificacoes_pix(db, tenant_id, [item])
    return {"success": True, "identificacao_pix": item["identificacao_pix"]}


def listar_pendencias_pix(db, tenant_id):
    """Último registro por pagamento em uma consulta; pendências não expiram."""
    # SQLite armazena JSON como texto e CAST(... AS JSON) o converte em número.
    # Em produção PostgreSQL a extração exige o cast do campo Text para JSON.
    estado_sql = (
        func.json_extract(AuditLog.new_value, "$.estado")
        if db.get_bind().dialect.name == "sqlite"
        else cast(AuditLog.new_value, JSON)["estado"].as_string()
    )
    ultimos = (
        db.query(func.max(AuditLog.id).label("id"))
        .filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.action == ACAO_PIX,
            AuditLog.entity_type == ENTIDADE_PIX,
        )
        .group_by(AuditLog.entity_id)
        .subquery()
    )
    registros = (
        db.query(AuditLog, VendaPagamento, Caixa.numero_caixa)
        .join(ultimos, ultimos.c.id == AuditLog.id)
        .join(VendaPagamento, VendaPagamento.id == AuditLog.entity_id)
        .join(Venda, Venda.id == VendaPagamento.venda_id)
        .join(Caixa, Caixa.id == VendaPagamento.caixa_id)
        .options(contains_eager(VendaPagamento.venda).lazyload(Venda.contas_receber))
        .filter(
            AuditLog.tenant_id == tenant_id,
            VendaPagamento.tenant_id == tenant_id,
            Venda.tenant_id == tenant_id,
            Caixa.tenant_id == tenant_id,
            estado_sql == "nao_identificado",
            *_filtro_pix_ativo(),
        )
        .all()
    )
    alertas = []
    for evento, pagamento, numero_caixa in registros:
        dados = _dados_evento(evento)
        assinatura = assinatura_item(item_pagamento_auditoria(pagamento))
        identificacao = _metadados([evento], assinatura)
        alertas.append(
            {
                "id": f"pix-{pagamento.id}",
                "tipo": "pix_nao_identificado",
                "data": identificacao["data"],
                "dataidentificacao": identificacao["data"],
                "titulo": f"Pix não identificado — venda #{pagamento.venda.numero_venda}",
                "operador_id": evento.user_id,
                "operador": dados.get("usuario_nome"),
                "justificativa": evento.details,
                "observacoes": evento.details,
                "caixa_id": pagamento.caixa_id,
                "numero_caixa": numero_caixa,
                "venda_id": pagamento.venda_id,
                "numero_venda": pagamento.venda.numero_venda,
                "pagamento_id": pagamento.id,
                "forma_pagamento": pagamento.forma_pagamento,
                "valor": float(pagamento.valor),
                "valor_informado": float(pagamento.valor),
                "assinatura": assinatura,
                "registro_id": evento.id,
                "identificacao_pix": identificacao,
                "origem": "registro",
                "independe_periodo": True,
            }
        )
    return alertas


def carregar_historico_alertas_pix(db, tenant_id, alertas):
    """Histórico completo somente da página visível, nunca de todas as pendências."""
    itens = [
        {
            "id": alerta["pagamento_id"],
            "forma_pagamento": alerta["forma_pagamento"],
            "valor": alerta["valor"],
            "assinatura": alerta["assinatura"],
        }
        for alerta in alertas
        if alerta["tipo"] == "pix_nao_identificado"
    ]
    carregar_identificacoes_pix(db, tenant_id, itens)
    por_pagamento = {item["id"]: item["identificacao_pix"] for item in itens}
    for alerta in alertas:
        if alerta["tipo"] == "pix_nao_identificado":
            alerta["identificacao_pix"] = por_pagamento[alerta["pagamento_id"]]
