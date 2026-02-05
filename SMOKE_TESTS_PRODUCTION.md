# 🧪 SMOKE TESTS — PRODUCTION

**Sistema:** Pet Shop Management System  
**Versão:** 1.0.0  
**Última Atualização:** 2026-02-05  
**Responsável:** DevOps / QA  
**Criticidade:** P0 (Crítico — Bloqueador de Deploy)

---

## 📋 ÍNDICE

1. [O que são Smoke Tests?](#-o-que-são-smoke-tests)
2. [Quando Executar](#-quando-executar)
3. [Testes de Startup](#-testes-de-startup)
4. [Testes de Endpoints Básicos](#-testes-de-endpoints-básicos)
5. [Testes de Fluxos Críticos](#-testes-de-fluxos-críticos)
6. [Testes de Banco de Dados](#-testes-de-banco-de-dados)
7. [Testes de Observabilidade](#-testes-de-observabilidade)
8. [Checklist de Execução](#-checklist-de-execução)
9. [Automação](#-automação)
10. [Troubleshooting](#-troubleshooting)

---

## 🔥 O QUE SÃO SMOKE TESTS?

**Definição:**
> Smoke Tests são testes superficiais e rápidos que validam se o sistema está "vivo" e funcionando após um deploy. O objetivo é detectar problemas críticos **antes** de liberar para usuários.

**Analogia:**
> Como acender um cigarro para verificar se há "fumaça" — se houver fumaça, algo está queimando (funcionando). Se não houver, está quebrado.

**Características:**
- ⚡ **Rápidos:** < 5 minutos
- 🎯 **Superficiais:** Não testam todas as funcionalidades
- 🚨 **Críticos:** Se falhar, bloqueia deploy
- ✅ **Binários:** Passa ou falha (sem ambiguidade)

**O que NÃO são:**
- ❌ Testes de integração completos
- ❌ Testes de carga
- ❌ Testes de segurança
- ❌ Testes de regressão

---

## ⏰ QUANDO EXECUTAR

| Momento | Obrigatório? | Responsável |
|---------|--------------|-------------|
| **Após deploy em produção** | ✅ SIM | DevOps |
| **Após rollback** | ✅ SIM | DevOps |
| **Após restart da aplicação** | ⚠️ RECOMENDADO | DevOps/SRE |
| **Após manutenção do banco** | ✅ SIM | DBA + DevOps |
| **Pós-incidente (validação)** | ✅ SIM | DevOps |
| **Durante CI/CD (staging)** | ⚠️ RECOMENDADO | CI/CD Pipeline |

---

## 🚀 TESTES DE STARTUP

### Objetivo
Validar que a aplicação inicia sem erros e todas as dependências estão OK.

---

### ✅ Teste 1.1: Aplicação Inicia

**Comando:**
```bash
# Verificar se container/processo está rodando
docker ps | grep fastapi_app

# OU (sem Docker)
ps aux | grep uvicorn
```

**Saída Esperada:**
```
CONTAINER ID   IMAGE              STATUS         PORTS
abc123def456   petshop:latest     Up 30 seconds  0.0.0.0:8000->8000/tcp
```

**Critério de Sucesso:**
- ✅ Container/processo está rodando
- ✅ Status: "Up" (não "Restarting" ou "Exited")
- ✅ Porta 8000 exposta

**Critério de Falha:**
- ❌ Container não existe
- ❌ Status: "Restarting" (loop de crash)
- ❌ Status: "Exited" (crashou)

---

### ✅ Teste 1.2: Logs de Startup

**Comando:**
```bash
# Ver logs dos últimos 2 minutos
docker logs --since 2m fastapi_app

# OU (sem Docker)
tail -100 /var/log/petshop/app.log
```

**Saída Esperada:**
```json
{"timestamp": "2026-02-05T10:00:00Z", "level": "INFO", "message": "🚀 Starting Pet Shop API"}
{"timestamp": "2026-02-05T10:00:01Z", "level": "INFO", "message": "✅ Environment validated: PROD"}
{"timestamp": "2026-02-05T10:00:02Z", "level": "INFO", "message": "✅ Database migrations up to date"}
{"timestamp": "2026-02-05T10:00:03Z", "level": "INFO", "message": "✅ Database connection established"}
{"timestamp": "2026-02-05T10:00:04Z", "level": "INFO", "message": "🌐 Uvicorn running on http://0.0.0.0:8000"}
{"timestamp": "2026-02-05T10:00:05Z", "level": "INFO", "message": "✅ Application startup complete"}
```

**Critério de Sucesso:**
- ✅ Mensagem "Starting Pet Shop API"
- ✅ Mensagem "Environment validated: PROD"
- ✅ Mensagem "Database migrations up to date"
- ✅ Mensagem "Database connection established"
- ✅ Mensagem "Application startup complete"
- ✅ Sem mensagens de ERROR ou CRITICAL

**Critério de Falha:**
- ❌ Qualquer mensagem de ERROR
- ❌ Qualquer mensagem de CRITICAL
- ❌ Stack trace de exceção
- ❌ Mensagem "Failed to connect to database"
- ❌ Mensagem "Database migrations pending"

---

### ✅ Teste 1.3: Porta Acessível

**Comando:**
```bash
# Testar conectividade TCP
nc -zv localhost 8000

# OU
telnet localhost 8000
```

**Saída Esperada:**
```
Connection to localhost 8000 port [tcp/*] succeeded!
```

**Critério de Sucesso:**
- ✅ Conexão bem-sucedida
- ✅ Porta 8000 respondendo

**Critério de Falha:**
- ❌ Connection refused
- ❌ Connection timeout
- ❌ No route to host

---

## 🩺 TESTES DE ENDPOINTS BÁSICOS

### Objetivo
Validar que endpoints de infraestrutura estão respondendo corretamente.

---

### ✅ Teste 2.1: Health Check (Liveness)

**Comando:**
```bash
curl -X GET http://localhost:8000/health \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-05T10:01:00Z"
}
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ Campo `status`: "healthy"
- ✅ Resposta em < 500ms

**Critério de Falha:**
- ❌ Status HTTP: 503, 500, 404
- ❌ Timeout (> 5 segundos)
- ❌ Connection refused

---

### ✅ Teste 2.2: Readiness Check

**Comando:**
```bash
curl -X GET http://localhost:8000/ready \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "migrations": "ok"
  },
  "timestamp": "2026-02-05T10:01:01Z"
}
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ Campo `status`: "ready"
- ✅ `checks.database`: "ok"
- ✅ `checks.migrations`: "ok"
- ✅ Resposta em < 2 segundos

**Critério de Falha:**
- ❌ Status HTTP: 503 (not ready)
- ❌ `checks.database`: "error" ou "down"
- ❌ `checks.migrations`: "pending" ou "error"
- ❌ Timeout (> 5 segundos)

---

### ✅ Teste 2.3: Documentação (OpenAPI)

**Comando:**
```bash
curl -X GET http://localhost:8000/docs \
  -w "\nStatus: %{http_code}\n" \
  -s -o /dev/null
```

**Saída Esperada:**
```
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ HTML retornado (Swagger UI)

**Critério de Falha:**
- ❌ Status HTTP: 404, 500
- ❌ Resposta vazia

---

### ✅ Teste 2.4: Root Endpoint

**Comando:**
```bash
curl -X GET http://localhost:8000/ \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "message": "Pet Shop API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ JSON válido retornado
- ✅ Campo `version` presente

**Critério de Falha:**
- ❌ Status HTTP: 404, 500
- ❌ JSON inválido

---

## 🔐 TESTES DE AUTENTICAÇÃO

### Objetivo
Validar que autenticação básica está funcionando.

---

### ✅ Teste 3.1: Login (Obter Token)

**Comando:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@petshop.local",
    "password": "admin123"
  }' \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ Campo `access_token` presente e não vazio
- ✅ Campo `token_type`: "bearer"

**Critério de Falha:**
- ❌ Status HTTP: 401 (credenciais inválidas)
- ❌ Status HTTP: 500 (erro interno)
- ❌ Campo `access_token` vazio ou ausente

---

### ✅ Teste 3.2: Endpoint Protegido (Com Token)

**Comando:**
```bash
# 1. Obter token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@petshop.local","password":"admin123"}' \
  -s | jq -r '.access_token')

# 2. Usar token em endpoint protegido
curl -X GET http://localhost:8000/api/usuarios/me \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "id": 1,
  "email": "admin@petshop.local",
  "nome": "Administrator",
  "role": "admin"
}
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ Dados do usuário retornados
- ✅ Token foi validado corretamente

**Critério de Falha:**
- ❌ Status HTTP: 401 (token inválido)
- ❌ Status HTTP: 403 (sem permissão)
- ❌ Status HTTP: 500

---

### ✅ Teste 3.3: Endpoint Protegido (Sem Token)

**Comando:**
```bash
curl -X GET http://localhost:8000/api/usuarios/me \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "detail": "Not authenticated"
}
Status: 401
```

**Critério de Sucesso:**
- ✅ Status HTTP: 401
- ✅ Mensagem de erro clara

**Critério de Falha:**
- ❌ Status HTTP: 200 (não deveria permitir!)
- ❌ Status HTTP: 500

---

## 🛒 TESTES DE FLUXOS CRÍTICOS

### Objetivo
Validar fluxos essenciais do negócio funcionam end-to-end.

---

### ✅ Teste 4.1: Criar Cliente

**Comando:**
```bash
# 1. Obter token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@petshop.local","password":"admin123"}' \
  -s | jq -r '.access_token')

# 2. Criar cliente
curl -X POST http://localhost:8000/api/clientes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Smoke Test Cliente",
    "email": "smoketest@example.com",
    "telefone": "(11) 98765-4321",
    "cpf": "123.456.789-00"
  }' \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "id": 123,
  "nome": "Smoke Test Cliente",
  "email": "smoketest@example.com",
  "telefone": "(11) 98765-4321",
  "cpf": "123.456.789-00",
  "created_at": "2026-02-05T10:05:00Z"
}
Status: 201
```

**Critério de Sucesso:**
- ✅ Status HTTP: 201 (Created)
- ✅ Campo `id` retornado (auto-incremento)
- ✅ Dados do cliente retornados

**Critério de Falha:**
- ❌ Status HTTP: 400 (validação)
- ❌ Status HTTP: 500 (erro interno)
- ❌ Campo `id` ausente

---

### ✅ Teste 4.2: Listar Clientes

**Comando:**
```bash
curl -X GET http://localhost:8000/api/clientes?limit=5 \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "items": [
    {
      "id": 123,
      "nome": "Smoke Test Cliente",
      "email": "smoketest@example.com"
    },
    {
      "id": 122,
      "nome": "Cliente Anterior",
      "email": "anterior@example.com"
    }
  ],
  "total": 123,
  "page": 1,
  "limit": 5
}
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ Array `items` presente
- ✅ Campo `total` > 0
- ✅ Cliente criado no teste anterior aparece na lista

**Critério de Falha:**
- ❌ Status HTTP: 500
- ❌ Array `items` vazio (se houver clientes)
- ❌ Cliente criado não aparece

---

### ✅ Teste 4.3: Buscar Cliente por ID

**Comando:**
```bash
# Usar ID do cliente criado no teste 4.1
CLIENTE_ID=123

curl -X GET http://localhost:8000/api/clientes/$CLIENTE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "id": 123,
  "nome": "Smoke Test Cliente",
  "email": "smoketest@example.com",
  "telefone": "(11) 98765-4321",
  "cpf": "123.456.789-00",
  "created_at": "2026-02-05T10:05:00Z",
  "updated_at": "2026-02-05T10:05:00Z"
}
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ Dados completos do cliente

**Critério de Falha:**
- ❌ Status HTTP: 404 (não encontrado)
- ❌ Status HTTP: 500

---

### ✅ Teste 4.4: Criar Produto

**Comando:**
```bash
curl -X POST http://localhost:8000/api/produtos \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Ração Smoke Test",
    "descricao": "Produto para smoke test",
    "preco": 49.90,
    "estoque": 100,
    "categoria": "Ração"
  }' \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "id": 456,
  "nome": "Ração Smoke Test",
  "preco": 49.90,
  "estoque": 100,
  "categoria": "Ração",
  "created_at": "2026-02-05T10:06:00Z"
}
Status: 201
```

**Critério de Sucesso:**
- ✅ Status HTTP: 201
- ✅ Campo `id` retornado
- ✅ Preço formatado corretamente

**Critério de Falha:**
- ❌ Status HTTP: 400, 500
- ❌ Campo `id` ausente

---

### ✅ Teste 4.5: Listar Produtos

**Comando:**
```bash
curl -X GET http://localhost:8000/api/produtos?limit=5 \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "items": [
    {
      "id": 456,
      "nome": "Ração Smoke Test",
      "preco": 49.90,
      "estoque": 100
    }
  ],
  "total": 456,
  "page": 1,
  "limit": 5
}
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ Produto criado aparece na lista

