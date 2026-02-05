import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuração do banco
DATABASE_URL = "postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def criar_permissoes():
    db = SessionLocal()
    try:
        # Permissões a criar
        novas_permissoes = [
            {
                'code': 'ia.fluxo_caixa',
                'description': 'Acesso ao fluxo de caixa preditivo com IA'
            },
            {
                'code': 'ia.whatsapp',
                'description': 'Acesso e configuração do bot WhatsApp'
            },
            {
                'code': 'compras.gerenciar',
                'description': 'Acesso completo ao módulo de compras'
            },
        ]
        
        print("📝 Criando permissões de IA e Compras...\n")
        
        for perm in novas_permissoes:
            # Verificar se já existe
            check = db.execute(text("""
                SELECT id FROM permissions WHERE code = :code
            """), {"code": perm['code']})
            
            if check.fetchone():
                print(f"ℹ️  Permissão '{perm['code']}' já existe")
            else:
                # Criar permissão
                db.execute(text("""
                    INSERT INTO permissions (code, description, created_at)
                    VALUES (:code, :description, NOW())
                """), perm)
                print(f"✅ Permissão '{perm['code']}' criada")
        
        db.commit()
        
        print("\n🎯 Atualizando roles com novas permissões...\n")
        
        # Buscar tenant_id
        tenant_result = db.execute(text("SELECT id FROM tenants LIMIT 1"))
        tenant_id = tenant_result.fetchone()[0]
        
        # Adicionar permissões aos roles apropriados
        updates = [
            # Admin e Gerente podem ver tudo de IA
            {'role': 'admin', 'permissions': ['ia.fluxo_caixa', 'ia.whatsapp', 'compras.gerenciar']},
            {'role': 'gerente', 'permissions': ['ia.fluxo_caixa', 'ia.whatsapp', 'compras.gerenciar']},
            # Estoque pode gerenciar compras
            {'role': 'estoque', 'permissions': ['compras.gerenciar']},
        ]
        
        for update in updates:
            role_result = db.execute(text("""
                SELECT id FROM roles WHERE name = :role_name AND tenant_id = :tenant_id
            """), {"role_name": update['role'], "tenant_id": tenant_id})
            
            role_row = role_result.fetchone()
            if not role_row:
                continue
                
            role_id = role_row[0]
            
            for perm_code in update['permissions']:
                # Buscar permission_id
                perm_result = db.execute(text("""
                    SELECT id FROM permissions WHERE code = :code
                """), {"code": perm_code})
                
                perm_row = perm_result.fetchone()
                if not perm_row:
                    continue
                    
                permission_id = perm_row[0]
                
                # Verificar se já existe
                check = db.execute(text("""
                    SELECT 1 FROM role_permissions 
                    WHERE role_id = :role_id 
                    AND permission_id = :permission_id
                    AND tenant_id = :tenant_id
                """), {"role_id": role_id, "permission_id": permission_id, "tenant_id": tenant_id})
                
                if check.fetchone():
                    print(f"   ℹ️  {update['role']} já tem {perm_code}")
                else:
                    db.execute(text("""
                        INSERT INTO role_permissions (role_id, permission_id, tenant_id)
                        VALUES (:role_id, :permission_id, :tenant_id)
                    """), {"role_id": role_id, "permission_id": permission_id, "tenant_id": tenant_id})
                    print(f"   ✅ {update['role']} recebeu {perm_code}")
        
        db.commit()
        print("\n✅ Permissões configuradas com sucesso!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    criar_permissoes()
