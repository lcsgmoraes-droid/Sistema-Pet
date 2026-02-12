#!/usr/bin/env python3
"""Script para reprocessar comissões de vendas"""

import sys
sys.path.insert(0, '/app')

from app.db import SessionLocal
from sqlalchemy.orm import configure_mappers

# Forçar configuração detodos mappers antes de importar services
# Isso resolve problemas de relacionamentos lazy entre models
configure_mappers()

from app.comissoes_service import gerar_comissoes_venda
from decimal import Decimal
from sqlalchemy import text

# IDs das vendas para reprocessar
vendas_ids = [23, 24, 28, 29, 39, 40, 41, 42]

db = SessionLocal()

try:
    for venda_id in vendas_ids:
        print(f"\n{'='*60}")
        print(f"🔄 Reprocessando venda ID {venda_id}...")
        print(f"{'='*60}")
        
        # Buscar dados da venda
        result = db.execute(text("""
            SELECT id, numero_venda, funcionario_id, status, total
            FROM vendas 
            WHERE id = :venda_id
        """), {'venda_id': venda_id})
        
        venda = result.fetchone()
        
        if not venda:
            print(f"❌ Venda {venda_id} não encontrada!")
            continue
        
        if not venda[2]:  # funcionario_id
            print(f"⚠️ Venda {venda[1]} sem funcionário - pulando")
            continue
        
        # Buscar total pago
        result_pago = db.execute(text("""
            SELECT COALESCE(SUM(valor), 0) 
            FROM venda_pagamentos 
            WHERE venda_id = :venda_id
        """), {'venda_id': venda_id})
        
        total_pago = result_pago.scalar() or 0
        valor_pago = Decimal(str(total_pago)) if total_pago > 0 else None
        
        print(f"📊 Venda: {venda[1]}")
        print(f"   Status: {venda[3]}")
        print(f"   Total: R$ {venda[4]:.2f}")
        print(f"   Funcionário ID: {venda[2]}")
        print(f"   Total pago: R$ {total_pago:.2f}" if total_pago else "   Sem pagamentos")
        
        # Gerar comissões
        resultado = gerar_comissoes_venda(
            venda_id=venda[0],
            funcionario_id=venda[2],
            valor_pago=valor_pago,
            parcela_numero=1,
            db=db
        )
        
        if resultado.get('success'):
            total_comissao = resultado.get('total_comissao', 0)
            if resultado.get('duplicated'):
                print(f"ℹ️ Comissões já existiam (R$ {total_comissao:.2f})")
            else:
                print(f"✅ Comissões geradas com sucesso!")
                print(f"   💰 Total comissão: R$ {total_comissao:.2f}")
        else:
            print(f"❌ Erro: {resultado.get('error', 'Erro desconhecido')}")
    
    print(f"\n{'='*60}")
    print(f"✅ Reprocessamento concluído!")
    print(f"{'='*60}")
    
except Exception as e:
    print(f"\n❌ ERRO FATAL: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
