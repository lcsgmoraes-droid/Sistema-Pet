"""
Script para tornar usuário admin
"""
import sys
sys.path.insert(0, '.')

from app.db import SessionLocal
from app.models import User

def tornar_admin():
    db = SessionLocal()
    
    try:
        # Buscar usuário
        user = db.query(User).filter(User.email == "admin@test.com").first()
        
        if not user:
            print("❌ Usuário admin@test.com não encontrado!")
            return
        
        # Tornar admin
        user.is_admin = True
        user.is_active = True
        db.commit()
        
        print("✅ Usuário atualizado com sucesso!")
        print(f"   Email: {user.email}")
        print(f"   Nome: {user.nome}")
        print(f"   Admin: {user.is_admin}")
        print(f"   Ativo: {user.is_active}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    tornar_admin()
