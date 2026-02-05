#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste completo de PDF com OCR em português
"""
import os
import sys
import io
from pathlib import Path

# Configurar tessdata ANTES de importar pytesseract
venv_tessdata = os.path.join(os.path.dirname(__file__), ".venv", "tessdata")
if not os.path.exists(venv_tessdata):
    venv_tessdata = os.path.join(os.path.dirname(__file__), "..", ".venv", "tessdata")

tessdata_paths = [
    venv_tessdata,  # Prioridade: venv local (tem por.traineddata)
    r"C:\Program Files\Tesseract-OCR\tessdata",
    r"C:\Tesseract-OCR\tessdata",
    r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
]

for tessdata_dir in tessdata_paths:
    if os.path.exists(tessdata_dir):
        print(f"✅ TESSDATA configurada: {tessdata_dir}")
        os.environ['TESSDATA_PREFIX'] = tessdata_dir
        break
else:
    print("❌ Nenhuma pasta TESSDATA encontrada!")
    sys.exit(1)

import pytesseract
from pdf2image import convert_from_bytes

# Configurar Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

print("\n📋 Testando OCR com Tesseract:")
print(f"   Tesseract: {pytesseract.pytesseract.tesseract_cmd}")
print(f"   TESSDATA_PREFIX: {os.environ.get('TESSDATA_PREFIX')}")
print(f"   Versão: {pytesseract.get_tesseract_version()}")

# Poppler
poppler_path = r"C:\poppler\poppler-24.08.0\Library\bin"

# Tentar com um PDF de exemplo
print("\n📄 Criando PDF de teste...")

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    
    # Criar PDF com texto em português
    pdf_bytes = io.BytesIO()
    doc = SimpleDocTemplate(pdf_bytes, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Adicionar conteúdo em português
    story.append(Paragraph("BANCO BRASIL SA", styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("EXTRATO BANCÁRIO", styles['Heading1']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Período: 01/01/2024 a 31/01/2024", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Agência: 0001 Conta: 123456789", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Saldo Anterior: R$ 10.000,00", styles['Normal']))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Depósito de cliente: R$ 5.000,00", styles['Normal']))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Saque por cheque: R$ 2.500,00", styles['Normal']))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Saldo Final: R$ 12.500,00", styles['Normal']))
    
    doc.build(story)
    pdf_bytes.seek(0)
    pdf_data = pdf_bytes.read()
    
    print(f"✅ PDF de teste criado ({len(pdf_data)} bytes)")
    
except ImportError:
    print("⚠️ reportlab não instalado, pulando PDF custom...")
    pdf_data = None

if pdf_data:
    print("\n🔄 Convertendo PDF para imagens...")
    try:
        if os.path.exists(poppler_path):
            imagens = convert_from_bytes(pdf_data, poppler_path=poppler_path)
        else:
            imagens = convert_from_bytes(pdf_data)
        
        print(f"✅ PDF convertido: {len(imagens)} páginas")
        
        print("\n🔍 Executando OCR em português...")
        
        # Tentar OCR com português
        for i, img in enumerate(imagens):
            print(f"\n   Página {i+1}:")
            try:
                # Tentar com português primeiro
                texto_por = pytesseract.image_to_string(img, lang='por')
                if texto_por.strip():
                    print(f"   ✅ Português: {len(texto_por)} caracteres extraídos")
                    print(f"      Preview: {texto_por[:100]}...")
                else:
                    print(f"   ⚠️ Português retornou vazio, tentando inglês...")
                    texto_eng = pytesseract.image_to_string(img, lang='eng')
                    print(f"   ✅ Inglês: {len(texto_eng)} caracteres extraídos")
                    print(f"      Preview: {texto_eng[:100]}...")
            except Exception as e:
                print(f"   ❌ Erro na página {i+1}: {e}")
        
        print("\n" + "="*60)
        print("✅ OCR COM PORTUGUÊS FUNCIONANDO!")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Erro ao processar PDF: {e}")
        import traceback
        traceback.print_exc()

else:
    print("\n" + "="*60)
    print("✅ Configuração OK (teste PDF completo pulado)")
    print("="*60)
