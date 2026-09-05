"""Central de conferência do gestor, restrita à empresa e à permissão gerencial."""

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, raiseload

from app.auth.dependencies import get_current_user_and_tenant
from app.caixa.conferencia import instante_fechamento, instante_fechamento_sql, moeda
from app.caixa_models import Caixa
from app.db import get_session
from app.models import User, UserTenant
from app.security.permissions_decorator import require_permission_dependency
from app.vendas_models import Venda

router = APIRouter(
    prefix="/alertas-gestor",
    tags=["Alertas do gestor"],
    dependencies=[Depends(require_permission_dependency("relatorios.gerencial"))],
)
FUSO = ZoneInfo("America/Sao_Paulo")
CONFERENCIA_LEGADA = re.compile(
    r"\[Conferencia de abertura\] Caixa anterior #(\d+): R\$ (\d+\.\d{2}); "
    r"abertura: R\$ (\d+\.\d{2}); diferenca: R\$ ([+\-]?\d+\.\d{2})\."
)
JUSTIFICATIVA = re.compile(r"JUSTIFICATIVA\s*\([^\n)]*\)\s*:\s*(.+)", re.I | re.S)


def _data_iso(valor):
    if valor is None:
        return None
    # Datas de venda/abertura legadas são horários locais sem fuso.
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=FUSO)
    return valor.isoformat()


def _conferencia(caixa):
    if caixa.conferencia_abertura is not None:
        return caixa.conferencia_abertura, "registro"
    encontrados = list(CONFERENCIA_LEGADA.finditer(caixa.observacoes_abertura or ""))
    if not encontrados:
        return None, None
    numero, anterior, abertura, diferenca = encontrados[-1].groups()
    # Preserva a referência efetivamente exibida; não inventa vínculos históricos.
    return {
        "numero_caixa": int(numero),
        "valor_fechamento": float(anterior),
        "valor_abertura": float(abertura),
        "diferenca": float(diferenca),
    }, "observacao_historica"


def _alerta_abertura(caixa):
    conferencia, origem = _conferencia(caixa)
    if not conferencia or moeda(conferencia["diferenca"]) == 0:
        return None
    return {
        "id": f"abertura-{caixa.id}",
        "tipo": "diferenca_abertura",
        "data": _data_iso(caixa.data_abertura),
        "titulo": f"Abertura do caixa #{caixa.numero_caixa}",
        "operador_id": caixa.usuario_id,
        "operador": caixa.usuario_nome,
        "valor_referencia": conferencia["valor_fechamento"],
        "valor_informado": conferencia["valor_abertura"],
        "diferenca": conferencia["diferenca"],
        "referencia": conferencia,
        "origem": origem,
        "observacoes": caixa.observacoes_abertura,
        "caixa_id": caixa.id,
    }


def _alerta_fechamento(caixa):
    if caixa.valor_informado is None or caixa.valor_esperado is None:
        return None
    diferenca = moeda(caixa.valor_informado) - moeda(caixa.valor_esperado)
    if diferenca == 0:
        return None
    return {
        "id": f"fechamento-{caixa.id}",
        "tipo": "diferenca_fechamento",
        "data": _data_iso(instante_fechamento(caixa)),
        "titulo": f"Fechamento do caixa #{caixa.numero_caixa}",
        "operador_id": caixa.usuario_fechamento_id or caixa.usuario_id,
        "operador": caixa.usuario_fechamento_nome or caixa.usuario_nome,
        "valor_referencia": caixa.valor_esperado,
        "valor_informado": caixa.valor_informado,
        "diferenca": float(diferenca),
        "observacoes": caixa.observacoes_fechamento,
        "origem": "registro",
        "caixa_id": caixa.id,
    }


