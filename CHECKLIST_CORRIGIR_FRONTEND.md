# ⚡ CHECKLIST: Corrigir Frontend em Produção

## 🎯 Problema
Frontend está usando `http://127.0.0.1:8000` em produção. Deve usar `/api`.

## ✅ Solução Rápida

### PASSO 1: Build com Configuração Correta
```bash
cd frontend
npm run build
```

**Verificar no console de build:**
- ✅ Deve aparecer: "Mode: production" ou similar
- ✅ Variável VITE_API_URL deve ser: `/api`

### PASSO 2: Deploy para Produção
```bash
scp -r dist/* root@mlprohub.com.br:/opt/petshop/frontend/dist/
```

### PASSO 3: Verificar no Navegador
1. Acessar: https://mlprohub.com.br
2. Abrir DevTools (F12) → Console
3. **Verificar log de inicialização:**
   ```
   🌐 [API Config] Configuração do Axios carregada
     Mode: production
     VITE_API_URL (configurado): /api  ← DEVE SER /api
     API_URL (final): /api
   ```

### PASSO 4: Testar Requisições
1. DevTools → Network tab
2. Navegar para Dashboard
3. **Verificar requisições:**
   - ✅ URL: `https://mlprohub.com.br/api/racoes/...`
   - ✅ Status: 200 OK ou 403 (autenticação)
   - ❌ NÃO deve ser: `http://127.0.0.1:8000/...`

## 🔍 Se Ainda Não Funcionar

### Cache do Navegador:
```
Ctrl + Shift + R (hard refresh)
OU
Ctrl + Shift + N (janela anônima)
```

### Cache do Vite:
```bash
cd frontend
rm -rf node_modules/.vite
npm run build
# Repetir deploy (PASSO 2)
```

## ✅ Sucesso!
Quando ver:
- Console mostra `API_URL (final): /api` ✅
- Network mostra requisições para `/api/...` ✅
- Status 200 ou dados carregando ✅

## ❌ Se Continuar 403
Problema diferente (autenticação):
1. Fazer logout
2. Fazer login novamente
3. Token deve ser atualizado

---

**ORDEM DE EXECUÇÃO:**
1️⃣ Build  
2️⃣ Deploy  
3️⃣ Verificar Browser  
4️⃣ Testar Login
