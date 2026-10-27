"""OPS: consumo de WhatsApp por loja, tarifas da Meta e fechamento mensal (repasse).

Fluxo: cadastrar tarifas -> acompanhar o consumo do mes -> fechar o mes (fotografia
imutavel com margem e valor de repasse) -> informar a fatura da Meta de cada loja
e conferir a divergencia. Os dados das lojas sao lidos uma loja por vez.
"""

from __future__ import annotations

import json
import os
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Tenant
from app.services.ops_tenant_log_service import registrar_alteracoes
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant
from app.whatsapp.consumo_models import (
    CATEGORIAS_DE_TARIFA,
    WhatsAppFechamento,
    WhatsAppTarifa,
)
from app.whatsapp.ledger_service import (
    periodo_do_mes,
    recalcular_custos,
    resumo_do_periodo,
)

LIMITE_DE_LOJAS = 500
CATEGORIA_DO_LOG = "consumo_whatsapp"
CENTAVO = Decimal("0.01")


class ConsumoError(Exception):
    def __init__(self, mensagem: str, status_code: int = 422):
        self.status_code = status_code
        super().__init__(mensagem)


def _mes_texto(inicio) -> str:
    return f"{inicio.year:04d}-{inicio.month:02d}"


def _dinheiro(valor: Any) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def margem_padrao() -> Decimal:
    """Margem de repasse padrao (%), por ambiente, enquanto o modelo de cobranca nao fecha."""
    try:
        return Decimal(os.getenv("WHATSAPP_REPASSE_MARGEM_PERCENT", "0") or "0")
    except ArithmeticError:
        return Decimal(0)


# --- tarifas ----------------------------------------------------------------------


def listar_tarifas(db: Session) -> list[dict[str, Any]]:
    linhas = (
        db.query(WhatsAppTarifa)
        .order_by(WhatsAppTarifa.categoria, WhatsAppTarifa.vigente_desde.desc())
        .all()
    )
    return [
        {
            "id": linha.id,
            "categoria": linha.categoria,
            "valor": float(linha.valor),
            "moeda": linha.moeda,
            "vigente_desde": linha.vigente_desde.isoformat(),
            "criado_por": linha.criado_por,
        }
        for linha in linhas
    ]


def cadastrar_tarifa(
    db: Session, *, categoria: str, valor: Any, vigente_desde: date, admin_email: str
) -> WhatsAppTarifa:
    """Nova tarifa a partir de uma data. Nunca sobrescreve: o historico fica."""
    if categoria not in CATEGORIAS_DE_TARIFA:
        raise ConsumoError(
            f"Categoria inválida. Use uma de: {', '.join(CATEGORIAS_DE_TARIFA)}."
        )
    try:
        preco = Decimal(str(valor))
    except ArithmeticError as erro:
        raise ConsumoError("Informe o valor em reais, por exemplo 0.36.") from erro
    if preco < 0 or preco > Decimal(100):
        raise ConsumoError("O valor por mensagem deve estar entre 0 e 100 reais.")
    existente = (
        db.query(WhatsAppTarifa)
        .filter(
            WhatsAppTarifa.categoria == categoria,
            WhatsAppTarifa.vigente_desde == vigente_desde,
        )
        .first()
    )
    if existente is not None:
        raise ConsumoError(
            "Já existe uma tarifa desta categoria para essa data. Use uma data de vigência nova.",
            409,
        )
    tarifa = WhatsAppTarifa(
        categoria=categoria,
        valor=preco,
        vigente_desde=vigente_desde,
        criado_por=admin_email,
    )
    db.add(tarifa)
    db.flush()
    return tarifa


# --- consumo do mes ---------------------------------------------------------------


def _fechamento_para_dict(f: WhatsAppFechamento) -> dict[str, Any]:
    return {
        "id": f.id,
        "mes": f.mes,
        "custo_estimado": float(f.custo_estimado),
        "margem_percentual": float(f.margem_percentual),
        "valor_repasse": float(f.valor_repasse),
        "fatura_meta": float(f.fatura_meta) if f.fatura_meta is not None else None,
        "divergencia": float(f.divergencia) if f.divergencia is not None else None,
        "conferido": bool(f.conferido),
        "observacao": f.observacao,
        "fechado_por": f.fechado_por,
        "fechado_em": f.fechado_em.isoformat() if f.fechado_em else None,
    }


