"""Lista operacional de clientes sem compras recentes."""

from datetime import date, datetime, time, timedelta
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.clientes.common import _somente_digitos, _validar_tenant_e_obter_usuario
from app.db import get_session
from app.models import Cliente
from app.security.permissions_decorator import require_permission
from app.utils.timezone import now_brasilia
from app.vendas_models import Venda

router = APIRouter()
PRAZOS_INATIVIDADE = (30, 60, 90)


def _validar_dias_sem_compra(valor: int) -> int:
    if valor not in PRAZOS_INATIVIDADE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dias_sem_compra deve ser 30, 60 ou 90",
        )
    return valor


def _mensagem_sugerida(nome: str) -> str:
    primeiro_nome = (nome or "").strip().split(" ")[0] or "cliente"
    return (
        f"Olá, {primeiro_nome}! Sentimos sua falta por aqui. "
        "Posso ajudar com algo ou separar seus produtos de costume?"
    )


def _telefone_preferencial(telefone: Optional[str], celular: Optional[str]):
    for candidato in (celular, telefone):
        if len(_somente_digitos(candidato)) >= 10:
            return candidato
    return celular or telefone


def _montar_resultado_inativos(
    linhas,
    *,
    hoje: date,
    dias_sem_compra: int,
    pagina: int,
    por_pagina: int,
) -> dict:
    clientes = []
    for linha in linhas:
        ultima_compra = linha.ultima_compra
        ultima_compra_data = (
            ultima_compra.date()
            if isinstance(ultima_compra, datetime)
            else ultima_compra
        )
        total_gasto = float(linha.total_gasto or 0)
        total_compras = int(linha.total_compras or 0)
        telefone = _telefone_preferencial(linha.telefone, linha.celular)
        clientes.append(
            {
                "cliente_id": linha.cliente_id,
                "codigo": linha.codigo,
                "nome": linha.nome,
                "telefone": telefone,
                "email": linha.email,
                "ultima_compra": (ultima_compra.isoformat() if ultima_compra else None),
                "dias_sem_comprar": (
                    (hoje - ultima_compra_data).days if ultima_compra_data else None
                ),
                "total_compras": total_compras,
                "total_gasto": round(total_gasto, 2),
                "ticket_medio": round(
                    total_gasto / total_compras if total_compras else 0,
                    2,
                ),
                "mensagem_sugerida": _mensagem_sugerida(linha.nome),
            }
        )

    total = len(clientes)
    com_whatsapp = sum(
        1 for cliente in clientes if len(_somente_digitos(cliente["telefone"])) >= 10
    )
    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina

    return {
        "resumo": {
            "total_inativos": total,
            "com_whatsapp": com_whatsapp,
            "sem_whatsapp": total - com_whatsapp,
        },
        "clientes": clientes[inicio:fim],
        "paginacao": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": max(1, ceil(total / por_pagina)),
        },
        "filtro": {"dias_sem_compra": dias_sem_compra},
    }


@router.get("/inativos")
@require_permission("clientes.visualizar")
def listar_clientes_inativos(
    dias_sem_compra: int = Query(30),
    busca: Optional[str] = Query(None, max_length=120),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=10, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna clientes cuja ultima venda finalizada ultrapassou o prazo escolhido."""
    dias_sem_compra = _validar_dias_sem_compra(dias_sem_compra)
    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    hoje = now_brasilia().date()
    corte = datetime.combine(
        hoje - timedelta(days=dias_sem_compra),
        time.min,
    )

    query = (
        db.query(
            Cliente.id.label("cliente_id"),
            Cliente.codigo.label("codigo"),
            Cliente.nome.label("nome"),
            Cliente.telefone.label("telefone"),
            Cliente.celular.label("celular"),
            Cliente.email.label("email"),
            func.max(Venda.data_venda).label("ultima_compra"),
            func.sum(Venda.total).label("total_gasto"),
            func.count(Venda.id).label("total_compras"),
        )
        .join(
            Venda,
            (Venda.cliente_id == Cliente.id) & (Venda.tenant_id == tenant_id),
        )
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "cliente",
            Cliente.merged_into_id.is_(None),
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
            Venda.status == "finalizada",
        )
    )

    termo = (busca or "").strip()
    if termo:
        like = f"%{termo}%"
        query = query.filter(
            or_(
                Cliente.nome.ilike(like),
                Cliente.codigo.ilike(like),
                Cliente.telefone.ilike(like),
                Cliente.celular.ilike(like),
                Cliente.email.ilike(like),
            )
        )

    linhas = (
        query.group_by(
            Cliente.id,
            Cliente.codigo,
            Cliente.nome,
            Cliente.telefone,
            Cliente.celular,
            Cliente.email,
        )
        .having(func.max(Venda.data_venda) < corte)
        .order_by(func.max(Venda.data_venda).asc(), Cliente.nome.asc())
        .all()
    )

    return _montar_resultado_inativos(
        linhas,
        hoje=hoje,
        dias_sem_compra=dias_sem_compra,
        pagina=pagina,
        por_pagina=por_pagina,
    )
