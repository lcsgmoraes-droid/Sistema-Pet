# ✅ CHECKLIST DE VALIDAÇÃO - IMPORTAÇÃO SIMPLESVET

## 📊 Dados Importados (Teste com 20 registros)

### Resumo da Importação
- ✅ **Espécies**: 10/11 (91%) - 1 registro com nome NULL
- ✅ **Raças**: 20/20 (100%)
- ✅ **Clientes**: 18/20 (90%) - 2 registros com erros
- ✅ **Produtos**: 20/20 (100%)
- ⚠️ **Pets**: 2/20 (10%) - 18 registros sem tutor nos 20 clientes importados
- ✅ **Vendas**: 20/20 (100%)
- ⚠️ **Itens de Venda**: Dependem de produtos não importados

---

## 🔍 1. VALIDAÇÃO NO BANCO DE DADOS (PostgreSQL)

### 1.1 Conectar ao Banco DEV
```bash
# PowerShell
$env:PGPASSWORD='devpass123'
psql -h localhost -p 5433 -U petshop_dev -d petshop_dev
```

### 1.2 Queries de Validação

#### **ESPÉCIES**
```sql
-- Listar espécies importadas
SELECT id, nome, ativo, created_at 
FROM especies 
ORDER BY nome;

-- Total: deve mostrar 10 espécies
SELECT COUNT(*) FROM especies;
```
✅ **Espere ver**: Avícola, Bovinos, Canina, Cunícula, Equina, Exótico, Felina, Outras, Primatas, Roedor

---

#### **RAÇAS**
```sql
-- Listar raças com suas espécies
SELECT r.id, r.nome as raca, e.nome as especie
FROM racas r
JOIN especies e ON r.especie_id = e.id
ORDER BY e.nome, r.nome
LIMIT 20;

-- Total importado
SELECT COUNT(*) FROM racas;
```
✅ **Espere ver**: Calopsita (Avícola), Affenpinscher (Canina), etc.

---

