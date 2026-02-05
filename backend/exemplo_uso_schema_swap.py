"""
Exemplo de Uso do Schema Swap - Fase 5.5
=========================================

Demonstra como fazer rebuild completo de read models sem downtime.
"""

from app.db import SessionLocal
from app.read_models.rebuild import rebuild_read_models_zero_downtime
from app.read_models.schema_swap import (
    create_temp_schema,
    validate_schema,
    swap_schemas_atomic,
    drop_temp_schema
)


def exemplo_rebuild_completo():
    """
    Exemplo 1: Rebuild completo com zero downtime.
    
    Este é o uso mais comum - rebuild total dos read models.
    """
    print("="*70)
    print("EXEMPLO 1: Rebuild Completo Zero Downtime")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        print("\n🚀 Iniciando rebuild completo...")
        print("ℹ️  O sistema continua operacional durante todo o processo!\n")
        
        result = rebuild_read_models_zero_downtime(db)
        
        if result.success:
            print(f"\n✅ REBUILD CONCLUÍDO COM SUCESSO!")
            print(f"⏱️  Duração total: {result.duration_seconds:.2f}s")
            print(f"📊 Eventos reprocessados: {result.replay_stats.total_events}")
            print(f"📦 Tabelas atualizadas: {', '.join(result.swap_result.tables_swapped)}")
            
            # Mostrar contagens
            if result.swap_result.validation_after:
                print(f"\n📊 Registros por tabela:")
                for table, count in result.swap_result.validation_after.table_counts.items():
                    print(f"  - {table}: {count} registros")
        else:
            print(f"\n❌ Rebuild falhou!")
            print(f"Fase alcançada: {result.phase_reached}")
            print(f"Erro: {result.error}")
            
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
    
    finally:
        db.close()


def exemplo_rebuild_por_tenant(user_id: int):
    """
    Exemplo 2: Rebuild filtrado por tenant.
    
    Útil para reconstruir dados de um cliente específico.
    """
    print("\n" + "="*70)
    print(f"EXEMPLO 2: Rebuild por Tenant (user_id={user_id})")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        print(f"\n🚀 Rebuild apenas para tenant {user_id}...")
        
        result = rebuild_read_models_zero_downtime(
            db,
            user_id=user_id
        )
        
        if result.success:
            print(f"\n✅ Rebuild do tenant {user_id} concluído!")
            print(f"📊 Eventos processados: {result.replay_stats.total_events}")
        else:
            print(f"❌ Erro: {result.error}")
            
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
    
    finally:
        db.close()


def exemplo_rebuild_batch_customizado():
    """
    Exemplo 3: Rebuild com batch customizado.
    
    Ajusta o tamanho do batch conforme recursos disponíveis.
    """
    print("\n" + "="*70)
    print("EXEMPLO 3: Rebuild com Batch Customizado")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        batch_size = 500  # Menor para processamento mais controlado
        
        print(f"\n🚀 Rebuild com batch_size={batch_size}...")
        
        result = rebuild_read_models_zero_downtime(
            db,
            batch_size=batch_size
        )
        
        if result.success:
            print(f"\n✅ Rebuild concluído!")
            print(f"📦 Batches processados: {result.replay_stats.batches_processed}")
            print(f"⚡ Velocidade média: {result.replay_stats.total_events/result.duration_seconds:.0f} eventos/s")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    finally:
        db.close()


def exemplo_validacao_manual():
    """
    Exemplo 4: Validação manual antes de rebuild.
    
    Verifica estado atual dos read models antes de fazer rebuild.
    """
    print("\n" + "="*70)
    print("EXEMPLO 4: Validação Manual Pré-Rebuild")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        print("\n🔍 Validando schema atual...")
        
        validation = validate_schema(db, use_temp=False)
        
        print(f"\n📊 Contagem de registros:")
        for table, count in validation.table_counts.items():
            print(f"  - {table}: {count} registros")
        
        if validation.errors:
            print(f"\n❌ Erros encontrados:")
            for error in validation.errors:
                print(f"  - {error}")
        
        if validation.warnings:
            print(f"\n⚠️  Avisos:")
            for warning in validation.warnings:
                print(f"  - {warning}")
        
        if validation.is_valid:
            print("\n✅ Schema válido!")
            print("✅ Pode prosseguir com rebuild se necessário")
        else:
            print("\n❌ Schema tem problemas!")
            print("⚠️  Corrija os erros antes de fazer rebuild")
            
    except Exception as e:
        print(f"❌ Erro na validação: {e}")
    
    finally:
        db.close()


