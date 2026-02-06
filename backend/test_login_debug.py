"""
Teste de login com debugging completo
"""
import sys
import traceback
from sqlalchemy.orm import Session

# Adicionar o diretório backend ao path
sys.path.insert(0, '.')

from app.db import SessionLocal
from app import models
from app.auth import verify_password
from app.session_manager import create_session

def test_login():
    db = SessionLocal()
    try:
        email = "admin@test.com"
        password = "test123"
        
        print(f"🔍 Buscando usuário: {email}")
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if not user:
            print("❌ Usuário não encontrado")
            return
        
        print(f"✅ Usuário encontrado: ID={user.id}, Nome={user.nome}")
        
        print(f"🔐 Verificando senha...")
        if not verify_password(password, user.hashed_password):
            print("❌ Senha incorreta")
            return
        
        print("✅ Senha correta")
        
        print(f"📋 Buscando tenants do usuário...")
        user_tenants = db.query(models.UserTenant).filter(
            models.UserTenant.user_id == user.id
        ).all()
        
        print(f"✅ Tenants encontrados: {len(user_tenants)}")
        for ut in user_tenants:
            print(f"   - Tenant ID: {ut.tenant_id}, Role ID: {ut.role_id}")
        
        print(f"📝 Criando sessão...")
        db_session = create_session(
            db=db,
            user_id=user.id,
            ip_address="127.0.0.1",
            user_agent="Test",
            expires_in_days=30
        )
        
        print(f"✅ Sessão criada: ID={db_session.id}, JTI={db_session.token_jti}")
        
        print("\n✨ Teste concluído com sucesso!")
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        print("\n📋 Traceback completo:")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_login()
