# 🔍 GUIA DE DIAGNÓSTICO - Erro 403 nos Endpoints de Rações

**Status Atual:** Backend funcionando ✅ | Frontend com erro 403 (autenticação)

---

## 📋 MUDANÇAS APLICADAS NO FRONTEND

### 1. Arquivo `frontend/src/api.js` (✅ MODIFICADO)

**Adicionado logging detalhado:**
- ✅ Log de cada requisição (URL, token, headers)
- ✅ Log de cada resposta (status, dados)
- ✅ Log detalhado de erros 403 e 401

**O que agora aparece no console:**
```javascript
🔐 [API Interceptor] {
  url: '/racoes/analises/opcoes-filtros',
  baseURL: 'http://127.0.0.1:8000',  // ou '/api' em produção
  fullURL: 'http://127.0.0.1:8000/racoes/analises/opcoes-filtros',
  hasToken: true,
  tokenPreview: 'eyJhbGciOiJIUzI1NiI...',
  headers: {...}
}
✅ Token adicionado ao header Authorization
```

### 2. Arquivo `frontend/src/components/DashboardAnaliseRacoes.jsx` (✅ MODIFICADO)

**Adicionado logging na função `carregarDados()`:**
- ✅ Log antes da requisição
- ✅ Log de sucesso com dados recebidos
- ✅ Log detalhado de erros com status e mensagem

### 3. Arquivo `frontend/src/components/AlertasRacao.jsx` (✅ MODIFICADO)

**Adicionado logging na função `carregarAlertasRacao()`:**
- ✅ Log antes da requisição
- ✅ Log de sucesso com contagem de itens
- ✅ Log detalhado de erros com status e mensagem

### 4. Arquivo `frontend/diagnostico-auth.js` (✅ CRIADO)

**Script de diagnóstico completo para executar no console do navegador:**
- ✅ Verifica se token existe no localStorage
- ✅ Decodifica o token JWT e mostra payload
- ✅ Verifica se token está expirado
- ✅ Testa requisição aos endpoints
- ✅ Mostra configuração do Axios (baseURL, modo)
- ✅ Lista cookies e contexto da página

---

## 🚀 COMO DIAGNOSTICAR AGORA

### PASSO 1: Recarregar o Frontend

```bash
# No terminal do frontend
npm run dev
```

Ou se estiver em produção, faça refresh da página com **Ctrl+Shift+R** (limpar cache).

---

### PASSO 2: Abrir DevTools

1. Pressione **F12** ou **Ctrl+Shift+I**
2. Vá para a aba **Console**
3. Limpe o console (ícone 🚫 ou Ctrl+L)

---

### PASSO 3: Executar o Script de Diagnóstico

1. Abra o arquivo `frontend/diagnostico-auth.js`
2. **Copie TODO o conteúdo**
3. Cole no console do navegador
4. Pressione **Enter**

**Você verá um relatório completo assim:**

```
========================================
🔍 DIAGNÓSTICO DE AUTENTICAÇÃO
========================================

1️⃣ TOKEN NO LOCALSTORAGE:
   Existe: true
   Preview: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOi...
   Tamanho: 342 caracteres
   Payload decodificado: {
     sub: "teste@teste.com",
     tenant_id: "abc-123-xyz",
     exp: 1739664000
   }
   Expira em: 15/02/2026 20:00:00
   Status: ✅ VÁLIDO
   Expira em: 45 minutos

2️⃣ TENANT:
   Tenants: {...}

3️⃣ CONFIGURAÇÃO DO AXIOS:
   VITE_API_URL: http://127.0.0.1:8000
   Modo: development
   Production: false
   Development: true

4️⃣ TESTE DE REQUISIÇÃO:
   Tentando chamar /racoes/analises/opcoes-filtros...
   URL completa: http://127.0.0.1:8000/racoes/analises/opcoes-filtros
   
   ✅ Resposta recebida:
   Status: 200 OK
   Dados: {...}

========================================
✅ DIAGNÓSTICO CONCLUÍDO
========================================
```

---

### PASSO 4: Acessar a Página com os Endpoints

