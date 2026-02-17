# 📊 ANÁLISE COMPLETA - IMPORTAÇÃO SIMPLESVET

## 🎯 OBJETIVO
Importar dados do sistema SimplesVet para o novo sistema, preservando:
- Históricos completos de vendas 
- Relacionamentos cliente-animal-vendas
- Dados veterinários (vacinas, exames, atendimentos)
- Histórico financeiro dos clientes
- Produtos vendidos

## 📈 VOLUMES DE DADOS (SimplesVet)

| Tabela | Registros | Prioridade |
|--------|-----------|------------|
| **VENDAS** | | |
| eco_venda | ~99.032 | ALTA ⭐⭐⭐ |
| eco_venda_produto | ~174.564 | ALTA ⭐⭐⭐ |
| eco_vendabaixa | ~97.531 | ALTA ⭐⭐⭐ |
| **CADASTROS** | | |
| glo_pessoa | ~10.009 | ALTA ⭐⭐⭐ |
| vet_animal | ~1.682 | ALTA ⭐⭐⭐ |
| eco_produto | ~6.361 | ALTA ⭐⭐⭐ |
| eco_fornecedor | ? | MÉDIA ⭐⭐ |
| **COMPRAS** | | |
| eco_compra | ~1.588 | MÉDIA ⭐⭐ |
| eco_compra_produto | ? | MÉDIA ⭐⭐ |
| **VETERINÁRIO** | | |
| vet_animalatendimento | 55 | ALTA ⭐⭐⭐ |
| vet_animal_vacina | 637 | ALTA ⭐⭐⭐ |
| vet_animalexame | 35 | ALTA ⭐⭐⭐ |
| vet_animalpeso | 76 | MÉDIA ⭐⭐ |
| vet_agenda | 80 | BAIXA ⭐ |
| **FINANCEIRO** | | |
| glo_pessoadebito | 32 | ALTA ⭐⭐⭐ |
| fin_lancamento | >50MB | N/A (muito grande) |
| **CADASTROS BASE** | | |
| vet_especie | 13 | ALTA ⭐⭐⭐ |
| vet_raca | ~150 | ALTA ⭐⭐⭐ |
| eco_marca | ? | MÉDIA ⭐⭐ |
| eco_tipoproduto | ? | MÉDIA ⭐⭐ |
| fin_categoria | 72 | BAIXA ⭐ |

---

## 🗂️ MAPEAMENTO: SimplesVet → Sistema Novo

### 1️⃣ CLIENTES (glo_pessoa → clientes)

#### SimplesVet (glo_pessoa):
```csv
pes_int_codigo, pes_var_nome, pes_var_chave, pes_var_sexo, 
pes_var_rg, pes_var_cpf, pes_var_aniversario, pes_txt_observacao,
end_var_cep, end_var_endereco, end_var_numero, end_var_complemento,
end_var_bairro, end_var_uf, end_var_municipio,
pes_dec_totalcompra, pes_dec_maiorcompra, pes_dat_primeiracompra,
pes_dat_ultimacompra, pes_dec_saldoaberto, pes_dec_ticketmedio
```

#### Nosso Sistema (clientes):
```python
id, user_id, codigo, nome, cpf, telefone, celular, email,
cep, endereco, numero, complemento, bairro, cidade, estado,
observacoes, ativo, credito, created_at, updated_at
```

#### ✅ Mapeamento:
- `pes_int_codigo` → Campo de referência para vincular vendas
- `pes_var_nome` → `nome` ✅
- `pes_var_chave` → `codigo` ✅ (identificador único)
- `pes_var_cpf` → `cpf` ✅
- `pes_txt_observacao` → `observacoes` ✅
- `end_var_cep` → `cep` ✅
- `end_var_endereco` → `endereco` ✅
- `end_var_numero` → `numero` ✅
- `end_var_complemento` → `complemento` ✅
- `end_var_bairro` → `bairro` ✅
- `end_var_municipio` → `cidade` ✅
- `end_var_uf` → `estado` ✅
- `pes_dat_primeiracompra` → `created_at` ✅
- `pes_dat_ultimacompra` → Histórico (campo informativo)
- `pes_dec_saldoaberto` → `credito` (se negativo) ⚠️
- `pes_dec_totalcompra`, `pes_dec_ticketmedio` → **Calculado dinamicamente** a partir das vendas

---

### 2️⃣ ANIMAIS (vet_animal → pets)

