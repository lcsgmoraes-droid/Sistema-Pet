"""
Script para resetar a senha do usuário admin
"""
import sys
import os

# Adiciona o diretório backend ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_session
from app.models import User
from app.auth import hash_password, verify_password

def resetar_senha_admin():
    """Reseta a senha do admin para admin123"""
    session = next(get_session())
    
    try:
        # Buscar usuário admin
        admin = session.query(User).filter(User.email == "admin@test.com").first()
        
        if not admin:
            print("❌ Usuário admin@test.com não encontrado!")
            print("Criando usuário admin...")
            
            # Criar usuário admin
            nova_senha = "admin123"
            admin = User(
                email="admin@test.com",
                nome="Administrador",
                hashed_password=hash_password(nova_senha),
                is_admin=True,
                is_active=True
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)
            
            print(f"✅ Usuário admin criado com sucesso!")
            print(f"   Email: admin@test.com")
            print(f"   Senha: admin123")
        else:
            # Atualizar senha
            nova_senha = "admin123"
            admin.hashed_password = hash_password(nova_senha)
            admin.is_active = True
            admin.is_admin = True
            session.commit()
            
            print(f"✅ Senha do admin atualizada com sucesso!")
            print(f"   Email: {admin.email}")
            print(f"   Senha: admin123")
        
        # Verificar se a senha está correta
        print("\n🔍 Verificando senha...")
        if verify_password("admin123", admin.hashed_password):
            print("✅ Verificação OK - senha está correta!")
        else:
            print("❌ ERRO - senha não está funcionando!")
            
        # Mostrar informações do usuário
        print("\n📋 Informações do usuário:")
        print(f"   ID: {admin.id}")
        print(f"   Email: {admin.email}")
        print(f"   Nome: {admin.nome}")
        print(f"   Admin: {admin.is_admin}")
        print(f"   Ativo: {admin.is_active}")
        print(f"   Hash: {admin.hashed_password[:50]}...")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    resetar_senha_admin()