def exemplo_processo_manual_passo_a_passo():
    """
    Exemplo 5: Processo manual (passo a passo).
    
    Para casos avançados onde você quer controle total.
    """
    print("\n" + "="*70)
    print("EXEMPLO 5: Processo Manual (Controle Total)")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        # PASSO 1: Criar schema temporário
        print("\n1️⃣ Criando schema temporário...")
        create_temp_schema(db)
        print("✅ Schema temporário criado")
        
        # PASSO 2: Fazer replay manualmente (aqui você tem controle total)
        print("\n2️⃣ Replay de eventos (manual)...")
        # from app.replay import replay_events
        # ... fazer replay customizado
        print("ℹ️  (implementar replay customizado conforme necessidade)")
        
        # PASSO 3: Validar
        print("\n3️⃣ Validando schema temporário...")
        validation = validate_schema(db, use_temp=True)
        
        if not validation.is_valid:
            print(f"❌ Validação falhou: {validation.errors}")
            print("🗑️  Removendo schema temporário...")
            drop_temp_schema(db)
            return
        
        print("✅ Validação passou")
        
        # PASSO 4: Swap
        print("\n4️⃣ Executando swap atômico...")
        swap_result = swap_schemas_atomic(db, validate_before=True)
        
        if swap_result.success:
            print(f"✅ Swap concluído em {swap_result.duration_seconds:.2f}s")
        else:
            print(f"❌ Swap falhou: {swap_result.error}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        
        # Cleanup em caso de erro
        try:
            print("🗑️  Fazendo cleanup...")
            drop_temp_schema(db)
        except:
            pass
    
    finally:
        db.close()


def exemplo_monitoramento_progresso():
    """
    Exemplo 6: Monitoramento de progresso.
    
    Rebuild com logging detalhado de progresso.
    """
    print("\n" + "="*70)
    print("EXEMPLO 6: Rebuild com Monitoramento Detalhado")
    print("="*70)
    
    import logging
    
    # Configurar logging verbose
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    db = SessionLocal()
    
    try:
        print("\n🚀 Iniciando rebuild com logging detalhado...")
        print("ℹ️  Acompanhe o progresso no console\n")
        
        result = rebuild_read_models_zero_downtime(db, batch_size=100)
        
        if result.success:
            print(f"\n✅ Rebuild concluído!")
            
            # Análise de performance
            if result.replay_stats:
                eventos = result.replay_stats.total_events
                duracao = result.duration_seconds
                velocidade = eventos / duracao if duracao > 0 else 0
                
                print(f"\n📊 Análise de Performance:")
                print(f"  - Eventos: {eventos}")
                print(f"  - Duração: {duracao:.2f}s")
                print(f"  - Velocidade: {velocidade:.0f} eventos/s")
                print(f"  - Batches: {result.replay_stats.batches_processed}")
                print(f"  - Tempo médio por batch: {duracao/result.replay_stats.batches_processed:.2f}s")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    finally:
        db.close()


def executar_todos_exemplos():
    """Executa todos os exemplos em sequência."""
    print("\n" + "="*70)
    print("EXEMPLOS DE USO DO SCHEMA SWAP - FASE 5.5")
    print("="*70)
    print("\nEste script demonstra rebuild de read models sem downtime.")
    print("Para executar em produção, ajuste os parâmetros conforme necessário.\n")
    
    # Exemplos
    # exemplo_rebuild_completo()
    # exemplo_rebuild_por_tenant(user_id=1)
    # exemplo_rebuild_batch_customizado()
    # exemplo_validacao_manual()
    # exemplo_processo_manual_passo_a_passo()
    # exemplo_monitoramento_progresso()
    
    print("\n" + "="*70)
    print("Para executar, descomente os exemplos desejados acima.")
    print("="*70)


if __name__ == '__main__':
    # Descomentar para executar
    # executar_todos_exemplos()
    
    # Ou executar exemplo específico
    # exemplo_rebuild_completo()
    # exemplo_validacao_manual()
    
    print("✅ Exemplos carregados. Descomente para executar.")
