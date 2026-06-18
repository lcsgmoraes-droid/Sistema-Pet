"""
Rotas para gerenciar integração com Bling
"""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.bling_integration import BlingAPI
from app.bling_flow_monitor_routes import (
    corrigir_incidente as corrigir_incidente_monitor,
    executar_auditoria as executar_auditoria_monitor,
    listar_eventos as listar_eventos_monitor,
    listar_incidentes as listar_incidentes_monitor,
    resolver_incidente as resolver_incidente_monitor,
    resumo_monitor as resumo_monitor_base,
)

router = APIRouter(prefix="/bling", tags=["Bling"])


def _carregar_controle_token_bling(token_control_file: Path) -> dict[str, object]:
    token_info = {
        "ultima_renovacao": None,
        "proxima_renovacao": None,
        "renovacoes_automaticas": 0,
    }

    if token_control_file.exists():
        with token_control_file.open("r", encoding="utf-8") as f:
            token_info = json.load(f)

    return token_info


@router.get("/naturezas-operacoes")
async def listar_naturezas(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as naturezas de operação cadastradas no Bling
    Use para descobrir o ID correto para configurar no sistema
    """
    try:
        bling = BlingAPI()
        resultado = bling.listar_naturezas_operacoes()

        # Extrair dados da resposta
        naturezas = resultado.get("data", [])

        return {
            "success": True,
            "total": len(naturezas),
            "naturezas": naturezas,
            "instrucoes": {
                "como_usar": "Copie o 'id' da natureza desejada e configure em BLING_NATUREZA_OPERACAO_ID no .env",
                "sugestao": "Procure por 'Venda de mercadoria' ou 'Venda presencial' ou 'Venda ao consumidor'",
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao listar naturezas: {str(e)}"
        )


@router.post("/renovar-token")
async def renovar_token(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
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
            "expires_in_hours": tokens.get("expires_in", 21600) / 3600,
            "new_access_token": tokens["access_token"][:50] + "...",
            "new_refresh_token": tokens["refresh_token"][:50] + "...",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao renovar token: {str(e)}")


@router.get("/teste-conexao")
async def testar_conexao(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Testa a conexão com a API do Bling e retorna status + info de renovação
    """
    try:
        # Tentar conectar
        bling = BlingAPI()
        resultado = bling.listar_naturezas_operacoes()

        # Carregar info de controle de token
        token_control_file = Path("bling_token_control.json")
        token_info = await asyncio.to_thread(
            _carregar_controle_token_bling,
            token_control_file,
        )

        return {
            "conectado": True,
            "message": "✅ Conexão com Bling OK!",
            "total_produtos_bling": resultado.get("data", [])
            and len(resultado.get("data", []))
            or 0,
            "ultima_renovacao": token_info.get("ultima_renovacao"),
            "proxima_renovacao": token_info.get("proxima_renovacao"),
            "renovacoes_automaticas": token_info.get("renovacoes_automaticas", 0),
            "temp_acesso_horas": 6,
        }
    except Exception as e:
        # Verificar se é erro de token expirado
        error_msg = str(e)
        if (
            "429" in error_msg
            or "TOO_MANY_REQUESTS" in error_msg
            or "Limite de requisi" in error_msg
        ):
            return {
                "conectado": True,
                "rate_limited": True,
                "message": "Conexao com o Bling valida, mas a API pediu uma pausa temporaria.",
                "detail": "A API do Bling respondeu com limite temporario de requisicoes. Isso nao significa token vencido.",
            }
        if (
            "401" in error_msg
            or "Unauthorized" in error_msg
            or "invalid_token" in error_msg
        ):
            return {
                "conectado": False,
                "message": "❌ Token expirado",
                "error": "Token expirado ou inválido",
                "detail": "Use o botão 'Renovar Token' para reconectar",
            }
        raise HTTPException(status_code=500, detail=f"Erro na conexão: {error_msg}")


@router.get("/monitor/resumo")
def resumo_monitor_compat(
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    return resumo_monitor_base(db=db, user_tenant=user_tenant)


@router.get("/monitor/incidentes")
def listar_incidentes_compat(
    status: str = Query("open"),
    severidade: str | None = Query(None),
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    return listar_incidentes_monitor(
        status=status,
        severidade=severidade,
        limite=limite,
        db=db,
        user_tenant=user_tenant,
    )


@router.get("/monitor/eventos")
def listar_eventos_compat(
    limite: int = Query(50, ge=1, le=200),
    tipo: str | None = Query(None),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    return listar_eventos_monitor(
        limite=limite,
        tipo=tipo,
        db=db,
        user_tenant=user_tenant,
    )


@router.post("/monitor/auditar")
def executar_auditoria_compat(
    dias: int = Query(7, ge=1, le=30),
    limite: int = Query(300, ge=1, le=1000),
    auto_fix: bool = Query(True),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    return executar_auditoria_monitor(
        dias=dias,
        limite=limite,
        auto_fix=auto_fix,
        db=db,
        user_tenant=user_tenant,
    )


@router.post("/monitor/incidentes/{incidente_id}/corrigir")
def corrigir_incidente_compat(
    incidente_id: int,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    return corrigir_incidente_monitor(
        incidente_id=incidente_id,
        db=db,
        user_tenant=user_tenant,
    )


@router.post("/monitor/incidentes/{incidente_id}/resolver")
def resolver_incidente_compat(
    incidente_id: int,
    nota: str | None = Query(None),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    return resolver_incidente_monitor(
        incidente_id=incidente_id,
        nota=nota,
        db=db,
        user_tenant=user_tenant,
    )