**Critério de Falha:**
- ❌ Status HTTP: 500
- ❌ Produto criado não aparece

---

### ✅ Teste 4.6: Criar Venda (Fluxo Financeiro)

**Comando:**
```bash
curl -X POST http://localhost:8000/api/vendas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 123,
    "itens": [
      {
        "produto_id": 456,
        "quantidade": 2,
        "preco_unitario": 49.90
      }
    ],
    "forma_pagamento": "cartao_credito",
    "observacoes": "Smoke test venda"
  }' \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "id": 789,
  "cliente_id": 123,
  "valor_total": 99.80,
  "forma_pagamento": "cartao_credito",
  "status": "concluida",
  "itens": [
    {
      "produto_id": 456,
      "quantidade": 2,
      "preco_unitario": 49.90,
      "subtotal": 99.80
    }
  ],
  "created_at": "2026-02-05T10:07:00Z"
}
Status: 201
```

**Critério de Sucesso:**
- ✅ Status HTTP: 201
- ✅ Campo `id` retornado
- ✅ `valor_total` calculado corretamente (2 × 49.90 = 99.80)
- ✅ `status`: "concluida"

**Critério de Falha:**
- ❌ Status HTTP: 400, 500
- ❌ `valor_total` incorreto
- ❌ Estoque não decrementado (verificar teste 4.7)