1. Navegue até a página de **Alertas de Ração** ou **Dashboard de Análise**
2. Veja o console aparecer os logs automáticos:

```javascript
🔐 [DashboardAnaliseRacoes] Iniciando carregamento de dados {
  hasToken: true,
  tokenPreview: 'eyJhbGciOiJIUzI1NiI...'
}

🔐 [API Interceptor] {
  url: '/racoes/analises/opcoes-filtros',
  baseURL: 'http://127.0.0.1:8000',
  fullURL: 'http://127.0.0.1:8000/racoes/analises/opcoes-filtros',
  hasToken: true,
  tokenPreview: 'eyJhbGciOiJIUzI1NiI...'
}

✅ Token adicionado ao header Authorization

✅ [API Response] {
  status: 200,
  url: '/racoes/analises/opcoes-filtros',
  dataPreview: '{"marcas":[...],"categorias":[...]}'
}

✅ [DashboardAnaliseRacoes] Opções carregadas: {...}
```

---

### PASSO 5: Verificar na Aba Network

1. Vá para a aba **Network** no DevTools
2. Filtre por **Fetch/XHR**
3. Clique na requisição `opcoes-filtros` ou `alertas`
4. Veja a seção **Headers**

**O que deve aparecer:**

```
Request Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  Content-Type: application/json
  
Request URL:
  http://127.0.0.1:8000/racoes/analises/opcoes-filtros

Status Code:
  200 OK  (✅ SUCESSO)
  
  OU
  
  403 Forbidden  (❌ Token inválido/expirado)
```

---

## 🔍 CENÁRIOS POSSÍVEIS

### ✅ CENÁRIO 1: Token Válido, Status 200

**Console mostra:**
```
✅ Token adicionado ao header Authorization
✅ [API Response] { status: 200, ... }
```

**Network mostra:**
```
Status: 200 OK
Authorization: Bearer eyJ...
```

**CONCLUSÃO:** Tudo funcionando corretamente! ✅

---

### ⚠️ CENÁRIO 2: Sem Token

**Console mostra:**
```
⚠️ Nenhum token encontrado no localStorage
❌ [API Response Error] { status: 403, ... }
```

**Network mostra:**
```
Status: 403 Forbidden
(sem header Authorization)
```

**SOLUÇÃO:**
1. Faça logout
2. Faça login novamente
3. Teste novamente

---

### ⚠️ CENÁRIO 3: Token Expirado

**Console mostra:**
```
✅ Token adicionado ao header Authorization
❌ [API Response Error] { 
  status: 403,
  errorData: { detail: "Token expired" }
}
```

**Diagnóstico mostra:**
```
1️⃣ TOKEN NO LOCALSTORAGE:
   Status: ❌ EXPIRADO
   Expirou há: 120 minutos
```

**SOLUÇÃO:**
1. Faça logout
2. Faça login novamente
3. Token será renovado

---

### ⚠️ CENÁRIO 4: Token Inválido/Corrompido

**Console mostra:**
```
✅ Token adicionado ao header Authorization
❌ [API Response Error] { 
  status: 403,
  errorData: { detail: "Could not validate credentials" }
}
```

**SOLUÇÃO:**
1. Limpe o localStorage manualmente:
   ```javascript
   localStorage.clear()
   ```
2. Faça login novamente

---

### ⚠️ CENÁRIO 5: BaseURL Errada (Em Produção)

**Console mostra:**
```
🔐 [API Interceptor] {
  fullURL: 'https://mlprohub.com.br/api/racoes/analises/opcoes-filtros',
  ...
}
❌ [API Response Error] { status: 404, ... }
```

**Network mostra:**
```
Status: 404 Not Found
Request URL: https://mlprohub.com.br/api/racoes/analises/opcoes-filtros
```

**VERIFICAÇÃO:**
- Nginx está configurado para reescrever `/api/xxx` → `/xxx`
- Backend responde em `/racoes/analises/opcoes-filtros` (sem `/api`)
- Frontend em produção usa `VITE_API_URL=/api`

