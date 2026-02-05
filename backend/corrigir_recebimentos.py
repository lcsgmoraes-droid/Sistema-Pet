"""
Script de correção: Criar registros de Recebimento para vendas em aberto que foram pagas
Executar dentro do diretório backend
"""

from app.db import SessionLocal
from app.financeiro_models import ContaReceber, Recebimento, FormaPagamento
from app.vendas_models import Venda, VendaPagamento
from datetime import date
from decimal import Decimal

def corrigir():
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 80)
        print("CORRECAO: Criando registros de Recebimento faltantes")
        print("=" * 80)
        
        # Buscar contas com valor recebido > 0
        contas = db.query(ContaReceber).filter(
            ContaReceber.valor_recebido > 0
        ).all()
        
        print(f"\nAnalisando {len(contas)} contas a receber com valores recebidos...")
        
        corrigidas = 0
        
        for conta in contas:
            # Verificar recebimentos existentes
            recebimentos = db.query(Recebimento).filter(
                Recebimento.conta_receber_id == conta.id
            ).all()
            
            total_rec = sum(float(r.valor_recebido) for r in recebimentos)
            valor_conta = float(conta.valor_recebido)
            diferenca = valor_conta - total_rec
            
            if abs(diferenca) > 0.01:
                print(f"\nConta #{conta.id} (Venda #{conta.venda_id})")
                print(f"   Valor recebido: R$ {valor_conta:.2f}")
                print(f"   Recebimentos: R$ {total_rec:.2f}")
                print(f"   Faltando: R$ {diferenca:.2f}")
                
                # Buscar forma de pagamento
                forma_id = None
                venda_num = "N/A"
                
                if conta.venda_id:
                    venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
                    if venda:
                        venda_num = venda.numero_venda
                        pags = db.query(VendaPagamento).filter(
                            VendaPagamento.venda_id == venda.id
                        ).first()
                        
                        if pags:
                            forma = db.query(FormaPagamento).filter(
                                FormaPagamento.nome.ilike(f"%{pags.forma_pagamento}%")
                            ).first()
                            if forma:
                                forma_id = forma.id
                
                # Criar recebimento
                rec = Recebimento(
                    conta_receber_id=conta.id,
                    valor_recebido=Decimal(str(diferenca)),
                    data_recebimento=conta.data_recebimento or date.today(),
                    forma_pagamento_id=forma_id,
                    observacoes=f"Correcao automatica - Venda {venda_num}",
                    user_id=conta.user_id
                )
                
                db.add(rec)
                corrigidas += 1
                print(f"   OK - Recebimento criado")
        
        if corrigidas > 0:
            db.commit()
            print("\n" + "=" * 80)
            print(f"SUCESSO! {corrigidas} recebimentos criados")
            print("=" * 80)
        else:
            print("\nNenhuma correcao necessaria!")
        
        return corrigidas
        
    except Exception as e:
        print(f"\nERRO: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    corrigir()