def consumo_do_mes(db: Session, mes: str | None) -> dict[str, Any]:
    """Resumo de cada loja no mes (ao vivo) e o fechamento, quando ja existir."""
    inicio, fim = periodo_do_mes(mes)
    texto_mes = _mes_texto(inicio)
    fechados = {
        str(f.tenant_id): f
        for f in db.query(WhatsAppFechamento).filter(
            WhatsAppFechamento.mes == texto_mes
        )
    }
    lojas = db.query(Tenant).order_by(Tenant.name).limit(LIMITE_DE_LOJAS).all()
    itens = []
    totais = {"enviadas": 0, "recebidas": 0, "falhas": 0, "cobraveis": 0}
    custo_total = Decimal(0)
    for tenant in lojas:
        tenant_id = UUID(str(tenant.id))
        with tenant_context(tenant_id):
            sync_rls_tenant(db, tenant_id)
            resumo = resumo_do_periodo(db, tenant_id, inicio, fim)
        movimento = resumo["totais"]
        fechamento = fechados.get(str(tenant_id))
        if not (movimento["enviadas"] or movimento["recebidas"]) and fechamento is None:
            continue
        itens.append(
            {
                "loja_id": str(tenant_id),
                "loja_nome": tenant.name,
                **resumo,
                "fechamento": _fechamento_para_dict(fechamento) if fechamento else None,
            }
        )
        for chave in totais:
            totais[chave] += movimento[chave]
        custo_total += _dinheiro(resumo["custo_estimado"])
    return {
        "mes": texto_mes,
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "lojas": itens,
        "totais": {**totais, "custo_estimado": float(custo_total)},
        "tarifas": listar_tarifas(db),
        "margem_padrao": float(margem_padrao()),
    }


# --- fechamento ---------------------------------------------------------------------


def fechar_mes(
    db: Session, *, mes: str, margem_percentual: Any, admin: Any
) -> dict[str, Any]:
    """Fotografa o consumo do mes de cada loja com movimento. Mes ja fechado nao muda."""
    inicio, fim = periodo_do_mes(mes)
    texto_mes = _mes_texto(inicio)
    try:
        margem = Decimal(str(margem_percentual))
    except ArithmeticError as erro:
        raise ConsumoError("Margem inválida.") from erro
    if margem < 0 or margem > Decimal(1000):
        raise ConsumoError("A margem deve estar entre 0% e 1000%.")

    ja_fechados = {
        str(f.tenant_id)
        for f in db.query(WhatsAppFechamento).filter(
            WhatsAppFechamento.mes == texto_mes
        )
    }
    lojas = db.query(Tenant).order_by(Tenant.name).limit(LIMITE_DE_LOJAS).all()
    novos, ignorados = 0, 0
    for tenant in lojas:
        tenant_id = UUID(str(tenant.id))
        if str(tenant_id) in ja_fechados:
            ignorados += 1
            continue
        with tenant_context(tenant_id):
            sync_rls_tenant(db, tenant_id)
            recalcular_custos(db, tenant_id, inicio, fim)
            db.flush()
            resumo = resumo_do_periodo(db, tenant_id, inicio, fim)
        totais = resumo["totais"]
        if not (totais["enviadas"] or totais["recebidas"]):
            continue
        custo = _dinheiro(resumo["custo_estimado"])
        repasse = (custo * (Decimal(1) + margem / Decimal(100))).quantize(
            CENTAVO, rounding=ROUND_HALF_UP
        )
        db.add(
            WhatsAppFechamento(
                tenant_id=tenant_id,
                mes=texto_mes,
                enviadas=totais["enviadas"],
                recebidas=totais["recebidas"],
                falhas=totais["falhas"],
                cobraveis=totais["cobraveis"],
                cobraveis_sem_tarifa=totais["cobraveis_sem_tarifa"],
                por_categoria=json.dumps(resumo["cobraveis_por_categoria"]),
                custo_estimado=custo,
                margem_percentual=margem,
                valor_repasse=repasse,
                fechado_por=getattr(admin, "email", "desconhecido"),
            )
        )
        registrar_alteracoes(
            db,
            tenant_id=str(tenant_id),
            admin=admin,
            categoria=CATEGORIA_DO_LOG,
            antes={f"fechamento {texto_mes}": None},
            depois={f"fechamento {texto_mes}": f"repasse R$ {repasse}"},
        )
        novos += 1
    db.flush()
    return {"mes": texto_mes, "fechados_agora": novos, "ja_fechados": ignorados}


def informar_fatura(
    db: Session,
    *,
    fechamento_id: int,
    fatura_meta: Any,
    observacao: str | None,
    admin: Any,
) -> dict[str, Any]:
    """Registra a fatura real da Meta da loja e calcula a divergencia com o estimado."""
    fechamento = db.get(WhatsAppFechamento, fechamento_id)
    if fechamento is None:
        raise ConsumoError("Fechamento não encontrado.", 404)
    try:
        valor = _dinheiro(fatura_meta)
    except ArithmeticError as erro:
        raise ConsumoError("Informe o valor da fatura em reais.") from erro
    if valor < 0:
        raise ConsumoError("O valor da fatura não pode ser negativo.")
    antes = fechamento.fatura_meta
    fechamento.fatura_meta = valor
    fechamento.divergencia = valor - fechamento.custo_estimado
    fechamento.conferido = True
    fechamento.observacao = (observacao or "").strip()[:1000] or None
    registrar_alteracoes(
        db,
        tenant_id=str(fechamento.tenant_id),
        admin=admin,
        categoria=CATEGORIA_DO_LOG,
        antes={f"fatura da Meta {fechamento.mes}": antes},
        depois={f"fatura da Meta {fechamento.mes}": valor},
    )
    db.flush()
    return _fechamento_para_dict(fechamento)
