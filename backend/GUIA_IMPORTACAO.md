# 🔄 GUIA DE IMPORTAÇÃO - SimplesVet

## 📋 Pré-requisitos

1. ✅ Backup do SimplesVet em: `C:\Users\Lucas\Downloads\simplesvet\banco`
2. ✅ Ambiente de **DEV** rodando (docker-compose-local-dev.yml)
3. ✅ Banco de dados PostgreSQL funcionando
4. ✅ Usuário admin criado no sistema

---

## 🚀 Como Usar

### 1️⃣ Preparação

```bash
# Entrar na pasta do backend
cd backend

# Ativar ambiente virtual (se necessário)
# venv\Scripts\activate

# Verificar conexão com banco
python -c "from app.db.session import SessionLocal; db = SessionLocal(); print('✅ Conexão OK')"
```

### 2️⃣ Teste com 20 Registros (RECOMENDADO)

```bash
# Importar TODAS as fases com limite de 20 registros
python importar_simplesvet.py --all --limite 20
```

**O que será importado:**
- 13 espécies (todas)
- 20 raças
- 20 clientes
- 20 produtos
- 10 pets
- 10 vendas
- Itens das 10 vendas

### 3️⃣ Importação Por Fase (Controlada)

```bash
# Fase 1: Cadastros Base (espécies e raças)
python importar_simplesvet.py --fase 1 --limite 20

# Fase 2: Clientes e Produtos
python importar_simplesvet.py --fase 2 --limite 20

# Fase 3: Pets (animais)
python importar_simplesvet.py --fase 3 --limite 20

# Fase 4: Vendas e Itens
python importar_simplesvet.py --fase 4 --limite 20
```

### 4️⃣ Importação Completa (SEM LIMITE)

⚠️ **CUIDADO**: Importa TUDO (99mil vendas, 10mil clientes, etc)

```bash
# Remover o --limite para importar tudo
python importar_simplesvet.py --all
```

---

## 📊 Validações Após Importação

### 1. Verificar Clientes

```sql
-- No PostgreSQL (DEV)
SELECT COUNT(*) FROM clientes WHERE codigo IS NOT NULL;  -- Deve ter 20

SELECT id, codigo, nome, cpf, cidade 
FROM clientes 
WHERE codigo IS NOT NULL 
LIMIT 10;
```

### 2. Verificar Produtos

```sql
SELECT COUNT(*) FROM produtos WHERE created_at IS NOT NULL;  -- Deve ter 20

SELECT id, codigo, nome, preco_venda, estoque_atual
FROM produtos
LIMIT 10;
```

### 3. Verificar Pets

```sql
SELECT COUNT(*) FROM pets;  -- Deve ter 10

SELECT p.id, p.nome, p.especie, p.raca, c.nome as tutor
FROM pets p
JOIN clientes c ON p.cliente_id = c.id
LIMIT 10;
```

### 4. Verificar Vendas

```sql
SELECT COUNT(*) FROM vendas WHERE numero_venda LIKE 'IMP-%';  -- Deve ter 10

SELECT v.numero_venda, v.data_venda, v.total, v.status, c.nome as cliente
FROM vendas v
LEFT JOIN clientes c ON v.cliente_id = c.id
WHERE v.numero_venda LIKE 'IMP-%'
ORDER BY v.data_venda DESC
LIMIT 10;
```

SELECT v.numero_venda, SUM(vi.quantidade) as qtd_itens, SUM(vi.preco_total) as soma_itens
FROM vendas v
JOIN venda_items vi ON v.id = vi.venda_id
WHERE v.numero_venda LIKE 'IMP-%'
GROUP BY v.numero_venda
LIMIT 10;
```

---

## 📈 Visualizações no Sistema

### Testar no Frontend (DEV)

1. **Clientes**: `http://localhost:3000/clientes`
   - Deve listar clientes importados
   - CPF, telefone, endereço devem estar preenchidos
   - Código único funcionando

