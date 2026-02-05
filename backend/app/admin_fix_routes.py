"""
Endpoint temporário para corrigir sequências do banco de dados
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_session
from app.auth import get_current_user_and_tenant

router = APIRouter(prefix="/admin/fix", tags=["Admin - Correções"])

@router.post("/sequences")
def fix_sequences(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Corrige sequências desincronizadas no PostgreSQL
    """
    current_user, tenant_id = user_and_tenant
    
    results = {}
    tables_to_fix = ['pets', 'clientes', 'produtos', 'vendas']
    
    for table_name in tables_to_fix:
        try:
            # Obter maior ID
            result = db.execute(text(f"SELECT MAX(id) FROM {table_name}"))
            max_id = result.fetchone()[0]
            
            if max_id is None:
                max_id = 0
            
            # Ajustar sequência
            next_id = max_id + 1
            seq_result = db.execute(
                text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), :next_id, false)"),
                {"next_id": next_id}
            )
            db.commit()
            
            new_value = seq_result.fetchone()[0]
            results[table_name] = {
                "max_id": max_id,
                "next_id": new_value,
                "status": "✅ OK"
            }
        except Exception as e:
            results[table_name] = {
                "status": "❌ ERRO",
                "error": str(e)
            }
    
    return {
        "message": "Sequências corrigidas",
        "results": results
    }
