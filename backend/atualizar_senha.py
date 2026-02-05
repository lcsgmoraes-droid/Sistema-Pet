import bcrypt
from app.database import SessionLocal
from app.models import User

# Gerar hash correto
senha = 'test123'
senha_bytes = senha.encode('utf-8')[:72]
senha_hash = bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode('utf-8')

print(f"Hash gerado: {senha_hash}")

# Atualizar no banco
db = SessionLocal()
try:
    user = db.query(User).filter(User.email == 'admin@test.com').first()
    if user:
        user.hashed_password = senha_hash
        db.commit()
        print(f"✅ Senha atualizada para: admin@test.com")
        print(f"   Senha: test123")
    else:
        print("❌ Usuário não encontrado")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
