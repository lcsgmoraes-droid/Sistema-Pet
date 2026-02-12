"""
Rota administrativa: Inicializar templates de adquirentes

Executar UMA VEZ ao configurar o sistema ou adicionar novo tenant.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_session
from app.auth_routes_multitenant import get_current_user
from app.seed_adquirentes import criar_templates_adquirentes

router = APIRouter(prefix="/api/admin", tags=["Administração"])


@router.post("/seed/adquirentes")
def seed_adquirentes_templates(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Cria templates básicos de operadoras (Stone, Cielo, Rede).
    
    Executa UMA VEZ ao inicializar sistema.
    Não duplica se já existir.
    
    Requer: Usuário autenticado (tenant_id)
    """
    
    tenant_id = current_user.get('tenant_id')
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant não identificado")
    
    resultado = criar_templates_adquirentes(db, tenant_id)
    
    return {
        "success": True,
        "message": "Templates de adquirentes inicializados",
        "total_criados": resultado["total_criados"],
        "adquirentes": resultado["adquirentes"]
    }
