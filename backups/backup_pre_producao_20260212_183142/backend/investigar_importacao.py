"""Script temporário para investigar problemas de importação"""
import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

from app.db import SessionLocal
from app.models import Cliente
from app.produtos_models import Produto
from app.vendas_models import Venda
from sqlalchemy import func, text

db = SessionLocal()

print("\n=== 1. CLIENTES DUPLICADOS ===")
# Clientes com mesmo código
duplicados = db.query(
    Cliente.codigo, 
    Cliente.nome,
    func.count(Cliente.id).label('vezes')
).group_by(Cliente.codigo, Cliente.nome).having(func.count(Cliente.id) > 1).all()

print(f"Total de códigos duplicados: {len(duplicados)}")
for cod, nome, vezes in duplicados[:10]:
    print(f"  {cod} - {nome}: {vezes}x")

print("\n=== 2. TELEFONES VAZIOS ===")
total_clientes = db.query(func.count(Cliente.id)).scalar()
com_telefone = db.query(func.count(Cliente.id)).filter(
    (Cliente.telefone != None) | (Cliente.celular != None)
).scalar()
print(f"Total clientes: {total_clientes}")
print(f"Com telefone/celular: {com_telefone}")
print(f"Sem telefone: {total_clientes - com_telefone}")

# Verificar alguns clientes específicos
print("\nExemplos de clientes importados:")
clientes = db.query(Cliente).filter(Cliente.codigo.in_(['9923', '3723', '4060'])).all()
for c in clientes:
    print(f"  {c.codigo} - {c.nome}")
    print(f"    Tel: {c.telefone} | Cel: {c.celular}")

print("\n=== 3. PRODUTOS - MARCA/FORNECEDOR ===")
# Verificar estrutura de produtos
produto = db.query(Produto).first()
if produto:
    print(f"Campos do modelo Produto:")
    for col in produto.__table__.columns:
        val = getattr(produto, col.name, None)
        print(f"  {col.name}: {val}")

print("\n=== 4. VENDAS - DATAS ===")
vendas = db.query(Venda).filter(Venda.numero_venda.like('IMP-%')).order_by(Venda.data_venda.desc()).limit(5).all()
print(f"Total vendas importadas: {db.query(func.count(Venda.id)).filter(Venda.numero_venda.like('IMP-%')).scalar()}")
print("5 vendas mais recentes:")
for v in vendas:
    print(f"  {v.numero_venda} - {v.data_venda.strftime('%d/%m/%Y')} - R$ {v.total}")

db.close()
