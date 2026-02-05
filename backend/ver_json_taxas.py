"""Verificar campo JSON taxas_por_parcela"""
from app.db import SessionLocal
from app.financeiro_models import FormaPagamento

db = SessionLocal()
forma = db.query(FormaPagamento).filter(FormaPagamento.id == 5).first()

print(f"\n📋 Forma de Pagamento: {forma.nome}")
print(f"   Permite parcelamento: {forma.permite_parcelamento}")
print(f"   Max parcelas: {forma.max_parcelas}")
print(f"   Taxas por parcela (JSON): {forma.taxas_por_parcela}")
print()

db.close()
