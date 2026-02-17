# 🔧 Correção do Erro 404 - Rota Frontend `/notas-fiscais`

## 🔍 Diagnóstico do Problema

O erro ocorre porque o nginx não está servindo o arquivo `index.html` do React para rotas do frontend. Quando você acessa `/notas-fiscais` diretamente, o nginx deveria:

1. ✅ Receber requisição para `/notas-fiscais`
2. ✅ Tentar encontrar o arquivo (não existe)
3. ✅ Fazer fallback para `/index.html` (React app)
4. ❌ **ESTÁ RETORNANDO 404 AO INVÉS DO INDEX.HTML**

## 🎯 Possíveis Causas

### 1. Frontend não foi construído/deployado
### 2. Pasta `dist` está vazia ou sem index.html
### 3. Nginx não está com a configuração correta
### 4. Cache do navegador/CDN

---

## 📋 PASSO 1: Verificar no Servidor

Execute no servidor de produção:

```bash
# Conectar ao servidor
ssh root@mlprohub.com.br

# Verificar se o container nginx está rodando
docker ps | grep nginx

# Verificar se o frontend foi construído
ls -lah ~/Sistema\ Pet/frontend/dist/

# Deve mostrar arquivos como:
# - index.html
# - assets/
# - vite.svg
# etc.

# Verificar dentro do container nginx
docker exec petshop-prod-nginx ls -lah /usr/share/nginx/html/

# Testar o nginx internamente
docker exec petshop-prod-nginx cat /etc/nginx/nginx.conf | grep -A 5 "location /"

# Verificar logs do nginx
docker logs petshop-prod-nginx --tail 50
```

---

## ✅ SOLUÇÃO 1: Rebuild e Deploy do Frontend

Se a pasta `dist` estiver vazia ou desatualizada:

### No Windows (local):

```powershell
# 1. Navegar até a pasta do frontend
cd "frontend"

# 2. Garantir que o .env.production está correto
Write-Output "VITE_API_URL=/api" | Out-File -FilePath .env.production -Encoding utf8

# 3. Instalar dependências (se necessário)
npm install

# 4. Fazer build de produção
npm run build

# 5. Verificar se o build foi criado
ls dist\

# 6. Fazer deploy completo
cd ..
.\deploy-prod-auto.ps1
```

---

## ✅ SOLUÇÃO 2: Rebuild Apenas do Frontend no Servidor

Se preferir fazer apenas o rebuild do frontend no servidor:

```bash
# No servidor
ssh root@mlprohub.com.br

cd ~/Sistema\ Pet/

# Rebuild apenas o frontend
docker-compose -f docker-compose.prod.yml build frontend

# Restart apenas nginx e frontend
docker-compose -f docker-compose.prod.yml restart frontend nginx

# Verificar logs
docker logs petshop-prod-nginx --tail 20
docker logs petshop-prod-frontend --tail 20
```

---

## ✅ SOLUÇÃO 3: Corrigir Permissões

Se os arquivos existem mas nginx não consegue lê-los:

```bash
# No servidor
ssh root@mlprohub.com.br

cd ~/Sistema\ Pet/

# Corrigir permissões da pasta dist
sudo chmod -R 755 frontend/dist/
sudo chown -R root:root frontend/dist/

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## ✅ SOLUÇÃO 4: Limpar Cache do Navegador

Às vezes o navegador está cacheando a resposta 404:

1. Abrir DevTools (F12)
2. Ir em Network
3. Marcar "Disable cache"
4. Fazer **Hard Refresh**: `Ctrl + Shift + R` ou `Ctrl + F5`
5. Ou abrir aba anônima

---

## 🔍 Verificação Rápida - Teste Manual

Execute este teste no servidor:

```bash
# Testar se o nginx está servindo index.html corretamente
curl -I http://localhost/notas-fiscais

# Se retornar 200 OK e Content-Type: text/html, está funcionando internamente
# Se retornar 404, o problema está no nginx/frontend

