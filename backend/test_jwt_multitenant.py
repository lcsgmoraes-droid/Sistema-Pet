"""
Teste controlado do JWT Multi-Tenant + RBAC
"""
from datetime import timedelta
from app.auth.core import create_access_token, JWT_SECRET_KEY, ALGORITHM
from jose import jwt

print("===================================================")
print(" TESTE CONTROLADO — JWT MULTI-TENANT + RBAC")
print("===================================================\n")

# Dados fake (não vêm do banco)
user_id = "user-test-123"
tenant_id = "tenant-test-456"
role = "owner"

token = create_access_token(
    data={"sub": user_id},
    expires_delta=timedelta(minutes=30),
    tenant_id=tenant_id,
    role=role,
)

print("🔐 TOKEN GERADO:\n")
print(token)
print("\n---------------------------------------------------")

decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])

print("📦 PAYLOAD DECODIFICADO:\n")
for k, v in decoded.items():
    print(f"{k}: {v}")

print("\n===================================================")
print("FIM DO TESTE")
print("COPIE TODO O OUTPUT E DEVOLVA AO ARQUITETO")
print("===================================================")
