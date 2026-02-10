"""Script para testar o processamento de taxas de uma venda específica"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from contextlib import contextmanager
from app.db import get_session
from app.vendas_models import Venda, VendaPagamento
from app.financeiro_models import FormaPagamento, ContaPagar
from app.dre_plano_contas_models import DRESubcategoria
from app.vendas.service import processar_contas_pagar_taxas
from app.utils.logger import logger

@contextmanager
def get_db_session():
    """Context manager para sessão de banco de dados"""
    db = next(get_session())
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

def testar_processar_taxas(venda_id: int):
    """Testa o processamento de taxas para uma venda específica"""
    print(f"\n{'='*60}")
    print(f"TESTE: Processamento de Taxas - Venda ID {venda_id}")
    print(f"{'='*60}\n")
    
    with get_db_session() as db:
        # Buscar venda
        venda = db.query(Venda).filter(Venda.id == venda_id).first()
        if not venda:
            print(f"❌ Venda {venda_id} não encontrada")
            return
        
        print(f"✅ Venda encontrada: {venda.numero_venda}")
        print(f"   Status: {venda.status}")
        print(f"   Canal: {venda.canal}")
        print(f"   DRE Gerada: {venda.dre_gerada}")
        print(f"   Tenant ID: {venda.tenant_id}")
        print(f"   User ID: {venda.user_id}")
        
        # Buscar pagamentos
        pagamentos = db.query(VendaPagamento).filter(
            VendaPagamento.venda_id == venda_id
        ).all()
        
        print(f"\n📋 Pagamentos ({len(pagamentos)}):")
        for p in pagamentos:
            print(f"   - {p.forma_pagamento}: R$ {p.valor} ({p.numero_parcelas}x) - Status: {p.status}")
        
        # Verificar formas de pagamento configuradas
        print(f"\n💳 Formas de Pagamento Configuradas:")
        formas = db.query(FormaPagamento).filter(
            FormaPagamento.tenant_id == venda.tenant_id,
            FormaPagamento.ativo == True
        ).all()
        
        for f in formas:
            print(f"   - {f.nome} (tipo: {f.tipo}): {f.taxa_percentual}% + R$ {f.taxa_fixa}")
        
        # Verificar subcategorias DRE
        print(f"\n📊 Subcategorias DRE de Taxas:")
        subcategorias = db.query(DRESubcategoria).filter(
            DRESubcategoria.tenant_id == venda.tenant_id,
            DRESubcategoria.ativo == True
        ).filter(
            (DRESubcategoria.nome.like('%Taxa%')) |
            (DRESubcategoria.nome.like('%Cartão%'))
        ).all()
        
        for s in subcategorias:
            print(f"   - ID {s.id}: {s.nome}")
        
        # Verificar contas a pagar existentes
        contas_existentes = db.query(ContaPagar).filter(
            ContaPagar.tenant_id == venda.tenant_id
        ).filter(
            ContaPagar.descricao.like(f'%Venda {venda.numero_venda}%')
        ).all()
        
        print(f"\n💰 Contas a Pagar Existentes para esta venda: {len(contas_existentes)}")
        for c in contas_existentes:
            print(f"   - ID {c.id}: {c.descricao} - R$ {c.valor_original}")
        
        # TESTAR O PROCESSAMENTO
        print(f"\n{'='*60}")
        print("🔧 INICIANDO TESTE DE PROCESSAMENTO DE TAXAS...")
        print(f"{'='*60}\n")
        
        try:
            resultado = processar_contas_pagar_taxas(
                venda=venda,
                pagamentos=pagamentos,
                user_id=venda.user_id,
                tenant_id=venda.tenant_id,
                db=db
            )
            
            print(f"\n✅ PROCESSAMENTO CONCLUÍDO!")
            print(f"   Total de contas: {resultado['total_contas']}")
            print(f"   Valor total: R$ {resultado['valor_total']:.2f}")
            print(f"   Contas criadas: {resultado['contas_criadas']}")
            print(f"   Detalhes: {resultado['detalhes']}")
            
            # Verificar novamente as contas após processamento
            contas_apos = db.query(ContaPagar).filter(
                ContaPagar.tenant_id == venda.tenant_id
            ).filter(
                ContaPagar.descricao.like(f'%Venda {venda.numero_venda}%')
            ).all()
            
            print(f"\n💰 Contas a Pagar APÓS processamento: {len(contas_apos)}")
            for c in contas_apos:
                subcategoria = db.query(DRESubcategoria).filter(
                    DRESubcategoria.id == c.dre_subcategoria_id
                ).first()
                subcategoria_nome = subcategoria.nome if subcategoria else "N/A"
                print(f"   - ID {c.id}: {c.descricao} - R$ {c.valor_original} (Subcategoria: {subcategoria_nome})")
            
        except Exception as e:
            print(f"\n❌ ERRO NO PROCESSAMENTO:")
            print(f"   {type(e).__name__}: {str(e)}")
            import traceback
            print(f"\n{traceback.format_exc()}")

if __name__ == "__main__":
    venda_id = int(input("Digite o ID da venda para testar (ex: 68): ") or "68")
    testar_processar_taxas(venda_id)
