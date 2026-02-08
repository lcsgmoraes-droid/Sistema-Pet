# 📦 Sistema de Predecessor/Sucessor de Produtos

## 🎯 Objetivo

Resolver o problema de perda de histórico quando um produto sofre alterações significativas (mudança de embalagem, peso, fornecedor, etc.), permitindo vincular produtos que substituem outros e manter um histórico consolidado.

---

## 🏗️ Como Funciona

### Conceitos Básicos

- **Predecessor**: Produto antigo que foi substituído
- **Sucessor**: Produto novo que substitui o anterior
- **Descontinuação Automática**: Quando você cria um produto sucessor, o predecessor é automaticamente marcado como descontinuado

### Exemplo Prático

```
📦 Ração Special Dog 350g (ID: 123)
   └─ Vendido de 2020 até 07/02/2026
   └─ Total vendido: 1.500 unidades
   
      ⬇️ SUBSTITUI (produto_predecessor_id = 123)
      
📦 Ração Special Dog 300g (ID: 456)
   └─ Vendendo desde 07/02/2026
   └─ Total vendido: 50 unidades
   
   🔍 Histórico Consolidado: 1.550 unidades
```

---

## 📊 Estrutura no Banco de Dados

### Campos Adicionados

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `produto_predecessor_id` | INTEGER | ID do produto que este substitui (NULL se não substitui ninguém) |
| `data_descontinuacao` | TIMESTAMP | Data em que o produto foi descontinuado (preenchido automaticamente) |
| `motivo_descontinuacao` | VARCHAR(255) | Motivo da descontinuação (ex: "Mudança de embalagem") |

### View Helper: `vw_produtos_evolucao`

Uma view que facilita consultas mostrando toda a cadeia de evolução:

```sql
SELECT * FROM vw_produtos_evolucao WHERE id = 456;
```

Retorna:
- Dados do produto atual
- Dados do predecessor (se houver)
- Dados do sucessor (se houver)
- Status na cadeia: `NORMAL`, `DESCONTINUADO`, `SUCESSOR`, `DESCONTINUADO_SEM_SUCESSOR`

---

## 🔧 Como Usar

### 1. Criar um Produto Sucessor (Frontend - em desenvolvimento)

Ao cadastrar um novo produto, você verá:

```
┌─────────────────────────────────────────┐
│ ☑️ Este produto substitui outro          │
│   🔍 [Buscar produto...]                 │
│                                          │
│ Produto selecionado:                     │
│ 📦 Ração Special Dog 350g                │
│                                          │
│ Motivo da substituição:                  │
│ [ Mudança de embalagem         ▼]       │
│                                          │
│ Ou descreva:                             │
│ [_________________________________]      │
└─────────────────────────────────────────┘
```

**O que acontece automaticamente:**
1. ✅ Novo produto é criado normalmente
2. ✅ Produto anterior é marcado como **descontinuado**
3. ✅ Data de descontinuação = data de criação do sucessor
4. ✅ Histórico completo fica acessível

### 2. Usar a API Diretamente

