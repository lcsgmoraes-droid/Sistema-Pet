"""Exceção explícita para recebimento monetário maior que a venda líquida."""

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.models import AuditLog
from app.services.venda_descontos import moeda

ACAO_EXCESSO = "venda_pagamento_excedente_justificado"


class ContextoPagamentoExcedenteSchema(BaseModel):
    total_venda: float = Field(ge=0, allow_inf_nan=False)
    total_ja_pago: float = Field(ge=0, allow_inf_nan=False)
    total_novos_pagamentos: float = Field(ge=0, allow_inf_nan=False)
    crediario_pendente: float = Field(default=0, ge=0, allow_inf_nan=False)


def snapshot_pagamentos_excedente(db, venda, tenant_id):
    from app.services.faturamento_service import montar_composicao_vendas
    from app.vendas.recebimentos_independentes import (
        carregar_recebimentos_independentes,
    )
    from app.services.faturamento_composicao import (
        _agrupar_formas_pagamento,
        _contas_planos,
        _serializar_formas_pagamento,
        eh_plano,
        normalizar,
    )
    from app.vendas.status_pagamento import pagamento_valido_para_saldo

    dia = venda.data_venda.date()
    composicao = montar_composicao_vendas(db, tenant_id, [venda], dia, dia)
    pagamentos = list(composicao["detalhes"][0]["pagamentos"])
    pagamentos.extend(
        carregar_recebimentos_independentes(
            db,
            venda=venda,
            tenant_id=tenant_id,
            pagamentos_identificados=pagamentos,
            contas=venda.contas_receber,
        )
    )
    monetario = sum(
        (moeda(p["valor"]) for p in pagamentos if p["tipo"] == "pagamento"), moeda(0)
    )
    beneficios = sum(
        (moeda(p["valor"]) for p in pagamentos if p["tipo"] == "beneficio"), moeda(0)
    )
    ativos = [p for p in venda.pagamentos if pagamento_valido_para_saldo(p)]
    planos = sum((moeda(p.valor) for p in ativos if eh_plano(p)), moeda(0))
    contas = _contas_planos(venda, ativos)
    recebido_planos = sum((moeda(c.valor_recebido) for c in contas), moeda(0))
    if not venda.pagamentos:
        from app.financeiro_models import FormaPagamento

        formas_ids = {
            c.forma_pagamento_id for c in contas if c.forma_pagamento_id is not None
        }
        tipos_formas = (
            dict(
                db.query(FormaPagamento.id, FormaPagamento.tipo)
                .filter(
                    FormaPagamento.tenant_id == tenant_id,
                    FormaPagamento.id.in_(formas_ids),
                )
                .all()
            )
            if formas_ids
            else {}
        )
        contas_legadas_plano = [
            c
            for c in contas
            if normalizar(tipos_formas.get(c.forma_pagamento_id))
            in {"crediario", "boleto"}
        ]
        planos = sum((moeda(c.valor_final) for c in contas_legadas_plano), moeda(0))
        recebido_planos = sum(
            (moeda(c.valor_recebido) for c in contas_legadas_plano), moeda(0)
        )
    return {
        "total_ja_pago": max(monetario, moeda(0)) + max(beneficios, moeda(0)),
        "recebido_monetario": max(monetario, moeda(0)),
        "creditos_utilizados": max(beneficios, moeda(0)),
        "crediario_pendente": max(planos - recebido_planos, moeda(0)),
        "formas_pagamento": _serializar_formas_pagamento(
            _agrupar_formas_pagamento(pagamentos)
        ),
        "pagamentos": pagamentos,
    }


def validar_excesso_pagamento(
    *,
    total_venda,
    total_ja_pago,
    total_novos_pagamentos,
    justificativa=None,
    contexto=None,
    crediario_pendente=0,
):
    fotografia = {
        "total_venda": float(moeda(total_venda)),
        "total_ja_pago": float(moeda(total_ja_pago)),
        "total_novos_pagamentos": float(moeda(total_novos_pagamentos)),
        "crediario_pendente": float(moeda(crediario_pendente)),
    }
    excesso = moeda(total_ja_pago) + moeda(total_novos_pagamentos) - moeda(total_venda)
    if excesso <= 0:
        return None
    motivo = justificativa.strip() if isinstance(justificativa, str) else ""
    informado = contexto.model_dump() if isinstance(contexto, BaseModel) else contexto
    corresponde = False
    if informado is not None:
        try:
            if not isinstance(informado, dict):
                raise TypeError
            corresponde = all(
                moeda(
                    informado.get(campo, 0)
                    if campo == "crediario_pendente"
                    else informado[campo]
                )
                == moeda(valor)
                for campo, valor in fotografia.items()
            )
        except (KeyError, TypeError, ValueError):
            corresponde = False
        if not corresponde:
            raise HTTPException(
                409,
                {
                    "code": "PAGAMENTO_EXCEDENTE_DESATUALIZADO",
                    "mensagem": "Os valores mudaram. Confira novamente o excedente e informe a justificativa.",
                    "contexto_pagamento_excedente": fotografia,
                    "excedente": float(excesso),
                },
            )
    if not corresponde or not 10 <= len(motivo) <= 1000:
        raise HTTPException(
            409,
            {
                "code": "PAGAMENTO_EXCEDENTE_REQUER_JUSTIFICATIVA",
                "mensagem": "O recebimento excede o saldo da venda. Confira os valores e justifique a exceção (10 a 1000 caracteres).",
                "contexto_pagamento_excedente": fotografia,
                "excedente": float(excesso),
            },
        )
    return {
        "contexto": fotografia,
        "excedente": float(excesso),
        "justificativa": motivo,
    }


def registrar_excesso_pagamento(
    db,
    *,
    venda,
    tenant_id,
    usuario_id,
    usuario_nome,
    validacao,
    origem,
    pagamentos_antes=None,
    pagamentos_novos=None,
    alteracao_venda=None,
):
    if not validacao:
        return None
    evento = AuditLog(
        tenant_id=tenant_id,
        user_id=usuario_id,
        action=ACAO_EXCESSO,
        entity_type="vendas",
        entity_id=venda.id,
        timestamp=datetime.now(timezone.utc),
        details=validacao["justificativa"],
        old_value=json.dumps(
            {"pagamentos": pagamentos_antes or []}, ensure_ascii=False, default=str
        ),
        new_value=json.dumps(
            {
                "origem": origem,
                "usuario_nome": usuario_nome,
                "numero_venda": venda.numero_venda,
                "contexto": validacao["contexto"],
                "excedente": validacao["excedente"],
                "pagamentos": pagamentos_novos or [],
                "alteracao_venda": alteracao_venda,
                "destinacao": "recebimento_excedente_sem_destinacao_automatica",
            },
            ensure_ascii=False,
            default=str,
        ),
    )
    db.add(evento)
    return evento


def buscar_justificativa_excesso(db, *, venda, tenant_id, contexto):
    evento = (
        db.query(AuditLog)
        .filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.action == ACAO_EXCESSO,
            AuditLog.entity_type == "vendas",
            AuditLog.entity_id == venda.id,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    if not evento:
        return None
    dados = json.loads(evento.new_value or "{}")
    anterior = dados.get("contexto", {})
    if not all(
        campo in anterior and moeda(anterior[campo]) == moeda(valor)
        for campo, valor in contexto.items()
    ):
        return None
    motivo = (evento.details or "").strip()
    return motivo if 10 <= len(motivo) <= 1000 else None
