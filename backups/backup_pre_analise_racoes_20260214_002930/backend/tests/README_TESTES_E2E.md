# 🧪 TESTES E2E - SISTEMA PET SHOP PRO

## 📋 Sobre os Testes

Este diretório contém a **suíte completa de testes End-to-End (E2E)** do sistema, que valida todos os fluxos críticos antes da produção.

## 🎯 O que é testado

### ✅ 1. CADASTROS BÁSICOS
- **Clientes**: Pessoa física e jurídica
- **Pets**: Associados a clientes
- **Produtos**: Simples e com variações

### ✅ 2. VENDAS À VISTA
- **Dinheiro**: Liquidação imediata
- **PIX**: Sem taxas
- **Cartão Débito**: Com taxa configurável
- **Validações**:
  - ✓ Contas a receber criadas e liquidadas
  - ✓ Fluxo de caixa realizado registrado
  - ✓ DRE atualizada (receita bruta)
  - ✓ Estoque baixado corretamente
  - ✓ Taxas descontadas (débito)

### ✅ 3. VENDAS PARCELADAS
- **Cartão Crédito**: 2x, 3x, 6x, 12x
- **Validações**:
  - ✓ Múltiplas contas a receber criadas
  - ✓ Parcelas com vencimentos corretos
  - ✓ Fluxo de caixa NÃO realizado (ainda não recebeu)
  - ✓ DRE atualizada (receita bruta)
  - ✓ Taxas calculadas por parcela

### ✅ 4. VENDAS COM DESCONTO
- **Percentual**: 5%, 10%, 15%
- **Valor fixo**: R$ 10, R$ 20, etc
- **Validações**:
  - ✓ Total recalculado corretamente
  - ✓ Desconto registrado na DRE
  - ✓ Contas a receber com valor líquido

### ✅ 5. OPERAÇÕES EM VENDAS
- **Cancelar venda**: Estorna TUDO
  - ✓ Contas a receber canceladas
  - ✓ Fluxo de caixa estornado
  - ✓ DRE atualizada (cancelamento)
  - ✓ Estoque devolvido
  - ✓ Comissões estornadas
  
- **Remover item**: Recalcula totais
  - ✓ Total da venda ajustado
  - ✓ Estoque devolvido
  - ✓ Contas a receber atualizadas
  
- **Reabrir venda**: (se implementado)
  - ✓ Status volta para "aberta"
  - ✓ Permite adicionar itens

### ✅ 6. FLUXOS COMPLEXOS
- **Múltiplas formas de pagamento**:
  - Exemplo: R$ 100 dinheiro + R$ 50 PIX + R$ 50 débito
  - ✓ Cada pagamento registrado corretamente
  - ✓ Taxas aplicadas individualmente
  
- **Venda com entrega**:
  - ✓ Taxa de entrega adicionada ao total
  - ✓ Endereço registrado
  - ✓ Entregador associado (se houver)
  
- **Venda com comissão**:
  - ✓ Comissão calculada por item/total
  - ✓ Funcionário comissionado vinculado
  - ✓ Registro na tabela de comissões

### ✅ 7. VALIDAÇÕES FINANCEIRAS
- **Contas a Receber**:
  - ✓ Quantidade de parcelas correta
  - ✓ Valores corretos (com descontos e taxas)
  - ✓ Status de liquidação
  - ✓ Datas de vencimento
  
- **Fluxo de Caixa**:
  - ✓ Entradas registradas (pagamento à vista)
  - ✓ Valores líquidos (após taxas)
  - ✓ Estornos em cancelamentos
  
- **DRE**:
  - ✓ Receita bruta lançada
  - ✓ Descontos registrados
  - ✓ CMV calculado
  - ✓ Taxas de cartão como despesa

### ✅ 8. VALIDAÇÕES DE ESTOQUE
- ✓ Baixa automática na venda
- ✓ Devolução no cancelamento
- ✓ Ajuste ao remover item
- ✓ Reserva em vendas abertas (se implementado)

## 🚀 Como Executar

### Método 1: Script Automatizado (RECOMENDADO)
```batch
# Na raiz do projeto
EXECUTAR_TESTES_E2E.bat
```

### Método 2: Manual
```bash
# 1. Inicie o backend
INICIAR_DEV.bat

# 2. Em outro terminal, execute os testes
cd backend
pytest tests/e2e_test_sistema_completo.py -v -s
```

