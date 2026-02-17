#!/bin/bash

# 🔧 Script de Diagnóstico e Correção - Erro 404 Frontend
# Uso: ./DIAGNOSTICAR_E_CORRIGIR_404.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 DIAGNÓSTICO - Erro 404 Frontend (/notas-fiscais)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Verificar se estamos na pasta correta
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}❌ Erro: docker-compose.prod.yml não encontrado${NC}"
    echo -e "${YELLOW}Execute este script na pasta raiz do projeto (Sistema Pet)${NC}"
    exit 1
fi

# ============================================================================
# PASSO 1: Verificar Containers
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📦 PASSO 1: Verificando Containers${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if docker ps | grep -q "petshop-prod-nginx"; then
    echo -e "${GREEN}✅ Container nginx está rodando${NC}"
else
    echo -e "${RED}❌ Container nginx NÃO está rodando${NC}"
    echo -e "${YELLOW}Action: Iniciando container...${NC}"
    docker-compose -f docker-compose.prod.yml up -d nginx
fi

if docker ps | grep -q "petshop-prod-frontend"; then
    echo -e "${GREEN}✅ Container frontend está rodando${NC}"
else
    echo -e "${YELLOW}⚠️  Container frontend NÃO está rodando${NC}"
fi

echo ""

# ============================================================================
# PASSO 2: Verificar Arquivos do Frontend (Local)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📁 PASSO 2: Verificando Arquivos Frontend (Local)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -d "frontend/dist" ]; then
    echo -e "${GREEN}✅ Pasta frontend/dist existe${NC}"
    
    if [ -f "frontend/dist/index.html" ]; then
        echo -e "${GREEN}✅ index.html existe${NC}"
        FILE_SIZE=$(stat -f%z "frontend/dist/index.html" 2>/dev/null || stat -c%s "frontend/dist/index.html" 2>/dev/null || echo "0")
        echo -e "   Tamanho: ${FILE_SIZE} bytes"
        
        if [ "$FILE_SIZE" -lt 1000 ]; then
            echo -e "${RED}❌ Arquivo muito pequeno - provavelmente inválido${NC}"
            REBUILD_NEEDED=true
        fi
    else
        echo -e "${RED}❌ index.html NÃO existe${NC}"
        REBUILD_NEEDED=true
    fi
    
    # Contar arquivos
    FILE_COUNT=$(find frontend/dist -type f | wc -l | tr -d ' ')
    echo -e "   Total de arquivos: ${FILE_COUNT}"
    
    if [ "$FILE_COUNT" -lt 5 ]; then
        echo -e "${RED}❌ Muito poucos arquivos - build incompleto${NC}"
        REBUILD_NEEDED=true
    fi
else
    echo -e "${RED}❌ Pasta frontend/dist NÃO existe${NC}"
    REBUILD_NEEDED=true
fi

echo ""

# ============================================================================
# PASSO 3: Verificar Arquivos dentro do Container Nginx
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🐳 PASSO 3: Verificando Arquivos no Container Nginx${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if docker exec petshop-prod-nginx test -f /usr/share/nginx/html/index.html; then
    echo -e "${GREEN}✅ index.html existe no container nginx${NC}"
    FILE_SIZE=$(docker exec petshop-prod-nginx stat -c%s /usr/share/nginx/html/index.html)
    echo -e "   Tamanho: ${FILE_SIZE} bytes"
else
    echo -e "${RED}❌ index.html NÃO existe no container nginx${NC}"
    echo -e "${YELLOW}   O volume não está montado corretamente!${NC}"
    REBUILD_NEEDED=true
fi

# Listar arquivos no container
echo -e "\n${YELLOW}📋 Conteúdo de /usr/share/nginx/html:${NC}"
docker exec petshop-prod-nginx ls -lh /usr/share/nginx/html/ | head -10

echo ""

# ============================================================================
# PASSO 4: Verificar Configuração do Nginx
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}⚙️  PASSO 4: Verificando Configuração Nginx${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${YELLOW}Verificando diretiva 'try_files':${NC}"
if docker exec petshop-prod-nginx grep -q "try_files.*index.html" /etc/nginx/nginx.conf; then
    echo -e "${GREEN}✅ try_files configurado corretamente${NC}"
    docker exec petshop-prod-nginx grep "try_files" /etc/nginx/nginx.conf | head -1
else
    echo -e "${RED}❌ try_files NÃO encontrado ou incorreto${NC}"
fi

# Testar configuração do nginx
echo -e "\n${YELLOW}Testando sintaxe do nginx:${NC}"
if docker exec petshop-prod-nginx nginx -t 2>&1 | grep -q "successful"; then
    echo -e "${GREEN}✅ Configuração nginx OK${NC}"
else
    echo -e "${RED}❌ Erro na configuração nginx${NC}"
    docker exec petshop-prod-nginx nginx -t 2>&1
fi

echo ""

# ============================================================================
# PASSO 5: Teste de Conectividade
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔌 PASSO 5: Testando Conectividade${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${YELLOW}Teste interno (localhost):${NC}"
RESPONSE_INTERNAL=$(docker exec petshop-prod-nginx wget -q -O - http://localhost/notas-fiscais 2>&1 | head -1)
if [[ "$RESPONSE_INTERNAL" == *"<html"* ]] || [[ "$RESPONSE_INTERNAL" == *"<!DOCTYPE"* ]]; then
    echo -e "${GREEN}✅ Nginx servindo HTML internamente${NC}"
else
    echo -e "${RED}❌ Nginx NÃO está servindo HTML internamente${NC}"
    echo -e "   Resposta: ${RESPONSE_INTERNAL}"
fi

echo ""

# ============================================================================
# PASSO 6: Verificar Logs
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📋 PASSO 6: Últimas Linhas dos Logs${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${YELLOW}Logs do Nginx (últimas 10 linhas):${NC}"
docker logs petshop-prod-nginx --tail 10 2>&1 | grep -v "GET /health" || echo "(nenhum log recente)"

echo ""
echo ""

# ============================================================================
# DECISÃO: PRECISA REBUILD?
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🎯 RESULTADO DO DIAGNÓSTICO${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

if [ "${REBUILD_NEEDED}" = true ]; then
    echo -e "${RED}❌ PROBLEMA DETECTADO: Frontend precisa ser reconstruído${NC}"
    echo ""
    echo -e "${YELLOW}Deseja fazer o rebuild e deploy agora? (s/n)${NC}"
    read -r RESPOSTA
    
    if [[ "$RESPOSTA" =~ ^[SsYy]$ ]]; then
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}🔧 CORREÇÃO AUTOMÁTICA${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        
        echo -e "\n${YELLOW}1. Verificando .env.production...${NC}"
        echo "VITE_API_URL=/api" > frontend/.env.production
        echo -e "${GREEN}✅ .env.production atualizado${NC}"
        
        echo -e "\n${YELLOW}2. Fazendo build do frontend...${NC}"
        cd frontend
        npm run build
        cd ..
        echo -e "${GREEN}✅ Build concluído${NC}"
        
        echo -e "\n${YELLOW}3. Reconstruindo container...${NC}"
        docker-compose -f docker-compose.prod.yml build --no-cache frontend
        echo -e "${GREEN}✅ Container reconstruído${NC}"
        
        echo -e "\n${YELLOW}4. Reiniciando serviços...${NC}"
        docker-compose -f docker-compose.prod.yml up -d frontend nginx
        echo -e "${GREEN}✅ Serviços reiniciados${NC}"
        
        echo -e "\n${YELLOW}5. Aguardando containers iniciarem...${NC}"
        sleep 5
        
        echo -e "\n${GREEN}✅ CORREÇÃO CONCLUÍDA!${NC}"
        echo ""
        echo -e "${YELLOW}Teste agora:${NC}"
        echo -e "   https://mlprohub.com.br/notas-fiscais"
        echo ""
    else
        echo -e "${YELLOW}Correção cancelada pelo usuário${NC}"
        echo ""
        echo -e "${YELLOW}Para corrigir manualmente, execute:${NC}"
        echo -e "   cd frontend"
        echo -e "   npm run build"
        echo -e "   cd .."
        echo -e "   docker-compose -f docker-compose.prod.yml up -d --build frontend nginx"
    fi
else
    echo -e "${GREEN}✅ Nenhum problema detectado no build do frontend${NC}"
    echo ""
    echo -e "${YELLOW}O problema pode ser:${NC}"
    echo -e "   1. Cache do navegador - Tente Ctrl+Shift+R"
    echo -e "   2. CDN/Proxy externo cacheando a resposta 404"
    echo -e "   3. Problema de rede/DNS"
    echo ""
    echo -e "${YELLOW}Tente:${NC}"
    echo -e "   - Abrir em aba anônima"
    echo -e "   - Limpar cache do navegador"
    echo -e "   - Testar de outro dispositivo"
    echo ""
    echo -e "${YELLOW}Ou force um restart:${NC}"
    echo -e "   docker-compose -f docker-compose.prod.yml restart nginx"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
