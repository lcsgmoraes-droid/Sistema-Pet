# 🚨 PROBLEMA: Frontend em Produção Usando Configurações de DEV

## ❌ Problema Identificado

O frontend em produção está fazendo requisições para:
```
http://127.0.0.1:8000/racoes/analises/opcoes-filtros
```

Quando deveria estar fazendo para:
```
https://mlprohub.com.br/api/racoes/analises/opcoes-filtros
```

Ou de forma relativa (recomendado):
```
/api/racoes/analises/opcoes-filtros
```

## 🔍 Causa Raiz

O build do frontend está usando o arquivo `.env` (desenvolvimento) em vez de `.env.production`:

### .env (DEV) ❌
```env
VITE_API_URL=http://127.0.0.1:8000
```

### .env.production (PROD) ✅
```env
VITE_API_URL=/api
```

## 🏗️ Arquitetura de Deploy Atual

O `docker-compose.prod.yml` mostra que o Nginx serve o conteúdo de:
```yaml
volumes:
  - ./frontend/dist:/usr/share/nginx/html:ro
```

Isso significa que o **build é feito fora do Docker** e o diretório `dist/` é montado diretamente.

## ✅ SOLUÇÃO 1: Build Local + Deploy Manual (RECOMENDADO AGORA)

### Passo 1: Executar Build de Produção

**No Windows:**
```batch
cd frontend
build-prod.bat
```

**No Linux/Mac:**
```bash
cd frontend
bash build-prod.sh
```

Ou manualmente:
```bash
cd frontend
npm run build
```

### Passo 2: Verificar Build Correto

Abra `frontend/dist/assets/*.js` e procure por:
- ❌ **NÃO DEVE CONTER**: `http://127.0.0.1:8000`
- ✅ **DEVE CONTER**: `/api` ou referências relativas

### Passo 3: Deploy para Produção

```bash
scp -r frontend/dist/* root@mlprohub.com.br:/opt/petshop/frontend/dist/
```

### Passo 4: Verificar no Servidor

```bash
ssh root@mlprohub.com.br
cd /opt/petshop
ls -lh frontend/dist/
cat frontend/dist/index.html
```

Verificar que os arquivos foram atualizados (data/hora recente).

## ✅ SOLUÇÃO 2: Corrigir Docker Build (FUTURO)

Para usar o build Docker corretamente, modifique `docker-compose.prod.yml`:

### Antes (Linha 104):
```yaml
- ./frontend/dist:/usr/share/nginx/html:ro
```

### Depois:
```yaml
# Remover o volume mount e deixar o nginx usar o conteúdo da imagem do frontend
```

E ajustar o Dockerfile.prod para copiar o dist/ para um volume compartilhado ou usar NGINX multi-stage build:

```dockerfile
# Stage 2: Servir com Nginx (já dentro do container frontend)
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

**⚠️ Nota:** Esta solução requer refatoração maior da arquitetura Docker.

## 📋 Verificação Pós-Deploy

### 1. Verificar Console do Browser

Acesse `https://mlprohub.com.br` e abra DevTools (F12):

```
🌐 [API Config] Configuração do Axios carregada
  Mode: production
  VITE_API_URL (configurado): /api
  API_URL (final): /api
```

### 2. Verificar Network Tab

As requisições devem ser:
- ✅ `https://mlprohub.com.br/api/racoes/analises/opcoes-filtros`
- ❌ ~~`http://127.0.0.1:8000/racoes/analises/opcoes-filtros`~~

### 3. Verificar Status das Requisições

- **200 OK**: Sucesso! ✅
- **403 Forbidden**: Token inválido ou expirado (problema de autenticação, não de URL)
- **500 Internal Server Error**: Erro no backend

## 🔧 Mudanças Já Realizadas

### ✅ 1. package.json
```json
"build": "vite build --mode production"
```
Força o uso do `.env.production` durante o build.

### ✅ 2. api.js - Validação de Ambiente
Adicionado código que alerta se a configuração estiver errada:
```javascript
if (isProduction && API_URL !== '/api') {
  console.error('❌ [API Config] ERRO: Em produção, VITE_API_URL deve ser "/api"!');
}
```

### ✅ 3. Scripts de Build
- `build-prod.bat` (Windows)
- `build-prod.sh` (Linux/Mac)

Validam que `.env.production` existe antes de fazer o build.

## 🎯 Próximos Passos

1. ⏳ **Executar**: `npm run build` ou usar script `build-prod.bat`
2. ⏳ **Verificar**: Console de build mostra `VITE_API_URL=/api`
3. ⏳ **Deploy**: `scp -r dist/* root@mlprohub.com.br:/opt/petshop/frontend/dist/`
4. ⏳ **Testar**: Acessar site e verificar requisições no DevTools Network
5. ⏳ **Validar**: Login funcionando, dados carregando, sem erros 403

## 📞 Em Caso de Problemas

### Problema: Build ainda usa .env

**Solução:**
```bash
# Deletar node_modules/.vite (cache)
rm -rf node_modules/.vite
# Rebuild
npm run build
```

### Problema: Ainda vejo 127.0.0.1 no console

**Solução:**
- Hard refresh no navegador: Ctrl + Shift + R
- Limpar cache: DevTools > Application > Clear Storage
- Modo anônimo: Ctrl + Shift + N

### Problema: 403 Forbidden após correção da URL

**Solução:**
- Problema diferente! A URL está correta agora.
- 403 = token inválido/expirado
- Fazer logout e login novamente
- Verificar que token está sendo enviado: DevTools > Network > Headers > Authorization

## 📚 Arquivos Relacionados

- [frontend/package.json](frontend/package.json) - Scripts de build
- [frontend/.env](frontend/.env) - Desenvolvimento
- [frontend/.env.production](frontend/.env.production) - Produção
- [frontend/src/api.js](frontend/src/api.js) - Configuração Axios
- [frontend/build-prod.bat](frontend/build-prod.bat) - Script Windows
- [frontend/build-prod.sh](frontend/build-prod.sh) - Script Linux/Mac
- [docker-compose.prod.yml](docker-compose.prod.yml) - Deploy Docker
- [nginx/nginx.conf](nginx/nginx.conf) - Configuração proxy /api

---

**Data:** 2025-01-XX  
**Status:** 🔴 PENDENTE EXECUÇÃO  
**Prioridade:** 🔥 CRÍTICA (PRODUÇÃO OFFLINE)
