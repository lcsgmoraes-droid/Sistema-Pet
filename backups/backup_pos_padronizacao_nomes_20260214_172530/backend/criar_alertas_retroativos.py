"""
Script para criar alertas retroativos para produtos com estoque negativo
"""
import sys
import os
sys.path.append('/app')

from sqlalchemy.orm import Session
from app.db import get_session
from app.produtos_models import Produto
from app.models import Tenant
from app.estoque_models import AlertaEstoqueNegativo

def criar_alertas_retroativos():
    """Cria alertas para produtos que já estão com estoque negativo"""
    db = next(get_session())
    
    try:
        # Buscar todos os produtos com estoque negativo
        produtos_negativos = db.query(Produto).filter(
            Produto.estoque_atual < 0
        ).all()
        
        print(f"\n🔍 Encontrados {len(produtos_negativos)} produtos com estoque negativo\n")
        
        alertas_criados = 0
        
        for produto in produtos_negativos:
            # Verificar se já existe alerta ativo para este produto
            alerta_existente = db.query(AlertaEstoqueNegativo).filter(
                AlertaEstoqueNegativo.produto_id == produto.id,
                AlertaEstoqueNegativo.resolvido == False
            ).first()
            
            if alerta_existente:
                print(f"⏭️  {produto.nome} - Já possui alerta ativo (ID: {alerta_existente.id})")
                continue
            
            # Criar alerta retroativo
            alerta = AlertaEstoqueNegativo(
                tenant_id=produto.tenant_id,
                produto_id=produto.id,
                produto_nome=produto.nome,
                estoque_anterior=0,  # Não sabemos o valor anterior
                quantidade_vendida=abs(produto.estoque_atual),  # Aproximação
                estoque_resultante=produto.estoque_atual,
                venda_id=None,  # Não sabemos qual venda causou
                venda_codigo=None,
                critico=(produto.estoque_atual < -5),
                status='pendente',
                observacao='Alerta criado retroativamente - produto já estava com estoque negativo'
            )
            
            db.add(alerta)
            alertas_criados += 1
            
            print(f"✅ {produto.nome} - Estoque: {produto.estoque_atual} - Alerta criado")
        
        db.commit()
        
        print(f"\n✅ Total de alertas criados: {alertas_criados}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    criar_alertas_retroativos()
