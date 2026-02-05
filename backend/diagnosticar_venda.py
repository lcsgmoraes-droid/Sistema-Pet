"""
Diagnostico: Ver estado das vendas em aberto e seus recebimentos
"""

from app.db import SessionLocal
from app.financeiro_models import ContaReceber, Recebimento
from app.vendas_models import Venda

db = SessionLocal()

try:
    print("\n" + "=" * 80)
    print("DIAGNOSTICO: Vendas em Aberto e Recebimentos")
    print("=" * 80)
    
    # Buscar venda específica mencionada
    venda = db.query(Venda).filter(Venda.numero_venda == '202601100003').first()
    
    if venda:
        print(f"\nVENDA #{venda.numero_venda} (ID: {venda.id})")
        print(f"   Status: {venda.status}")
        print(f"   Total: R$ {float(venda.total):.2f}")
        print(f"   Data: {venda.data_venda}")
        
        # Buscar contas a receber desta venda
        contas = db.query(ContaReceber).filter(
            ContaReceber.venda_id == venda.id
        ).all()
        
        print(f"\n   CONTAS A RECEBER: {len(contas)} encontrada(s)")
        
        for conta in contas:
            print(f"\n   Conta #{conta.id}:")
            print(f"      Descricao: {conta.descricao}")
            print(f"      Valor original: R$ {float(conta.valor_original):.2f}")
            print(f"      Valor recebido: R$ {float(conta.valor_recebido):.2f}")
            print(f"      Valor final: R$ {float(conta.valor_final):.2f}")
            print(f"      Status: {conta.status}")
            print(f"      Data emissao: {conta.data_emissao}")
            print(f"      Data vencimento: {conta.data_vencimento}")
            print(f"      Data recebimento: {conta.data_recebimento}")
            
            # Buscar recebimentos
            recebimentos = db.query(Recebimento).filter(
                Recebimento.conta_receber_id == conta.id
            ).all()
            
            print(f"\n      RECEBIMENTOS: {len(recebimentos)} encontrado(s)")
            
            for rec in recebimentos:
                print(f"         Recebimento #{rec.id}:")
                print(f"            Valor: R$ {float(rec.valor_recebido):.2f}")
                print(f"            Data: {rec.data_recebimento}")
                print(f"            Observacoes: {rec.observacoes}")
            
            if len(recebimentos) == 0:
                print("         >>> SEM RECEBIMENTOS REGISTRADOS <<<")
    else:
        print("\nVenda #202601100003 NAO ENCONTRADA")
        print("\nListando todas as vendas abertas:")
        
        vendas_abertas = db.query(Venda).filter(
            Venda.status == 'aberta'
        ).limit(10).all()
        
        for v in vendas_abertas:
            print(f"   - {v.numero_venda} (Total: R$ {float(v.total):.2f})")
    
    print("\n" + "=" * 80)
    print("FIM DO DIAGNOSTICO")
    print("=" * 80)
    
except Exception as e:
    print(f"\nERRO: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
