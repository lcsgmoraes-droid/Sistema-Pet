# Funcionalidade: Controle DRE por Fornecedor/Cliente

## Objetivo

Permitir marcar fornecedores/clientes que **NÃO devem gerar lançamentos no DRE**, como fornecedores de produtos para revenda (ex: Buendia).

## Como Funciona

### 1. Campo `controla_dre` na tabela `clientes`

- **`controla_dre = True`** (padrão): Lançamentos deste fornecedor/cliente vão para DRE (despesas operacionais, receitas, etc)
- **`controla_dre = False`**: Lançamentos NÃO vão para DRE (compras de produtos para revenda/estoque)

### 2. Comportamento Automático

Quando um fornecedor tem `controla_dre = False`:

✅ **Lançamentos são automaticamente ignorados**:
- NÃO aparecem na lista de pendentes de classificação
- NÃO geram sugestões de classificação DRE
- São automaticamente excluídos do processo de classificação

### 3. Uso Prático

**Exemplo: Buendia (fornecedor de produtos)**
- Buendia fornece produtos para revenda
- Produtos só impactam DRE quando são VENDIDOS (CMV - Custo de Mercadoria Vendida)
- Compra do produto NÃO deve aparecer no DRE diretamente
- Solução: Marcar `controla_dre = False` para Buendia

## API Endpoint

### PATCH `/clientes/{cliente_id}/controla-dre?controla_dre={true|false}`

**Request:**
```http
PATCH /clientes/123/controla-dre?controla_dre=false
Authorization: Bearer {token}
```

**Response:**
```json
{
  "success": true,
  "message": "Desativado controle DRE para Buendia LTDA",
  "data": {
    "id": 123,
    "nome": "Buendia LTDA",
    "tipo_cadastro": "fornecedor",
    "controla_dre": false
  }
}
```

## Migration

**Arquivo:** `4819578f7f40_add_controla_dre_to_clientes.py`

```sql
-- Adiciona coluna controla_dre (default=True)
ALTER TABLE clientes ADD COLUMN controla_dre BOOLEAN NOT NULL DEFAULT TRUE;
```

## Modificações no Código

### 1. Model `Cliente` (backend/app/models.py)

```python
controla_dre = Column(Boolean, nullable=False, default=True, server_default='1')
```

### 2. Serviço de Classificação DRE (backend/app/dre_classificacao_service.py)

**Função `analisar_lancamento()`:**
- Verifica se fornecedor/cliente tem `controla_dre = False`
- Se sim, retorna lista vazia (sem sugestões)

**Função `listar_pendentes()`:**
- Filtra lançamentos apenas de fornecedores/clientes com `controla_dre = True`
- Lançamentos de fornecedores com `controla_dre = False` não aparecem na lista

### 3. Frontend (futuro)

Adicionar checkbox na tela de cadastro/edição de fornecedores:

```jsx
<label>
  <input 
    type="checkbox" 
    checked={fornecedor.controla_dre}
    onChange={(e) => atualizarControlaDRE(fornecedor.id, e.target.checked)}
  />
  Controla DRE (despesas operacionais)
</label>
<p className="text-sm text-gray-500">
  Desmarque para fornecedores de produtos para revenda (ex: Buendia)
</p>
```

## Casos de Uso

| Tipo de Fornecedor | controla_dre | Motivo |
|-------------------|--------------|--------|
| Buendia (produtos) | ❌ False | Produtos para revenda - só impacta DRE quando vendido |
| Fornecedor de ração | ❌ False | Produtos para revenda |
| Fornecedor de embalagens | ❌ False | Insumos que vão para estoque |
| Contador | ✅ True | Despesa operacional - vai direto para DRE |
| Aluguel | ✅ True | Despesa operacional - vai direto para DRE |
| Funcionário | ✅ True | Despesa com pessoal - vai direto para DRE |
| Cliente (vendas) | ✅ True | Receita - vai direto para DRE |

## Benefícios

1. ✅ **Automação**: Não precisa ficar clicando "Não Controla DRE" toda vez
2. ✅ **Organização**: Lista de pendentes fica mais limpa (sem compras de produtos)
3. ✅ **Precisão**: Evita erro de classificar compra de produto no DRE
4. ✅ **Eficiência**: Sistema já sabe que Buendia nunca vai pro DRE

## Observação

- Produtos comprados de fornecedores com `controla_dre = False` impactam o DRE **quando são vendidos** através do cálculo de CMV (Custo de Mercadoria Vendida)
- A compra em si não aparece no DRE, apenas o custo proporcional quando há venda
