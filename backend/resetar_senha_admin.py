import sys
sys.path.append('.')

from app.database import SessionLocal
from app.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def resetar_senha():
    db = SessionLocal()
    try:
        # Buscar admin
        admin = db.query(User).filter(User.email == "admin@test.com").first()
        
        if admin:
            # Nova senha: admin123
            nova_senha_hash = pwd_context.hash("admin123")
            admin.senha = nova_senha_hash
            db.commit()
            print(f"✅ Senha do usuário '{admin.nome}' ({admin.email}) resetada para: admin123")
        else:
            print("❌ Usuário admin@test.com não encontrado")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    resetar_senha()
