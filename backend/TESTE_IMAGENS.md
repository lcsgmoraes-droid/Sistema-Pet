# 📸 Testes - Endpoints de Imagens

## ✅ Endpoints Implementados

### 1. Upload de Imagem
```http
POST /produtos/{produto_id}/imagens
Content-Type: multipart/form-data
Authorization: Bearer {token}

Body:
- file: arquivo (JPG, PNG, WebP - máx 5MB)
- ordem: int (opcional, padrão 0)
- principal: bool (opcional, padrão false)
```

**Resposta:**
```json
{
  "id": 1,
  "produto_id": 1,
  "url": "/uploads/produtos/1/uuid.jpg",
  "ordem": 0,
  "principal": true,
  "created_at": "2026-01-05T22:00:00"
}
```

### 2. Listar Imagens do Produto
```http
GET /produtos/{produto_id}/imagens
Authorization: Bearer {token}
```

**Resposta:**
```json
[
  {
    "id": 1,
    "produto_id": 1,
    "url": "/uploads/produtos/1/uuid1.jpg",
    "ordem": 0,
    "principal": true,
    "created_at": "2026-01-05T22:00:00"
  },
  {
    "id": 2,
    "produto_id": 1,
    "url": "/uploads/produtos/1/uuid2.jpg",
    "ordem": 1,
    "principal": false,
    "created_at": "2026-01-05T22:01:00"
  }
]
```

### 3. Atualizar Imagem
```http
PUT /produtos/imagens/{imagem_id}
Content-Type: application/json
Authorization: Bearer {token}

Body:
{
  "ordem": 1,
  "principal": true
}
```

### 4. Deletar Imagem
```http
DELETE /produtos/imagens/{imagem_id}
Authorization: Bearer {token}
```

**Resposta:**
```json
{
  "message": "Imagem deletada com sucesso"
}
```

---

## 🧪 Como Testar

### Via Swagger (Documentação Interativa)
1. Acesse: http://127.0.0.1:8000/docs
2. Faça login para obter o token
3. Clique em "Authorize" e cole o token
4. Navegue até a seção "produtos"
5. Teste os endpoints de imagens

### Via cURL

**1. Fazer Upload:**
```bash
curl -X POST "http://127.0.0.1:8000/produtos/1/imagens" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -F "file=@imagem.jpg" \
  -F "principal=true"
```

**2. Listar Imagens:**
```bash
curl -X GET "http://127.0.0.1:8000/produtos/1/imagens" \
  -H "Authorization: Bearer SEU_TOKEN"
```

**3. Atualizar:**
```bash
curl -X PUT "http://127.0.0.1:8000/produtos/imagens/1" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"principal": true}'
```

**4. Deletar:**
```bash
curl -X DELETE "http://127.0.0.1:8000/produtos/imagens/1" \
  -H "Authorization: Bearer SEU_TOKEN"
```

---

## 📁 Estrutura de Arquivos

```
backend/
├── uploads/
│   └── produtos/
│       ├── 1/
│       │   ├── uuid1.jpg
│       │   └── uuid2.jpg
│       ├── 2/
│       │   └── uuid3.png
│       └── ...
```

---

## ✅ Validações Implementadas

- ✅ Apenas JPG, PNG e WebP aceitos
- ✅ Tamanho máximo: 5MB
- ✅ Verifica se produto existe e pertence ao usuário
- ✅ Apenas 1 imagem principal por produto
- ✅ Ordena por principal DESC, ordem ASC
- ✅ Deleta arquivo físico ao remover do banco
- ✅ Cria pasta do produto automaticamente

---

## 🔐 Segurança

- ✅ Requer autenticação (Bearer token)
- ✅ Verifica propriedade do produto (multi-tenant)
- ✅ Valida formato e tamanho do arquivo
- ✅ Gera nomes únicos (UUID) para evitar conflitos
- ✅ Logs de auditoria em todas as operações

---

## 🚀 Próximos Passos

1. ✅ **Backend - Imagens** (CONCLUÍDO)
2. ⏳ **Backend - Fornecedores** (próximo)
3. ⏳ **Frontend - Interface de upload**
4. ⏳ **Frontend - Galeria de imagens**
