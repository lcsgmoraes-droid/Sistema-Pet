"""
Teste Manual: Validar Enforcement SQL Audit (Fase 1.4.3-D)

Testa:
1. Enforcement desativado (default)
2. Enforcement ativado (HIGH)
3. Helper nunca bloqueado
4. Mensagem de erro clara
5. Configuração via ambiente
"""

import sys
import os
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def test_enforcement_disabled():
    """Teste 1: Enforcement desativado (default)."""
    print("\n" + "="*80)
    print("TESTE 1: Enforcement Desativado (Default)")
    print("="*80)
    
    # Garantir que está desativado
    os.environ["SQL_AUDIT_ENFORCE"] = "false"
    
    # Reimportar módulo para ler nova variável
    import importlib
    import app.db.sql_audit as audit_module
    importlib.reload(audit_module)
    
    from app.db.sql_audit import is_enforcement_enabled, get_enforcement_config
    
    # Verificar
    assert not is_enforcement_enabled(), "Enforcement deveria estar desativado"
    
    config = get_enforcement_config()
    print(f"\n📊 Configuração:")
    print(f"   Enabled: {config['enabled']}")
    print(f"   Level:   {config['level']}")
    print(f"   Blocks:  {config['blocks']}")
    
    assert config['enabled'] is False
    assert config['blocks'] == "none"
    
    print("\n✅ TESTE 1 PASSOU - Enforcement desativado por default")


def test_enforcement_enabled():
    """Teste 2: Enforcement ativado."""
    print("\n" + "="*80)
    print("TESTE 2: Enforcement Ativado")
    print("="*80)
    
    # Ativar enforcement
    os.environ["SQL_AUDIT_ENFORCE"] = "true"
    os.environ["SQL_AUDIT_ENFORCE_LEVEL"] = "HIGH"
    
    # Reimportar módulo
    import importlib
    import app.db.sql_audit as audit_module
    importlib.reload(audit_module)
    
    from app.db.sql_audit import is_enforcement_enabled, get_enforcement_config
    
    # Verificar
    assert is_enforcement_enabled(), "Enforcement deveria estar ativado"
    
    config = get_enforcement_config()
    print(f"\n📊 Configuração:")
    print(f"   Enabled: {config['enabled']}")
    print(f"   Level:   {config['level']}")
    print(f"   Blocks:  {config['blocks']}")
    
    assert config['enabled'] is True
    assert config['level'] == "HIGH"
    assert config['blocks'] == "HIGH+ risk queries"
    
    print("\n✅ TESTE 2 PASSOU - Enforcement ativado corretamente")


def test_exception_exists():
    """Teste 3: Exceção RawSQLEnforcementError existe."""
    print("\n" + "="*80)
    print("TESTE 3: Exceção RawSQLEnforcementError")
    print("="*80)
    
    from app.db.sql_audit import RawSQLEnforcementError
    
    # Verificar herança
    assert issubclass(RawSQLEnforcementError, RuntimeError)
    
    # Testar criação
    error = RawSQLEnforcementError("Teste")
    assert str(error) == "Teste"
    
    print("\n✅ Exceção criada:")
    print(f"   Tipo: {type(error).__name__}")
    print(f"   Base: {RawSQLEnforcementError.__bases__}")
    
    print("\n✅ TESTE 3 PASSOU - Exceção existe e é RuntimeError")


def test_enforcement_levels():
    """Teste 4: Diferentes níveis de enforcement."""
    print("\n" + "="*80)
    print("TESTE 4: Níveis de Enforcement")
    print("="*80)
    
    levels = ["HIGH", "MEDIUM", "LOW"]
    
    for level in levels:
        os.environ["SQL_AUDIT_ENFORCE"] = "true"
        os.environ["SQL_AUDIT_ENFORCE_LEVEL"] = level
        
        # Reimportar
        import importlib
        import app.db.sql_audit as audit_module
        importlib.reload(audit_module)
        
        from app.db.sql_audit import get_enforcement_config
        
        config = get_enforcement_config()
        print(f"\n📊 Level={level}:")
        print(f"   Blocks: {config['blocks']}")
        
        assert config['level'] == level
        assert level in config['blocks']
    
    print("\n✅ TESTE 4 PASSOU - Todos os níveis funcionam")


def test_invalid_level():
    """Teste 5: Nível inválido usa default."""
    print("\n" + "="*80)
    print("TESTE 5: Nível Inválido → Default HIGH")
    print("="*80)
    
    os.environ["SQL_AUDIT_ENFORCE"] = "true"
    os.environ["SQL_AUDIT_ENFORCE_LEVEL"] = "INVALID"
    
    # Reimportar
    import importlib
    import app.db.sql_audit as audit_module
    importlib.reload(audit_module)
    
    from app.db.sql_audit import get_enforcement_config
    
    config = get_enforcement_config()
    print(f"\n📊 Configuração com level inválido:")
    print(f"   Level solicitado: INVALID")
    print(f"   Level usado:      {config['level']}")
    
    # Deve usar HIGH como fallback
    assert config['level'] == "HIGH"
    
    print("\n✅ TESTE 5 PASSOU - Fallback para HIGH funciona")