# Testar externamente
curl -I https://mlprohub.com.br/notas-fiscais

# Comparar ambos os resultados
```

---

## 🔧 Solução Rápida (Recomendada)

Execute este comando **no servidor**:

```bash
ssh root@mlprohub.com.br << 'ENDSSH'
cd ~/Sistema\ Pet/
echo "🔄 Verificando frontend..."
ls -lah frontend/dist/ | head -10

echo ""
echo "🔄 Rebuilding frontend..."
docker-compose -f docker-compose.prod.yml build --no-cache frontend

echo ""
echo "🔄 Reiniciando serviços..."
docker-compose -f docker-compose.prod.yml up -d frontend nginx

echo ""
echo "✅ Aguardando containers..."
sleep 5

echo ""
echo "🔍 Verificando status..."
docker ps | grep -E "frontend|nginx"

echo ""
echo "📋 Logs do nginx:"
docker logs petshop-prod-nginx --tail 10

echo ""
echo "✅ Teste o site agora: https://mlprohub.com.br/notas-fiscais"
ENDSSH
```

---

## ⚡ Solução Emergencial - Se nada funcionar

Recriar completamente os containers:

```bash
# No servidor
ssh root@mlprohub.com.br

cd ~/Sistema\ Pet/

# Parar tudo
docker-compose -f docker-compose.prod.yml down

# Rebuild completo (sem cache)
docker-compose -f docker-compose.prod.yml build --no-cache

# Subir novamente
docker-compose -f docker-compose.prod.yml up -d

# Aguardar 30 segundos
sleep 30

# Verificar status
docker-compose -f docker-compose.prod.yml ps

# Verificar logs
docker-compose -f docker-compose.prod.yml logs --tail 50
```

---

## 📊 Como Confirmar que Funcionou

1. Acesse: `https://mlprohub.com.br/notas-fiscais`
2. Você deve ver a página de Notas Fiscais (não 404)
3. Abra DevTools (F12) → Console
4. Não deve ter erro `404 (Not Found)` para `/notas-fiscais`
5. Deve ter logs de API como: `🔐 [API Interceptor]`

---

## 🎯 Prevenção Futura

### Sempre que modificar o frontend:

```bash
# 1. Fazer build local
cd frontend
npm run build

# 2. Deploy completo
cd ..
.\deploy-prod-auto.ps1
```

### Ou no servidor:

```bash
cd ~/Sistema\ Pet/
docker-compose -f docker-compose.prod.yml build frontend
docker-compose -f docker-compose.prod.yml up -d frontend nginx
```

---

## 📝 Checklist Final

- [ ] Frontend foi construído (`npm run build`)
- [ ] Pasta `frontend/dist/` tem arquivos (especialmente `index.html`)
- [ ] Nginx está rodando (`docker ps | grep nginx`)
- [ ] Configuração nginx tem `try_files $uri $uri/ /index.html;`
- [ ] Permissões da pasta dist estão corretas
- [ ] Cache do navegador foi limpo
- [ ] Testado em aba anônima

---

## 🆘 Se ainda não funcionar

Execute e me mostre o resultado:

```bash
ssh root@mlprohub.com.br << 'ENDSSH'
cd ~/Sistema\ Pet/
echo "=== FRONTEND DIST ==="
ls -lah frontend/dist/ | head -15

echo ""
echo "=== NGINX CONTAINER ==="
docker exec petshop-prod-nginx ls -lah /usr/share/nginx/html/ | head -15

echo ""
echo "=== NGINX CONFIG ==="
docker exec petshop-prod-nginx grep -A 10 "location /" /etc/nginx/nginx.conf

echo ""
echo "=== TEST INTERNO ==="
docker exec petshop-prod-nginx wget -O - http://localhost/notas-fiscais 2>&1 | head -20

echo ""
echo "=== LOGS NGINX ==="
docker logs petshop-prod-nginx --tail 30
ENDSSH
```
