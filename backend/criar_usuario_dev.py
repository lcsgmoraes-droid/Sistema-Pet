from app.models.tenant import Tenant
from app.models.user import User
from app.database import SessionLocal
from app.auth import hash_password
import uuid

db = SessionLocal()

try:
    # Criar tenant se não existir
    tenant = db.query(Tenant).first()
    if not tenant:
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name='Pet Shop Teste',
            status='active',
            plan='free'
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        print(f'✅ Tenant criado: {tenant.name} (ID: {tenant.id})')
    else:
        print(f'✅ Tenant já existe: {tenant.name} (ID: {tenant.id})')

    # Criar usuário admin se não existir
    user = db.query(User).filter(User.email == 'admin@test.com').first()
    if not user:
        user = User(
            email='admin@test.com',
            nome='Administrador',
            hashed_password=hash_password('test123'),
            tenant_id=tenant.id,
            is_admin=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        print(f'✅ Usuário criado: {user.email} / Senha: test123')
    else:
        # Atualizar senha
        user.hashed_password = hash_password('test123')
        db.commit()
        print(f'✅ Senha do usuário atualizada: {user.email} / Senha: test123')

except Exception as e:
    print(f'❌ Erro: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
