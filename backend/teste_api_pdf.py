#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de upload de PDF via API do backend
Simula o que o frontend faz ao enviar um PDF para extração
"""
import requests
import json
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

BASE_URL = "http://localhost:8000"

print("📡 Testando API de extrato...")

# Criar PDF de teste
print("\n📄 Criando PDF de teste...")
pdf_bytes = io.BytesIO()
doc = SimpleDocTemplate(pdf_bytes, pagesize=letter)
styles = getSampleStyleSheet()
story = []

story.append(Paragraph("BANCO DO BRASIL S.A.", styles['Title']))
story.append(Spacer(1, 12))
story.append(Paragraph("EXTRATO DE CONTA CORRENTE", styles['Heading1']))
story.append(Spacer(1, 12))

# Simular um extrato bancário
conteudo = """
Período: 01/01/2024 a 31/01/2024
Agência: 1234-5
Conta Corrente: 987654-3

SALDO ANTERIOR: 10.000,00

OPERAÇÕES:

01/01/2024 - Depósito de clientes: 5.000,00
02/01/2024 - Saque - cheque 123456: -1.500,00
05/01/2024 - Transferência recebida - BB: 2.500,00
08/01/2024 - Taxa de manutenção: -50,00
10/01/2024 - Rendimento poupança: 150,00
15/01/2024 - Depósito de vendas: 3.200,00
20/01/2024 - Pagamento boleto: -800,00
25/01/2024 - Saque caixa eletrônico: -1.000,00

SALDO FINAL: 17.500,00
"""

for linha in conteudo.split('\n'):
    if linha.strip():
        story.append(Paragraph(linha, styles['Normal']))

doc.build(story)
pdf_bytes.seek(0)
pdf_data = pdf_bytes.getvalue()

print(f"✅ PDF criado: {len(pdf_data)} bytes")

# Testar upload
print(f"\n📤 Testando POST {BASE_URL}/api/ia/extrato/processar")

try:
    # Preparar multipart form
    files = {'arquivo': ('teste_extrato.pdf', io.BytesIO(pdf_data), 'application/pdf')}
    data = {
        'nome_arquivo': 'teste_extrato.pdf',
        'tipo': 'pdf'
    }
    
    response = requests.post(
        f"{BASE_URL}/api/ia/extrato/processar",
        files=files,
        data=data,
        timeout=30
    )
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCESSO!")
        print(f"   Registros extraídos: {len(result.get('lancamentos', []))}")
        
        if result.get('lancamentos'):
            print(f"\n   Primeiros registros:")
            for i, reg in enumerate(result['lancamentos'][:3]):
                print(f"   {i+1}. {reg}")
        
        print(f"\n   Resposta completa:")
        print(json.dumps(result, indent=2, default=str)[:500] + "...")
    else:
        print(f"❌ ERRO!")
        print(f"   Response: {response.text[:500]}")
        
except requests.exceptions.ConnectionError:
    print(f"❌ Não conseguiu conectar. Backend está rodando?")
    print(f"   Execute: python -m uvicorn app.main:app --reload")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Teste de API concluído")
print("="*60)
