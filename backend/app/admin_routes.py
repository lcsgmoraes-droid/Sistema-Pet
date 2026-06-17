"""
Rota administrativa: Inicializar templates de adquirentes

Executar UMA VEZ ao configurar o sistema ou adicionar novo tenant.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_session
from app.auth import get_current_user_and_tenant
from app.seed_adquirentes import criar_templates_adquirentes

router = APIRouter(prefix="/admin", tags=["Administração"])


@router.post("/seed/adquirentes")
def seed_adquirentes_templates(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria templates básicos de operadoras (Stone, Cielo, Rede).

    Executa UMA VEZ ao inicializar sistema.
    Não duplica se já existir.

    Requer: usuário autenticado com tenant selecionado.
    """
    _current_user, tenant_id = user_and_tenant

    resultado = criar_templates_adquirentes(db, tenant_id)

    return {
        "success": True,
        "message": "Templates de adquirentes inicializados",
        "total_criados": resultado["total_criados"],
        "adquirentes": resultado["adquirentes"],
    }
