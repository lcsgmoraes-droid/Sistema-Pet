"""Conferência rastreável de caixas, sem substituir fechamentos anteriores."""

import hashlib
import json
from datetime import date, datetime, timezone

from app.models import AuditLog
from app.caixa.conferencia import moeda
from app.utils.timezone import as_brasilia_naive


def assinatura_item(item: dict) -> str:
    # O estado da conferencia nao altera o conteudo financeiro conferido.
    # Mantem a assinatura legada dos itens sem metadados e permite recalcular
    # a assinatura do proprio item retornado pelo GET sem invalidar a revisao.
    conteudo = {
        campo: valor
        for campo, valor in item.items()
        if campo
        not in {
            "assinatura",
            "conferencia",
            "conferido",
            "estado_conferencia",
            "conferencia_alterada",
        }
    }
    return hashlib.sha256(
        json.dumps(conteudo, sort_keys=True, ensure_ascii=False, default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def estado_conferencia_salvo(dados: dict) -> str:
    estado = dados.get("estado")
    if estado in {"pendente", "ok", "divergencia"}:
        return estado
    return "ok" if dados.get("conferido") else "pendente"


def situacao_conferencia(assinatura: str, conferencia: dict | None) -> dict:
    dados = conferencia["dados"] if conferencia else {}
    alterada = bool(conferencia and dados.get("assinatura") != assinatura)
    estado = (
        estado_conferencia_salvo(dados) if conferencia and not alterada else "pendente"
    )
    return {
        "estado_conferencia": estado,
        "conferido": estado == "ok",
        "conferencia_alterada": alterada,
    }


def incluir_composicao_comercial(db, *, vendas, resumo, tenant_id):
    """Vincula o hash da venda aos mesmos valores comerciais vistos no caixa."""
    from app.services.faturamento_service import (
        montar_composicao_vendas,
        opcoes_composicao_vendas,
    )
    from app.vendas_models import Venda

    periodo = resumo["vendas_periodo"]
    composicoes = {item["venda_id"]: item for item in periodo["detalhes"]}
    faltantes = {item["venda_id"] for item in vendas} - composicoes.keys()
    if faltantes:
        # A auditoria tambem lista vendas antigas recebidas neste caixa. Elas
        # ficam fora do vendido do periodo, mas precisam de referencia propria
        # para conferir quitacao, beneficios e saldos sem consultas por linha.
        registros = (
            db.query(Venda)
            .options(*opcoes_composicao_vendas())
            .filter(Venda.tenant_id == tenant_id, Venda.id.in_(faltantes))
            .all()
        )
        extras = montar_composicao_vendas(
            db,
            tenant_id,
            registros,
            date.fromisoformat(periodo["data_inicio"]),
            date.fromisoformat(periodo["data_fim"]),
        )
        composicoes.update({item["venda_id"]: item for item in extras["detalhes"]})
    for venda in vendas:
        composicao = composicoes.get(venda["venda_id"])
        venda["composicao_comercial"] = (
            {
                **composicao,
                # Relacionamentos e recibos nao tem ORDER BY em todas as
                # origens legadas. Ordem de consulta nao e mudanca financeira.
                "pagamentos": sorted(
                    composicao["pagamentos"],
                    key=lambda item: (
                        item.get("data_pagamento") or "",
                        json.dumps(item, sort_keys=True, ensure_ascii=False),
                    ),
                ),
            }
            if composicao
            else None
        )
    return vendas


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
