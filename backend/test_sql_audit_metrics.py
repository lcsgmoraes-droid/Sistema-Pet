"""
Teste Manual: Validar Métricas SQL Audit (Fase 1.4.3-C)

Testa:
1. Incremento de métricas
2. Snapshot trigger
3. get_audit_stats()
4. reset_audit_stats()
5. Performance
"""

import sys
import time
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_increment_stats():
    """Teste 1: Incremento básico de métricas."""
    print("\n" + "="*80)
    print("TESTE 1: Incremento Básico de Métricas")
    print("="*80)
    
    from app.db.sql_audit import SQL_AUDIT_STATS, _increment_stats, reset_audit_stats
    
    # Reset
    reset_audit_stats()
    print("✅ Stats resetados")
    
    # Incrementar 3 queries
    _increment_stats("HIGH", ["comissoes_itens"], "comissoes_routes.py")
    _increment_stats("HIGH", ["vendas"], "comissoes_routes.py")
    _increment_stats("MEDIUM", ["tenants"], "auth_service.py")
    print("✅ 3 queries incrementadas")
    
    # Verificar
    assert SQL_AUDIT_STATS["total"] == 3, f"Expected total=3, got {SQL_AUDIT_STATS['total']}"
    assert SQL_AUDIT_STATS["HIGH"] == 2, f"Expected HIGH=2, got {SQL_AUDIT_STATS['HIGH']}"
    assert SQL_AUDIT_STATS["MEDIUM"] == 1, f"Expected MEDIUM=1, got {SQL_AUDIT_STATS['MEDIUM']}"
    assert SQL_AUDIT_STATS["by_file"]["comissoes_routes.py"] == 2
    assert SQL_AUDIT_STATS["by_table"]["comissoes_itens"] == 1
    
    print(f"📊 Total: {SQL_AUDIT_STATS['total']}")
    print(f"📊 HIGH: {SQL_AUDIT_STATS['HIGH']}, MEDIUM: {SQL_AUDIT_STATS['MEDIUM']}, LOW: {SQL_AUDIT_STATS['LOW']}")
    print(f"📊 by_file: {SQL_AUDIT_STATS['by_file']}")
    print(f"📊 by_table: {SQL_AUDIT_STATS['by_table']}")
    
    print("\n✅ TESTE 1 PASSOU")


def test_snapshot_trigger():
    """Teste 2: Snapshot automático a cada 50 queries."""
    print("\n" + "="*80)
    print("TESTE 2: Snapshot Trigger (50 queries)")
    print("="*80)
    
    from app.db.sql_audit import SQL_AUDIT_STATS, _increment_stats, _log_snapshot, reset_audit_stats, SNAPSHOT_INTERVAL
    
    # Reset
    reset_audit_stats()
    
    # Simular queries com check de snapshot
    print(f"Simulando {SNAPSHOT_INTERVAL} queries...")
    for i in range(SNAPSHOT_INTERVAL):
        _increment_stats("HIGH", ["comissoes_itens"], "comissoes_routes.py")
        
        # Simular o check do audit_raw_sql
        if SQL_AUDIT_STATS["total"] % SNAPSHOT_INTERVAL == 0:
            _log_snapshot()
    
    # Verificar
    assert SQL_AUDIT_STATS["total"] == SNAPSHOT_INTERVAL, f"Expected total={SNAPSHOT_INTERVAL}, got {SQL_AUDIT_STATS['total']}"
    assert SQL_AUDIT_STATS["last_snapshot"] is not None, "Snapshot não foi criado"
    
    print(f"✅ {SNAPSHOT_INTERVAL} queries incrementadas")
    print(f"✅ Snapshot criado em: {SQL_AUDIT_STATS['last_snapshot']}")
    
    print("\n✅ TESTE 2 PASSOU")


def test_top_files():
    """Teste 3: Top files ordenados corretamente."""
    print("\n" + "="*80)
    print("TESTE 3: Top Files")
    print("="*80)
    
    from app.db.sql_audit import get_audit_stats, _increment_stats, reset_audit_stats
    
    reset_audit_stats()
    
    # Gerar queries de diferentes arquivos
    print("Gerando queries de diferentes arquivos...")
    for i in range(10):
        _increment_stats("HIGH", ["comissoes_itens"], "comissoes_routes.py")
    for i in range(5):
        _increment_stats("HIGH", ["vendas"], "vendas_routes.py")
    for i in range(3):
        _increment_stats("MEDIUM", ["produtos"], "produtos_routes.py")
    
    stats = get_audit_stats()
    
    # Verificar top files
    top_files = stats["top_files"]
    print(f"\n📊 Top Files:")
    for i, (file, count) in enumerate(top_files[:5], 1):
        print(f"  {i}. {file}: {count} queries")
    
    assert top_files[0] == ("comissoes_routes.py", 10)
    assert top_files[1] == ("vendas_routes.py", 5)
    assert top_files[2] == ("produtos_routes.py", 3)
    
    print("\n✅ TESTE 3 PASSOU")


