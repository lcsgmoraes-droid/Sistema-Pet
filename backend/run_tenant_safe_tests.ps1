# Script para executar testes com PostgreSQL local
$env:DATABASE_URL="postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db"
python -m pytest tests/test_tenant_safe_sql.py -v --tb=short
