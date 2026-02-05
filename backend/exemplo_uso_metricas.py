"""
Exemplo Prático: Usando Métricas SQL Audit em Produção

Demonstra como:
1. Consultar métricas durante runtime
2. Identificar arquivos problemáticos
3. Monitorar evolução das correções
"""

import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def exemplo_consultar_metricas():
    """Exemplo 1: Consultar métricas em runtime."""
    print("="*80)
    print("EXEMPLO 1: Consultar Métricas em Runtime")
    print("="*80)
    
    from app.db.sql_audit import get_audit_stats
    
    # Obter stats
    stats = get_audit_stats()
    
    # Exibir resumo
    total = stats['total']
    
    if total == 0:
        print("📊 Nenhuma query RAW SQL detectada ainda")
        return
    
    print(f"\n📊 RESUMO:")
    print(f"   Total de queries auditadas: {total}")
    print(f"   🔴 HIGH risk:   {stats['HIGH']:3d} ({stats['HIGH']/total*100:5.1f}%)")
    print(f"   🟡 MEDIUM risk: {stats['MEDIUM']:3d} ({stats['MEDIUM']/total*100:5.1f}%)")
    print(f"   🟢 LOW risk:    {stats['LOW']:3d} ({stats['LOW']/total*100:5.1f}%)")
    
    # Top 5 arquivos
    print(f"\n📂 TOP 5 ARQUIVOS COM MAIS QUERIES INSEGURAS:")
    for i, (file, count) in enumerate(stats['top_files'][:5], 1):
        print(f"   {i}. {file}: {count} queries")
    
    # Top 5 tabelas
    print(f"\n📊 TOP 5 TABELAS MAIS ACESSADAS VIA RAW SQL:")
    for i, (table, count) in enumerate(stats['top_tables'][:5], 1):
        print(f"   {i}. {table}: {count} accesses")
    
    print("\n")


def exemplo_identificar_prioridades():
    """Exemplo 2: Identificar arquivos prioritários para migração."""
    print("="*80)
    print("EXEMPLO 2: Identificar Prioridades de Migração")
    print("="*80)
    
    from app.db.sql_audit import get_audit_stats
    
    stats = get_audit_stats()
    
    if stats['total'] == 0:
        print("📊 Nenhuma query detectada ainda")
        return
    
    # Calcular HIGH risk por arquivo
    high_risk_threshold = 5  # Arquivos com 5+ queries HIGH
    
    print(f"\n🔴 ARQUIVOS DE ALTA PRIORIDADE (>{high_risk_threshold} queries):")
    print(f"{'='*80}")
    
    high_priority = [
        (file, count)
        for file, count in stats['top_files']
        if count >= high_risk_threshold
    ]
    
    if not high_priority:
        print("✅ Nenhum arquivo com alta concentração de queries inseguras!")
    else:
        for i, (file, count) in enumerate(high_priority, 1):
            print(f"   P{i}: {file}")
            print(f"       └─ {count} queries RAW SQL detectadas")
            print(f"       └─ Estimativa: ~{count * 5} minutos para migração")
            print()


def exemplo_monitorar_progresso():
    """Exemplo 3: Monitorar progresso de migração."""
    print("="*80)
    print("EXEMPLO 3: Monitorar Progresso de Migração")
    print("="*80)
    
    from app.db.sql_audit import get_audit_stats
    
    stats = get_audit_stats()
    
    # Baseline esperado (do inventário inicial)
    BASELINE_UNSAFE_QUERIES = 89
    
    # Calcular progresso
    total = stats['total']
    high_count = stats['HIGH']
    
    if total == 0:
        print("\n📊 Sistema ainda sem detecções de RAW SQL")
        print("   Execute a aplicação para coletar métricas")
        return
    
    # Percentual de queries HIGH
    high_pct = (high_count / total * 100) if total > 0 else 0
    
    print(f"\n📈 PROGRESSO DA MIGRAÇÃO:")
    print(f"{'='*80}")
    print(f"   Baseline inicial:     {BASELINE_UNSAFE_QUERIES} queries inseguras")
    print(f"   Queries HIGH atuais:  {high_count} queries")
    print(f"   Redução:              {BASELINE_UNSAFE_QUERIES - high_count} queries migradas")
    print(f"   Progresso:            {(BASELINE_UNSAFE_QUERIES - high_count) / BASELINE_UNSAFE_QUERIES * 100:.1f}%")
    print()
    
    # Status
    if high_pct > 70:
        print("   🔴 STATUS: CRÍTICO - Muitas queries HIGH risk detectadas")
        print("   ⚠️  AÇÃO: Priorizar migração de queries HIGH")
    elif high_pct > 40:
        print("   🟡 STATUS: ATENÇÃO - Quantidade moderada de queries HIGH")
        print("   ⚠️  AÇÃO: Continuar migração gradual")
    else:
        print("   🟢 STATUS: BOM - Poucas queries HIGH risk")
        print("   ✅ AÇÃO: Finalizar queries restantes")
    
    print()