**CONCLUSÃO:** Configuração correta! Se der 404, verifique se o nginx está rodando.

---

## 🎯 CHECKLIST COMPLETO

Use este checklist para verificar tudo:

- [ ] **1. Token existe no localStorage**
  ```javascript
  console.log(localStorage.getItem('access_token'))
  ```

- [ ] **2. Token não está expirado**
  - Execute o script `diagnostico-auth.js`
  - Verifique a linha "Status: ✅ VÁLIDO"

- [ ] **3. Headers na requisição**
  - Abra Network → Clique na requisição → Headers
  - Deve ter: `Authorization: Bearer eyJ...`

- [ ] **4. BaseURL correta**
  - DEV: `http://127.0.0.1:8000`
  - PROD: `/api`

- [ ] **5. Nginx rodando (apenas produção)**
  ```bash
  ssh root@mlprohub.com.br "docker ps | grep nginx"
  ```

- [ ] **6. Backend respondendo**
  ```bash
  curl -X GET http://localhost:8000/health
  # Deve retornar: {"status":"healthy"}
  ```

- [ ] **7. Interceptor do Axios configurado**
  - Verifique se `frontend/src/api.js` tem o código atualizado
  - Deve aparecer logs no console começando com 🔐

---

## 📊 CÓDIGO ATUALIZADO

### `frontend/src/api.js`

```javascript
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ✅ INTERCEPTOR COM LOGGING DETALHADO
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');

    // 🔍 DEBUG: Log token e configuração
    console.log('🔐 [API Interceptor]', {
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
      hasToken: !!token,
      tokenPreview: token ? `${token.substring(0, 20)}...` : 'NO TOKEN',
      headers: config.headers
    });

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('✅ Token adicionado ao header Authorization');
    } else {
      console.warn('⚠️ Nenhum token encontrado no localStorage');
    }

    return config;
  },
  (error) => {
    console.error('❌ [API Interceptor] Erro na requisição:', error);
    return Promise.reject(error);
  }
);

// ✅ INTERCEPTOR DE RESPOSTA COM LOGGING
api.interceptors.response.use(
  (response) => {
    console.log('✅ [API Response]', {
      status: response.status,
      url: response.config.url,
      dataPreview: JSON.stringify(response.data).substring(0, 100)
    });
    return response;
  },
  (error) => {
    const status = error.response?.status;

    // 🔍 DEBUG: Log detalhado do erro
    console.error('❌ [API Response Error]', {
      status: status,
      url: error.config?.url,
      fullURL: `${error.config?.baseURL}${error.config?.url}`,
      errorData: error.response?.data,
      headers: error.response?.headers,
      requestHeaders: error.config?.headers
    });

    if (status === 401) {
      console.warn('⚠️ Status 401: Sessão inválida');
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }

    if (status === 403) {
      console.warn('⚠️ Status 403: Acesso negado');
      console.log('🔍 Detalhes do erro 403:', {
        message: error.response?.data?.detail,
        token: localStorage.getItem('access_token')?.substring(0, 20) + '...'
      });
    }

    return Promise.reject(error);
  }
);

export default api;
```

---

## 🎬 PRÓXIMOS PASSOS

1. **Recarregue o frontend** (npm run dev ou Ctrl+Shift+R)
2. **Execute o script de diagnóstico** no console
3. **Acesse a página de rações**
4. **Copie os logs do console** e envie para análise
5. **Tire um print da aba Network** mostrando os headers

**Com essas informações, será possível identificar exatamente onde está o problema!**

---

## 💡 DICA RÁPIDA

Se quiser testar RAPIDAMENTE sem fazer login, execute no console:

```javascript
// Buscar um token válido existente
const token = localStorage.getItem('access_token');
console.log('Token atual:', token ? token.substring(0, 50) + '...' : 'Nenhum');

// Testar requisição diretamente
fetch('http://127.0.0.1:8000/racoes/analises/opcoes-filtros', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => console.log('Dados:', data))
.catch(err => console.error('Erro:', err));
```

---

**✅ Frontend está pronto para diagnóstico completo!**
