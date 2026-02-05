import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuração do banco
DATABASE_URL = "postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def check_user_permissions():
    db = SessionLocal()
    try:
        # Buscar usuário atacadaopetpp@gmail.com
        result = db.execute(text("""
            SELECT 
                u.id as user_id,
                u.email,
                r.name as role_name,
                array_agg(p.code) as permissions
            FROM users u
            LEFT JOIN user_tenants ut ON ut.user_id = u.id
            LEFT JOIN roles r ON r.id = ut.role_id
            LEFT JOIN role_permissions rp ON rp.role_id = r.id
            LEFT JOIN permissions p ON p.id = rp.permission_id
            WHERE u.email = 'atacadaopetpp@gmail.com'
            GROUP BY u.id, u.email, r.name
        """))
        
        user = result.fetchone()
        if user:
            print(f"\n👤 Usuário: {user.email}")
            print(f"🎭 Role: {user.role_name}")
            print(f"🔑 Permissões ({len([p for p in user.permissions if p])} total):")
            
            if user.permissions and user.permissions[0]:
                for perm in sorted(user.permissions):
                    if perm:
                        print(f"   ✅ {perm}")
            else:
                print("   ❌ NENHUMA PERMISSÃO ENCONTRADA!")
                
            # Verificar permissões específicas
            perms_list = user.permissions or []
            print("\n🔍 Verificação específica:")
            print(f"   clientes.visualizar: {'✅' if 'clientes.visualizar' in perms_list else '❌'}")
            print(f"   produtos.visualizar: {'✅' if 'produtos.visualizar' in perms_list else '❌'}")
            print(f"   vendas.criar: {'✅' if 'vendas.criar' in perms_list else '❌'}")
        else:
            print("❌ Usuário não encontrado!")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_user_permissions()
