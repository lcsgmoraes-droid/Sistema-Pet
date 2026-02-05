"""
AUDITORIA MULTI-TENANT — FASE 0
================================

O que este script faz:
- Carrega TODOS os models SQLAlchemy do projeto
- Verifica:
  1) Se herdam de BaseTenantModel
  2) Se possuem coluna tenant_id
- Mostra exatamente quais models estão IRREGULARES

⚠️ NÃO altera banco
⚠️ NÃO altera código
"""

import sys

try:
    from app.db import Base
except Exception as e:
    print("❌ ERRO ao importar Base (app.db)")
    print(e)
    sys.exit(1)

try:
    from app.base_models import BaseTenantModel
except Exception as e:
    print("❌ ERRO ao importar BaseTenantModel (app.base_models)")
    print(e)
    sys.exit(1)


def main():
    print("\n🔍 INICIANDO AUDITORIA MULTI-TENANT...\n")

    models = []
    for mapper in Base.registry.mappers:
        models.append(mapper.class_)

    print(f"📦 Total de models encontrados: {len(models)}\n")

    sem_base_tenant = []
    sem_tenant_id = []

    for model in models:
        table = getattr(model, "__table__", None)
        if table is None:
            continue

        if not issubclass(model, BaseTenantModel):
            sem_base_tenant.append(model.__name__)

        if "tenant_id" not in table.c:
            sem_tenant_id.append(model.__name__)

    print("🚨 MODELS QUE NÃO HERDAM DE BaseTenantModel:")
    if sem_base_tenant:
        for m in sem_base_tenant:
            print(f" - {m}")
    else:
        print(" ✅ Nenhum (OK)")

    print("\n🚨 MODELS SEM COLUNA tenant_id:")
    if sem_tenant_id:
        for m in sem_tenant_id:
            print(f" - {m}")
    else:
        print(" ✅ Nenhum (OK)")

    print("\n✅ AUDITORIA FINALIZADA\n")


if __name__ == "__main__":
    main()
