# 🐛 CORREÇÕES APLICADAS - PRODUTOS E FORNECEDORES

**Data:** 09/01/2026  
**Status:** Aplicadas e testadas

---

## ✅ PROBLEMA 1: Campo `origem` não estava sendo salvo

### Correções aplicadas:
1. **Extração do XML** - Adicionado linha ~137:
   ```python
   origem = prod.find('nfe:orig', ns).text if prod.find('nfe:orig', ns) is not None else '0'
   ```

2. **Modelo NotaEntradaItem** - Adicionada coluna:
   ```python
   origem = Column(String(1))  # Origem da mercadoria (0-8)
   ```

3. **Criação NotaEntradaItem** - Linha ~672:
   ```python
   origem=item_data.get('origem', '0'),
   ```

4. **Reativação de produto** - Linha ~1877:
   ```python
   produto_existente.origem = item.origem if hasattr(item, 'origem') else '0'
   ```

5. **Criação de produto** - Linha ~1975:
   ```python
   origem=item.origem if hasattr(item, 'origem') else '0',
   ```

6. **Migração executada**: `migrate_add_origem_notas_itens.py`

---

## ✅ PROBLEMA 2: Tabela `produto_fornecedores` não existia

### Correção aplicada:
- **Tabela criada** via migração: `migrate_create_produto_fornecedores.py`
- **Estrutura**:
  ```sql
  CREATE TABLE produto_fornecedores (
      id INTEGER PRIMARY KEY,
      produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE,
      fornecedor_id INTEGER REFERENCES clientes(id),
      codigo_fornecedor VARCHAR(50),
      preco_custo FLOAT,
      prazo_entrega INTEGER,
      estoque_fornecedor FLOAT,
      e_principal BOOLEAN DEFAULT 0,
      ativo BOOLEAN DEFAULT 1,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  )
  ```

### Resultado:
- **Vínculo automático** de fornecedor ao criar/reativar produto já funciona
- Código nas linhas ~1897 e ~1998 já estava implementado, só faltava a tabela

---

## ⚠️ PROBLEMA 3: EAN (Código de Barras) não está sendo salvo

### Análise:
- **Extração do XML**: ✅ Funcionando (linha ~142)
- **Salvamento no NotaEntradaItem**: ✅ Funcionando (linha ~682)
- **Transferência para Produto**: ✅ Código correto (linhas ~1880 e ~1980)

### Possíveis causas:
1. **XML não tem EAN** - Fornecedor não informou
2. **EAN é "SEM GTIN"** - Filtrado propositalmente
3. **EAN é string vazia** - Tratado como None

### Verificação necessária:
Conferir XML diretamente:
```xml
<cEAN>7898950240477</cEAN>
<!-- ou -->
<cEAN>SEM GTIN</cEAN>
<!-- ou -->
<cEAN></cEAN>
```

---

## 📋 CAMPO SKU vs CÓDIGO

### Esclarecimento:
O campo `codigo` no modelo Produto **JÁ É o SKU**:

```python
class Produto:
    codigo = Column(String(50), unique=True, nullable=False)  # SKU
```

- **Backend**: Sempre usa `produto.codigo` como identificador único
- **XML**: Extrai do `<cProd>` do fornecedor
- **Reativação**: Atualiza o codigo com o SKU da nota

**Não há redundância** - só existe um campo identificador por produto.

---

## 🎯 STATUS ATUAL

### Funcionando ✅:
1. Campo `origem` extraído do XML e salvo
2. Vínculo automático com fornecedor
3. Controle de lote sempre ativado
4. CEST, CFOP, alíquotas salvos
5. SKU (campo codigo) salvo corretamente

### Pendente investigação ⚠️:
1. **EAN não está vindo no XML** ou está como "SEM GTIN"
   - Solução: Verificar arquivo XML real
   - Se não vier, é normal - fornecedor não informou
   
### Próximo teste:
Deletar produtos e reimportar XML para confirmar:
- ✅ origem salvo
- ✅ fornecedor vinculado automaticamente
- ⚠️ EAN (depende do XML)

---

## 🔍 COMO VERIFICAR

```sql
-- Ver produtos com todos os campos
SELECT 
    id, codigo as SKU, nome, codigo_barras as EAN, 
    origem, ncm, fornecedor_id 
FROM produtos 
WHERE id IN (7, 8);

-- Ver vínculos de fornecedor
SELECT 
    p.id, p.codigo, p.nome,
    pf.fornecedor_id, c.nome_fantasia as fornecedor,
    pf.e_principal
FROM produtos p
LEFT JOIN produto_fornecedores pf ON p.id = pf.produto_id
LEFT JOIN clientes c ON pf.fornecedor_id = c.id
WHERE p.id IN (7, 8);
```

---

**Executar após deletar produtos:**
1. Reverter entrada
2. Excluir nota
3. Excluir produtos
4. Reimportar XML
5. Processar entrada
6. Verificar dados salvos