---

### ✅ Teste 4.7: Validar Decremento de Estoque

**Comando:**
```bash
# Buscar produto criado no teste 4.4
curl -X GET http://localhost:8000/api/produtos/456 \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nStatus: %{http_code}\n" \
  -s
```

**Saída Esperada:**
```json
{
  "id": 456,
  "nome": "Ração Smoke Test",
  "preco": 49.90,
  "estoque": 98,  // 100 - 2 (vendidos) = 98
  "categoria": "Ração"
}
Status: 200
```

**Critério de Sucesso:**
- ✅ Status HTTP: 200
- ✅ `estoque`: 98 (decrementou corretamente)

**Critério de Falha:**
- ❌ `estoque`: 100 (não decrementou!)
- ❌ `estoque` negativo

---

## 🗄️ TESTES DE BANCO DE DADOS

### Objetivo
Validar que conexão com banco está OK e operações básicas funcionam.

---

### ✅ Teste 5.1: Conexão com Banco

**Comando:**
```bash
# Via psql
PGPASSWORD=postgres psql -h localhost -U postgres -d petshop_db -c "SELECT 1 AS result;"

# OU via API (readiness já testa isso)
curl -X GET http://localhost:8000/ready -s | jq '.checks.database'
```

**Saída Esperada:**
```
 result 
--------
      1
(1 row)
```

