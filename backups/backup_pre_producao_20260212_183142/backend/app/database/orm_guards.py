"""
ORM Guards - Proteções automáticas para operações de banco de dados
"""
from sqlalchemy import event
from sqlalchemy.orm import Session


# 🔒 GUARDA ABSOLUTO DE IDENTITY (ANTI DUPLICATE PK)
# Garante que o PostgreSQL gere o ID automaticamente
# e impede qualquer insert com ID manual.

@event.listens_for(Session, "before_flush")
def force_identity_ids(session, flush_context, instances):
    """
    Força todos os IDs a serem None antes do flush.
    Qualquer entidade nova com atributo "id" DEVE ter id=None
    para o PostgreSQL gerar via IDENTITY.
    
    EXCEÇÃO: Tenant usa UUID manual (String), não IDENTITY.
    
    Isso previne erros de UniqueViolation causados por sequences dessincronizadas.
    """
    for obj in session.new:
        # Pular Tenant - usa UUID manual
        if obj.__class__.__name__ == 'Tenant':
            continue
            
        # Qualquer entidade nova com atributo "id"
        # DEVE ter id=None para o PostgreSQL gerar via IDENTITY
        if hasattr(obj, "id"):
            obj.id = None
