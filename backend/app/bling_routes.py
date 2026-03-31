"""
Rotas para gerenciar integração com Bling
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_session
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.bling_integration import BlingAPI
from app.bling_flow_monitor_models import BlingFlowEvent, BlingFlowIncident
from app.bling_flow_monitor_routes import (
    _mapa_numeros_pedidos,
    _mapa_numeros_notas_cache,
    _nf_numero_payload,
    _numero_pedido_loja_payload,
    _primeiro_preenchido,
    _serializar_data_monitor,
    _texto,
)
from app.services.bling_flow_monitor_service import (
    auditar_fluxo_bling,
    autocorrigir_incidente,
    obter_resumo_monitoramento,
    resolver_incidente_por_id,
)

router = APIRouter(prefix="/bling", tags=["Bling"])


@router.get("/naturezas-operacoes")
async def listar_naturezas(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as naturezas de operação cadastradas no Bling
    Use para descobrir o ID correto para configurar no sistema
    """
    try:
        bling = BlingAPI()
        resultado = bling.listar_naturezas_operacoes()
        
        # Extrair dados da resposta
        naturezas = resultado.get('data', [])
        
        return {
            "success": True,
            "total": len(naturezas),
            "naturezas": naturezas,
            "instrucoes": {
                "como_usar": "Copie o 'id' da natureza desejada e configure em BLING_NATUREZA_OPERACAO_ID no .env",
                "sugestao": "Procure por 'Venda de mercadoria' ou 'Venda presencial' ou 'Venda ao consumidor'"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar naturezas: {str(e)}")


@router.post("/renovar-token")
async def renovar_token(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Renova o access token do Bling usando o refresh token
    Atualiza automaticamente o .env com os novos tokens
    """
    try:
        bling = BlingAPI()
        tokens = bling.renovar_access_token()
        
        return {
            "success": True,
            "message": "Token renovado com sucesso!",
            "expires_in_hours": tokens.get('expires_in', 21600) / 3600,
            "new_access_token": tokens['access_token'][:50] + "...",
            "new_refresh_token": tokens['refresh_token'][:50] + "..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao renovar token: {str(e)}")


@router.get("/teste-conexao")
async def testar_conexao(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Testa a conexão com a API do Bling e retorna status + info de renovação
    """
    from datetime import datetime
    from pathlib import Path
    import json
    
    try:
        # Tentar conectar
        bling = BlingAPI()
        resultado = bling.listar_naturezas_operacoes()
        
        # Carregar info de controle de token
        token_control_file = Path("bling_token_control.json")
        token_info = {
            "ultima_renovacao": None,
            "proxima_renovacao": None,
            "renovacoes_automaticas": 0
        }
        
        if token_control_file.exists():
            with open(token_control_file, 'r') as f:
                token_info = json.load(f)
        
        return {
            "conectado": True,
            "message": "✅ Conexão com Bling OK!",
            "total_produtos_bling": resultado.get('data', []) and len(resultado.get('data', [])) or 0,
            "ultima_renovacao": token_info.get('ultima_renovacao'),
            "proxima_renovacao": token_info.get('proxima_renovacao'),
            "renovacoes_automaticas": token_info.get('renovacoes_automaticas', 0),
            "temp_acesso_horas": 6
        }
    except Exception as e:
        # Verificar se é erro de token expirado
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "invalid_token" in error_msg:
            return {
                "conectado": False,
                "message": "❌ Token expirado",
                "error": "Token expirado ou inválido",
                "detail": "Use o botão 'Renovar Token' para reconectar"
            }
        raise HTTPException(status_code=500, detail=f"Erro na conexão: {error_msg}")


@router.get("/monitor/resumo")
def resumo_monitor_compat(
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    return obter_resumo_monitoramento(db, tenant_id=tenant_id)


@router.get("/monitor/incidentes")
def listar_incidentes_compat(
    status: str = Query("open"),
    severidade: str | None = Query(None),
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    query = db.query(BlingFlowIncident).filter(BlingFlowIncident.tenant_id == tenant_id)
    if status:
        query = query.filter(BlingFlowIncident.status == status)
    if severidade:
        query = query.filter(BlingFlowIncident.severity == severidade)

    incidentes = (
        query.order_by(BlingFlowIncident.last_seen_em.desc(), BlingFlowIncident.id.desc())
        .limit(limite)
        .all()
    )
    registros = [
        {
            "id": incidente.id,
            "code": incidente.code,
            "severity": incidente.severity,
            "status": incidente.status,
            "title": incidente.title,
            "message": incidente.message,
            "suggested_action": incidente.suggested_action,
            "auto_fixable": incidente.auto_fixable,
            "auto_fix_status": incidente.auto_fix_status,
            "pedido_integrado_id": incidente.pedido_integrado_id,
            "pedido_bling_id": incidente.pedido_bling_id,
            "nf_bling_id": incidente.nf_bling_id,
            "sku": incidente.sku,
            "occurrences": incidente.occurrences,
            "first_seen_em": _serializar_data_monitor(incidente.first_seen_em),
            "last_seen_em": _serializar_data_monitor(incidente.last_seen_em),
            "resolved_em": _serializar_data_monitor(incidente.resolved_em),
            "details": incidente.details or {},
        }
        for incidente in incidentes
    ]
    mapa_numeros = _mapa_numeros_pedidos(db, tenant_id, registros)
    mapa_notas = _mapa_numeros_notas_cache(db, tenant_id, registros)
    for registro in registros:
        info = mapa_numeros.get(
            (registro.get("pedido_integrado_id"), registro.get("pedido_bling_id"))
        ) or mapa_numeros.get((registro.get("pedido_integrado_id"), None)) or mapa_numeros.get(
            (None, registro.get("pedido_bling_id"))
        )
        info_nf = mapa_notas.get(_texto(registro.get("nf_bling_id")) or "") or {}
        detalhes = registro.get("details") or {}
        registro["pedido_bling_numero"] = (
            (info or {}).get("pedido_bling_numero")
            or _texto(
                _primeiro_preenchido(
                    detalhes.get("pedido_bling_numero"),
                    (detalhes.get("nf_detectada") or {}).get("pedido_bling_numero"),
                )
            )
        )
        registro["numero_pedido_loja"] = (
            (info or {}).get("numero_pedido_loja")
            or _texto(
                _primeiro_preenchido(
                    detalhes.get("numero_pedido_loja"),
                    (detalhes.get("nf_detectada") or {}).get("numero_pedido_loja"),
                )
            )
            or (info_nf or {}).get("numero_pedido_loja")
        )
        registro["nf_numero"] = (
            _texto(
                _primeiro_preenchido(
                    detalhes.get("nf_numero"),
                    (detalhes.get("nf_detectada") or {}).get("numero"),
                )
            )
            or (info_nf or {}).get("nf_numero")
            or (info or {}).get("nf_numero")
        )
        registro["pedido_status_atual"] = (info or {}).get("pedido_status_atual")
    return registros


@router.get("/monitor/eventos")
def listar_eventos_compat(
    limite: int = Query(50, ge=1, le=200),
    tipo: str | None = Query(None),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    query = db.query(BlingFlowEvent).filter(BlingFlowEvent.tenant_id == tenant_id)
    if tipo:
        query = query.filter(BlingFlowEvent.event_type == tipo)

    eventos = (
        query.order_by(BlingFlowEvent.processed_at.desc(), BlingFlowEvent.id.desc())
        .limit(limite)
        .all()
    )
    registros = [
        {
            "id": evento.id,
            "source": evento.source,
            "event_type": evento.event_type,
            "entity_type": evento.entity_type,
            "status": evento.status,
            "severity": evento.severity,
            "message": evento.message,
            "error_message": evento.error_message,
            "pedido_integrado_id": evento.pedido_integrado_id,
            "pedido_bling_id": evento.pedido_bling_id,
            "nf_bling_id": evento.nf_bling_id,
            "sku": evento.sku,
            "auto_fix_applied": evento.auto_fix_applied,
            "processed_at": _serializar_data_monitor(evento.processed_at),
            "payload": evento.payload or {},
        }
        for evento in eventos
    ]
    mapa_numeros = _mapa_numeros_pedidos(db, tenant_id, registros)
    mapa_notas = _mapa_numeros_notas_cache(db, tenant_id, registros)
    for registro in registros:
        info = mapa_numeros.get(
            (registro.get("pedido_integrado_id"), registro.get("pedido_bling_id"))
        ) or mapa_numeros.get((registro.get("pedido_integrado_id"), None)) or mapa_numeros.get(
            (None, registro.get("pedido_bling_id"))
        )
        info_nf = mapa_notas.get(_texto(registro.get("nf_bling_id")) or "") or {}
        payload = registro.get("payload") or {}
        registro["pedido_bling_numero"] = (
            (info or {}).get("pedido_bling_numero")
            or _texto(
                _primeiro_preenchido(
                    payload.get("pedido_bling_numero"),
                    (payload.get("pedido") or {}).get("numero"),
                )
            )
        )
        registro["numero_pedido_loja"] = (
            (info or {}).get("numero_pedido_loja")
            or _numero_pedido_loja_payload(payload)
            or (info_nf or {}).get("numero_pedido_loja")
        )
        registro["nf_numero"] = (
            _nf_numero_payload(payload)
            or (info_nf or {}).get("nf_numero")
            or (info or {}).get("nf_numero")
        )
        registro["pedido_status_atual"] = (info or {}).get("pedido_status_atual") or _texto(payload.get("pedido_status_atual"))
    return registros


@router.post("/monitor/auditar")
def executar_auditoria_compat(
    dias: int = Query(7, ge=1, le=30),
    limite: int = Query(300, ge=1, le=1000),
    auto_fix: bool = Query(True),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    return auditar_fluxo_bling(
        db,
        tenant_id=tenant_id,
        dias=dias,
        limite=limite,
        auto_fix=auto_fix,
    )


@router.post("/monitor/incidentes/{incidente_id}/corrigir")
def corrigir_incidente_compat(
    incidente_id: int,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    incidente = db.query(BlingFlowIncident).filter(
        BlingFlowIncident.id == incidente_id,
        BlingFlowIncident.tenant_id == tenant_id,
    ).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente nao encontrado")
    if not incidente.auto_fixable:
        raise HTTPException(status_code=400, detail="Incidente sem autocorrecao disponivel")
    return autocorrigir_incidente(db, incidente)


@router.post("/monitor/incidentes/{incidente_id}/resolver")
def resolver_incidente_compat(
    incidente_id: int,
    nota: str | None = Query(None),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    incidente = resolver_incidente_por_id(db, tenant_id, incidente_id, resolution_note=nota)
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente nao encontrado")
    return {
        "status": "ok",
        "incidente_id": incidente.id,
        "resolved_em": _serializar_data_monitor(incidente.resolved_em),
    }