**Critério de Sucesso:**
- ✅ Conexão estabelecida
- ✅ Query executada com sucesso

**Critério de Falha:**
- ❌ Connection refused
- ❌ Authentication failed
- ❌ Database does not exist

---

### ✅ Teste 5.2: Migrations Aplicadas

**Comando:**
```bash
# Verificar versão atual
PGPASSWORD=postgres psql -h localhost -U postgres -d petshop_db -c "SELECT version_num FROM alembic_version;"

# OU via API
curl -X GET http://localhost:8000/ready -s | jq '.checks.migrations'
```

**Saída Esperada:**
```
 version_num
-------------
 abc123def456
(1 row)
```

**Critério de Sucesso:**
- ✅ Tabela `alembic_version` existe
- ✅ `version_num` não é NULL
- ✅ Versão é a esperada (HEAD do Alembic)

**Critério de Falha:**
- ❌ Tabela `alembic_version` não existe
- ❌ `version_num` é NULL ou vazio
- ❌ Versão está desatualizada

---

### ✅ Teste 5.3: Escrita no Banco

**Comando:**
```bash
# Inserir registro de teste
PGPASSWORD=postgres psql -h localhost -U postgres -d petshop_db -c "
INSERT INTO smoke_test_log (test_name, executed_at, result)
VALUES ('db_write_test', NOW(), 'success')
RETURNING id, test_name, executed_at;
"
```

**Saída Esperada:**
```
 id | test_name      | executed_at
----|----------------|---------------------
  1 | db_write_test  | 2026-02-05 10:10:00
(1 row)
```

**Critério de Sucesso:**
- ✅ INSERT executado com sucesso
- ✅ ID auto-incrementado retornado

**Critério de Falha:**
- ❌ Permission denied
- ❌ Table does not exist
- ❌ Constraint violation

---

### ✅ Teste 5.4: Leitura do Banco

**Comando:**
```bash
# Ler registro inserido no teste anterior
PGPASSWORD=postgres psql -h localhost -U postgres -d petshop_db -c "
SELECT id, test_name, executed_at, result
FROM smoke_test_log
WHERE test_name = 'db_write_test'
ORDER BY executed_at DESC
LIMIT 1;
"
```

**Saída Esperada:**
```
 id | test_name      | executed_at         | result
----|----------------|---------------------|--------
  1 | db_write_test  | 2026-02-05 10:10:00 | success
(1 row)
```

**Critério de Sucesso:**
- ✅ SELECT executado com sucesso
- ✅ Registro inserido foi encontrado

**Critério de Falha:**
- ❌ Registro não encontrado
- ❌ Query timeout

---

### ✅ Teste 5.5: Integridade Referencial

**Comando:**
```bash
# Verificar foreign keys críticas
PGPASSWORD=postgres psql -h localhost -U postgres -d petshop_db -c "
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name IN ('vendas', 'vendas_itens', 'pagamentos')
ORDER BY tc.table_name;
"
```

**Saída Esperada:**
```
   table_name   | column_name |  foreign_table_name  | foreign_column_name
----------------|-------------|----------------------|--------------------
 vendas         | cliente_id  | clientes             | id
 vendas_itens   | venda_id    | vendas               | id
 vendas_itens   | produto_id  | produtos             | id
 pagamentos     | venda_id    | vendas               | id
(4 rows)
```

**Critério de Sucesso:**
- ✅ Foreign keys esperadas estão presentes
- ✅ Referências corretas (vendas → clientes, etc.)

**Critério de Falha:**
- ❌ Foreign key ausente
- ❌ Referência incorreta

---

## 📊 TESTES DE OBSERVABILIDADE

### Objetivo
Validar que logs, métricas e traces estão funcionando.

---

### ✅ Teste 6.1: Request ID Presente