**POST /produtos/**

```json
{
  "codigo": "RAC-SD-300G",
  "nome": "Ração Special Dog 300g",
  "preco_venda": 45.90,
  "produto_predecessor_id": 123,
  "motivo_descontinuacao": "Mudança de embalagem do fabricante",
  // ... outros campos normais
}
```

**Resposta:**
```json
{
  "id": 456,
  "nome": "Ração Special Dog 300g",
  "produto_predecessor_id": 123,
  "predecessor_nome": "Ração Special Dog 350g",
  "data_descontinuacao": null,
  // ...
}
```

O predecessor (ID 123) agora terá:
```json
{
  "id": 123,
  "nome": "Ração Special Dog 350g",
  "data_descontinuacao": "2026-02-07T14:30:00Z",
  "motivo_descontinuacao": "Mudança de embalagem do fabricante",
  "sucessor_nome": "Ração Special Dog 300g"
}
```

---

## 📈 Relatórios Consolidados (Próxima Fase)

### Visualizações Planejadas

#### 1. Gráfico de Vendas Consolidado
```
   Vendas
     |
1500 |████████████████████████████████
     |                                  ║
1000 |                                  ║ ← Mudança
     |                                  ║   350g → 300g
 500 |                                  ║
     |                                  ▼
   0 |________________________________█████
     2020    2022    2024    2026
     
     [x] Mostrar consolidado (padrão)
     [ ] Separar por produto
```

#### 2. Card do Produto Descontinuado
```
╔════════════════════════════════════════╗
║ ⚠️ PRODUTO DESCONTINUADO                ║
║                                        ║
║ Este produto foi substituído           ║
║ por: Ração Special Dog 300g            ║
║ em: 07/02/2026                         ║
║                                        ║
║ Motivo: Mudança de embalagem           ║
║                                        ║
║ [Ver produto sucessor →]               ║
║ [Ver histórico completo →]             ║
╚════════════════════════════════════════╝
```

#### 3. Cadeia de Evolução
```
📦 Linha do Tempo - Ração Special Dog

2019 ──┬── Special Dog 400g (ID: 100)
       │   └─ Descontinuado: Mudança de fornecedor
       │
2020 ──┼── Special Dog 350g (ID: 123)
       │   └─ Descontinuado: Mudança de embalagem
       │
2026 ──┴── Special Dog 300g (ID: 456) ✅ ATUAL
```

---

## 🎓 Casos de Uso

### 1. Mudança de Embalagem/Peso
**Antes:** Ração 350g  
**Agora:** Ração 300g  
**Motivo:** Fabricante alterou a gramatura

### 2. Mudança de Fornecedor
**Antes:** Produto importado do fornecedor A  
**Agora:** Mesmo produto do fornecedor B  
**Motivo:** Melhor preço/prazo

### 3. Reformulação
**Antes:** Ração linha standard  
**Agora:** Ração linha premium (nova fórmula)  
**Motivo:** Upgrade de linha

### 4. Mudança de Marca/Parceria
**Antes:** Produto marca X  
**Agora:** Produto marca Y (mesmo produto, novo distribuidor)  
**Motivo:** Contrato comercial

---

## 🔍 Queries Úteis

### Ver produtos descontinuados
```sql
SELECT 
    id, 
    nome, 
    data_descontinuacao, 
    motivo_descontinuacao
FROM produtos 
WHERE data_descontinuacao IS NOT NULL
ORDER BY data_descontinuacao DESC;
```

### Ver cadeia completa de um produto
```sql
-- Recursivo: pega todos os predecessores
WITH RECURSIVE cadeia AS (
    SELECT id, nome, produto_predecessor_id, 0 as nivel
    FROM produtos WHERE id = 456  -- ID do produto atual
    
    UNION ALL
    
    SELECT p.id, p.nome, p.produto_predecessor_id, c.nivel + 1
    FROM produtos p
    INNER JOIN cadeia c ON p.id = c.produto_predecessor_id
)
SELECT * FROM cadeia ORDER BY nivel DESC;
```

### Histórico consolidado de vendas
```sql
-- Somar vendas do produto e todos os predecessores
WITH RECURSIVE predecessores AS (
    SELECT id FROM produtos WHERE id = 456
    UNION ALL
    SELECT p.produto_predecessor_id 
    FROM produtos p
    INNER JOIN predecessores pr ON p.id = pr.id
    WHERE p.produto_predecessor_id IS NOT NULL
)
SELECT 
    SUM(quantidade) as total_vendido,
    SUM(valor_total) as valor_total
FROM itens_venda
WHERE produto_id IN (SELECT id FROM predecessores);
```

---

## ⚠️ Regras e Validações

### ✅ Permitido
- ✅ Um produto pode ter apenas **1 predecessor**
- ✅ Um produto pode ter **múltiplos sucessores** (ex: produto dividido em 2 linhas)
- ✅ Produto descontinuado **continua consultável/visível**
- ✅ Produto descontinuado **não pode ser vendido** (opção futura)

### ❌ Não Permitido
- ❌ Criar cadeia circular (A → B → A)
- ❌ Alterar predecessor de um produto já criado (deve criar novo)
- ❌ Excluir produto que é predecessor de outro

---

## 🚀 Próximos Passos

### Fase 1: Estrutura Básica ✅
- [x] Migration do banco
- [x] Modelo atualizado
- [x] Rotas da API
- [x] Documentação

### Fase 2: Interface (Em Desenvolvimento)
- [ ] Campo "Substitui produto" no formulário
- [ ] Busca de produtos com autocomplete
- [ ] Alert de descontinuação na visualização
- [ ] Badge "DESCONTINUADO" na listagem

### Fase 3: Relatórios Consolidados
- [ ] API endpoint de histórico consolidado
- [ ] Gráfico de vendas com linha contínua
- [ ] Card de evolução do produto
- [ ] Dashboard de produtos descontinuados

### Fase 4: Automações
- [ ] Notificar quando produto predecessor acabar estoque
- [ ] Sugerir troca automática no PDV
- [ ] Migração automática em listas de compra recorrentes

---

## 📞 Suporte

Dúvidas ou sugestões sobre o sistema de Predecessor/Sucessor?

- **Documentação técnica:** `/backend/migrations/003_produto_predecessor_sucessor.sql`
- **View helper:** `vw_produtos_evolucao`
- **Modelo:** `backend/app/produtos_models.py` (linha ~240)

---

**Última atualização:** 07/02/2026  
**Status:** ✅ Backend implementado | 🚧 Frontend em desenvolvimento