def test_get_audit_stats():
    """Teste 4: API get_audit_stats()."""
    print("\n" + "="*80)
    print("TESTE 4: get_audit_stats() API")
    print("="*80)
    
    from app.db.sql_audit import get_audit_stats, _increment_stats, reset_audit_stats
    
    reset_audit_stats()
    
    # Gerar algumas queries
    _increment_stats("HIGH", ["comissoes_itens", "vendas"], "comissoes_routes.py")
    _increment_stats("MEDIUM", ["tenants"], "auth_service.py")
    _increment_stats("LOW", [], "health_router.py")
    
    stats = get_audit_stats()
    
    # Verificar estrutura
    assert "total" in stats
    assert "HIGH" in stats
    assert "MEDIUM" in stats
    assert "LOW" in stats
    assert "by_file" in stats
    assert "by_table" in stats
    assert "top_files" in stats
    assert "top_tables" in stats
    assert "status" in stats
    assert "listener_registered" in stats
    
    print(f"\n📊 Stats completos:")
    print(f"  Total: {stats['total']}")
    print(f"  HIGH: {stats['HIGH']}, MEDIUM: {stats['MEDIUM']}, LOW: {stats['LOW']}")
    print(f"  Status: {stats['status']}")
    print(f"  Listener: {stats['listener_registered']}")
    print(f"  Top Files: {stats['top_files']}")
    print(f"  Top Tables: {stats['top_tables']}")
    
    print("\n✅ TESTE 4 PASSOU")


def test_performance():
    """Teste 5: Performance do incremento."""
    print("\n" + "="*80)
    print("TESTE 5: Performance")
    print("="*80)
    
    from app.db.sql_audit import _increment_stats, reset_audit_stats
    
    reset_audit_stats()
    
    # Medir 1000 incrementos
    iterations = 1000
    print(f"Medindo {iterations} incrementos...")
    
    start = time.perf_counter()
    for i in range(iterations):
        _increment_stats("HIGH", ["comissoes_itens", "vendas"], "comissoes_routes.py")
    elapsed = time.perf_counter() - start
    
    # Calcular overhead
    per_query_us = (elapsed / iterations) * 1_000_000
    
    print(f"\n⏱️  Total: {elapsed*1000:.2f}ms")
    print(f"⏱️  Por query: {per_query_us:.1f}μs")
    
    assert per_query_us < 100, f"Overhead muito alto: {per_query_us:.1f}μs (esperado <100μs)"
    
    print(f"✅ Performance OK: {per_query_us:.1f}μs < 100μs")
    print("\n✅ TESTE 5 PASSOU")


def test_reset():
    """Teste 6: Reset de métricas."""
    print("\n" + "="*80)
    print("TESTE 6: Reset Stats")
    print("="*80)
    
    from app.db.sql_audit import SQL_AUDIT_STATS, _increment_stats, reset_audit_stats
    
    # Adicionar alguns dados
    _increment_stats("HIGH", ["comissoes_itens"], "comissoes_routes.py")
    _increment_stats("HIGH", ["vendas"], "vendas_routes.py")
    
    print(f"Antes do reset: total={SQL_AUDIT_STATS['total']}")
    
    # Reset
    reset_audit_stats()
    
    # Verificar
    assert SQL_AUDIT_STATS["total"] == 0
    assert SQL_AUDIT_STATS["HIGH"] == 0
    assert SQL_AUDIT_STATS["MEDIUM"] == 0
    assert SQL_AUDIT_STATS["LOW"] == 0
    assert SQL_AUDIT_STATS["by_file"] == {}
    assert SQL_AUDIT_STATS["by_table"] == {}
    assert SQL_AUDIT_STATS["last_snapshot"] is None
    
    print(f"Depois do reset: total={SQL_AUDIT_STATS['total']}")
    print("\n✅ TESTE 6 PASSOU")


def main():
    """Executar todos os testes."""
    print("="*80)
    print("🧪 VALIDAÇÃO DE MÉTRICAS SQL AUDIT - FASE 1.4.3-C")
    print("="*80)
    
    try:
        test_increment_stats()
        test_snapshot_trigger()
        test_top_files()
        test_get_audit_stats()
        test_performance()
        test_reset()
        
        print("\n" + "="*80)
        print("✅ TODOS OS TESTES PASSARAM (6/6)")
        print("="*80)
        print("\n📊 Fase 1.4.3-C implementada e validada com sucesso!")
        print("📝 Próximo passo: Monitorar logs em ambiente real")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
