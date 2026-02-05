"""
Script para instalar dados de idioma português (por.traineddata) no Tesseract
Executa com privilégios elevados se necessário
"""

import os
import shutil
import urllib.request
import sys

print("=" * 70)
print("INSTALADOR - Idioma Português para Tesseract OCR")
print("=" * 70)

# Caminhos
TEMP_FILE = os.path.join(os.environ['TEMP'], 'por.traineddata')
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tessdata",
    r"C:\Tesseract-OCR\tessdata",
    r"C:\Program Files (x86)\Tesseract-OCR\tessdata"
]

# URL do arquivo
URL = "https://raw.githubusercontent.com/tesseract-ocr/tessdata/master/por.traineddata"

print("\n1. Baixando arquivo de idioma português...")
print(f"   URL: {URL}")

try:
    urllib.request.urlretrieve(URL, TEMP_FILE)
    if os.path.exists(TEMP_FILE):
        size_mb = os.path.getsize(TEMP_FILE) / (1024 * 1024)
        print(f"   ✅ Download concluído ({size_mb:.1f} MB)")
    else:
        print("   ❌ Falha no download")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Erro: {e}")
    sys.exit(1)

# Encontrar e copiar para o Tesseract
print("\n2. Procurando diretório do Tesseract...")
dest_found = False

for tessdata_dir in TESSERACT_PATHS:
    if os.path.exists(tessdata_dir):
        dest_file = os.path.join(tessdata_dir, 'por.traineddata')
        
        print(f"   Encontrado: {tessdata_dir}")
        print(f"   Copiando para: {dest_file}")
        
        try:
            shutil.copy2(TEMP_FILE, dest_file)
            if os.path.exists(dest_file):
                size_mb = os.path.getsize(dest_file) / (1024 * 1024)
                print(f"   ✅ Instalado com sucesso ({size_mb:.1f} MB)")
                dest_found = True
                break
        except PermissionError:
            print(f"   ⚠️  Sem permissão para escrever em {tessdata_dir}")
            continue
        except Exception as e:
            print(f"   ❌ Erro ao copiar: {e}")
            continue

if not dest_found:
    print("\n   ❌ Não foi possível instalar em nenhum diretório")
    print("   Possíveis soluções:")
    print("   1. Execute este script como Administrador (botão direito → Executar como administrador)")
    print("   2. Ou configure a variável TESSDATA_PREFIX no ambiente")
    sys.exit(1)

# Limpar arquivo temporário
try:
    os.remove(TEMP_FILE)
except:
    pass

print("\n" + "=" * 70)
print("✅ INSTALAÇÃO CONCLUÍDA COM SUCESSO!")
print("=" * 70)
print("\n💡 Próximos passos:")
print("   1. Reinicie o servidor backend")
print("   2. Tente fazer upload de um PDF")
print("   3. O OCR em português deve funcionar agora!")
print("\n" + "=" * 70)
