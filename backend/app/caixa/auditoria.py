"""Conferência rastreável de caixas, sem substituir fechamentos anteriores."""

import hashlib
import json
from datetime import datetime, timezone

from app.models import AuditLog
from app.caixa.conferencia import moeda
from app.utils.timezone import as_brasilia_naive


def assinatura_item(item: dict) -> str:
    return hashlib.sha256(
        json.dumps(item, sort_keys=True, ensure_ascii=False, default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def reunir_espelhos_baixa_lote(movimentacoes, pagamentos):
    """Reúne somente espelhos eletrônicos identificados do recebimento em lote."""
    disponiveis = list(pagamentos)
    resultado = []
    espelhos = []
    for movimento in movimentacoes:
        forma = str(movimento.get("forma_pagamento") or "").strip().casefold()
        espelho = (
            movimento.get("tipo") == "venda"
            and movimento.get("categoria") == "venda"
            and str(movimento.get("descricao") or "").startswith("Baixa venda #")
            and forma != "dinheiro"
        )
        correspondentes = []
        if espelho and movimento.get("data_movimento"):
            for pagamento in disponiveis:
                if not pagamento.get("data_movimento"):
                    continue
                segundos = abs(
                    (
                        as_brasilia_naive(
                            datetime.fromisoformat(movimento["data_movimento"])
                        )
                        - as_brasilia_naive(
                            datetime.fromisoformat(pagamento["data_movimento"])
                        )
                    ).total_seconds()
                )
                if (
                    pagamento["venda_id"] == movimento.get("venda_id")
                    and str(pagamento["forma_pagamento"]).strip().casefold() == forma
                    and moeda(pagamento["valor"]) == moeda(movimento["valor"])
                    and segundos <= 2
                ):
                    correspondentes.append(pagamento)
        if len(correspondentes) == 1:
            pagamento = correspondentes[0]
            disponiveis.remove(pagamento)
            espelhos.append({**movimento, "pagamento_id": pagamento["id"]})
        else:
            resultado.append(movimento)
    return resultado, espelhos


def snapshot_caixa(db, caixa_id, usuario_e_tenant):
    from app.caixa_routes import obter_resumo_caixa, listar_vendas_caixa

    return {
        "resumo": obter_resumo_caixa(
            caixa_id, db=db, current_user_and_tenant=usuario_e_tenant
        ),
        "vendas": listar_vendas_caixa(
            caixa_id, db=db, current_user_and_tenant=usuario_e_tenant
        ),
    }


def registrar_evento_caixa(
    db, *, caixa_id, usuario, tenant_id, acao, motivo=None, anterior=None, novo=None
):
    # Na mesma transação da alteração: falha de auditoria impede apagar o fechamento.
    nome = usuario.nome or getattr(usuario, "username", None) or usuario.email
    evento = AuditLog(
        tenant_id=tenant_id,
        user_id=usuario.id,
        action=acao,
        entity_type="caixa",
        entity_id=caixa_id,
        old_value=json.dumps(anterior, ensure_ascii=False, default=str)
        if anterior
        else None,
        new_value=json.dumps(
            {**(novo or {}), "usuario_nome": nome}, ensure_ascii=False, default=str
        ),
        details=motivo,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(evento)
    return evento
