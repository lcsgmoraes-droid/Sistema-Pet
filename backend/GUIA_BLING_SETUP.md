# 🚀 Guia: Configurar Integração com Bling

## 📋 Pré-requisitos

1. Conta ativa no Bling
2. Python 3.11+ instalado
3. Backend do sistema rodando

---

## 📝 Passo 1: Criar Aplicativo no Bling

### 1.1. Acessar Portal de Desenvolvedores

Acesse: https://developer.bling.com.br/

### 1.2. Criar Novo Aplicativo

1. Faça login com sua conta Bling
2. Vá em **"Meus Aplicativos"**
3. Clique em **"Criar Aplicativo"**
4. Preencha:
   - **Nome do aplicativo:** Sistema Pet Shop Pro
   - **Descrição:** Integração para emissão de NF-e
   - **Redirect URI:** `http://localhost:8000/auth/bling/callback` (desenvolvimento)
   - **Escopos necessários:** 
     - `NFe.Create` - Criar NF-e
     - `NFe.Read` - Consultar NF-e
     - `NFe.Update` - Atualizar NF-e (cancelar)

5. Clique em **"Salvar"**

### 1.3. Anotar Credenciais

Após criar, você receberá:
- **Client ID** (ex: `abc123def456`)
- **Client Secret** (ex: `xyz789uvw321`)

⚠️ **IMPORTANTE:** Guarde o Client Secret em local seguro! Ele só é mostrado uma vez.

---

## 🔐 Passo 2: Obter Access Token (OAuth2)

### Método 1: Via Navegador (Recomendado)

1. Monte a URL de autorização:
```
https://www.bling.com.br/Api/v3/oauth/authorize?
  response_type=code
  &client_id=SEU_CLIENT_ID
  &redirect_uri=http://localhost:8000/auth/bling/callback
```

2. Acesse a URL no navegador
3. Autorize o aplicativo
4. Você será redirecionado para: `http://localhost:8000/auth/bling/callback?code=CODIGO_AQUI`
5. Copie o `code` da URL

6. Troque o código por access token:
```bash
curl -X POST https://www.bling.com.br/Api/v3/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "code": "SEU_CODIGO",
    "client_id": "SEU_CLIENT_ID",
    "client_secret": "SEU_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8000/auth/bling/callback"
  }'
```

7. Resposta (copie access_token e refresh_token):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "Bearer",
  "expires_in": 21600,
  "refresh_token": "def50200e74f..."
}
```

### Método 2: Via Python Script

Execute o script auxiliar:

```bash
cd backend
python scripts/setup_bling_oauth.py
```

Siga as instruções na tela.

---

## ⚙️ Passo 3: Configurar Backend

### 3.1. Copiar .env.example para .env

```bash
cd backend
cp .env.example .env
```

### 3.2. Editar .env

Abra `backend/.env` e preencha:

```env
# Credenciais do aplicativo Bling
BLING_CLIENT_ID=abc123def456
BLING_CLIENT_SECRET=xyz789uvw321

# Tokens OAuth2
BLING_ACCESS_TOKEN=eyJhbGciOiJIUzI1NiIsIn...
BLING_REFRESH_TOKEN=def50200e74f...
```

⚠️ **Notas importantes:**
- Access token expira em ~6 horas
- Use refresh token para renovar automaticamente
- NUNCA commite o arquivo .env no Git!

---

## 🗄️ Passo 4: Executar Migração do Banco

Adicionar campos de NF-e na tabela vendas:

```bash
cd backend
python migrate_add_nfe.py
```

Saída esperada:
```
🔄 Iniciando migração: Adicionar campos NF-e...
  ✅ Campo 'nfe_numero' adicionado
  ✅ Campo 'nfe_serie' adicionado
  ✅ Campo 'nfe_chave' adicionado
  ...
