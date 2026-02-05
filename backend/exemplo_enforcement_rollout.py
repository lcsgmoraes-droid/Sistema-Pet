"""
Exemplo Prático: Ativando Enforcement em Diferentes Ambientes

Demonstra:
1. Configuração local (desenvolvimento)
2. Configuração staging
3. Configuração produção
4. Como testar antes de ativar
"""

import os


def exemplo_desenvolvimento():
    """
    DESENVOLVIMENTO LOCAL
    
    Enforcement ativado para forçar uso do helper.
    """
    print("="*80)
    print("DESENVOLVIMENTO LOCAL")
    print("="*80)
    
    print("\n1. Adicionar ao .env:")
    print("""
# SQL Audit Enforcement (ATIVO em dev)
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=HIGH
""")
    
    print("\n2. Reiniciar aplicação:")
    print("   docker-compose restart backend")
    
    print("\n3. Testar funcionalidades:")
    print("   - Vendas")
    print("   - Comissões")
    print("   - Relatórios")
    
    print("\n4. Queries bloqueadas aparecerão como:")
    print("""
RawSQLEnforcementError: HIGH risk query detected
📍 Origin: comissoes_routes.py:234
📊 Tables: comissoes_itens
""")
    
    print("\n5. Migrar usando helper:")
    print("""
from app.utils.tenant_safe_sql import execute_tenant_safe

# Antes (BLOQUEADO)
result = db.execute(text(\"\"\"
    SELECT SUM(valor) FROM comissoes_itens WHERE status = 'pago'
\"\"\"))

# Depois (PERMITIDO)
result = execute_tenant_safe(db, \"\"\"
    SELECT SUM(valor) FROM comissoes_itens 
    WHERE {tenant_filter} AND status = :status
\"\"\", {"status": "pago"})
""")


def exemplo_staging():
    """
    STAGING
    
    Enforcement ativado para validar antes de produção.
    """
    print("\n" + "="*80)
    print("STAGING")
    print("="*80)
    
    print("\n1. Configurar docker-compose.staging.yml:")
    print("""
services:
  backend:
    environment:
      SQL_AUDIT_ENFORCE: "true"
      SQL_AUDIT_ENFORCE_LEVEL: "HIGH"
""")
    
    print("\n2. Deploy em staging:")
    print("   docker-compose -f docker-compose.staging.yml up -d")
    
    print("\n3. Executar testes automatizados:")
    print("   pytest tests/ -v")
    
    print("\n4. QA manual:")
    print("   - Testar todos os fluxos críticos")
    print("   - Verificar se alguma funcionalidade quebrou")
    print("   - Monitorar logs de enforcement")
    
    print("\n5. Verificar métricas:")
    print("""
from app.db.sql_audit import get_audit_stats

stats = get_audit_stats()
print(f"Queries bloqueadas: {stats['HIGH']}")
""")


def exemplo_producao():
    """
    PRODUÇÃO
    
    Enforcement ativado gradualmente.
    """
    print("\n" + "="*80)
    print("PRODUÇÃO (Rollout Gradual)")
    print("="*80)
    
    print("\n📅 SEMANA 1: 10% dos requests")
    print("""
# app/main.py
import random

@app.on_event("startup")
async def configure_enforcement():
    if random.random() < 0.10:  # 10%
        os.environ["SQL_AUDIT_ENFORCE"] = "true"
""")
    
    print("\n📅 SEMANA 2: 50% dos requests")
    print("""
    if random.random() < 0.50:  # 50%
        os.environ["SQL_AUDIT_ENFORCE"] = "true"
""")
    
    print("\n📅 SEMANA 3: 100% (permanente)")
    print("""
# docker-compose.production.yml
services:
  backend:
    environment:
      SQL_AUDIT_ENFORCE: "true"
      SQL_AUDIT_ENFORCE_LEVEL: "HIGH"
""")
    
    print("\n⚠️  MONITORAR:")
    print("   - Taxa de erro 500")
    print("   - Logs de enforcement")
    print("   - Feedback de usuários")
    
    print("\n🔙 ROLLBACK (se necessário):")
    print("""
# Desativar imediatamente
SQL_AUDIT_ENFORCE=false
docker-compose restart backend
""")