**Comando:**
```bash
# Fazer request e capturar header X-Request-ID
curl -X GET http://localhost:8000/health \
  -H "Accept: application/json" \
  -i -s | grep -i "x-request-id"
```

**Saída Esperada:**
```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

**Critério de Sucesso:**
- ✅ Header `X-Request-ID` presente
- ✅ Valor é um UUID válido

**Critério de Falha:**
- ❌ Header ausente
- ❌ Valor vazio ou inválido

---

### ✅ Teste 6.2: Logs Estruturados (JSON)

**Comando:**
```bash
# Fazer request e verificar logs
curl -X GET http://localhost:8000/health -s > /dev/null

# Ver logs gerados (últimos 5)
docker logs --tail 5 fastapi_app
```

**Saída Esperada:**
```json
{"timestamp":"2026-02-05T10:15:00Z","level":"INFO","request_id":"550e8400-e29b-41d4-a716-446655440000","method":"GET","path":"/health","status":200,"duration_ms":12.3}
```

**Critério de Sucesso:**
- ✅ Logs em formato JSON
- ✅ Campo `request_id` presente
- ✅ Campo `method`, `path`, `status`, `duration_ms` presentes

**Critério de Falha:**
- ❌ Logs em texto plano (não JSON)
- ❌ Campo `request_id` ausente
- ❌ Campos importantes ausentes

---

### ✅ Teste 6.3: Request ID Correlacionado nos Logs

**Comando:**
```bash
# 1. Fazer request com X-Request-ID customizado
REQUEST_ID="test-12345-67890"
curl -X GET http://localhost:8000/api/clientes \
  -H "X-Request-ID: $REQUEST_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -s > /dev/null

# 2. Buscar logs com esse request_id
docker logs fastapi_app 2>&1 | grep "$REQUEST_ID"
```

**Saída Esperada:**
```json
{"timestamp":"2026-02-05T10:16:00Z","level":"INFO","request_id":"test-12345-67890","message":"Request started","method":"GET","path":"/api/clientes"}
{"timestamp":"2026-02-05T10:16:00Z","level":"INFO","request_id":"test-12345-67890","message":"Query executed","query":"SELECT * FROM clientes LIMIT 10"}
{"timestamp":"2026-02-05T10:16:00Z","level":"INFO","request_id":"test-12345-67890","message":"Request completed","status":200,"duration_ms":45.2}
```

**Critério de Sucesso:**
- ✅ Múltiplas linhas de log com mesmo `request_id`
- ✅ Request ID passado no header foi usado

**Critério de Falha:**
- ❌ Nenhum log encontrado com o request_id
- ❌ Request ID diferente do enviado

---

### ✅ Teste 6.4: Logs Não Contêm Dados Sensíveis

**Comando:**
```bash
# Fazer login e verificar logs
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@petshop.local","password":"admin123"}' \
  -s > /dev/null

# Buscar por senha nos logs
docker logs fastapi_app 2>&1 | grep -i "admin123"
```

**Saída Esperada:**
```
(nenhum resultado)
```

**Critério de Sucesso:**
- ✅ Nenhuma senha encontrada nos logs
- ✅ Nenhum token completo nos logs
- ✅ Nenhum CPF/cartão de crédito nos logs

**Critério de Falha:**
- ❌ Senha aparece em logs
- ❌ Token JWT completo aparece em logs
- ❌ Dados sensíveis (CPF, cartão) aparecem

---

## ✅ CHECKLIST DE EXECUÇÃO

### Pré-Requisitos

- [ ] Aplicação deployada
- [ ] Container/processo rodando
- [ ] Banco de dados acessível
- [ ] Variáveis de ambiente configuradas
- [ ] `curl` ou `httpie` instalado
- [ ] `jq` instalado (para parsing JSON)
- [ ] Token de admin disponível (ou credenciais)

---

### Sequência de Execução

**Tempo Estimado:** 3-5 minutos

```
┌─────────────────────────────────────┐
│ BLOCO 1: STARTUP (30s)              │
├─────────────────────────────────────┤
│ ✅ 1.1 Aplicação inicia             │
│ ✅ 1.2 Logs corretos                │
│ ✅ 1.3 Porta acessível              │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ BLOCO 2: ENDPOINTS (30s)            │
├─────────────────────────────────────┤
│ ✅ 2.1 /health → 200                │
│ ✅ 2.2 /ready → 200                 │
│ ✅ 2.3 /docs → 200                  │
│ ✅ 2.4 / → 200                      │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ BLOCO 3: AUTENTICAÇÃO (30s)         │
├─────────────────────────────────────┤
│ ✅ 3.1 Login → token                │
│ ✅ 3.2 Endpoint protegido → 200     │
│ ✅ 3.3 Sem token → 401              │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ BLOCO 4: FLUXOS CRÍTICOS (2 min)    │
├─────────────────────────────────────┤
│ ✅ 4.1 Criar cliente                │
│ ✅ 4.2 Listar clientes              │
│ ✅ 4.3 Buscar cliente por ID        │
│ ✅ 4.4 Criar produto                │
│ ✅ 4.5 Listar produtos              │
│ ✅ 4.6 Criar venda                  │
│ ✅ 4.7 Validar estoque              │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ BLOCO 5: BANCO (30s)                │
├─────────────────────────────────────┤
│ ✅ 5.1 Conexão                      │
│ ✅ 5.2 Migrations                   │
│ ✅ 5.3 Escrita                      │
│ ✅ 5.4 Leitura                      │
│ ✅ 5.5 Integridade                  │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ BLOCO 6: OBSERVABILIDADE (30s)      │
├─────────────────────────────────────┤
│ ✅ 6.1 Request ID presente          │
│ ✅ 6.2 Logs JSON                    │
│ ✅ 6.3 Request ID correlacionado    │
│ ✅ 6.4 Sem dados sensíveis          │
└─────────────────────────────────────┘
         ↓
     ✅ APROVADO
