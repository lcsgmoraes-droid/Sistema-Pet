"""
Script de teste da Segmentação Automática de Clientes
Testa cálculo de métricas e aplicação de regras
"""

import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.services.segmentacao_service import SegmentacaoService
from app.models import Cliente, User
from sqlalchemy import func


def testar_segmentacao():
    """Testa o sistema de segmentação"""
    
    print("=" * 60)
    print("TESTE: Sistema de Segmentação Automática")
    print("=" * 60)
    print()
    
    db = SessionLocal()
    
    try:
        # 1. Buscar usuário do sistema
        print("1️⃣ Buscando usuário...")
        user = db.query(User).filter(User.is_active == True).first()
        
        if not user:
            print("❌ Nenhum usuário ativo encontrado")
            return
        
        print(f"✅ Usuário encontrado: {user.email} (ID: {user.id})")
        print()
        
        # 2. Buscar clientes com vendas
        print("2️⃣ Buscando clientes com vendas...")
        
        clientes_query = db.query(Cliente).filter(
            Cliente.user_id == user.id,
            Cliente.ativo == True
        ).limit(5)
        
        clientes = clientes_query.all()
        
        if not clientes:
            print("❌ Nenhum cliente encontrado")
            return
        
        print(f"✅ {len(clientes)} clientes encontrados para teste")
        print()
        
        # 3. Testar cálculo de métricas
        print("3️⃣ Testando cálculo de métricas...")
        print("-" * 60)
        
        for i, cliente in enumerate(clientes, 1):
            print(f"\n📊 Cliente {i}: {cliente.nome} (ID: {cliente.id})")
            
            try:
                # Calcular métricas
                metricas = SegmentacaoService.calcular_metricas_cliente(
                    cliente_id=cliente.id,
                    user_id=user.id,
                    db=db
                )
                
                print(f"   Total compras 90d: R$ {metricas['total_compras_90d']:.2f}")
                print(f"   Quantidade compras 90d: {metricas['compras_90d']}")
                print(f"   Ticket médio: R$ {metricas['ticket_medio']:.2f}")
                print(f"   Última compra: {metricas['ultima_compra_dias']} dias atrás")
                print(f"   Primeira compra: {metricas['primeira_compra_dias']} dias atrás")
                print(f"   Total em aberto: R$ {metricas['total_em_aberto']:.2f}")
                print(f"   Compras período anterior: {metricas['compras_90d_anteriores']}")
                
                # Aplicar regras
                segmento, tags = SegmentacaoService.aplicar_regras_segmentacao(metricas)
                
                print(f"   🏷️  Segmento: {segmento}")
                print(f"   🏷️  Tags: {', '.join(tags)}")
                
            except Exception as e:
                print(f"   ❌ Erro ao calcular métricas: {str(e)}")
        
        print()
        print("-" * 60)
        
        # 4. Testar recálculo e persistência
        print("\n4️⃣ Testando recálculo e persistência...")
        
        cliente_teste = clientes[0]
        print(f"   Recalculando segmento do cliente: {cliente_teste.nome}")
        
        try:
            resultado = SegmentacaoService.recalcular_segmento_cliente(
                cliente_id=cliente_teste.id,
                user_id=user.id,
                db=db
            )
            
            print(f"   ✅ Segmento calculado: {resultado['segmento']}")
            print(f"   ✅ Tags: {', '.join(resultado['tags'])}")
            print(f"   ✅ Persistido no banco de dados")
            
        except Exception as e:
            print(f"   ❌ Erro ao recalcular: {str(e)}")
        
        # 5. Testar consulta de segmento
        print("\n5️⃣ Testando consulta de segmento...")
        
        try:
            segmento_salvo = SegmentacaoService.obter_segmento_cliente(
                cliente_id=cliente_teste.id,
                user_id=user.id,
                db=db
            )
            
            if segmento_salvo:
                print(f"   ✅ Segmento recuperado do banco: {segmento_salvo['segmento']}")
                print(f"   ✅ Última atualização: {segmento_salvo['updated_at']}")
            else:
                print(f"   ℹ️  Nenhum segmento salvo encontrado")
                
        except Exception as e:
            print(f"   ❌ Erro ao consultar: {str(e)}")
        
        print()
        print("=" * 60)
        print("✅ TESTES CONCLUÍDOS!")
        print("=" * 60)
        print()
        print("🚀 Próximos passos:")
        print("   1. Acesse /docs para ver os endpoints")
        print("   2. POST /segmentacao/recalcular-todos para processar todos")
        print("   3. GET /segmentacao/estatisticas para ver distribuição")
        print()
        
    except Exception as e:
        print(f"\n❌ Erro durante testes: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()


if __name__ == "__main__":
    testar_segmentacao()
