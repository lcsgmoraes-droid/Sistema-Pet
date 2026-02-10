# 🧪 GUIA COMPLETO DE TESTES PRÉ-PRODUÇÃO
## Sistema Pet Shop Pro - Última Validação

---

## 🎯 O QUE VOCÊ PRECISA SABER

### Criei para você 3 ferramentas poderosas:

1. **📦 Testes E2E Automatizados** (`backend/tests/e2e_test_sistema_completo.py`)
   - **Faz TUDO automaticamente**
   - Testa os fluxos
   - Valida TODOS os efeitos colaterais
   - Você só vê os resultados

2. **🚀 Script Executor** (`EXECUTAR_TESTES_E2E.bat`)
   - Clique duplo e pronto!
   - Verifica se backend está rodando
   - Roda todos os testes
   - Mostra relatório detalhado

3. **✅ Checklist Manual** (`CHECKLIST_TESTES_PRE_PRODUCAO.md`)
   - Para você testar manualmente no navegador
   - Garante cobertura 100%
   - Documento oficial para assinar

---

## 🤖 TESTES AUTOMATIZADOS vs ✋ TESTES MANUAIS

### Quando usar AUTOMATIZADOS (Python/Pytest):
✅ **Validação rápida** - roda tudo em minutos  
✅ **Testes repetitivos** - toda vez que alterar código  
✅ **CI/CD** - rodar antes de cada deploy  
✅ **Validação técnica** - efeitos colaterais, cálculos  
✅ **Regressão** - garantir que nada quebrou  

### Quando usar MANUAIS (Navegador):
✅ **UX/UI** - aparência, layout, usabilidade  
✅ **Fluxos de usuário real** - clicar, digitar, ver  
✅ **Validação de negócio** - "faz sentido?"  
✅ **Aceitação do cliente** - mostrar funcionando  
✅ **Edge cases visuais** - mensagens de erro, alertas  

### 🎯 **RECOMENDAÇÃO**: Faça AMBOS!
1. **Automatizados primeiro** - validam a lógica
2. **Manuais depois** - validam a experiência

---

## 🚀 COMO EXECUTAR OS TESTES AUTOMATIZADOS

### Passo 1: Inicie o Backend
```batch
# Na raiz do projeto
INICIAR_DEV.bat

# OU, se preferir produção
INICIAR_PRODUCAO.bat
```

**Aguarde até ver**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Passo 2: Execute os Testes (3 opções)

#### Opção A: Clique Duplo no Script 🖱️ (MAIS FÁCIL)
```
EXECUTAR_TESTES_E2E.bat
```

#### Opção B: PowerShell Manual
```powershell
cd backend
pytest tests/e2e_test_sistema_completo.py -v -s
```

#### Opção C: VS Code Terminal
```bash
# Abra o terminal integrado (Ctrl + `)
cd backend
pytest tests/e2e_test_sistema_completo.py -v -s
```

### Passo 3: Leia os Resultados

#### ✅ Se TUDO PASSAR:
```
============================== 15 passed in 12.34s ==============================
✅ TODOS OS TESTES PASSARAM!
    Sistema pronto para produção! 🎉
```

**PARABÉNS! Sistema validado! 🎉**

#### ❌ Se ALGO FALHAR:
```
FAILED tests/e2e_test_sistema_completo.py::test_venda_dinheiro_completa
❌ Erro ao buscar contas a receber: 404 Not Found
```

**O QUE FAZER:**
1. Leia a mensagem de erro
2. Corrija o problema no código
3. Rode os testes novamente
4. Repita até tudo passar

---

## 📊 ENTENDENDO OS RESULTADOS

### Exemplo de Teste PASSANDO:
```
🧪 TESTE: Venda à Vista - Dinheiro
════════════════════════════════════════════════════════════════════════════
✅ Venda criada: ID 42
   Total: R$ 300.00
   Status: finalizada

📋 Validando efeitos colaterais...
✅ Contas a receber OK: 1 parcela(s), total R$ 300.00
✅ Fluxo de caixa OK: R$ 300.00 recebido
✅ DRE OK: Receita bruta R$ 300.00
✅ Estoque OK: 48 unidades

🎉 TESTE PASSOU! Todos os efeitos validados!
```

**Isso significa que:**
- ✅ Venda foi criada
- ✅ Conta a receber foi gerada E liquidada
- ✅ Dinheiro entrou no fluxo de caixa
- ✅ Receita foi registrada na DRE
- ✅ Estoque foi baixado (de 50 para 48)

### Exemplo de Teste FALHANDO:
```
🧪 TESTE: Venda Cartão Débito com Taxa
════════════════════════════════════════════════════════════════════════════
✅ Venda débito criada: ID 43
   Total: R$ 80.00
   Taxa esperada: R$ 1.60 (2% de R$ 80)

