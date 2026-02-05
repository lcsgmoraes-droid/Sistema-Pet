# Teste dos Endpoints de Fornecedores

## Configuração Inicial

### 1. Obter Token de Autenticação
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seu@email.com",
    "senha": "sua_senha"
  }'
```

Copie o `access_token` retornado e use nas próximas requisições.

### 2. Variáveis de Ambiente
```bash
# Substitua pelo seu token
export TOKEN="seu_token_aqui"

# IDs para teste (substitua pelos seus)
export PRODUTO_ID=1
export FORNECEDOR_ID=1
export VINCULO_ID=1
```

---

## Endpoints Implementados

### 1. POST /api/produtos/{produto_id}/fornecedores
**Vincular fornecedor a um produto**

#### Campos:
- `fornecedor_id` (obrigatório): ID do fornecedor (deve ser tipo "fornecedor" no cadastro)
- `codigo_fornecedor`: Código do produto no catálogo do fornecedor
- `preco_custo`: Preço de custo praticado por este fornecedor
- `prazo_entrega`: Prazo de entrega em dias
- `estoque_fornecedor`: Quantidade em estoque no fornecedor
- `e_principal`: Define se é o fornecedor principal (boolean)

#### Validações:
- ✅ Produto deve existir e pertencer ao usuário
- ✅ Fornecedor deve existir, pertencer ao usuário e ser tipo "fornecedor"
- ✅ Não permite duplicar vínculo (mesmo fornecedor no mesmo produto)
- ✅ Apenas 1 fornecedor pode ser principal por produto
- ✅ Se marcar como principal, desmarca os outros automaticamente

#### Exemplo cURL:
```bash
curl -X POST "http://localhost:8000/api/produtos/${PRODUTO_ID}/fornecedores" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "fornecedor_id": 1,
    "codigo_fornecedor": "PROD-001",
    "preco_custo": 25.50,
    "prazo_entrega": 7,
    "estoque_fornecedor": 100,
    "e_principal": true
  }'
```

#### Resposta Esperada (200):
```json
{
  "id": 1,
  "produto_id": 1,
  "fornecedor_id": 1,
  "codigo_fornecedor": "PROD-001",
  "preco_custo": 25.50,
  "prazo_entrega": 7,
  "estoque_fornecedor": 100.0,
  "e_principal": true,
  "ativo": true,
  "created_at": "2025-01-20T10:30:00",
  "updated_at": "2025-01-20T10:30:00",
  "fornecedor_nome": "Distribuidora XYZ Ltda",
  "fornecedor_cpf_cnpj": "12.345.678/0001-90",
  "fornecedor_email": "contato@distribuidora.com",
  "fornecedor_telefone": "(11) 98765-4321"
}
```

---

### 2. GET /api/produtos/{produto_id}/fornecedores
**Listar fornecedores vinculados ao produto**

#### Query Parameters:
- `apenas_ativos` (opcional, default=true): Se deve retornar apenas vínculos ativos

#### Ordenação:
1. Fornecedor principal primeiro (`e_principal DESC`)
2. Depois por data de criação (`created_at ASC`)

#### Exemplo cURL:
```bash
# Todos os fornecedores ativos
curl -X GET "http://localhost:8000/api/produtos/${PRODUTO_ID}/fornecedores" \
  -H "Authorization: Bearer ${TOKEN}"

# Incluindo inativos
curl -X GET "http://localhost:8000/api/produtos/${PRODUTO_ID}/fornecedores?apenas_ativos=false" \
  -H "Authorization: Bearer ${TOKEN}"
