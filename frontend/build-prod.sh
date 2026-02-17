#!/bin/bash

# =========================================
# SCRIPT DE BUILD PARA PRODUÇÃO
# =========================================
# Este script garante que o build use as variáveis de ambiente corretas

echo "=========================================="
echo "🏗️  BUILD DE PRODUÇÃO - PET SHOP PRO"
echo "=========================================="

# Verificar se estamos na pasta frontend
if [ ! -f "package.json" ]; then
  echo "❌ Erro: Execute este script na pasta frontend/"
  exit 1
fi

# Mostrar configuração
echo ""
echo "📋 Configuração:"
echo "   - Modo: production"
echo "   - Arquivo .env: .env.production"
echo "   - VITE_API_URL esperado: /api"
echo ""

# Verificar se .env.production existe
if [ ! -f ".env.production" ]; then
  echo "❌ Erro: Arquivo .env.production não encontrado!"
  echo "   Crie o arquivo com: VITE_API_URL=/api"
  exit 1
fi

# Mostrar conteúdo do .env.production
echo "📄 Conteúdo do .env.production:"
cat .env.production
echo ""

# Confirmar
read -p "🔍 Pressione ENTER para continuar com o build..."

# Remover build anterior
echo "🗑️  Limpando build anterior..."
rm -rf dist/

# Build de produção
echo "🏗️  Iniciando build de produção..."
npm run build

# Verificar se build foi bem-sucedido
if [ $? -eq 0 ]; then
  echo ""
  echo "=========================================="
  echo "✅ BUILD CONCLUÍDO COM SUCESSO!"
  echo "=========================================="
  echo ""
  echo "📦 Pasta: dist/"
  echo ""
  echo "🚀 Próximos passos:"
  echo "   1. Copiar dist/ para o servidor"
  echo "   2. Reiniciar o nginx"
  echo ""
  echo "📋 Comando de deploy:"
  echo "   scp -r dist/* root@mlprohub.com.br:/opt/petshop/frontend/dist/"
  echo ""
else
  echo ""
  echo "❌ ERRO NO BUILD!"
  echo "Verifique os erros acima"
  exit 1
fi