📋 Validando efeitos colaterais...
❌ Valor total das contas (80.00) diferente do esperado (78.40)

FAILED - Taxa não foi descontada!
```

**Problema identificado:**
❌ A taxa de 2% do débito não foi descontada  
❌ Deveria receber R$ 78,40 mas ficou R$ 80,00

**Onde corrigir:**
Provavelmente em `vendas_routes.py` ou `formas_pagamento_routes.py`

---

## 📋 TESTES MANUAIS - PASSO A PASSO

### 1. Abra o Sistema
```
http://localhost:5173  (Development)
OU
http://localhost:8000  (Backend direto)
```

### 2. Faça Login
```
Email: seu-email@teste.com
Senha: sua-senha
```

### 3. Siga o Checklist

Abra o arquivo:
```
CHECKLIST_TESTES_PRE_PRODUCAO.md
```

**Vá marcando cada item:**
- [ ] Item não testado
- [x] Item testado e OK
- [⚠] Item testado com problema

### 4. Anote TUDO

Para cada teste:
- ✅ O que funcionou
- ❌ O que falhou
- 📝 Valores testados
- 🐛 Bugs encontrados

### 5. Calcule a Taxa de Sucesso

```
Taxa = (Itens OK / Total de Itens) × 100%

Exemplo: 95 de 100 = 95% de sucesso
```

**Meta**: Mínimo 98% para produção

---

## 🎯 O QUE CADA TESTE VALIDA

### Venda à Vista (Dinheiro/PIX)
```python
Quando: Criar venda de R$ 100 em dinheiro
Então: 
  ✓ Venda criada com status "finalizada"
  ✓ 1 conta a receber criada
  ✓ Conta liquidada imediatamente
  ✓ R$ 100 no fluxo de caixa REALIZADO
  ✓ R$ 100 na receita bruta da DRE
  ✓ Estoque baixado
```

### Venda Débito com Taxa
```python
Quando: Criar venda de R$ 100 no débito (taxa 2%)
Então:
  ✓ Venda criada com total R$ 100
  ✓ 1 conta a receber de R$ 98 (100 - 2%)
  ✓ R$ 98 no fluxo de caixa
  ✓ R$ 100 na receita bruta da DRE
  ✓ R$ 2 em despesa com taxas na DRE
```

### Venda Parcelada 3x
```python
Quando: Criar venda de R$ 300 parcelada em 3x
Então:
  ✓ Venda criada
  ✓ 3 contas a receber criadas
  ✓ Cada conta com R$ 100
  ✓ Vencimentos: hoje+30, hoje+60, hoje+90
  ✓ Contas NÃO liquidadas
  ✓ NENHUM lançamento no fluxo de caixa
  ✓ R$ 300 na receita bruta da DRE (competência)
```

### Cancelamento de Venda
```python
Quando: Cancelar venda de R$ 100 (já finalizada)
Então:
  ✓ Status muda para "cancelada"
  ✓ Contas a receber canceladas
  ✓ Fluxo de caixa ESTORNADO (-R$ 100)
  ✓ DRE atualizada com cancelamento
  ✓ Estoque DEVOLVIDO
  ✓ Comissões estornadas
```

### Remover Item
```python
Quando: Venda com 3 itens (total R$ 300), remover 1 item (R$ 100)
Então:
  ✓ Venda fica com 2 itens
  ✓ Total recalculado para R$ 200
  ✓ Contas a receber ajustadas para R$ 200
  ✓ Estoque do item removido DEVOLVIDO
  ✓ DRE ajustada