```

#### Resposta Esperada (200):
```json
[
  {
    "id": 1,
    "produto_id": 1,
    "fornecedor_id": 1,
    "codigo_fornecedor": "PROD-001",
    "preco_custo": 25.50,
    "prazo_entrega": 7,
    "estoque_fornecedor": 100.0,
    "e_principal": true,
    "ativo": true,
    "created_at": "2025-01-20T10:30:00",
    "updated_at": "2025-01-20T10:30:00",
    "fornecedor_nome": "Distribuidora XYZ Ltda",
    "fornecedor_cpf_cnpj": "12.345.678/0001-90",
    "fornecedor_email": "contato@distribuidora.com",
    "fornecedor_telefone": "(11) 98765-4321"
  },
  {
    "id": 2,
    "produto_id": 1,
    "fornecedor_id": 2,
    "codigo_fornecedor": "SKU-789",
    "preco_custo": 27.00,
    "prazo_entrega": 10,
    "estoque_fornecedor": 50.0,
    "e_principal": false,
    "ativo": true,
    "created_at": "2025-01-20T11:00:00",
    "updated_at": "2025-01-20T11:00:00",
    "fornecedor_nome": "Pet Supply SA",
    "fornecedor_cpf_cnpj": "98.765.432/0001-10",
    "fornecedor_email": "vendas@petsupply.com",
    "fornecedor_telefone": "(21) 91234-5678"
  }
]
```

---

### 3. PUT /api/produtos/fornecedores/{vinculo_id}
**Atualizar dados do vínculo fornecedor-produto**

#### Campos (todos opcionais):
- `codigo_fornecedor`: Atualizar código
- `preco_custo`: Atualizar preço
- `prazo_entrega`: Atualizar prazo
- `estoque_fornecedor`: Atualizar estoque
- `e_principal`: Alterar status principal
- `ativo`: Ativar/desativar vínculo

#### Validações:
- ✅ Vínculo deve existir e produto pertencer ao usuário
- ✅ Se marcar como principal, desmarca os outros automaticamente
- ✅ Atualiza `fornecedor_id` do produto quando mudar principal

#### Exemplo cURL:
```bash
# Atualizar preço e prazo
curl -X PUT "http://localhost:8000/api/produtos/fornecedores/${VINCULO_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "preco_custo": 24.90,
    "prazo_entrega": 5
  }'

# Promover a fornecedor principal
curl -X PUT "http://localhost:8000/api/produtos/fornecedores/${VINCULO_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "e_principal": true
  }'

# Desativar vínculo
curl -X PUT "http://localhost:8000/api/produtos/fornecedores/${VINCULO_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "ativo": false
  }'
```

#### Resposta Esperada (200):
```json
{
  "id": 1,
  "produto_id": 1,
  "fornecedor_id": 1,
  "codigo_fornecedor": "PROD-001",
  "preco_custo": 24.90,
  "prazo_entrega": 5,
  "estoque_fornecedor": 100.0,
  "e_principal": true,
  "ativo": true,
  "created_at": "2025-01-20T10:30:00",
  "updated_at": "2025-01-20T12:00:00",
  "fornecedor_nome": "Distribuidora XYZ Ltda",
  "fornecedor_cpf_cnpj": "12.345.678/0001-90",
  "fornecedor_email": "contato@distribuidora.com",
  "fornecedor_telefone": "(11) 98765-4321"
}
```

---

### 4. DELETE /api/produtos/fornecedores/{vinculo_id}
**Desvincular fornecedor do produto**

#### Comportamento:
- Remove o vínculo permanentemente do banco de dados
- Se era o fornecedor principal:
  - Promove automaticamente outro fornecedor ativo
  - Se não houver outros, limpa o `fornecedor_id` do produto

#### Exemplo cURL:
```bash
curl -X DELETE "http://localhost:8000/api/produtos/fornecedores/${VINCULO_ID}" \
  -H "Authorization: Bearer ${TOKEN}"
```

#### Resposta Esperada (200):
```json
{
  "message": "Fornecedor desvinculado com sucesso"
}
```

---

## Fluxo Completo de Teste

### 1. Criar dois fornecedores no módulo de clientes
```bash
# Fornecedor 1
curl -X POST "http://localhost:8000/api/clientes" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Distribuidora XYZ Ltda",
    "tipo": "fornecedor",
    "cpf_cnpj": "12.345.678/0001-90",
    "email": "contato@distribuidora.com",
    "telefone": "(11) 98765-4321"
  }'