```

---

### Critérios de Aprovação

| Status | Descrição |
|--------|-----------|
| ✅ **PASSOU** | Todos os testes passaram → **LIBERAR PARA TRÁFEGO** |
| ⚠️ **PASSOU COM AVISOS** | Alguns testes não críticos falharam → **REVISAR LOGS** |
| ❌ **FALHOU** | Testes críticos falharam → **ROLLBACK IMEDIATO** |

**Testes Críticos (bloqueiam deploy):**
- 1.1 Aplicação inicia
- 2.1 /health → 200
- 2.2 /ready → 200
- 3.1 Login funciona
- 5.1 Conexão com banco
- 5.2 Migrations aplicadas

**Testes Importantes (geram alerta):**
- 4.6 Criar venda
- 4.7 Validar estoque
- 6.2 Logs estruturados

**Testes Opcionais (informativo):**
- 2.3 /docs acessível
- 6.4 Sem dados sensíveis nos logs

---

## 🤖 AUTOMAÇÃO

### Script Completo de Smoke Tests

```bash
#!/bin/bash
# smoke_tests.sh - Smoke tests automatizados

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@petshop.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

PASSED=0
FAILED=0
WARNINGS=0

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função auxiliar
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local expected_status="$4"
    local headers="$5"
    local data="$6"
    
    echo -n "Testing: $name ... "
    
    if [ -z "$data" ]; then
        status=$(curl -X "$method" "$BASE_URL$endpoint" \
            -H "$headers" \
            -w "%{http_code}" -s -o /dev/null)
    else
        status=$(curl -X "$method" "$BASE_URL$endpoint" \
            -H "$headers" \
            -d "$data" \
            -w "%{http_code}" -s -o /dev/null)
    fi
    
    if [ "$status" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ PASSED${NC} (HTTP $status)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC} (expected $expected_status, got $status)"
        ((FAILED++))
        return 1
    fi
}

echo "🧪 ============================================"
echo "🧪  SMOKE TESTS - PET SHOP API"
echo "🧪 ============================================"
echo "🌐 Base URL: $BASE_URL"
echo "⏰ Started at: $(date)"
echo ""

# BLOCO 1: STARTUP
echo "📦 BLOCO 1: STARTUP"
echo "-------------------------------------------"

# 1.1: Container rodando
echo -n "Testing: Container rodando ... "
if docker ps | grep -q fastapi_app; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# BLOCO 2: ENDPOINTS BÁSICOS
echo ""
echo "🩺 BLOCO 2: ENDPOINTS BÁSICOS"
echo "-------------------------------------------"

test_endpoint "Health Check" "GET" "/health" 200 "Accept: application/json"
test_endpoint "Readiness Check" "GET" "/ready" 200 "Accept: application/json"
test_endpoint "Documentation" "GET" "/docs" 200 ""
test_endpoint "Root Endpoint" "GET" "/" 200 "Accept: application/json"

# BLOCO 3: AUTENTICAÇÃO
echo ""
echo "🔐 BLOCO 3: AUTENTICAÇÃO"
echo "-------------------------------------------"

# 3.1: Login
echo -n "Testing: Login (obter token) ... "
TOKEN=$(curl -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
    -s | jq -r '.access_token')

if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC} (token not received)"
    ((FAILED++))
    exit 1
fi

# 3.2: Endpoint protegido COM token
test_endpoint "Endpoint protegido (com token)" "GET" "/api/usuarios/me" 200 "Authorization: Bearer $TOKEN"

# 3.3: Endpoint protegido SEM token
test_endpoint "Endpoint protegido (sem token)" "GET" "/api/usuarios/me" 401 ""

# BLOCO 4: FLUXOS CRÍTICOS
echo ""
echo "🛒 BLOCO 4: FLUXOS CRÍTICOS"
echo "-------------------------------------------"

