import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuração do banco
DATABASE_URL = "postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def add_produtos_visualizar():
    db = SessionLocal()
    try:
        # Buscar IDs necessários
        result = db.execute(text("""
            SELECT 
                r.id as role_id,
                p.id as permission_id,
                r.tenant_id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'Role Teste'
            AND p.code = 'produtos.visualizar'
        """))
        
        row = result.fetchone()
        if not row:
            print("❌ Role ou permissão não encontrada!")
            return
            
        role_id = row.role_id
        permission_id = row.permission_id
        tenant_id = row.tenant_id
        
        # Verificar se já existe
        check = db.execute(text("""
            SELECT 1 FROM role_permissions 
            WHERE role_id = :role_id 
            AND permission_id = :permission_id
            AND tenant_id = :tenant_id
        """), {"role_id": role_id, "permission_id": permission_id, "tenant_id": tenant_id})
        
        if check.fetchone():
            print("ℹ️  Permissão 'produtos.visualizar' já existe na Role Teste")
            return
        
        # Adicionar permissão
        db.execute(text("""
            INSERT INTO role_permissions (role_id, permission_id, tenant_id)
            VALUES (:role_id, :permission_id, :tenant_id)
        """), {"role_id": role_id, "permission_id": permission_id, "tenant_id": tenant_id})
        
        db.commit()
        print("✅ Permissão 'produtos.visualizar' adicionada à Role Teste")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_produtos_visualizar()