def exemplo_endpoint_admin():
    """Exemplo 4: Como usar em endpoint admin."""
    print("="*80)
    print("EXEMPLO 4: Endpoint Admin (Código de Exemplo)")
    print("="*80)
    
    codigo = '''
from fastapi import APIRouter, Depends
from app.db.sql_audit import get_audit_stats
from app.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/sql-audit/metrics")
def get_sql_audit_metrics(admin = Depends(require_admin)):
    """
    Retorna métricas de auditoria SQL em tempo real.
    
    Requer: Role admin
    
    Retorna:
    - total: Total de queries RAW SQL detectadas
    - HIGH/MEDIUM/LOW: Contagem por nível de risco
    - top_files: Top 10 arquivos com mais queries
    - top_tables: Top 10 tabelas mais acessadas
    """
    return get_audit_stats()


# Exemplo de resposta:
# GET /admin/sql-audit/metrics
{
    "status": "active",
    "listener_registered": true,
    "total": 156,
    "HIGH": 89,
    "MEDIUM": 52,
    "LOW": 15,
    "top_files": [
        ["comissoes_routes.py", 42],
        ["relatorio_vendas.py", 25],
        ["relatorio_dre.py", 15]
    ],
    "top_tables": [
        ["comissoes_itens", 35],
        ["vendas", 28],
        ["produtos", 18]
    ],
    "last_snapshot": "2026-02-05T14:30:00Z"
}
'''
    
    print(codigo)


def exemplo_script_monitoring():
    """Exemplo 5: Script de monitoramento contínuo."""
    print("="*80)
    print("EXEMPLO 5: Script de Monitoramento (Código de Exemplo)")
    print("="*80)
    
    codigo = '''
#!/usr/bin/env python
"""
Script de Monitoramento: Alertar quando HIGH risk > threshold

Uso:
    python monitor_sql_audit.py --threshold 10 --interval 60

Envia alerta se HIGH risk queries > threshold
"""

import time
import argparse
from app.db.sql_audit import get_audit_stats

def check_high_risk_threshold(threshold: int) -> bool:
    """Verifica se HIGH risk excede threshold."""
    stats = get_audit_stats()
    return stats['HIGH'] > threshold

def send_alert(stats: dict):
    """Envia alerta (email, Slack, etc.)."""
    print(f"⚠️  ALERTA: {stats['HIGH']} queries HIGH risk detectadas!")
    print(f"   Top files: {stats['top_files'][:3]}")
    # Implementar envio de email/Slack aqui

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=int, default=10)
    parser.add_argument('--interval', type=int, default=60)
    args = parser.parse_args()
    
    print(f"Monitorando SQL Audit (threshold={args.threshold})...")
    
    while True:
        if check_high_risk_threshold(args.threshold):
            stats = get_audit_stats()
            send_alert(stats)
        
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
'''
    
    print(codigo)


def main():
    """Executar todos os exemplos."""
    print("\n")
    print("="*80)
    print("🔍 EXEMPLOS PRÁTICOS - MÉTRICAS SQL AUDIT")
    print("="*80)
    print("\n")
    
    exemplo_consultar_metricas()
    exemplo_identificar_prioridades()
    exemplo_monitorar_progresso()
    exemplo_endpoint_admin()
    exemplo_script_monitoring()
    
    print("="*80)
    print("✅ Exemplos gerados com sucesso!")
    print("="*80)
    print("\n📝 Próximos passos:")
    print("   1. Integrar get_audit_stats() em endpoint admin")
    print("   2. Monitorar logs em ambiente de desenvolvimento")
    print("   3. Usar top_files para priorizar migração")
    print("   4. Implementar alertas para HIGH risk > threshold")
    print("\n")


if __name__ == "__main__":
    main()