✨ Migração concluída com sucesso!
```

---

## 🧪 Passo 5: Testar Conexão

### 5.1. Iniciar Backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 5.2. Testar no Navegador

Acesse: http://localhost:8000/docs

### 5.3. Testar Endpoint de Conexão

1. Expanda: **GET /nfe/config/testar-conexao**
2. Clique em **"Try it out"**
3. Clique em **"Execute"**

Resposta esperada:
```json
{
  "success": true,
  "message": "Conexão com Bling OK"
}
```

---

## 📄 Passo 6: Emitir Primeira NF-e

### 6.1. Via Swagger UI (http://localhost:8000/docs)

1. Faça login no sistema
2. Finalize uma venda no PDV
3. Expanda: **POST /nfe/emitir**
4. Clique em **"Try it out"**
5. Preencha:
```json
{
  "venda_id": 1
}
```
6. Clique em **"Execute"**

### 6.2. Validações Automáticas

O sistema valida:
- ✅ Cliente possui CPF/CNPJ
- ✅ Cliente possui endereço completo
- ✅ Venda possui itens
- ✅ Produtos possuem dados fiscais (NCM, CFOP)

Se houver erro, ajuste os dados e tente novamente.

### 6.3. Resposta de Sucesso

```json
{
  "success": true,
  "message": "NF-e #1 emitida com sucesso",
  "nfe_id": 123456789,
  "numero": 1,
  "serie": 1,
  "chave_acesso": "35260101234567890001550010000000011000000019",
  "situacao": "autorizada",
  "danfe_url": "https://bling.com.br/..."
}
```

---

## 🔄 Renovar Access Token Automaticamente

### Script para Renovação

Crie: `backend/scripts/refresh_bling_token.py`

```python
import requests
import os
from dotenv import load_dotenv, set_key

load_dotenv()

def renovar_token():
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": os.getenv("BLING_REFRESH_TOKEN"),
        "client_id": os.getenv("BLING_CLIENT_ID"),
        "client_secret": os.getenv("BLING_CLIENT_SECRET")
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    # Atualizar .env
    set_key(".env", "BLING_ACCESS_TOKEN", data["access_token"])
    set_key(".env", "BLING_REFRESH_TOKEN", data["refresh_token"])
    
    print("✅ Token renovado com sucesso!")
    print(f"Expira em: {data['expires_in']} segundos")

if __name__ == "__main__":
    renovar_token()
```

Execute periodicamente (cron job ou task scheduler).

---

## 📚 Endpoints Disponíveis

### Emitir NF-e
```
POST /nfe/emitir
Body: { "venda_id": 1 }
```

### Consultar NF-e
```
GET /nfe/{nfe_id}
```

### Baixar XML
```
GET /nfe/{nfe_id}/xml
```

### Baixar DANFE
```
GET /nfe/{nfe_id}/danfe
```

### Cancelar NF-e
```
POST /nfe/{nfe_id}/cancelar
Body: { "justificativa": "Motivo aqui (mín 15 caracteres)" }
```

### Listar NF-es
```
GET /nfe?data_inicial=2026-01-01&data_final=2026-01-31
```

---

## ❓ Troubleshooting

### Erro: "Token de acesso do Bling não configurado"
- Verifique se o arquivo `.env` existe
- Confirme que `BLING_ACCESS_TOKEN` está preenchido

### Erro: "401 Unauthorized"
- Token expirou (6 horas)
- Renove usando `refresh_bling_token.py`

### Erro: "Cliente não possui CPF/CNPJ"
- Cadastre CPF/CNPJ do cliente antes de emitir NF-e

### Erro: "Produto sem NCM"
- Adicione NCM nos produtos (campo opcional no cadastro)
- Para pet shop: consulte tabela NCM de produtos veterinários

### NF-e rejeitada pela SEFAZ
- Verifique código de rejeição no response
- Consulte: http://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=9YqQr2Fkrz4=

---

## 🎯 Próximos Passos

1. ✅ Testar emissão em ambiente de homologação
2. ✅ Ajustar cadastro de produtos (adicionar NCM, CFOP)
3. ✅ Ajustar cadastro de clientes (CPF/CNPJ obrigatório)
4. ✅ Criar rotina de renovação automática de token
5. ✅ Implementar interface no frontend (botão "Emitir NF-e")

---

## 📞 Suporte

- **Documentação Bling:** https://developer.bling.com.br/
- **API Reference:** https://developer.bling.com.br/referenceapi
- **Suporte Bling:** https://ajuda.bling.com.br/

---

**Última atualização:** 06/01/2026
