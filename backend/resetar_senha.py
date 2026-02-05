"""
Script para resetar senha do admin
"""
import sys
sys.path.insert(0, '.')

from app.db import SessionLocal
from app.models import User
from app.auth import hash_password

def resetar_senha():
    db = SessionLocal()
    
    try:
        # Buscar usuário
        user = db.query(User).filter(User.email == "admin@test.com").first()
        
        if not user:
            print("❌ Usuário admin@test.com não encontrado!")
            return
        
        # Resetar senha
        user.hashed_password = hash_password("teste123")
        user.is_admin = True
        user.is_active = True
        db.commit()
        
        print("✅ Senha resetada com sucesso!")
        print(f"   Email: admin@test.com")
        print(f"   Senha: teste123")
        print(f"   Admin: {user.is_admin}")
        print(f"   Ativo: {user.is_active}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    resetar_senha()
