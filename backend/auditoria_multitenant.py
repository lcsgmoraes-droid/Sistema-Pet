"""
Auditoria completa de Multi-Tenant no banco de dados
"""
from app.db import Base

print("\n==============================================================")
print("🔍 AUDITORIA TOTAL — MULTI-TENANT / MODELS / RELACIONAMENTOS")
print("==============================================================\n")

print("1) LISTAGEM COMPLETA DAS TABELAS E COLUNAS (SQLAlchemy Models)\n")

for table_name, table in Base.metadata.tables.items():
    print(f"\n📦 TABELA: {table_name}")
    for column in table.columns:
        flags = []
        if column.primary_key:
            flags.append("PK")
        if column.foreign_keys:
            flags.append("FK")
        nullable = "NULL" if column.nullable else "NOT NULL"
        print(f"  - {column.name:<25} {str(column.type):<20} {nullable:<10} {' '.join(flags)}")

print("\n--------------------------------------------------------------")
print("2) VERIFICAÇÃO DE ISOLAMENTO MULTI-TENANT (tenant_id / empresa)\n")

suspects = ["tenant_id", "empresa_id", "company_id"]

for table_name, table in Base.metadata.tables.items():
    found = [c.name for c in table.columns if c.name in suspects]
    if found:
        print(f"✅ {table_name}: possui {found}")
    else:
        print(f"❌ {table_name}: NÃO possui tenant_id")

print("\n--------------------------------------------------------------")
print("3) MAPEAMENTO DE RELACIONAMENTOS (FOREIGN KEYS)\n")

for table_name, table in Base.metadata.tables.items():
    for column in table.columns:
        for fk in column.foreign_keys:
            print(f"🔗 {table_name}.{column.name} -> {fk.column}")

print("\n--------------------------------------------------------------")
print("4) TABELAS LIGADAS A USERS (AUTENTICAÇÃO / AUTORIZAÇÃO)\n")

for table_name, table in Base.metadata.tables.items():
    for column in table.columns:
        for fk in column.foreign_keys:
            if "user" in str(fk.column).lower():
                print(f"👤 {table_name}.{column.name} -> {fk.column}")

print("\n--------------------------------------------------------------")
print("5) RESUMO AUTOMÁTICO DE RISCO\n")

critical_tables = []
for table_name, table in Base.metadata.tables.items():
    has_tenant = any(c.name == "tenant_id" for c in table.columns)
    has_business_data = table_name not in ("alembic_version",)
    if has_business_data and not has_tenant:
        critical_tables.append(table_name)

print("🚨 TABELAS CRÍTICAS SEM TENANT_ID:\n")
for t in critical_tables:
    print(f" - {t}")

print(f"\nTOTAL: {len(critical_tables)}")

print("\n==============================================================")
print("📌 ANÁLISE CONCLUÍDA")
print("==============================================================")
