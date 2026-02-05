"""Corrigir taxa fixa do PIX de 100 para 1"""
from app.db import SessionLocal
from app.financeiro_models import FormaPagamento

db = SessionLocal()

# PIX
pix = db.query(FormaPagamento).filter(FormaPagamento.id == 2).first()
if pix:
    print(f"PIX - Taxa fixa atual: {pix.taxa_fixa}")
    pix.taxa_fixa = 1.00
    db.commit()
    print(f"PIX - Taxa fixa corrigida: {pix.taxa_fixa}")

db.close()
print("\n✅ Correção concluída!")