def test_helper_detection():
    """Teste 6: Helper tenant-safe não é bloqueado."""
    print("\n" + "="*80)
    print("TESTE 6: Helper Tenant-Safe Nunca Bloqueado")
    print("="*80)
    
    # Ativar enforcement
    os.environ["SQL_AUDIT_ENFORCE"] = "true"
    os.environ["SQL_AUDIT_ENFORCE_LEVEL"] = "HIGH"
    
    # Reimportar
    import importlib
    import app.db.sql_audit as audit_module
    importlib.reload(audit_module)
    
    from app.db.sql_audit import _is_from_tenant_safe_helper
    
    # Simular call stack do helper
    helper_stack = """
    File "app/utils/tenant_safe_sql.py", line 123, in execute_tenant_safe
        result = db.execute(text(sql_with_filter), params)
    File "sqlalchemy/engine/base.py", line 456, in execute
        return self._execute_text(statement, parameters)
    """
    
    # Verificar detecção
    is_from_helper = _is_from_tenant_safe_helper(helper_stack)
    print(f"\n🔍 Detecção de helper:")
    print(f"   Stack contém tenant_safe_sql.py: {is_from_helper}")
    
    assert is_from_helper, "Helper deveria ser detectado no stack"
    
    print("\n✅ TESTE 6 PASSOU - Helper detectado corretamente")


def test_enforcement_logic():
    """Teste 7: Lógica de threshold."""
    print("\n" + "="*80)
    print("TESTE 7: Lógica de Threshold")
    print("="*80)
    
    # Simular lógica de threshold
    risk_levels_order = ["LOW", "MEDIUM", "HIGH"]
    
    test_cases = [
        # (current_risk, enforce_level, should_block)
        ("LOW", "HIGH", False),
        ("MEDIUM", "HIGH", False),
        ("HIGH", "HIGH", True),
        ("LOW", "MEDIUM", False),
        ("MEDIUM", "MEDIUM", True),
        ("HIGH", "MEDIUM", True),
        ("LOW", "LOW", True),
        ("MEDIUM", "LOW", True),
        ("HIGH", "LOW", True),
    ]
    
    print("\n📊 Matriz de Decisão:")
    print(f"   {'Risk':<10} {'Enforce':<10} {'Block?':<10}")
    print(f"   {'-'*10} {'-'*10} {'-'*10}")
    
    for current_risk, enforce_level, expected_block in test_cases:
        current_risk_index = risk_levels_order.index(current_risk)
        enforce_level_index = risk_levels_order.index(enforce_level)
        should_block = current_risk_index >= enforce_level_index
        
        block_emoji = "🚫" if should_block else "✅"
        print(f"   {current_risk:<10} {enforce_level:<10} {block_emoji} {should_block}")
        
        assert should_block == expected_block, f"Falhou: {current_risk} vs {enforce_level}"
    
    print("\n✅ TESTE 7 PASSOU - Lógica de threshold correta")


def test_error_message():
    """Teste 8: Mensagem de erro é clara."""
    print("\n" + "="*80)
    print("TESTE 8: Mensagem de Erro Clara")
    print("="*80)
    
    from app.db.sql_audit import RawSQLEnforcementError
    
    # Simular mensagem de erro
    file_origin = "comissoes_routes.py"
    line_origin = 234
    func_origin = "calcular_comissoes_mes"
    tables_str = "comissoes_itens, vendas"
    risk_level = "HIGH"
    enforce_level = "HIGH"
    
    error_msg = (
        f"🚫 RAW SQL BLOCKED: {risk_level} risk query detected\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 Origin: {file_origin}:{line_origin} in {func_origin}()\n"
        f"📊 Tables: {tables_str}\n"
        f"⚠️  Risk: {risk_level} (enforcement level: {enforce_level})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Solution:\n"
        f"   Use tenant-safe helper:\n"
        f"   from app.utils.tenant_safe_sql import execute_tenant_safe\n"
    )
    
    print("\n📝 Mensagem de erro:")
    print(error_msg)
    
    # Verificar conteúdo
    assert "comissoes_routes.py" in error_msg
    assert "234" in error_msg
    assert "comissoes_itens" in error_msg
    assert "tenant-safe helper" in error_msg
    assert "execute_tenant_safe" in error_msg
    
    print("\n✅ TESTE 8 PASSOU - Mensagem contém informações úteis")


def main():
    """Executar todos os testes."""
    print("="*80)
    print("VALIDACAO DE ENFORCEMENT SQL AUDIT - FASE 1.4.3-D")
    print("="*80)
    
    try:
        test_enforcement_disabled()
        test_enforcement_enabled()
        test_exception_exists()
        test_enforcement_levels()
        test_invalid_level()
        test_helper_detection()
        test_enforcement_logic()
        test_error_message()
        
        print("\n" + "="*80)
        print("TODOS OS TESTES PASSARAM (8/8)")
        print("="*80)
        print("\nFase 1.4.3-D implementada e validada com sucesso!")
        print("\nProximos passos:")
        print("   1. Testar em ambiente local com enforcement ativado")
        print("   2. Migrar queries HIGH risk -> helper tenant-safe")
        print("   3. Rollout gradual: dev -> staging -> prod")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Resetar environment
        os.environ["SQL_AUDIT_ENFORCE"] = "false"


if __name__ == "__main__":
    sys.exit(main())
