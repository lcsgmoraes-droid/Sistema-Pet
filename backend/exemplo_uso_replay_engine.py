"""
Exemplo de Uso do Replay Engine - Fase 5.4
============================================

Este arquivo demonstra como usar o replay engine em diferentes cenários.
"""

from datetime import datetime
from app.replay import replay_events, ReplayStats
from app.db import SessionLocal


def get_db():
    """Helper para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def exemplo_replay_total():
    """
    Exemplo 1: Replay total de todos os eventos.
    
    Casos de uso:
    - Rebuild completo dos read models
    - Correção de bug em handler
    - Migração de schema
    """
    print("=" * 70)
    print("EXEMPLO 1: Replay Total")
    print("=" * 70)
    
    db = next(get_db())
    
    try:
        print("🔄 Iniciando replay de todos os eventos...")
        
        stats = replay_events(db)
        
        print(f"\n✅ Replay concluído com sucesso!")
        print(f"📊 Total de eventos: {stats.total_events}")
        print(f"📦 Batches processados: {stats.batches_processed}")
        print(f"⏱️  Duração: {stats.duration_seconds:.2f}s")
        print(f"⚡ Velocidade: {stats.total_events/stats.duration_seconds:.0f} eventos/s")
        
    except Exception as e:
        print(f"❌ Erro no replay: {e}")
    
    finally:
        db.close()


def exemplo_replay_por_tenant(user_id: int):
    """
    Exemplo 2: Replay filtrado por tenant (user_id).
    
    Casos de uso:
    - Rebuild de um único cliente
    - Correção de dados de um usuário específico
    - Auditoria de dados de um tenant
    """
    print("\n" + "=" * 70)
    print(f"EXEMPLO 2: Replay por Tenant (user_id={user_id})")
    print("=" * 70)
    
    db = next(get_db())
    
    try:
        print(f"🔄 Reprocessando eventos do tenant {user_id}...")
        
        stats = replay_events(db, user_id=user_id)
        
        if stats.success:
            print(f"\n✅ Replay concluído!")
            print(f"📊 Eventos do tenant: {stats.total_events}")
            print(f"⏱️  Duração: {stats.duration_seconds:.2f}s")
        else:
            print(f"\n❌ Replay falhou: {stats.error}")
            
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
    
    finally:
        db.close()


def exemplo_replay_incremental(from_sequence: int):
    """
    Exemplo 3: Replay incremental (apenas eventos novos).
    
    Casos de uso:
    - Reprocessar eventos após deploy de handler
    - Aplicar correção em eventos recentes
    - Rebuild parcial
    """
    print("\n" + "=" * 70)
    print(f"EXEMPLO 3: Replay Incremental (desde seq={from_sequence})")
    print("=" * 70)
    
    db = next(get_db())
    
    try:
        print(f"🔄 Reprocessando eventos a partir do sequence {from_sequence}...")
        
        stats = replay_events(db, from_sequence=from_sequence)
        
        print(f"\n✅ Replay incremental concluído!")
        print(f"📊 Eventos novos processados: {stats.total_events}")
        print(f"📦 Batches: {stats.batches_processed}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    finally:
        db.close()


def exemplo_replay_por_tipo(event_type: str):
    """
    Exemplo 4: Replay filtrado por tipo de evento.
    
    Casos de uso:
    - Reprocessar apenas VendaFinalizada
    - Corrigir handler específico
    - Rebuild de read model específico
    """
    print("\n" + "=" * 70)
    print(f"EXEMPLO 4: Replay por Tipo (event_type={event_type})")
    print("=" * 70)
    
    db = next(get_db())
    
    try:
        print(f"🔄 Reprocessando eventos do tipo '{event_type}'...")
        
        stats = replay_events(db, event_type=event_type)
        
        print(f"\n✅ Replay por tipo concluído!")
        print(f"📊 Eventos '{event_type}': {stats.total_events}")
        print(f"⏱️  Duração: {stats.duration_seconds:.2f}s")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    finally:
        db.close()


def exemplo_replay_intervalo(from_seq: int, to_seq: int):
    """
    Exemplo 5: Replay de intervalo específico.
    
    Casos de uso:
    - Reprocessar eventos de um período
    - Auditoria de eventos específicos
    - Debug de problema em range específico
    """
    print("\n" + "=" * 70)
    print(f"EXEMPLO 5: Replay de Intervalo (seq {from_seq} até {to_seq})")
    print("=" * 70)
    
    db = next(get_db())
    
    try:
        print(f"🔄 Reprocessando eventos do intervalo...")
        
        stats = replay_events(
            db,
            from_sequence=from_seq,
            to_sequence=to_seq
        )
        
        print(f"\n✅ Replay de intervalo concluído!")
        print(f"📊 Eventos no intervalo: {stats.total_events}")
        print(f"📦 Batches: {stats.batches_processed}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    finally:
        db.close()


def exemplo_replay_combinado():
    """
    Exemplo 6: Replay com múltiplos filtros.
    
    Casos de uso:
    - Reprocessar eventos de um tenant em período específico
    - Corrigir dados de cliente específico
    - Auditoria detalhada
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 6: Replay Combinado (múltiplos filtros)")
    print("=" * 70)
    
    db = next(get_db())
    
    try:
        print("🔄 Reprocessando com filtros combinados...")
        print("   - Tenant: 1")
        print("   - Tipo: VendaFinalizada")
        print("   - Intervalo: 1000 até 2000")
        
        stats = replay_events(
            db,
            user_id=1,
            event_type='VendaFinalizada',
            from_sequence=1000,
            to_sequence=2000
        )
        
        print(f"\n✅ Replay combinado concluído!")
        print(f"📊 Eventos filtrados: {stats.total_events}")
        print(f"🎯 Filtros aplicados:")
        for key, value in stats.filters_applied.items():
            if value is not None:
                print(f"   - {key}: {value}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    finally:
        db.close()


def exemplo_replay_com_batch_customizado():
    """
    Exemplo 7: Replay com tamanho de batch customizado.
    
    Casos de uso:
    - Ajustar performance conforme necessidade
    - Batches menores para eventos pesados
    - Batches maiores para eventos leves
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 7: Replay com Batch Customizado")
    print("=" * 70)
    
    db = next(get_db())
    
    try:
        batch_size = 500
        print(f"🔄 Reprocessando com batch_size={batch_size}...")
        
        stats = replay_events(
            db,
            batch_size=batch_size
        )
        
        print(f"\n✅ Replay concluído!")
        print(f"📊 Total de eventos: {stats.total_events}")
        print(f"📦 Batches de {batch_size}: {stats.batches_processed}")
        print(f"⏱️  Tempo médio por batch: {stats.duration_seconds/stats.batches_processed:.2f}s")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    finally:
        db.close()


def exemplo_replay_com_tratamento_erro():
    """
    Exemplo 8: Replay com tratamento de erro robusto.
    
    Demonstra como lidar com falhas no replay.
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 8: Replay com Tratamento de Erro")
    print("=" * 70)
    
    db = next(get_db())
    
    try:
        print("🔄 Iniciando replay com tratamento de erro...")
        
        stats = replay_events(db, user_id=1)
        
        # Verificar sucesso
        if stats.success:
            print(f"\n✅ Replay bem-sucedido!")
            print(f"📊 Eventos: {stats.total_events}")
        else:
            print(f"\n⚠️  Replay falhou parcialmente")
            print(f"❌ Erro: {stats.error}")
            print(f"📊 Eventos processados antes da falha: {stats.total_events}")
            
            # Tomar ação corretiva
            print("\n🔧 Ações corretivas sugeridas:")
            print("   1. Verificar logs detalhados")
            print("   2. Corrigir handler problemático")
            print("   3. Executar replay novamente")
            
    except Exception as e:
        print(f"\n❌ Erro fatal no replay: {e}")
        print("🔧 Sistema fez rollback automático")
        print("🔧 Estado do banco permanece consistente")
        
    finally:
        db.close()


def executar_todos_exemplos():
    """Executa todos os exemplos em sequência."""
    print("\n" + "="*70)
    print("EXEMPLOS DE USO DO REPLAY ENGINE - FASE 5.4")
    print("="*70)
    print("\nEste script demonstra os diferentes modos de uso do replay engine.")
    print("Para executar em produção, ajuste os parâmetros conforme necessário.\n")
    
    # Exemplos
    # exemplo_replay_total()
    # exemplo_replay_por_tenant(user_id=1)
    # exemplo_replay_incremental(from_sequence=5000)
    # exemplo_replay_por_tipo(event_type='VendaFinalizada')
    # exemplo_replay_intervalo(from_seq=1000, to_seq=2000)
    # exemplo_replay_combinado()
    # exemplo_replay_com_batch_customizado()
    # exemplo_replay_com_tratamento_erro()
    
    print("\n" + "="*70)
    print("Para executar, descomente os exemplos desejados acima.")
    print("="*70)


if __name__ == '__main__':
    # Descomentar para executar
    # executar_todos_exemplos()
    
    # Ou executar exemplo específico
    # exemplo_replay_total()
    # exemplo_replay_por_tenant(user_id=1)
    
    print("✅ Exemplos carregados. Descomente para executar.")