# 4.1: Criar cliente
echo -n "Testing: Criar cliente ... "
CLIENTE_RESPONSE=$(curl -X POST "$BASE_URL/api/clientes" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "nome": "Smoke Test Cliente",
        "email": "smoketest@example.com",
        "telefone": "(11) 98765-4321",
        "cpf": "123.456.789-00"
    }' -s)

CLIENTE_ID=$(echo "$CLIENTE_RESPONSE" | jq -r '.id')
if [ -n "$CLIENTE_ID" ] && [ "$CLIENTE_ID" != "null" ]; then
    echo -e "${GREEN}✅ PASSED${NC} (ID: $CLIENTE_ID)"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# 4.2: Listar clientes
test_endpoint "Listar clientes" "GET" "/api/clientes?limit=5" 200 "Authorization: Bearer $TOKEN"

# 4.4: Criar produto
echo -n "Testing: Criar produto ... "
PRODUTO_RESPONSE=$(curl -X POST "$BASE_URL/api/produtos" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "nome": "Ração Smoke Test",
        "descricao": "Produto para smoke test",
        "preco": 49.90,
        "estoque": 100,
        "categoria": "Ração"
    }' -s)

PRODUTO_ID=$(echo "$PRODUTO_RESPONSE" | jq -r '.id')
if [ -n "$PRODUTO_ID" ] && [ "$PRODUTO_ID" != "null" ]; then
    echo -e "${GREEN}✅ PASSED${NC} (ID: $PRODUTO_ID)"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# 4.5: Listar produtos
test_endpoint "Listar produtos" "GET" "/api/produtos?limit=5" 200 "Authorization: Bearer $TOKEN"

# BLOCO 5: BANCO DE DADOS
echo ""
echo "🗄️  BLOCO 5: BANCO DE DADOS"
echo "-------------------------------------------"

# 5.1: Conexão
echo -n "Testing: Conexão com banco ... "
DB_STATUS=$(curl -X GET "$BASE_URL/ready" -s | jq -r '.checks.database')
if [ "$DB_STATUS" == "ok" ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC} (status: $DB_STATUS)"
    ((FAILED++))
fi

# 5.2: Migrations
echo -n "Testing: Migrations aplicadas ... "
MIGRATIONS_STATUS=$(curl -X GET "$BASE_URL/ready" -s | jq -r '.checks.migrations')
if [ "$MIGRATIONS_STATUS" == "ok" ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC} (status: $MIGRATIONS_STATUS)"
    ((FAILED++))
fi

# BLOCO 6: OBSERVABILIDADE
echo ""
echo "📊 BLOCO 6: OBSERVABILIDADE"
echo "-------------------------------------------"

# 6.1: Request ID
echo -n "Testing: Request ID presente ... "
REQUEST_ID=$(curl -X GET "$BASE_URL/health" -i -s | grep -i "x-request-id" | awk '{print $2}' | tr -d '\r')
if [ -n "$REQUEST_ID" ]; then
    echo -e "${GREEN}✅ PASSED${NC} (ID: ${REQUEST_ID:0:20}...)"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  WARNING${NC} (header not found)"
    ((WARNINGS++))
fi

# RESULTADO FINAL
echo ""
echo "🏁 ============================================"
echo "🏁  RESULTADO FINAL"
echo "🏁 ============================================"
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
echo "⏰ Finished at: $(date)"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ SMOKE TESTS: PASSED${NC}"
    echo "🚀 Sistema pronto para tráfego de produção"
    exit 0
else
    echo -e "${RED}❌ SMOKE TESTS: FAILED${NC}"
    echo "🚨 Rollback necessário!"
    exit 1
fi
```

**Executar:**
```bash
chmod +x smoke_tests.sh
./smoke_tests.sh
```

---

### Integração CI/CD

#### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Deploy to server
        run: |
          ssh deploy@prod-server "cd /app && docker-compose pull && docker-compose up -d"

      - name: Wait for startup
        run: sleep 30

      - name: Run smoke tests
        run: |
          BASE_URL=https://api.petshop.com \
          ADMIN_EMAIL=${{ secrets.ADMIN_EMAIL }} \
          ADMIN_PASSWORD=${{ secrets.ADMIN_PASSWORD }} \
          ./smoke_tests.sh

      - name: Rollback on failure
        if: failure()
        run: |
          ssh deploy@prod-server "cd /app && docker-compose down && docker-compose up -d --no-deps --build app_backup"
          exit 1

      - name: Notify success
        if: success()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -H 'Content-Type: application/json' \
            -d '{"text":"✅ Deploy successful! Smoke tests passed."}'
```

---

## 🔧 TROUBLESHOOTING

### Problema 1: /health retorna 503

**Causa:** Aplicação ainda está inicializando.

**Solução:**
```bash
# Aguardar mais tempo (até 60s em produção)
sleep 30
curl http://localhost:8000/health
```

---

### Problema 2: /ready retorna "migrations: pending"