#### SimplesVet (vet_animal):
```csv
ani_int_codigo, ani_var_chave, pes_int_codigo, pes_var_nome,
ani_var_nome, ani_var_sexo, ani_var_esterilizacao, ani_var_morto,
esp_var_nome, esp_int_codigo, rac_int_codigo, rac_var_nome,
pel_int_codigo, pel_var_nome, ani_dat_nascimento, ani_var_chip,
ani_dec_peso, ani_dat_peso
```

#### Nosso Sistema (pets):
```python
id, cliente_id, user_id, codigo, nome, especie, raca, sexo, castrado,
data_nascimento, peso, cor, cor_pelagem, porte, microchip,
alergias, doencas_cronicas, observacoes, foto_url, ativo
```

#### ✅ Mapeamento:
- `ani_int_codigo` → Campo de referência
- `ani_var_chave` → `codigo` ✅
- `pes_int_codigo` → `cliente_id` (via lookup) ✅
- `ani_var_nome` → `nome` ✅
- `esp_var_nome` → `especie` ✅
- `rac_var_nome` → `raca` ✅
- `ani_var_sexo` → `sexo` ✅
- `ani_var_esterilizacao` → `castrado` ✅
- `ani_dat_nascimento` → `data_nascimento` ✅
- `ani_var_chip` → `microchip` ✅
- `ani_dec_peso` → `peso` ✅
- `pel_var_nome` → `cor` ou `cor_pelagem` ✅

---

### 3️⃣ PRODUTOS (eco_produto → produtos)

#### SimplesVet (eco_produto):
```csv
pro_int_codigo, pro_var_chave, pro_var_nome, pro_cha_tipo,
tpr_int_codigo, tpr_var_nome, mar_int_codigo, mar_var_nome,
pro_var_controlaestoque, pro_var_status, pro_var_unidade,
pro_dec_custo, pro_dec_preco, pro_var_codigobarra,
pro_var_codigoncm, pro_dec_estoque, pro_dec_minimo, pro_dec_maximo
```

#### Nosso Sistema (produtos):
```python
id, codigo, nome, tipo, situacao, preco_custo, preco_venda,
codigo_barras, estoque_atual, estoque_minimo, estoque_maximo,
categoria_id, marca_id, fornecedor_id
```

#### ✅ Mapeamento:
- `pro_int_codigo` → Campo de referência
- `pro_var_chave` → `codigo` ✅
- `pro_var_nome` → `nome` ✅
- `pro_cha_tipo` → `tipo` (P=produto, S=serviço) ✅
- `tpr_var_nome` → `categoria` (criar categoria) ✅
- `mar_var_nome` → `marca` (criar marca) ✅
- `pro_var_status` → `situacao` ✅
- `pro_var_unidade` → campo informativo
- `pro_dec_custo` → `preco_custo` ✅
- `pro_dec_preco` → `preco_venda` ✅
- `pro_var_codigobarra` → `codigo_barras` ✅
- `pro_dec_estoque` → `estoque_atual` ✅
- `pro_dec_minimo` → `estoque_minimo` ✅
- `pro_dec_maximo` → `estoque_maximo` ✅

---

### 4️⃣ VENDAS (eco_venda → vendas)

#### SimplesVet (eco_venda):
```csv
ven_int_codigo, ven_var_chave, pes_int_codigo, pes_var_nome,
ani_int_codigo, ani_var_nome, usu_int_codigo, usu_var_nome,
ven_dat_data, ven_dec_bruto, ven_var_tipodesconto,
ven_dec_descontopercentual, ven_dec_descontovalor,
ven_dec_liquido, ven_dat_pagamento, ven_dec_pago,
ven_var_status, ven_txt_observacao
```

#### Nosso Sistema (vendas):
```python
id, numero_venda, cliente_id, vendedor_id, subtotal,
desconto_valor, desconto_percentual, total,
observacoes, status, data_venda, data_finalizacao
```

#### ✅ Mapeamento:
- `ven_int_codigo` → Campo de referência
- `ven_var_chave` → `numero_venda` (adaptar formato) ✅
- `pes_int_codigo` → `cliente_id` (via lookup) ✅
- `usu_int_codigo` → `vendedor_id` (criar/mapear usuário) ✅
- `ven_dat_data` → `data_venda` ✅
- `ven_dec_bruto` → `subtotal` ✅
- `ven_dec_descontovalor` → `desconto_valor` ✅
- `ven_dec_descontopercentual` → `desconto_percentual` ✅
- `ven_dec_liquido` → `total` ✅
- `ven_var_status` → `status` (mapear: Baixado→finalizada, Aberto→aberta) ✅
- `ven_dat_pagamento` → `data_finalizacao` ✅
- `ven_txt_observacao` → `observacoes` ✅

