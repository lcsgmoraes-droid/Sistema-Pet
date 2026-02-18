# Guia de Importação de Produtos - Modo Seguro

## 📋 O que foi melhorado?

### 1. Validação Rigorosa de SKU
- **Antes**: Importava produtos sem SKU
- **Agora**: Recusa produtos com SKU vazio/nulo
- **Motivo**: Evita produtos com SKUs gerados automaticamente (ex: 150.010.005.007)

### 2. Relatório de Não Importados
- Gera arquivo CSV com todos os produtos que **NÃO** foram importados
- Inclui motivo de cada rejeição:
  - `SEM_SKU` - Produto sem código/SKU
  - `DUPLICADO` - SKU já existe no banco
  - `INVALIDO` - Outro erro de validação

### 3. Estatísticas Detalhadas
- Total processados
- Válidos / Inválidos
- Quantidade sem SKU
- Duplicados
- Importados com sucesso

---

## 🚀 Como usar

### Passo 1: Testar em DEV (ambiente local)

```bash
cd backend

# Simular importação (não grava nada)
python importador_produtos.py --dry-run --limite 100

# Importar apenas 50 produtos de teste
python importador_produtos.py --limite 50

# Importar todos (cuidado!)
python importador_produtos.py
```

### Passo 2: Verificar arquivos gerados

Após executar, verifique a pasta `backend/logs_importacao/`:

1. **Log principal**: `importacao_produtos_YYYYMMDD_HHMMSS.log`
   - Mostra cada produto processado
   - Erros detalhados
   - Estatísticas finais

2. **Produtos não importados**: `nao_importados_YYYYMMDD_HHMMSS.csv`
   - Lista o que NÃO foi importado
   - Motivo de cada rejeição
   - Use para corrigir dados no SimplesVet

### Passo 3: Importar para PRODUÇÃO (cuidado!)

**ANTES de importar para produção:**
1. Configure as variáveis em `importar_producao_lotes.py`:
   ```python
   DATABASE_URL_PROD = "postgresql://postgres:senha@ip:porta/banco"
   TENANT_ID_PROD = "seu-tenant-id-uuid"
   ```

2. Execute o script interativo:
   ```bash
   python importar_producao_lotes.py
   ```

3. Escolha opção 1 (simulação) primeiro!

4. Depois, opção 2 para importar de verdade

---

## 📊 Exemplo de Saída

```
RELATÓRIO FINAL DE IMPORTAÇÃO
================================================================================

PRODUTOS:
  Total processados: 100
  Válidos:          85 (85.0%)
  Inválidos:        15
    - Sem SKU:       8
  Duplicados:       0
  Importados:       85
  NÃO Importados:   15

Arquivo de produtos NÃO importados: logs_importacao/nao_importados_20260218_143020.csv

Erros encontrados: 15
Primeiros 10 erros:
  - Linha 12: SKU_VAZIO: Produto sem código/SKU (pro_var_chave vazio)
  - Linha 23: SKU_VAZIO: Produto sem código/SKU (pro_var_chave vazio)
  ...
```

---

## 🔍 Verificando produtos não importados

Abra o arquivo CSV gerado:

| linha | sku | nome | motivo | erro |
|-------|-----|------|--------|------|
| 12 | | Produto Teste | SEM_SKU | SKU_VAZIO: Produto sem código/SKU |
| 45 | 5907 | Special Dog 10kg | DUPLICADO | |
| 78 | | Outro produto | SEM_SKU | SKU_VAZIO: Produto sem código/SKU |

**O que fazer:**
1. Produtos `SEM_SKU`: Cadastrar SKU no SimplesVet antes de reimportar
2. Produtos `DUPLICADO`: Já estão no sistema, pode ignorar
3. Produtos `INVALIDO`: Verificar erro específico na coluna "erro"

---

## ⚠️ Importante

- **SEMPRE** teste com `--dry-run` primeiro
- **SEMPRE** use `--limite` ao testar
- **Verifique** o arquivo de não importados
- **Corrija** dados no SimplesVet antes de reimportar
- **Faça backup** do banco antes de importação grande

---

## 🐛 Problemas comuns

### Problema: Muitos produtos sem SKU
**Solução**: Corrigir no SimplesVet ou aceitar que não serão importados

### Problema: SKUs duplicados
**Solução**: Normal, produtos já importados anteriormente

### Problema: Erro de conexão
**Solução**: Verificar DATABASE_URL e se o PostgreSQL está rodando

---

## 📞 Dúvidas?

Consulte os logs em `backend/logs_importacao/` para detalhes completos.
