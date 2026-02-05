# -*- coding: utf-8 -*-
from app.main import app

print("✅ Backend carregado com sucesso!")
print(f"✅ Total de rotas: {len(app.routes)}")

extrato_routes = [r for r in app.routes if 'extrato' in str(r.path)]
print(f"✅ Rotas de extrato: {len(extrato_routes)}")
for r in extrato_routes:
    print(f"  - {r.methods} {r.path}")