def exemplo_teste_seco():
    """
    Como testar enforcement SEM ativar globalmente.
    """
    print("\n" + "="*80)
    print("TESTE SECO (Dry Run)")
    print("="*80)
    
    print("\n1. Simular bloqueio localmente:")
    print("""
from app.db.sql_audit import classify_raw_sql_risk, RawSQLEnforcementError

# Query suspeita
sql = "SELECT * FROM comissoes_itens WHERE status = 'pago'"

# Classificar
risk_level, tables = classify_raw_sql_risk(sql, has_tenant_filter=False)

# Verificar o que aconteceria
if risk_level == "HIGH":
    print(f"⚠️  Esta query seria BLOQUEADA!")
    print(f"   Tabelas: {tables}")
else:
    print(f"✅ Esta query seria permitida ({risk_level})")
""")
    
    print("\n2. Auditar todo o código sem bloquear:")
    print("""
# SQL_AUDIT_ENFORCE=false (default)
# Apenas observar logs e métricas

from app.db.sql_audit import get_audit_stats

stats = get_audit_stats()
print(f"Queries que SERIAM bloqueadas: {stats['HIGH']}")

# Ver arquivos afetados
for file, count in stats['top_files'][:10]:
    print(f"  - {file}: {count} queries")
""")


def exemplo_whitelist():
    """
    Como adicionar queries legítimas à whitelist.
    """
    print("\n" + "="*80)
    print("ADICIONAR À WHITELIST")
    print("="*80)
    
    print("\n❓ QUANDO USAR:")
    print("   - Query legítima mas classificada como HIGH")
    print("   - Tabela específica não precisa tenant_filter")
    print("   - Query administrativa (relatórios globais)")
    
    print("\n📝 EXEMPLO:")
    print("""
# app/db/sql_audit.py

WHITELIST_TABLES = {
    "tenants",
    "permissions",
    "roles",
    "alembic_version",
    
    # ✨ ADICIONAR AQUI
    "fiscal_catalogo_produtos",  # Catálogo global
    "configuracoes_sistema",      # Configs globais
}
""")
    
    print("\n⚠️  CUIDADO:")
    print("   - Documentar motivo da whitelist")
    print("   - Revisar periodicamente")
    print("   - Preferir usar helper quando possível")


def exemplo_bypass_temporario():
    """
    Como fazer bypass temporário para hotfix.
    """
    print("\n" + "="*80)
    print("BYPASS TEMPORÁRIO (Hotfix)")
    print("="*80)
    
    print("\n⚠️  USAR APENAS EM EMERGÊNCIA!")
    
    print("\n1. Desativar enforcement:")
    print("""
# docker-compose.production.yml
SQL_AUDIT_ENFORCE=false
docker-compose restart backend
""")
    
    print("\n2. Aplicar hotfix:")
    print("   - Corrigir bug crítico")
    print("   - Deploy urgente")
    
    print("\n3. Re-ativar enforcement:")
    print("""
# Após resolver o problema
SQL_AUDIT_ENFORCE=true
docker-compose restart backend
""")
    
    print("\n4. Migrar query problemática:")
    print("   - Usar helper tenant-safe")
    print("   - Testar em staging")
    print("   - Deploy normal")


def main():
    """Executar todos os exemplos."""
    print("\n")
    print("="*80)
    print("EXEMPLOS PRÁTICOS - ENFORCEMENT SQL AUDIT")
    print("="*80)
    
    exemplo_desenvolvimento()
    exemplo_staging()
    exemplo_producao()
    exemplo_teste_seco()
    exemplo_whitelist()
    exemplo_bypass_temporario()
    
    print("\n" + "="*80)
    print("RESUMO")
    print("="*80)
    
    print("""
📋 CHECKLIST DE ATIVAÇÃO:

□ Fase 0: Implementação (CONCLUÍDO)
  ✓ Código implementado
  ✓ Testes passando
  ✓ Documentação criada

□ Fase 1: Desenvolvimento Local (1-2 semanas)
  □ Ativar SQL_AUDIT_ENFORCE=true
  □ Testar todas as funcionalidades
  □ Migrar queries bloqueadas
  □ Validar 0 queries HIGH risk

□ Fase 2: Staging (1 semana)
  □ Deploy com enforcement ativo
  □ Executar testes automatizados
  □ QA manual completo
  □ Verificar 0 bloqueios inesperados

□ Fase 3: Produção (2-3 semanas)
  □ Semana 1: 10% rollout
  □ Semana 2: 50% rollout
  □ Semana 3: 100% rollout
  □ Monitorar métricas
  □ Ter plano de rollback pronto

□ Fase 4: Hardening (contínuo)
  □ Mês 1-2: Enforce=HIGH
  □ Mês 3-4: Enforce=MEDIUM
  □ Mês 5+: Enforce=LOW
""")
    
    print("\n🔗 Referências:")
    print("   - CHANGES_SQL_AUDIT_P0_D.md - Documentação completa")
    print("   - test_sql_audit_enforcement.py - Testes unitários")
    print("   - CHANGES_RAW_SQL_INFRA_P0.md - Helper tenant-safe")
    
    print("\n")


if __name__ == "__main__":
    main()
