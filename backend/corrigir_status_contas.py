"""
Corrigir status de contas a receber: baixa_parcial -> parcial
"""

from app.db import SessionLocal
from app.financeiro_models import ContaReceber
from app.vendas_models import Venda  # Importar para resolver foreign key
from app.models import Cliente  # Importar para resolver foreign key

db = SessionLocal()

try:
    print("\n" + "=" * 80)
    print("CORRECAO: Ajustando status de contas a receber")
    print("=" * 80)
    
    # Buscar contas com status incorreto
    contas = db.query(ContaReceber).filter(
        ContaReceber.status == 'baixa_parcial'
    ).all()
    
    print(f"\nEncontradas {len(contas)} contas com status 'baixa_parcial'")
    
    for conta in contas:
        print(f"   Conta #{conta.id} - Alterando de 'baixa_parcial' para 'parcial'")
        conta.status = 'parcial'
        db.add(conta)
    
    # Buscar outras variações incorretas
    contas_recebido = db.query(ContaReceber).filter(
        ContaReceber.status == 'recebido',
        ContaReceber.valor_recebido < ContaReceber.valor_final
    ).all()
    
    if contas_recebido:
        print(f"\nEncontradas {len(contas_recebido)} contas marcadas como 'recebido' mas com saldo")
        for conta in contas_recebido:
            saldo = float(conta.valor_final) - float(conta.valor_recebido)
            print(f"   Conta #{conta.id} - Saldo restante: R$ {saldo:.2f} - Alterando para 'parcial'")
            conta.status = 'parcial'
            db.add(conta)
    
    if len(contas) > 0 or len(contas_recebido) > 0:
        db.commit()
        print("\n" + "=" * 80)
        print(f"SUCESSO! {len(contas) + len(contas_recebido)} contas corrigidas")
        print("=" * 80)
    else:
        print("\nNenhuma correcao necessaria!")
    
except Exception as e:
    print(f"\nERRO: {e}")
    db.rollback()
    import traceback
    traceback.print_exc()
finally:
    db.close()