---

### 5️⃣ ITENS DA VENDA (eco_venda_produto → venda_items)

#### SimplesVet (eco_venda_produto):
```csv
vpr_int_codigo, ven_int_codigo, ven_var_chave,
pro_int_codigo, pro_var_nome, vpr_dec_quantidade,
vpr_dec_preco
```

#### Nosso Sistema (venda_items):
```python
id, venda_id, produto_id, quantidade, preco_unitario,
preco_total, desconto
```

#### ✅ Mapeamento:
- `ven_int_codigo` → `venda_id` (via lookup) ✅
- `pro_int_codigo` → `produto_id` (via lookup) ✅
- `vpr_dec_quantidade` → `quantidade` ✅
- `vpr_dec_preco` → `preco_unitario` ✅
- `quantidade * preco` → `preco_total` (calcular) ✅

---

### 6️⃣ DÉBITOS EM ABERTO (glo_pessoadebito)

#### SimplesVet (glo_pessoadebito):
```csv
pes_int_codigo, pes_var_nome, pes_var_chave,
pes_dat_ultimacompra, pes_dec_saldoaberto,
pes_txt_celularlista, pes_txt_emaillista
```

#### ✅ Como Tratar:
- Criar observação no cadastro do cliente com o débito
- OU criar lançamento manual de "Débito Anterior" no financeiro
- 32 clientes apenas (volume baixo)

---

### 7️⃣ HISTÓRICOS VETERINÁRIOS

#### ✅ Vacinas (vet_animal_vacina):
- Criar tabela `historico_vacinas` ou usar campo JSON no pet
- Campos: data, vacina, laboratório, lote, status

#### ✅ Exames (vet_animalexame):
- Criar tabela `historico_exames` ou usar campo JSON no pet
- Campos: data, exame, observações

#### ✅ Atendimentos (vet_animalatendimento):
- Criar tabela `atendimentos_veterinarios`
- Campos: data, descrição (HTML), tipo_atendimento, veterinário

#### ✅ Pesos (vet_animalpeso):
- Criar tabela `historico_peso` ou campo JSON
- Campos: data, peso, observação

---

## 🔄 ESTRATÉGIA DE IMPORTAÇÃO

### FASE 1: Cadastros Base (sem dependências)
```
1. Espécies (vet_especie) → 13 registros
2. Raças (vet_raca) → ~150 registros
3. Marcas (eco_marca)
4. Tipos de Produto (eco_tipoproduto)
5. Formas de Pagamento (fin_formapagamento)
```

### FASE 2: Entidades Principais
```
6. Clientes (glo_pessoa → clientes) → ~10.000 registros
   - Mapear CPF, telefone, endereço
   - Criar código único
   - Importar observações
   
7. Produtos (eco_produto → produtos) → ~6.361 registros
   - Criar marcas e categorias primeiro
   - Mapear preços e estoque
   - Importar código de barras
```

### FASE 3: Relacionamentos Diretos
```
8. Animais/Pets (vet_animal → pets) → ~1.682 registros
   - Vincular com cliente (via pes_int_codigo)
   - Mapear espécie e raça
   - Importar dados de saúde
```

### FASE 4: Históricos Veterinários (Opcional - criar tabelas novas)
```
9. Vacinas aplicadas (vet_animal_vacina) → 637 registros
10. Exames realizados (vet_animalexame) → 35 registros
11. Histórico de peso (vet_animalpeso) → 76 registros
12. Atendimentos (vet_animalatendimento) → 55 registros
```

### FASE 5: Transações Comerciais ⭐⭐⭐ CRÍTICO
```
13. Vendas (eco_venda → vendas) → ~99.000 registros
    - Vincular cliente
    - Mapear data e valores
    - Status (baixado/aberto)
    
14. Itens da Venda (eco_venda_produto → venda_items) → ~174.000 registros
    - Vincular venda
    - Vincular produto
    - Quantidade e preço
    
15. Baixas/Pagamentos (eco_vendabaixa → venda_pagamentos) → ~97.000 registros
    - Data de pagamento
    - Valor pago
```