@router.get("")
def listar_alertas_gestor(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    tipo: Literal[
        "todos", "venda_justificada", "diferenca_abertura", "diferenca_fechamento"
    ] = "todos",
    operador_id: int | None = None,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    fim = data_fim or datetime.now(FUSO).date()
    inicio = data_inicio or (fim - timedelta(days=6))
    if inicio > fim or (fim - inicio).days > 92:
        raise HTTPException(
            422, "Selecione um período de até 93 dias, com início anterior ao fim."
        )
    inicio_local = datetime.combine(inicio, time.min)
    fim_local = datetime.combine(fim + timedelta(days=1), time.min)
    inicio_utc = inicio_local.replace(tzinfo=FUSO).astimezone(timezone.utc)
    fim_utc = fim_local.replace(tzinfo=FUSO).astimezone(timezone.utc)
    eventos = []

    aberturas = (
        db.query(Caixa)
        .filter(
            Caixa.tenant_id == tenant_id,
            Caixa.data_abertura >= inicio_local,
            Caixa.data_abertura < fim_local,
            or_(
                Caixa.conferencia_abertura.is_not(None),
                Caixa.observacoes_abertura.contains("[Conferencia de abertura]"),
            ),
        )
        .all()
    )
    for caixa in aberturas:
        evento = _alerta_abertura(caixa)
        if evento:
            eventos.append(evento)

    fechamentos = (
        db.query(Caixa)
        .filter(
            Caixa.tenant_id == tenant_id,
            Caixa.status == "fechado",
            instante_fechamento_sql() >= inicio_utc,
            instante_fechamento_sql() < fim_utc,
        )
        .all()
    )
    for caixa in fechamentos:
        evento = _alerta_fechamento(caixa)
        if evento:
            eventos.append(evento)

    vendas = (
        db.query(Venda, User.nome, User.username)
        .options(raiseload("*"))
        .outerjoin(
            UserTenant,
            and_(
                UserTenant.user_id == Venda.vendedor_id,
                UserTenant.tenant_id == tenant_id,
            ),
        )
        .outerjoin(User, User.id == UserTenant.user_id)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.data_venda >= inicio_local,
            Venda.data_venda < fim_local,
            Venda.status.in_(["finalizada", "baixa_parcial"]),
            Venda.observacoes.ilike("%JUSTIFICATIVA%"),
        )
        .all()
    )
    for venda, nome, username in vendas:
        justificativa = JUSTIFICATIVA.search(venda.observacoes or "")
        if justificativa:
            eventos.append(
                {
                    "id": f"venda-{venda.id}",
                    "tipo": "venda_justificada",
                    "data": _data_iso(venda.data_venda),
                    "titulo": f"Venda #{venda.numero_venda}",
                    "operador_id": venda.vendedor_id,
                    "operador": nome or username or f"Usuário #{venda.vendedor_id}",
                    "valor_informado": float(moeda(venda.total)),
                    "desconto": float(moeda(venda.desconto_valor)),
                    "observacoes": justificativa.group(1).strip(),
                    "venda_id": venda.id,
                    "origem": "registro",
                }
            )

    operadores = {evento["operador_id"]: evento["operador"] for evento in eventos}
    if operador_id is not None:
        eventos = [evento for evento in eventos if evento["operador_id"] == operador_id]
    resumo = {
        categoria: sum(e["tipo"] == categoria for e in eventos)
        for categoria in (
            "venda_justificada",
            "diferenca_abertura",
            "diferenca_fechamento",
        )
    }
    if tipo != "todos":
        eventos = [evento for evento in eventos if evento["tipo"] == tipo]
    eventos.sort(
        key=lambda e: (datetime.fromisoformat(e["data"]), e["id"]), reverse=True
    )
    total = len(eventos)
    return {
        "itens": eventos[(pagina - 1) * por_pagina : pagina * por_pagina],
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "resumo": resumo,
        "operadores": [
            {"id": id_, "nome": nome}
            for id_, nome in sorted(operadores.items(), key=lambda par: par[1])
        ],
    }