### Executar teste específico
```bash
# Testar apenas vendas à vista
pytest tests/e2e_test_sistema_completo.py::TestVendasVista -v -s

# Testar apenas cancelamento
pytest tests/e2e_test_sistema_completo.py::TestOperacoesVendas::test_cancelar_venda_completo -v -s
```

## 📊 Entendendo os Resultados

### ✅ Teste PASSOU
```
✅ Cliente criado com sucesso: ID 123
✅ Contas a receber OK: 1 parcela(s), total R$ 100.00
✅ Fluxo de caixa OK: R$ 100.00 recebido
✅ DRE OK: Receita bruta R$ 100.00
✅ Estoque OK: 47 unidades
🎉 TESTE PASSOU! Todos os efeitos validados!
```

### ❌ Teste FALHOU
```
❌ Esperado 3 parcelas, encontrado 1
❌ Valor total das contas (90.00) diferente do esperado (100.00)
FAILED tests/e2e_test_sistema_completo.py::test_venda_parcelada
```

## 🔧 Requisitos

- Backend rodando em `http://localhost:8000`
- Python 3.8+
- Bibliotecas instaladas:
  ```bash
  pip install pytest requests
  ```

## 📝 Estrutura do Código

```python
# Fixture de autenticação
@pytest.fixture(scope="module")
def auth_headers():
    # Autentica e retorna token JWT

# Helpers de validação
def validar_contas_receber(venda_id, esperado, headers):
def validar_fluxo_caixa(venda_id, esperado, headers):
def validar_dre(venda_id, esperado, headers):
def validar_estoque(produto_id, esperado, headers):
def validar_comissoes(venda_id, esperado, headers):

# Classes de teste
class TestCadastros:           # Testes de cadastro
class TestVendasVista:         # Vendas à vista
class TestVendasParceladas:    # Vendas parceladas
class TestOperacoesVendas:     # Cancelar, remover item
class TestFluxosComplexos:     # Cenários complexos
```

## 🎯 Cobertura de Testes

| Módulo | Funcionalidade | Status |
|--------|---------------|--------|
| 📋 Cadastros | Clientes | ✅ |
| 📋 Cadastros | Pets | ✅ |
| 📋 Cadastros | Produtos | ✅ |
| 💰 Vendas | Dinheiro | ✅ |
| 💰 Vendas | PIX | ✅ |
| 💰 Vendas | Débito | ✅ |
| 💰 Vendas | Crédito Parcelado | ✅ |
| 💰 Vendas | Desconto | ✅ |
| 💰 Vendas | Múltiplos Pagamentos | ✅ |
| 💰 Vendas | Com Entrega | ✅ |
| 🔄 Operações | Cancelar Venda | ✅ |
| 🔄 Operações | Remover Item | ✅ |
| 📊 Financeiro | Contas a Receber | ✅ |
| 📊 Financeiro | Fluxo de Caixa | ✅ |
| 📊 Financeiro | DRE | ✅ |
| 📦 Estoque | Baixa Automática | ✅ |
| 📦 Estoque | Devolução | ✅ |
| 💼 Comissões | Cálculo | ✅ |
| 💼 Comissões | Estorno | ✅ |

## 🐛 Troubleshooting

### Erro: "Backend não está rodando"
```bash
# Inicie o backend primeiro
INICIAR_DEV.bat
```

### Erro: "Não foi possível autenticar"
```python
# Verifique as credenciais em e2e_test_sistema_completo.py
TEST_USER = {
    "email": "teste@petshop.com",
    "password": "Teste@123"
}
```

### Erro: "Não foi possível abrir caixa"
```bash
# Verifique se a tabela caixas existe no banco
# Se necessário, execute as migrations
cd backend
alembic upgrade head
```

## 📈 Próximos Testes a Adicionar

- [ ] Venda com variações de produto
- [ ] Conciliação de cartão
- [ ] Integração com Bling
- [ ] Emissão de NF-e
- [ ] Relatórios (vendas, DRE, comissões)
- [ ] Gestão de estoque (transferências, ajustes)
- [ ] Módulo de WhatsApp
- [ ] IA de vendas

## 🎉 Quando TODOS os testes passarem...

**Seu sistema está pronto para PRODUÇÃO! 🚀**

Você terá a garantia de que:
- ✅ Todas as operações funcionam corretamente
- ✅ Todos os efeitos colaterais são tratados
- ✅ Cálculos estão corretos
- ✅ Integridade de dados é mantida
- ✅ Não há regressões em funcionalidades existentes