# Fornecedor 2
curl -X POST "http://localhost:8000/api/clientes" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Pet Supply SA",
    "tipo": "fornecedor",
    "cpf_cnpj": "98.765.432/0001-10",
    "email": "vendas@petsupply.com",
    "telefone": "(21) 91234-5678"
  }'
```

### 2. Vincular primeiro fornecedor (como principal)
```bash
curl -X POST "http://localhost:8000/api/produtos/1/fornecedores" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "fornecedor_id": 1,
    "codigo_fornecedor": "PROD-001",
    "preco_custo": 25.50,
    "prazo_entrega": 7,
    "estoque_fornecedor": 100,
    "e_principal": true
  }'
```

### 3. Vincular segundo fornecedor (alternativo)
```bash
curl -X POST "http://localhost:8000/api/produtos/1/fornecedores" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "fornecedor_id": 2,
    "codigo_fornecedor": "SKU-789",
    "preco_custo": 27.00,
    "prazo_entrega": 10,
    "estoque_fornecedor": 50,
    "e_principal": false
  }'
```

### 4. Listar todos os fornecedores do produto
```bash
curl -X GET "http://localhost:8000/api/produtos/1/fornecedores" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 5. Atualizar preço do fornecedor principal
```bash
curl -X PUT "http://localhost:8000/api/produtos/fornecedores/1" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "preco_custo": 24.00
  }'
```

### 6. Trocar fornecedor principal
```bash
# Promove o segundo fornecedor (o primeiro será desmarcado automaticamente)
curl -X PUT "http://localhost:8000/api/produtos/fornecedores/2" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "e_principal": true
  }'
```

### 7. Desvincular fornecedor
```bash
curl -X DELETE "http://localhost:8000/api/produtos/fornecedores/1" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## Testando via Swagger UI

1. Acesse: http://localhost:8000/docs
2. Clique em "Authorize" no topo
3. Cole seu token no formato: `Bearer seu_token_aqui`
4. Navegue até a seção "produtos" e encontre os endpoints:
   - POST /api/produtos/{produto_id}/fornecedores
   - GET /api/produtos/{produto_id}/fornecedores
   - PUT /api/produtos/fornecedores/{vinculo_id}
   - DELETE /api/produtos/fornecedores/{vinculo_id}

---

## Casos de Erro

### 404 - Produto não encontrado
```bash
curl -X POST "http://localhost:8000/api/produtos/99999/fornecedores" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"fornecedor_id": 1}'
```

Resposta:
```json
{
  "detail": "Produto não encontrado"
}
```

### 404 - Fornecedor não encontrado ou não é tipo fornecedor
```bash
curl -X POST "http://localhost:8000/api/produtos/1/fornecedores" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"fornecedor_id": 99999}'
```

Resposta:
```json
{
  "detail": "Fornecedor não encontrado ou não é do tipo fornecedor"
}
```

### 400 - Fornecedor já vinculado
```bash
# Tentar vincular o mesmo fornecedor novamente
curl -X POST "http://localhost:8000/api/produtos/1/fornecedores" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"fornecedor_id": 1}'
```

Resposta:
```json
{
  "detail": "Fornecedor já vinculado a este produto"
}
```

---

## Integração com Modelo Produto

Quando um fornecedor é marcado como principal:
- O campo `fornecedor_id` do Produto é atualizado automaticamente
- Se o fornecedor principal for desvinculado, outro é promovido
- Se não houver mais fornecedores, `fornecedor_id` vira `null`

Isso mantém compatibilidade com o código existente que usa `produto.fornecedor_id`.

---

## Logs

Todas as operações geram logs:
- `Fornecedor X vinculado ao produto Y por user@example.com`
- `Vínculo fornecedor Z atualizado por user@example.com`
- `Fornecedor desvinculado (id W) por user@example.com`

---

## Próximos Passos

✅ Backend - Categorias, Marcas, FIFO
✅ Backend - Imagens
✅ Backend - Fornecedores

Faltam:
⏳ Frontend - Interface de produtos
⏳ Frontend - Upload de imagens
⏳ Frontend - Gestão de fornecedores
