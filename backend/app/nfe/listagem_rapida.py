"""Consulta paginada local; sincronizacao remota separada da abertura da tela."""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session, defer

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.nfe.listagem_base import (
    _canal_label,
    _canal_slug,
    _planejar_sincronizacao_bling_nfes,
)
from app.nfe.listagem_sync import (
    _enriquecer_notas_com_vendas,
    _sincronizar_cache_nfes_com_bling,
    _sincronizar_fontes_locais_nfe_em_cache,
)
from app.nfe_cache_models import BlingNotaFiscalCache as Nota
from app.services.bling_tenant_guard import tenant_pode_usar_bling_global
from app.services.nfe_cache_service import (
    FONTES_NFE_LOCAIS,
    obter_estado_cache_notas,
    serializar_nota_cache,
)
from app.tenancy.context import tenant_context

router = APIRouter()


def consultar_pagina(
    db,
    tenant_id,
    *,
    pagina=1,
    por_pagina=50,
    canal=None,
    busca=None,
    situacao=None,
    data_inicial=None,
    data_final=None,
):
    query = db.query(Nota).filter(Nota.tenant_id == tenant_id)
    if not tenant_pode_usar_bling_global(tenant_id):
        query = query.filter(Nota.source.in_(FONTES_NFE_LOCAIS))
    valores_canais = [
        valor for (valor,) in query.with_entities(Nota.canal).distinct().all()
    ]
    canais = sorted({_canal_slug(valor) or "sem_canal" for valor in valores_canais})
    if canal == "sem_canal":
        query = query.filter(or_(Nota.canal.is_(None), Nota.canal == ""))
    elif canal:
        aliases = [
            valor
            for valor in valores_canais
            if _canal_slug(valor) == _canal_slug(canal)
        ]
        query = query.filter(Nota.canal.in_(aliases))
    if situacao:
        query = query.filter(func.lower(Nota.status) == situacao.lower())
    if data_inicial:
        query = query.filter(
            Nota.data_emissao >= datetime.combine(data_inicial, time.min)
        )
    if data_final:
        query = query.filter(
            Nota.data_emissao
            < datetime.combine(data_final + timedelta(days=1), time.min)
        )
    if busca and busca.strip():
        termo = (
            busca.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        query = query.filter(
            or_(
                *[
                    coluna.ilike(f"%{termo}%", escape="\\")
                    for coluna in (
                        Nota.numero,
                        Nota.serie,
                        cast(Nota.cliente, String),
                        Nota.numero_pedido_loja,
                    )
                ]
            )
        )
    total = query.count()
    registros = (
        query.options(defer(Nota.resumo_payload), defer(Nota.detalhe_payload))
        .order_by(
            Nota.data_emissao.desc().nullslast(), Nota.bling_id.desc(), Nota.id.desc()
        )
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )
    notas = [serializar_nota_cache(nota) for nota in registros]
    _enriquecer_notas_com_vendas(db, tenant_id, notas)
    return {
        "notas": notas,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "canais": [
            {
                "value": c,
                "label": _canal_label(c, c) if c != "sem_canal" else "Sem canal",
            }
            for c in canais
        ],
    }


@router.get("/lista")
def listar_pagina(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=100),
    canal: str | None = None,
    busca: str | None = Query(None, max_length=150),
    situacao: str | None = None,
    data_inicial: date | None = None,
    data_final: date | None = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    return consultar_pagina(
        db,
        user_and_tenant[1],
        pagina=pagina,
        por_pagina=por_pagina,
        canal=canal,
        busca=busca,
        situacao=situacao,
        data_inicial=data_inicial,
        data_final=data_final,
    )


@router.post("/atualizar-lista")
def atualizar_lista(
    force_refresh: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    with tenant_context(tenant_id):
        estado = obter_estado_cache_notas(db, tenant_id)
        _sincronizar_fontes_locais_nfe_em_cache(db, tenant_id, estado_cache=estado)
        db.commit()
        remoto = tenant_pode_usar_bling_global(tenant_id)
        atualizar, inicio, fim, _ = _planejar_sincronizacao_bling_nfes(
            force_refresh=force_refresh,
            data_inicial=None,
            data_final=None,
            cache_total=estado.get("total", 0),
            cache_intervalo_tem_dados=bool(estado.get("total")),
            ultimo_sync=estado.get("ultimo_sync"),
            ultima_data_emissao=estado.get("ultima_data_emissao"),
        )
        ok = True
        if remoto and atualizar:
            ok, _ = _sincronizar_cache_nfes_com_bling(
                db,
                tenant_id,
                data_inicial=inicio,
                data_final=fim,
                enriquecer_detalhes=False,
            )
        return {
            "success": ok,
            "mensagem": "Notas atualizadas."
            if ok
            else "O Bling não respondeu. As notas já disponíveis continuam acessíveis.",
        }