**Causa:** Migrations não aplicadas.

**Solução:**
```bash
# Aplicar migrations
docker exec fastapi_app alembic upgrade head

# Ou via script
cd backend && python -m alembic upgrade head
```

---

### Problema 3: Login retorna 401

**Causa:** Credenciais incorretas ou seed não aplicado.

**Solução:**
```bash
# Verificar se usuário admin existe
PGPASSWORD=postgres psql -h localhost -U postgres -d petshop_db -c "SELECT id, email FROM usuarios WHERE email = 'admin@petshop.local';"

# Se não existir, aplicar seed
cd backend && python scripts/seed_initial_data.py
```

---

### Problema 4: Criar venda retorna 400

**Causa:** Cliente ou produto não existe.

**Solução:**
```bash
# Verificar IDs usados nos testes
echo "Cliente ID: $CLIENTE_ID"
echo "Produto ID: $PRODUTO_ID"

# Verificar no banco
PGPASSWORD=postgres psql -h localhost -U postgres -d petshop_db -c "SELECT id FROM clientes WHERE id = $CLIENTE_ID;"
PGPASSWORD=postgres psql -h localhost -U postgres -d petshop_db -c "SELECT id FROM produtos WHERE id = $PRODUTO_ID;"
```

---

### Problema 5: Request ID não aparece nos logs

**Causa:** Middleware não configurado.

**Solução:**
```bash
# Verificar se RequestContextMiddleware está ativo
docker logs fastapi_app | grep "RequestContextMiddleware"

# Se não estiver, verificar main.py
cat backend/app/main.py | grep "RequestContextMiddleware"
```

---

## 📊 MÉTRICAS DE SUCESSO

### KPIs dos Smoke Tests

| Métrica | Valor Esperado |
|---------|----------------|
| **Taxa de Sucesso** | 100% |
| **Tempo de Execução** | < 5 minutos |
| **Rollbacks Evitados** | 95%+ |
| **Falsos Positivos** | < 5% |

### Histórico de Execuções

```
Data       | Resultado | Tempo | Testes | Falhas | Notas
-----------|-----------|-------|--------|--------|------------------
2026-02-05 | ✅ PASSED | 3m 45s| 24     | 0      | -
2026-02-01 | ✅ PASSED | 4m 12s| 24     | 0      | -
2026-01-28 | ❌ FAILED | 2m 30s| 24     | 3      | Migrations pending
2026-01-25 | ✅ PASSED | 3m 55s| 24     | 0      | -
```

---

## ✅ GO / NO-GO DECISION

### Critérios para GO LIVE

- [ ] **Smoke Tests:** 100% aprovado (0 falhas críticas)
- [ ] **RTO Validado:** Restore testado nos últimos 7 dias
- [ ] **Backups:** Último backup < 24h e íntegro
- [ ] **Monitoramento:** Alertas configurados e funcionando
- [ ] **Logs:** Request ID presente e logs estruturados
- [ ] **Documentação:** Runbook atualizado
- [ ] **Equipe:** On-call definido e disponível
- [ ] **Rollback Plan:** Testado e documentado
- [ ] **Stakeholders:** Notificados sobre deploy
- [ ] **Janela de Manutenção:** Agendada e comunicada

### Decisão Final

```
✅ GO LIVE
   → Todos os critérios atendidos
   → Sistema pronto para tráfego de produção
   → Liberar para usuários

❌ NO-GO
   → Smoke tests falharam
   → Pendências críticas
   → Adiar deploy e corrigir
```

---

## 📞 CONTATOS

| Papel | Nome | Disponibilidade |
|-------|------|-----------------|
| **DevOps Lead** | Maria Santos | 24/7 |
| **QA Lead** | Pedro Oliveira | Seg-Sex 9-18h |
| **DBA** | João Silva | 24/7 |

---

## 📚 REFERÊNCIAS

- [CHANGES_PREPROD_ENV_VALIDATION.md](CHANGES_PREPROD_ENV_VALIDATION.md)
- [CHANGES_PREPROD_HEALTH_READY.md](CHANGES_PREPROD_HEALTH_READY.md)
- [CHANGES_PREPROD_DB_MIGRATIONS.md](CHANGES_PREPROD_DB_MIGRATIONS.md)
- [CHANGES_PREPROD_OBSERVABILITY.md](CHANGES_PREPROD_OBSERVABILITY.md)
- [CHANGES_PREPROD_SEED_CONTROL.md](CHANGES_PREPROD_SEED_CONTROL.md)
- [BACKUP_RESTORE_RUNBOOK.md](BACKUP_RESTORE_RUNBOOK.md)
- [Google SRE Book - Smoke Tests](https://sre.google/sre-book/monitoring-distributed-systems/)

---

**FIM DO DOCUMENTO**

**Última Revisão:** 2026-02-05  
**Próxima Revisão:** Após cada deploy  
**Responsável:** DevOps Lead
