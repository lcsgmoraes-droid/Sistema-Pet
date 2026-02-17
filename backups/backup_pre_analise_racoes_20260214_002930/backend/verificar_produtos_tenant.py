#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verificar produtos por tenant"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Produtos por tenant
    print("\n" + "="*60)
    print("PRODUTOS POR TENANT")
    print("="*60)
    result = conn.execute(text("SELECT tenant_id, COUNT(*) as total FROM produtos GROUP BY tenant_id"))
    for row in result:
        print(f"Tenant {row[0]}: {row[1]} produtos")
    
    # Total geral
    result = conn.execute(text("SELECT COUNT(*) FROM produtos"))
    total = result.fetchone()[0]
    print(f"\nTotal geral: {total} produtos")
    
    # Produtos sem tenant (problema!)
    result = conn.execute(text("SELECT COUNT(*) FROM produtos WHERE tenant_id IS NULL"))
    sem_tenant = result.fetchone()[0]
    if sem_tenant > 0:
        print(f"\n⚠️  PROBLEMA: {sem_tenant} produtos SEM tenant_id!")
        print("Esses produtos não aparecerão no frontend!")
    
    print("="*60)
