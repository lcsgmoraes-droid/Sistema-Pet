"""
Resetar senha do admin para admin123
"""
import sys
sys.path.insert(0, '.')

from app.db import SessionLocal
from app.models import User
from app.auth import hash_password

def reset_senha():
    db = SessionLocal()
    
    try:
        admin = db.query(User).filter(User.email == "admin@test.com").first()
        
        if not admin:
            print("❌ Admin não encontrado!")
            return
        
        # Atualizar senha
        admin.hashed_password = hash_password("admin123")
        db.commit()
        
        print("✅ Senha atualizada com sucesso!")
        print(f"   Email: admin@test.com")
        print(f"   Nova senha: admin123")
        print(f"   User ID: {admin.id}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_senha()
