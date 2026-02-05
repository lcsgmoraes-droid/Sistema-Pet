# 🧪 Testes do Módulo de Conciliação de Cartão

## ✅ Endpoints Implementados

### 1. POST /financeiro/conciliacao-cartao
Concilia uma transação de cartão com base no NSU.

**Request:**
```bash
curl -X POST "http://localhost:8000/financeiro/conciliacao-cartao" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "nsu": "123456789",
    "valor": 150.00,
    "data_recebimento": "2026-01-31",
    "adquirente": "Stone",
    "forma_pagamento_id": 5
  }'
```

**Response (200 OK):**
```json
{
  "message": "Conciliação realizada com sucesso",
  "conta_receber_id": 42,
  "nsu": "123456789",
  "conciliado": true,
  "data_conciliacao": "2026-01-31",
  "adquirente": "Stone",
  "valor": 150.00,
  "status": "recebido"
}
```

**Possíveis Erros:**
- `404` - Conta não encontrada para o NSU informado
- `409` - Conta já conciliada anteriormente
- `422` - Valor informado não confere com a parcela

---

### 2. GET /financeiro/conciliacao-cartao/pendentes
Lista contas a receber pendentes de conciliação.

**Request (sem filtros):**
```bash
curl -X GET "http://localhost:8000/financeiro/conciliacao-cartao/pendentes" \
  -H "Authorization: Bearer SEU_TOKEN_JWT"
```

**Request (com filtros):**
```bash
curl -X GET "http://localhost:8000/financeiro/conciliacao-cartao/pendentes?adquirente=Stone&data_inicio=2026-01-01&data_fim=2026-01-31" \
  -H "Authorization: Bearer SEU_TOKEN_JWT"
```

**Response (200 OK):**
```json
[
  {
    "id": 42,
    "nsu": "123456789",
    "adquirente": "Stone",
    "valor": 150.0,
    "data_prevista": "2026-01-31",
    "numero_parcela": 1,
    "total_parcelas": 3,
    "descricao": "Venda VEN-20260131-0001",
    "status": "pendente"
  },
  {
    "id": 43,
    "nsu": "987654321",
    "adquirente": "Cielo",
    "valor": 200.0,
    "data_prevista": "2026-02-28",
    "numero_parcela": 2,
    "total_parcelas": 3,
    "descricao": "Venda VEN-20260131-0002",
    "status": "pendente"
  }
]
```

---

### 3. POST /financeiro/conciliacao-cartao/upload
Upload de arquivo CSV para conciliação em lote.

**Formato do CSV:**
```csv
nsu,valor,data_recebimento,adquirente
123456789,150.00,2026-01-31,Stone
987654321,89.90,2026-02-01,Cielo
555111222,250.50,2026-01-30,Rede
```

**Request (via cURL):**
```bash
curl -X POST "http://localhost:8000/financeiro/conciliacao-cartao/upload" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -F "file=@conciliacao.csv"
```

**Response (200 OK):**
```json
{
  "message": "Processamento concluído: 2/3 conciliados",
  "processados": 3,
  "conciliados": 2,
  "erros": [
    {
      "linha": 3,
      "nsu": "987654321",
      "erro": "Conta já conciliada anteriormente em 2026-01-30"
    }
  ],
  "taxa_sucesso": 66.67
}
```

**Possíveis Erros:**
- `400` - Arquivo não é CSV ou codificação inválida
- `400` - Colunas do CSV incorretas
- Erros individuais por linha são retornados no array `erros`

**Características:**
- ✅ Processa linha por linha
- ✅ Erros em uma linha não interrompem o processamento
- ✅ Usa o mesmo service de conciliação individual
- ✅ Retorna resumo detalhado com taxa de sucesso
- ✅ Commit individual por linha (isolamento de erros)

---

## 🔧 Estrutura Implementada

### Models (financeiro_models.py)
```python
# Campos adicionados em ContaReceber:
nsu = Column(String(100), nullable=True, index=True)
adquirente = Column(String(50), nullable=True)
conciliado = Column(Boolean, default=False, nullable=False, index=True)
data_conciliacao = Column(Date, nullable=True)
```

### Migration
```bash
# Executada:
alembic upgrade b1eaca5a7d14
```

### Service (conciliacao_cartao_service.py)
- `conciliar_parcela_cartao()` - Valida e concilia uma transação
- `buscar_contas_nao_conciliadas()` - Lista contas pendentes

### Router (conciliacao_cartao_routes.py)
- POST `/financeiro/conciliacao-cartao` - Conciliação individual
- GET `/financeiro/conciliacao-cartao/pendentes` - Listar pendentes
- POST `/financeiro/conciliacao-cartao/upload` - Upload CSV em lote

---

## ✅ Validações Implementadas

1. **Multi-tenant**: Todas as operações respeitam o tenant do usuário autenticado
2. **Validação de NSU**: Busca conta pelo NSU + tenant
3. **Validação de valor**: Tolerância de 1 centavo para diferenças
4. **Validação de duplicidade**: Impede conciliação de conta já conciliada
5. **Auditoria**: Logs estruturados de todas as operações

---

## 🔒 Segurança

- ✅ Requer autenticação JWT
- ✅ Isolamento multi-tenant
- ✅ Validação de permissões via `get_current_user_and_tenant`
- ✅ Sanitização de inputs via Pydantic

---

## 📊 Fluxo Completo

```
1. Venda no PDV
   ↓
2. NSU capturado no pagamento
   ↓
3. Conta a receber criada com NSU
   ↓
4. Upload de arquivo da adquirente OU consulta manual
   ↓
5. POST /conciliacao-cartao
   ↓
6. Validações (NSU, valor, duplicidade)
   ↓
7. Marca conciliado = true
   ↓
8. Cria registro de Recebimento
   ↓
9. Atualiza status da conta
   ↓
10. Fluxo de caixa + DRE atualizados automaticamente
```
