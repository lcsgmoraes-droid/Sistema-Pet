"""
Testar busca de vendas com join de cliente
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, or_, func
from sqlalchemy.orm import sessionmaker, joinedload
from app.vendas_models import Venda
from app.models import Cliente

# Conectar ao banco
engine = create_engine('sqlite:///petshop.db')
Session = sessionmaker(bind=engine)
db = Session()

try:
    print("=" * 60)
    print("TESTE DE BUSCA COM JOIN")
    print("=" * 60)
    
    busca = "lucas"
    busca_lower = f'%{busca.lower()}%'
    
    print(f"\n1. Busca: '{busca}' -> Pattern: '{busca_lower}'")
    
    # Query básica
    query = db.query(Venda).options(
        joinedload(Venda.pagamentos),
        joinedload(Venda.cliente)
    ).filter_by(user_id=1)
    
    print(f"\n2. Query inicial criada (user_id=1)")
    
    # Aplicar busca
    print(f"\n3. Aplicando outerjoin + filter...")
    query = query.outerjoin(Cliente, Venda.cliente_id == Cliente.id).filter(
        or_(
            Venda.numero_venda.contains(busca),
            Venda.observacoes_entrega.contains(busca),
            func.lower(Cliente.nome).like(busca_lower)
        )
    )
    
    print(f"\n4. Executando query.all()...")
    vendas = query.all()
    
    print(f"\n5. ✅ Query executada com sucesso!")
    print(f"   Total de vendas encontradas: {len(vendas)}")
    
    for venda in vendas[:5]:  # Mostrar apenas 5
        cliente_nome = venda.cliente.nome if venda.cliente else "Consumidor Final"
        print(f"   - Venda #{venda.id} ({venda.numero_venda}) - Cliente: {cliente_nome}")
    
    print(f"\n6. Testando to_dict()...")
    if vendas:
        venda_dict = vendas[0].to_dict()
        print(f"   ✅ to_dict() funcionou!")
        print(f"   - cliente_id: {venda_dict.get('cliente_id')}")
        print(f"   - cliente_nome: {venda_dict.get('cliente_nome')}")
        print(f"   - cliente: {venda_dict.get('cliente')}")
    
    print(f"\n{'='*60}")
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("="*60)
    
except Exception as e:
    print(f"\n{'='*60}")
    print(f"❌ ERRO: {type(e).__name__}")
    print(f"{'='*60}")
    print(f"\nMensagem: {str(e)}")
    print(f"\nStack trace:")
    import traceback
    traceback.print_exc()
    print("="*60)
finally:
    db.close()
