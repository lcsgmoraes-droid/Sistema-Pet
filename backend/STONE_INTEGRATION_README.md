# 💳 Integração Stone Pagamentos

Documentação completa para integração com a API da Stone (Ton) para processar pagamentos via PIX e Cartão.

## 📋 Índice

- [Recursos Implementados](#recursos-implementados)
- [Pré-requisitos](#pré-requisitos)
- [Configuração Inicial](#configuração-inicial)
- [Como Usar](#como-usar)
- [Endpoints API](#endpoints-api)
- [Webhooks](#webhooks)
- [Exemplos de Código](#exemplos-de-código)
- [Tratamento de Erros](#tratamento-de-erros)
- [Segurança](#segurança)

---

## 🚀 Recursos Implementados

### ✅ Pagamentos PIX
- Geração de QR Code PIX
- Código PIX Copia e Cola
- Configuração de tempo de expiração
- Notificações via webhook quando pagamento é confirmado

### ✅ Pagamentos com Cartão
- Cartão de crédito (parcelado em até 12x)
- Cartão de débito
- Processamento imediato
- Cálculo automático de taxas

### ✅ Gestão de Transações
- Consulta de status
- Listagem com filtros
- Histórico completo
- Cancelamentos e estornos

### ✅ Webhooks
- Recebimento automático de notificações
- Atualização automática de status
- Log completo de eventos

---

## 📦 Pré-requisitos

### 1. Criar Conta Stone

1. Acesse o [Portal Stone](https://portal.stone.com.br/)
2. Cadastre-se como estabelecimento
3. Solicite acesso à API

### 2. Obter Credenciais

No dashboard da Stone, você precisará:

- **Client ID**: Identificação da sua aplicação
- **Client Secret**: Chave secreta da aplicação
- **Merchant ID**: ID do seu estabelecimento
- **Webhook Secret**: Chave para validar webhooks (opcional)

### 3. Instalar Dependências

As dependências já estão no `requirements.txt`:

```bash
httpx==0.27.0  # Cliente HTTP assíncrono
```

---

## ⚙️ Configuração Inicial

### 1. Configurar Credenciais via API

Faça uma requisição POST para configurar as credenciais Stone do seu tenant:

```bash
POST /api/stone/config
Content-Type: application/json
Authorization: Bearer {seu_token_jwt}

{
  "client_id": "seu_client_id_stone",
  "client_secret": "seu_client_secret_stone",
  "merchant_id": "seu_merchant_id",
  "webhook_secret": "seu_webhook_secret",
  "sandbox": true,  // true = ambiente de testes, false = produção
  "enable_pix": true,
  "enable_credit_card": true,
  "enable_debit_card": false,
  "max_installments": 12,
  "webhook_url": "https://seu-dominio.com/api/stone/webhook"
}
```

### 2. Criar Tabelas no Banco de Dados

Execute a migration para criar as tabelas:

```bash
# Crie uma migration
alembic revision --autogenerate -m "Add Stone tables"

# Aplique a migration
alembic upgrade head
```

### 3. Configurar Webhook na Stone

1. Acesse o dashboard Stone
2. Vá em **Configurações → Webhooks**
3. Adicione a URL: `https://seu-dominio.com/api/stone/webhook`
4. Selecione os eventos:
   - `payment.approved`
   - `payment.cancelled`
   - `payment.refunded`
   - `payment.failed`

---

## 🎯 Como Usar

### 1. Criar Pagamento PIX

```bash
POST /api/stone/payments/pix
Content-Type: application/json
Authorization: Bearer {seu_token_jwt}

{
  "amount": 100.50,
  "description": "Venda #123 - Ração Premium 15kg",
  "external_id": "venda-123-2024",
  "customer_name": "João Silva",
  "customer_document": "12345678900",
  "customer_email": "joao@email.com",
  "expiration_minutes": 30,
  "venda_id": 123,
  "conta_receber_id": 456
}
```

**Resposta:**

```json
{
  "success": true,
  "message": "Pagamento PIX criado com sucesso",
  "transaction": {
    "id": 1,
    "stone_payment_id": "pay_abc123",
    "external_id": "venda-123-2024",
    "payment_method": "pix",
    "amount": 100.50,
    "status": "pending"
  },
  "pix": {
    "qr_code": "00020126580014br.gov.bcb.pix...",
    "qr_code_url": "https://api.stone.com.br/qrcodes/abc123.png",
    "copy_paste": "00020126580014br.gov.bcb.pix...",
    "expiration": "2024-02-03T15:30:00Z"
  }
}
```

### 2. Criar Pagamento com Cartão

```bash
POST /api/stone/payments/card
Content-Type: application/json
Authorization: Bearer {seu_token_jwt}

{
  "amount": 250.00,
  "description": "Venda #124 - Banho e Tosa",
  "external_id": "venda-124-2024",
  "card_number": "4111111111111111",
  "card_holder_name": "MARIA SANTOS",
  "card_expiration_date": "12/25",
  "card_cvv": "123",
  "installments": 3,
  "customer_name": "Maria Santos",
  "customer_document": "98765432100",
  "customer_email": "maria@email.com",
  "venda_id": 124
}
```

**Resposta:**

```json
{
  "success": true,
  "message": "Pagamento processado com sucesso",
  "transaction": {
    "id": 2,
    "stone_payment_id": "pay_xyz789",
    "external_id": "venda-124-2024",
    "payment_method": "credit_card",
    "amount": 250.00,
    "installments": 3,
    "status": "approved",
    "card_brand": "visa",
    "card_last_digits": "1111",
    "fee_amount": 7.50,
    "net_amount": 242.50
  },
  "status": "approved"
}
```

### 3. Consultar Pagamento

```bash
GET /api/stone/payments/1
Authorization: Bearer {seu_token_jwt}
```

### 4. Listar Pagamentos

```bash
GET /api/stone/payments?status=approved&payment_method=pix&limit=50&offset=0
Authorization: Bearer {seu_token_jwt}
```

### 5. Cancelar Pagamento

```bash
POST /api/stone/payments/1/cancel
Content-Type: application/json
Authorization: Bearer {seu_token_jwt}

{
  "reason": "Cliente desistiu da compra"
}
```

### 6. Estornar Pagamento

```bash
POST /api/stone/payments/2/refund
Content-Type: application/json
Authorization: Bearer {seu_token_jwt}

{
  "amount": 83.33,  // null = estorno total
  "reason": "Produto com defeito"
}
```

---

## 📡 Endpoints API

### Configuração

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/stone/config` | Configurar credenciais Stone |
| GET | `/api/stone/config` | Obter configuração atual |

### Pagamentos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/stone/payments/pix` | Criar pagamento PIX |
| POST | `/api/stone/payments/card` | Criar pagamento com cartão |
| GET | `/api/stone/payments/{id}` | Consultar pagamento específico |
| GET | `/api/stone/payments` | Listar pagamentos com filtros |

### Gestão

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/stone/payments/{id}/cancel` | Cancelar pagamento pendente |
| POST | `/api/stone/payments/{id}/refund` | Estornar pagamento aprovado |

### Webhook

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/stone/webhook` | Receber notificações Stone (sem auth) |

---

## 🔔 Webhooks

A Stone envia webhooks para notificar mudanças de status:

### Eventos Suportados

- `payment.approved` - Pagamento aprovado
- `payment.cancelled` - Pagamento cancelado
- `payment.refunded` - Pagamento estornado
- `payment.failed` - Pagamento falhou

### Estrutura do Webhook

```json
{
  "event": "payment.approved",
  "payment": {
    "id": "pay_abc123",
    "amount": 10050,
    "status": "approved",
    "payment_method": "pix",
    "created_at": "2024-02-03T12:00:00Z",
    "approved_at": "2024-02-03T12:05:00Z"
  }
}
```

### Processamento Automático

O sistema processa webhooks automaticamente:

1. ✅ Valida assinatura (se configurado `webhook_secret`)
2. ✅ Atualiza status da transação
3. ✅ Registra log do evento
4. ✅ Atualiza datas relevantes
5. ✅ Incrementa contador de webhooks

---

## 💡 Exemplos de Código

### Python - Criar Pagamento PIX

```python
import httpx

async def criar_pix(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/stone/payments/pix",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": 50.00,
                "description": "Consulta veterinária",
                "external_id": f"consulta-{uuid.uuid4()}",
                "customer_name": "Carlos Oliveira",
                "customer_email": "carlos@email.com",
                "expiration_minutes": 15
            }
        )
        
        data = response.json()
        
        # Exibir QR Code para o cliente
        print(f"QR Code: {data['pix']['qr_code']}")
        print(f"Link da imagem: {data['pix']['qr_code_url']}")
        print(f"Código copia e cola: {data['pix']['copy_paste']}")
        
        return data['transaction']['id']
```

### JavaScript - Criar Pagamento Cartão

```javascript
async function criarPagamentoCartao(token) {
  const response = await fetch('http://localhost:8000/api/stone/payments/card', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      amount: 150.00,
      description: 'Compra de produtos',
      external_id: `compra-${Date.now()}`,
      card_number: '5555555555554444',
      card_holder_name: 'CLIENTE TESTE',
      card_expiration_date: '12/25',
      card_cvv: '123',
      installments: 2,
      customer_name: 'Cliente Teste',
      customer_email: 'cliente@email.com'
    })
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log('Pagamento aprovado!', data.transaction);
  } else {
    console.error('Erro no pagamento:', data);
  }
  
  return data;
}
```

### Python - Consultar Status

```python
async def verificar_status(transaction_id: int, token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/stone/payments/{transaction_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        data = response.json()
        transaction = data['transaction']
        
        print(f"Status: {transaction['status']}")
        print(f"Valor: R$ {transaction['amount']}")
        
        if transaction['status'] == 'approved':
            print(f"Pago em: {transaction['paid_at']}")
        
        return transaction['status']
```

---

## ⚠️ Tratamento de Erros

### Códigos HTTP

| Código | Significado |
|--------|-------------|
| 200 | Sucesso |
| 400 | Requisição inválida (dados incorretos) |
| 401 | Não autenticado |
| 404 | Recurso não encontrado |
| 500 | Erro interno do servidor |

### Erros Comuns

#### 1. Configuração não encontrada

```json
{
  "detail": "Configuração Stone não encontrada. Configure primeiro em /api/stone/config"
}
```

**Solução:** Configure as credenciais Stone via POST `/api/stone/config`

#### 2. External ID duplicado

```json
{
  "detail": "Pagamento com external_id 'venda-123' já existe"
}
```

**Solução:** Use um `external_id` único para cada pagamento

#### 3. Erro na Stone API

```json
{
  "detail": "Erro ao criar pagamento PIX: Unauthorized"
}
```

**Solução:** Verifique se as credenciais Stone estão corretas

---

## 🔒 Segurança

### 1. Dados de Cartão

⚠️ **IMPORTANTE:** Dados de cartão são extremamente sensíveis!

- ✅ Use HTTPS em produção
- ✅ Nunca armazene número completo do cartão
- ✅ Nunca armazene CVV
- ✅ Use tokenização quando possível
- ✅ Sistema armazena apenas últimos 4 dígitos e bandeira

### 2. Credenciais

- 🔐 Client Secret deve ser criptografado no banco
- 🔐 Webhook Secret deve ser secreto
- 🔐 Use variáveis de ambiente em produção
- 🔐 Nunca commite credenciais no Git

### 3. Validação de Webhooks

O sistema valida webhooks usando HMAC-SHA256:

```python
import hmac
import hashlib

def validar_webhook(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)
```

### 4. Isolamento Multi-Tenant

- ✅ Cada tenant tem suas próprias credenciais
- ✅ Transações isoladas por `tenant_id`
- ✅ Impossível acessar transações de outro tenant
- ✅ Middleware valida tenant automaticamente

---

## 🧪 Testes

### Ambiente Sandbox

A Stone oferece ambiente de testes (sandbox):

```python
# Configuração para testes
{
  "sandbox": true,  # Ativa modo de testes
  ...
}
```

### Cartões de Teste

Use estes cartões para testar:

| Cartão | Resultado |
|--------|-----------|
| 4111 1111 1111 1111 | Aprovado |
| 5555 5555 5555 4444 | Aprovado |
| 4000 0000 0000 0002 | Negado |
| 4000 0000 0000 0119 | Erro de processamento |

**CVV:** Qualquer (123)  
**Validade:** Qualquer data futura (12/25)

### PIX de Teste

No sandbox, pagamentos PIX são aprovados automaticamente após alguns segundos.

---

## 📊 Monitoramento

### Logs

Todos os eventos são registrados:

```python
# Ver logs de uma transação
GET /api/stone/payments/{id}/logs
```

### Métricas

Acompanhe:

- Taxa de aprovação
- Valor médio de transações
- Tempo médio de processamento
- Taxa de estorno
- Webhooks recebidos

---

## 🆘 Suporte

### Documentação Stone

- [Docs Oficiais](https://docs.stone.com.br/)
- [Portal do Desenvolvedor](https://developer.stone.com.br/)
- [Status da API](https://status.stone.com.br/)

### Issues Conhecidas

1. **PIX não expira automaticamente:** Sistema não cancela PIX expirados automaticamente. Implemente job para isso se necessário.

2. **Webhooks duplicados:** Stone pode enviar o mesmo webhook múltiplas vezes. Sistema conta ocorrências no campo `webhook_count`.

3. **Rate Limit:** API Stone tem limite de requisições. Implemente retry com backoff exponencial.

---

## 📝 TODO / Melhorias Futuras

- [ ] Implementar job para cancelar PIX expirados
- [ ] Adicionar retry automático com backoff
- [ ] Implementar cache de tokens OAuth2
- [ ] Criar dashboard de analytics
- [ ] Adicionar suporte a split de pagamento
- [ ] Implementar reconciliação bancária automática
- [ ] Adicionar suporte a boleto
- [ ] Criar relatório de taxas por forma de pagamento

---

## 📄 Licença

Este módulo faz parte do Sistema Pet Shop Pro.

---

**Desenvolvido com ❤️ para facilitar pagamentos digitais no seu Pet Shop!**