```

---

## 🐛 PROBLEMAS COMUNS E SOLUÇÕES

### ❌ "Backend não está rodando"
**Solução:**
```batch
# Abra outro terminal e execute:
INICIAR_DEV.bat
```

### ❌ "Não foi possível autenticar"
**Solução:**
1. Verifique se o usuário existe
2. Se não, crie em `/auth/register`
3. Ou ajuste as credenciais em `e2e_test_sistema_completo.py`:
```python
TEST_USER = {
    "email": "seu-email@teste.com",
    "password": "SuaSenha123"
}
```

### ❌ "Erro ao criar produto: 500 Internal Server Error"
**Solução:**
1. Veja os logs do backend
2. Provavelmente falta campo obrigatório
3. Ou erro de banco de dados

### ❌ "Taxa não descontada corretamente"
**Solução:**
1. Verifique `formas_pagamento_routes.py`
2. Confirme que a taxa está configurada
3. Valide o cálculo: `valor_liquido = valor * (1 - taxa/100)`

### ❌ "Estoque não baixado"
**Solução:**
1. Verifique `vendas_routes.py` método de criar venda
2. Confirme que existe chamada ao `estoque_service`
3. Valide que o produto tem estoque disponível

---

## 📈 FLUXO RECOMENDADO DE TESTES

### Dia 1: Testes Automatizados
```
1. [X] Executar EXECUTAR_TESTES_E2E.bat
2. [X] Corrigir erros encontrados
3. [X] Rodar novamente até 100% passar
4. [X] Commit no git: "✅ Todos testes E2E passando"
```

### Dia 2: Testes Manuais - Cadastros
```
1. [ ] Clientes (física e jurídica)
2. [ ] Pets
3. [ ] Produtos (simples e variações)
4. [ ] Formas de pagamento
5. [ ] Abrir caixa
```

### Dia 3: Testes Manuais - Vendas
```
1. [ ] Venda dinheiro
2. [ ] Venda PIX
3. [ ] Venda débito
4. [ ] Venda crédito 2x, 3x, 6x
5. [ ] Venda com desconto
6. [ ] Venda com entrega
7. [ ] Venda com múltiplos pagamentos
```

### Dia 4: Testes Manuais - Operações
```
1. [ ] Cancelar venda
2. [ ] Reabrir venda
3. [ ] Remover item
4. [ ] Adicionar item
5. [ ] Fechar caixa
```

### Dia 5: Testes Manuais - Financeiro
```
1. [ ] Contas a receber
2. [ ] Contas a pagar
3. [ ] Fluxo de caixa
4. [ ] DRE
5. [ ] Comissões
6. [ ] Relatórios
```

### Dia 6: Edge Cases e Integrações
```
1. [ ] Teste limite (valores extremos)
2. [ ] Teste concorrência (2 vendas simultâneas)
3. [ ] Integração Bling
4. [ ] Integração Stone
5. [ ] WhatsApp
6. [ ] Emissão NF-e
```

### Dia 7: Homologação Final
```
1. [ ] Rodar TUDO de novo
2. [ ] Cliente testa e aprova
3. [ ] Backup completo
4. [ ] Deploy em produção
5. [ ] 🎉 SISTEMA NO AR!
```

---

## ✅ CRITÉRIOS DE APROVAÇÃO

### Para LIBERAR PRODUÇÃO, você precisa:

1. **Testes Automatizados**: 100% passando ✅
   ```
   pytest: 15/15 passed
   ```

2. **Testes Manuais**: Mínimo 98% de sucesso ✅
   ```
   95+ itens OK de 100 total
   ```

3. **Sem bugs críticos** ✅
   - ❌ Perda de dados
   - ❌ Cálculos errados
   - ❌ Estoque negativo
   - ❌ Duplicação de cobranças

4. **Performance OK** ✅
   - Lista de produtos: < 2s
   - Criar venda: < 1s
   - Relatórios: < 5s

5. **Backup testado** ✅
   - Backup funciona
   - Restore funciona
   - Dados íntegros

---

## 📞 PRECISA DE AJUDA?

### Durante os Testes Automatizados:
1. Leia a mensagem de erro completa
2. Veja os logs do backend
3. Use `pytest -v -s` para mais detalhes
4. Use `pytest --pdb` para debugar

### Durante os Testes Manuais:
1. Abra DevTools (F12) e veja Console
2. Veja Network para requisições falhas
3. Anote exatamente o que fez antes do erro
4. Tire print da tela

### Não conseguiu resolver?
- Revise o código do endpoint que falhou
- Confira se o banco de dados tem as tabelas certas
- Veja se as migrations rodaram: `alembic upgrade head`

---

## 🎉 QUANDO TUDO PASSAR...

**PARABÉNS! 🚀**

Você tem um sistema:
✅ Funcionalmente completo  
✅ Testado e validado  
✅ Pronto para usuários reais  
✅ Com garantia de qualidade  

**Próximos passos:**
1. Deploy em produção
2. Treinamento dos usuários
3. Monitoramento pós-deploy
4. Suporte e ajustes finos

**Seu sistema está PRONTO para RODAR PRA VALER! 💪**

---

## 📝 RESUMO EXECUTIVO

| Item | Automatizado | Manual | Total |
|------|-------------|--------|-------|
| Cadastros | ✅ 3 testes | ✅ Checklist | ~15 itens |
| Vendas Vista | ✅ 3 testes | ✅ Checklist | ~20 itens |
| Vendas Parceladas | ✅ 1 teste | ✅ Checklist | ~10 itens |
| Operações | ✅ 2 testes | ✅ Checklist | ~15 itens |
| Financeiro | ✅ Helpers | ✅ Checklist | ~25 itens |
| Estoque | ✅ Helpers | ✅ Checklist | ~10 itens |
| Relatórios | ⚠️ Manual | ✅ Checklist | ~10 itens |
| Integrações | ⚠️ Manual | ✅ Checklist | ~15 itens |

**Total**: ~120 pontos de validação  
**Meta**: 98%+ de sucesso (**118+ itens OK**)

---

**Boa sorte com os testes! 🍀**  
**Você consegue! 💪**