### FASE 6: Contas em Aberto
```
16. Débitos (glo_pessoadebito) → 32 registros
    - Criar observação no cliente
    - OU criar lançamento financeiro manual
```

---

## 🎯 TESTE CONTROLADO (20 REGISTROS)

Para validar o processo, vamos importar **AMOSTRA PEQUENA**:

```python
LIMITES_TESTE = {
    'especies': 13,        # TODOS (volume pequeno)
    'racas': 50,           # Primeiros 50
    'clientes': 20,        # Primeiros 20 clientes
    'produtos': 20,        # Primeiros 20 produtos
    'pets': 10,            # Primeiros 10 pets
    'vendas': 10,          # Primeiras 10 vendas
    'itens_venda': 'ALL',  # Todos os itens das 10 vendas
}
```

### ✅ Validações do Teste:
1. **Clientes importados corretamente?**
   - Nome, CPF, telefone, endereço
   - Código único funcionando
   
2. **Produtos com preços e estoque?**
   - Custo e venda corretos
   - Estoque atual preservado
   
3. **Pets vinculados ao tutor certo?**
   - Relação cliente_id correta
   - Espécie e raça corretas
   
4. **Vendas amarradas?**
   - Cliente vinculado
   - Itens da venda corretos
   - Valores batendo (subtotal, desconto, total)
   - Status correto
   
5. **Histórico visível no sistema?**
   - Vendas aparecem na tela do cliente
   - Produtos vendidos aparecem
   - Valores e datas corretos

---

## ⚠️ DESAFIOS E SOLUÇÕES

### 1. **Arquivo fin_lancamento.csv muito grande (>50MB)**
❌ **Problema**: Não conseguimos abrir/processar
✅ **Solução**: Ignorar e recalcular a partir das vendas

### 2. **Códigos de cliente/produto diferentes**
❌ **Problema**: SimplesVet usa `pes_var_chave`, `pro_var_chave`
✅ **Solução**: Criar mapeamento de conversão e manter campo `codigo` para busca

### 3. **Usuário vendedor não existe no novo sistema**
❌ **Problema**: `usu_int_codigo` pode não existir
✅ **Solução**: Criar usuário "Importado" ou mapear para admin

### 4. **Vendas com animal vinculado**
⚠️ **Atenção**: SimplesVet vincula venda diretamente ao animal
✅ **Solução**: Nosso sistema não tem esse campo (adicionar ou ignorar)

### 5. **Saldo em aberto (débito)**
❌ **Problema**: 32 clientes têm débito em aberto
✅ **Solução**: Criar observação ou lançamento manual "Débito Anterior"

### 6. **Históricos veterinários (vacinas, exames)**
⚠️ **Atenção**: Nosso sistema pode não ter essas tabelas
✅ **Solução**: Criar tabelas novas ou campo JSON no pet

---

## 📊 CAMPOS CALCULADOS (não importar)

Esses campos do SimplesVet **NÃO devem ser importados**, pois são calculados:
- `pes_dec_totalcompra` → Calcula a partir das vendas
- `pes_dec_maiorcompra` → Calcula a partir das vendas
- `pes_dec_ticketmedio` → Calcula a partir das vendas

---

## 🚀 PRÓXIMOS PASSOS

1. ✅ **Análise completa** (este documento)
2. ⏭️ **Criar script de importação modular**
3. ⏭️ **Testar com 20 registros em DEV**
4. ⏭️ **Validar dados importados**
5. ⏭️ **Ajustar e refinar**
6. ⏭️ **Importação completa em DEV**
7. ⏭️ **Validação final e testes**
8. ⏭️ **Importação em PRODUÇÃO** (se aprovado)

---

## 📝 OBSERVAÇÕES IMPORTANTES

1. **Preservar dados originais**: Sempre manter referência ao ID original
2. **Timestamps**: Usar datas originais quando disponíveis
3. **Validações**: CPF, telefone, email (limpar dados inválidos)
4. **Transações**: Importar vendas em transações (rollback se erro)
5. **Log detalhado**: Registrar tudo que foi importado/ignorado
6. **Backup antes**: SEMPRE fazer backup antes de importar

---

**Data da Análise**: 12/02/2026  
**Sistema de Origem**: SimplesVet  
**Sistema de Destino**: Sistema Pet (FastAPI + PostgreSQL)