#### **CLIENTES**
```sql
-- Listar clientes importados
SELECT id, codigo, nome, cpf, telefone, celular, cidade, estado
FROM clientes
WHERE codigo IN ('9923', '3723', '4060', '1743', '2731', '6220', '1773', '7202', '1250', '8083')
ORDER BY nome
LIMIT 20;

-- Total importado
SELECT COUNT(*) FROM clientes WHERE codigo LIKE '%';

-- Verificar endereços completos
SELECT nome, endereco, numero, bairro, cidade, estado, cep
FROM clientes
WHERE codigo = '9923';
```
✅ **Espere ver**: 
- **+ Q Racao** (#9923)
- **Abdo Tohme** (#3723)  
- **Abenor Fernandes** (#4060)
- Endereços com CEP, cidade, estado completos

---

#### **PRODUTOS**
```sql
-- Listar produtos importados
SELECT id, codigo, nome, tipo, preco_venda, estoque_atual, situacao
FROM produtos
WHERE codigo IN ('3465', '1635', '1630', '991', '6041', '1636', '997', '6040')
ORDER BY nome
LIMIT 20;

-- Verificar tipos (produto vs serviço)
SELECT tipo, COUNT(*) 
FROM produtos 
GROUP BY tipo;

-- Verificar preços
SELECT codigo, nome, preco_custo, preco_venda
FROM produtos
WHERE codigo = '3465';
```
✅ **Espere ver**:
- **Abajour Para Hamster** (#3465)
- **Acessorios 800** (#1635)
- Preços de custo e venda preenchidos

---

#### **PETS**
```sql
-- Listar pets importados
SELECT p.id, p.codigo, p.nome, p.especie, p.raca, p.sexo, 
       c.nome as tutor, c.codigo as codigo_tutor
FROM pets p
JOIN clientes c ON p.cliente_id = c.id
ORDER BY p.created_at DESC
LIMIT 20;

-- Verificar relação com tutores
SELECT 
    c.nome as tutor,
    COUNT(p.id) as total_pets
FROM clientes c
LEFT JOIN pets p ON c.id = p.cliente_id
GROUP BY c.nome
HAVING COUNT(p.id) > 0
ORDER BY  total_pets DESC;
```
✅ **Espere ver**: Poucos pets (apenas os que têm tutores nos 20 clientes importados)

---

#### **VENDAS**
```sql
-- Listar vendas importadas
SELECT 
    v.id, 
    v.numero_venda, 
    v.data_venda,
    v.subtotal, 
    v.desconto_valor,
    v.total,
    v.status,
    c.nome as cliente
FROM vendas v
LEFT JOIN clientes c ON v.cliente_id = c.id
WHERE v.numero_venda LIKE 'IMP-%'
ORDER BY v.data_venda
LIMIT 20;

-- Verificar totais
SELECT 
    status,
    COUNT(*) as qtd_vendas,
    SUM(total) as total_vendas
FROM vendas
WHERE numero_venda LIKE 'IMP-%'
GROUP BY status;

-- Vendas por data
SELECT 
    DATE(data_venda) as data,
    COUNT(*) as qtd,
    SUM(total) as total
FROM vendas
WHERE numero_venda LIKE 'IMP-%'
GROUP BY DATE(data_venda)
ORDER BY data;
```
✅ **Espere ver**:
- **IMP-20190517-1**: R$ 2,50
- **IMP-20190518-2**: R$ 34,20
- **IMP-20190519-3**: R$ 4,00
- Status: **finalizada**
- Datas: **Maio/Junho 2019**

---

#### **ITENS DE VENDA**
```sql
-- Listar itens das vendas importadas
SELECT 
    vi.id,
    v.numero_venda,
    p.nome as produto,
    vi.quantidade,
    vi.preco_unitario,
    vi.preco_total
FROM vendas_itens vi
JOIN vendas v ON vi.venda_id = v.id
JOIN produtos p ON vi.produto_id = p.id
WHERE v.numero_venda LIKE 'IMP-%'
ORDER BY v.data_venda, vi.id
LIMIT 30;

-- Total de itens por venda
SELECT 
    v.numero_venda,
    COUNT(vi.id) as qtd_itens,
    SUM(vi.preco_total) as total
FROM vendas v
LEFT JOIN vendas_itens vi ON v.id = vi.venda_id
WHERE v.numero_venda LIKE 'IMP-%'
GROUP BY v.numero_venda
ORDER BY v.data_venda;
```

---

## 🖥️ 2. VALIDAÇÃO NO FRONTEND

### 2.1 Cadastros Base

#### **Espécies e Raças**
1. Acesse: http://localhost:8080/configuracoes/especies
2. ✅ Verifique se aparece: **Canina, Felina, Avícola, Roedor**, etc.
3. Clique em uma espécie (ex: Canina)
4. ✅ Verifique se aparecem raças: **Affenpinscher, Afghanhound, Airedale Terrier**, etc.

---

### 2.2 Clientes

#### **Lista de Clientes**
1. Acesse: http://localhost:8080/clientes
2. ✅ Procure por: **"+ Q Racao"**, **"Abdo Tohme"**, **"Abenor Fernandes"**
3. Clique em um cliente
4. ✅ Verifique:
   - Nome completo
   - CPF formatado (se houver)
   - Telefone/Celular
   - Endereço completo (Rua, Nº, Bairro, Cidade/UF, CEP)
   - Observações (se houver)

#### **Detalhes de Cliente Específico**
1. Busque cliente **"+ Q Racao"** (código #9923)
2. ✅ Verifique todos os campos preenchidos
3. ✅ Veja se há pets associados (provavelmente não, pois pet precisaria de mais clientes)

---

### 2.3 Produtos

#### **Lista de Produtos**
1. Acesse: http://localhost:8080/produtos
2. ✅ Procure por: **"Abajour Para Hamster"**, **"Acessorios 800"**, **"Adesivo"**
3. Clique em um produto
4. ✅ Verifique:
   - Código/SKU (ex: #3465)
   - Nome
   - Tipo (Produto ou Serviço)
   - Preço de custo
   - Preço de venda
   - Estoque atual/mínimo/máximo
   - Código de barras (se houver)
   - Status (Ativo/Inativo)

---

### 2.4 Pets

#### **Lista de Pets**
1. Acesse: http://localhost:8080/pets
2. ⚠️ **Espere ver**: Poucos ou nenhum pet (maioria falhou por falta de tutores)
3. Se houver pets:
   - ✅ Verifique espécie (Canina, Felina, etc.)
   - ✅ Verifique raça
   - ✅ Verifique tutor associado
   - ✅ Veja sexo, idade, peso, cor
   - ✅ Verifique status ativo (não morto)

---

### 2.5 Vendas

#### **Lista de Vendas**
1. Acesse: http://localhost:8080/vendas
2. ✅ Procure vendas com número: **IMP-20190517-**, **IMP-20190518-**, etc.
3. Clique em uma venda
4. ✅ Verifique:
   - Número da venda (ex: IMP-20190517-1)
   - Data da venda (Maio/Junho 2019)
   - Cliente (pode estar em branco se for venda avulsa)
   - Vendedor: **Admin** (user_id=1)
   - Status: **Finalizada**
   - Subtotal, Desconto, Total
   - Data de finalização
   - Observações (se houver)

#### **Itens da Venda**
1. Dentro de uma venda, role até **Itens**
2. ✅ Verifique:
   - Lista de produtos vendidos
   - Quantidade de cada item
   - Preço unitário
   - Preço total do item
   - Total da venda = soma dos itens - descontos

---

## 📋 3. VALIDAÇÃO DE INTEGRIDADE

### 3.1 Verificar Relacionamentos

```sql
-- Pets sem tutores (não deve ter)
SELECT p.* 
FROM pets p
LEFT JOIN clientes c ON p.cliente_id = c.id
WHERE c.id IS NULL;

-- Vendas sem cliente (OK para vendas avulsas)
SELECT v.numero_venda, v.total, v.cliente_id
FROM vendas v
WHERE v.numero_venda LIKE 'IMP-%'
  AND v.cliente_id IS NULL;

-- Itens de venda sem produto (não deve ter)
SELECT vi.* 
FROM vendas_itens vi
LEFT JOIN produtos p ON vi.produto_id = p.id
WHERE p.id IS NULL
  AND vi.venda_id IN (
    SELECT id FROM vendas WHERE numero_venda LIKE 'IMP-%'
  );
```

---

### 3.2 Verificar Valores Calculados

```sql
-- Total da venda = subtotal - desconto_valor
SELECT 
    numero_venda,
    subtotal,
    desconto_valor,
    total,
    (subtotal - desconto_valor) as total_calculado,
    CASE 
        WHEN ABS(total - (subtotal - desconto_valor)) < 0.01 THEN 'OK'
        ELSE 'ERRO'
    END as validacao
FROM vendas
WHERE numero_venda LIKE 'IMP-%';

-- Total de itens = soma dos itens da venda
SELECT 
    v.numero_venda,
    v.subtotal as total_venda,
    SUM(vi.preco_total) as total_itens,
    CASE 
        WHEN ABS(v.subtotal - SUM(vi.preco_total)) < 0.01 THEN 'OK'
        ELSE 'DIVERGENTE'
    END as validacao
FROM vendas v
JOIN vendas_itens vi ON v.id = vi.venda_id
WHERE v.numero_venda LIKE 'IMP-%'
GROUP BY v.id, v.numero_venda, v.subtotal;
```

---

### 3.3 Verificar Mapeamento de IDs

```sql
-- Verificar se código antigo foi preservado
SELECT 
    'Clientes' as tabela,
    COUNT(DISTINCT codigo) as total_codigos
FROM clientes
UNION ALL
SELECT 'Produtos', COUNT(DISTINCT codigo) FROM produtos
UNION ALL
SELECT 'Pets', COUNT(DISTINCT codigo) FROM pets;
```

---

## ❗ 4. PROBLEMAS CONHECIDOS E ESPERADOS

### 4.1 Pets com Baixa Taxa de Importação (10%)
- **Causa**: Pet precisa ter tutor (cliente) importado
- **Solução para importação completa**: Importar TODOS os clientes primeiro (--limite sem restrição)

### 4.2 Itens de Venda com 0% Importados
- **Causa**: Produtos dos itens não estão no lote de 20 produtos importados
- **Solução**: Importar TODOS os produtos primeiro

### 4.3 Vendas Sem Cliente (NULL)
- **Esperado**: Vendas avulsas (sem cliente associado no sistema antigo)
- **Não é erro**: Sistema novo suporta vendas sem cliente

### 4.4 Espécie/Raça Duplicadas
- **Causa**: Sistema antigo e novo podem ter cadastros pré-existentes
- **Solução**: Script já verifica duplicatas por nome antes de inserir

---

## 🚀 5. PRÓXIMOS PASSOS - IMPORTAÇÃO COMPLETA

### Para importar TODOS os dados do SimplesVet:

```bash
# 1. Limpar dados de teste (opcional)
python backend/importar_simplesvet.py --limpar

# 2. Importar tudo sem limite
python backend/importar_simplesvet.py --all

# Ou por fases:
python backend/importar_simplesvet.py --fase 1  # Espécies e Raças
python backend/importar_simplesvet.py --fase 2  # Clientes e Produtos (demora mais)
python backend/importar_simplesvet.py --fase 3  # Pets
python backend/importar_simplesvet.py --fase 4  # Vendas e Itens
```

### Volumes Esperados (Importação Completa):
- 📊 **Espécies**: ~11
- 📊 **Raças**: ~150
- 📊 **Clientes**: ~10.000
- 📊 **Produtos**: ~6.361
- 📊 **Pets**: ~1.682
- 📊 **Vendas**: ~99.032
- 📊 **Itens de Venda**: ~174.562

**Tempo Estimado**: 30-60 minutos (depende do hardware)

---

## ✅ 6. CHECKLIST FINAL AFTER FULL IMPORT

Após importação completa, verificar:

- [ ] Total de clientes >= 10.000
- [ ] Total de produtos >= 6.000
- [ ] Total de pets >= 1.500
- [ ] Total de vendas >= 90.000
- [ ] Total de itens de venda >= 170.000
- [ ] CPFs formatados corretamente (###.###.###-##)
- [ ] Telefones formatados corretamente
- [ ] Endereços completos (CEP, Cidade, Estado)
- [ ] Preços de produtos > 0
- [ ] Estoque de produtos >= 0
- [ ] Vendas finalizadas têm data_finalizacao
- [ ] Relações Pet ↔ Cliente corretas
- [ ] Relações Venda ↔ Cliente corretas
- [ ] Relações VendaItem ↔ Produto corretas
- [ ] Frontend exibe todos os dados corretamente
- [ ] Busca de clientes funciona
- [ ] Filtros de produtos funcionam
- [ ] Histórico de vendas completo

---

## 📞 Em caso de problemas:

1. Verifique os logs do script de importação
2. Revise [ANALISE_IMPORTACAO_SIMPLESVET.md](./ANALISE_IMPORTACAO_SIMPLESVET.md)
3. Consulte [GUIA_IMPORTACAO.md](./GUIA_IMPORTACAO.md)
4. Execute queries de validação acima para identificar inconsistências
