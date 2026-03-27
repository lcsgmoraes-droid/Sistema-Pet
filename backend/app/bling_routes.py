"""
Rotas para gerenciar integração com Bling
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_session
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.bling_integration import BlingAPI

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