2. **Produtos**: `http://localhost:3000/produtos`
   - Deve listar produtos importados
   - Preço de custo e venda corretos
   - Estoque atual preservado

3. **Pets**: `http://localhost:3000/pets`
   - Deve listar pets importados
   - Vinculados ao tutor correto
   - Espécie e raça corretas

4. **Vendas**: `http://localhost:3000/vendas`
   - Deve listar vendas importadas (IMP-*)
   - Cliente vinculado
   - Itens da venda corretos
   - Total calculado corretamente

---

## ⚠️ Problemas Comuns

### Erro: "Arquivo não encontrado"
```
❌ Arquivo não encontrado: vet_especie.csv
```

**Solução**: Verificar caminho em `SIMPLESVET_PATH`
```python
# No arquivo importar_simplesvet.py (linha ~40)
SIMPLESVET_PATH = Path(r"c:\Users\Lucas\Downloads\simplesvet\banco")
```

### Erro: "USER_ID não configurado"
```
❌ user_id cannot be null
```

**Solução**: Configurar USER_ID no script
```python
# No arquivo importar_simplesvet.py (linha ~68)
USER_ID = 1  # ID do seu usuário admin
```

Para descobrir o ID:
```sql
SELECT id, username, email FROM users WHERE is_admin = true LIMIT 1;
```

### Erro: "Cliente não encontrado para pet"
```
⚠️ Cliente não encontrado para pet Thor
```

**Solução**: Importar clientes primeiro (Fase 2) antes de pets (Fase 3)

### Erro: "Duplicated key"
```
❌ duplicate key value violates unique constraint "produtos_codigo_key"
```

**Solução**: Produto já existe. Script ignora automaticamente.

---

## 🗑️ Limpar Importação (Recomeçar)

```sql
-- ⚠️ CUIDADO: Apaga TUDO importado
-- Execute somente em DEV

-- Apagar vendas importadas
DELETE FROM venda_items WHERE venda_id IN (
    SELECT id FROM vendas WHERE numero_venda LIKE 'IMP-%'
);
DELETE FROM vendas WHERE numero_venda LIKE 'IMP-%';

-- Apagar pets importados
DELETE FROM pets WHERE codigo IS NOT NULL AND created_at < NOW();

-- Apagar produtos importados
DELETE FROM produtos WHERE created_at < NOW();

-- Apagar clientes importados
DELETE FROM clientes WHERE codigo IS NOT NULL;

-- Apagar espécies e raças
DELETE FROM racas;
DELETE FROM especies;

-- Resetar sequences (opcional)
-- ALTER SEQUENCE vendas_id_seq RESTART WITH 1;
-- ALTER SEQUENCE clientes_id_seq RESTART WITH 1;
-- etc...
```

---

## 📝 Logs da Importação

O script exibe logs detalhados:

```
[14:30:15] 🚀 IMPORTAÇÃO SIMPLESVET
[14:30:15] ℹ️  Limite de registros: 20
[14:30:15] ℹ️  ═══ FASE 1.1 - ESPÉCIES ═══
[14:30:15] 📖 Lidos 13 registros de vet_especie.csv
[14:30:16] ✅ Espécie: Canina
[14:30:16] ✅ Espécie: Felina
...
[14:30:20] ℹ️  ✓ Espécies: 13/13
[14:30:20] ℹ️  ═══ FASE 1.2 - RAÇAS ═══
...
```

---

## 🎯 Próximos Passos

1. ✅ Testar com 20 registros
2. ✅ Validar dados no banco e frontend
3. ✅ Verificar relacionamentos (cliente-pet-venda)
4. ✅ Ajustar mapeamentos se necessário
5. ⏭️ Importação completa em DEV
6. ⏭️ Validação final
7. ⏭️ Importação em PRODUÇÃO (se aprovado)

---

## 📞 Suporte

- Documentação completa: `ANALISE_IMPORTACAO_SIMPLESVET.md`
- Script: `importar_simplesvet.py`
