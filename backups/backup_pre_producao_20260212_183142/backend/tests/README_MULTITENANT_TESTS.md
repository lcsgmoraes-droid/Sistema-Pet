# 🔒 TESTES DE CONTRATO MULTI-TENANT

## 📋 VISÃO GERAL

Este diretório contém **testes de contrato** que garantem o isolamento multi-tenant do Sistema Pet Shop Pro.

> ⚠️ **CRITICIDADE MÁXIMA**: Estes testes validam segurança LGPD e isolamento de dados entre empresas.

---

## 🎯 PROPÓSITO

### O QUE SÃO TESTES DE CONTRATO?

Testes de contrato validam **GARANTIAS ARQUITETURAIS** do sistema, não lógica de negócio.

**Exemplos:**
- ✅ "Toda tabela de negócio DEVE ter tenant_id"
- ✅ "Dados do Tenant A NUNCA aparecem para Tenant B"
- ✅ "tenant_id é NOT NULL em todas as tabelas"

### POR QUE EXISTEM?

1. **Prevenir regressão** - Se alguém quebrar isolamento, teste falha
2. **Documentação viva** - Explicam regras arquiteturais
3. **Confiança no deploy** - Validam estrutura antes de produção
4. **Conformidade LGPD** - Garantem isolamento de dados pessoais

---

## 📦 ARQUIVO PRINCIPAL

### `test_multitenant_contract.py`

**Contém 10 testes críticos:**

| # | Teste | O que valida |
|---|-------|--------------|
| 1 | `test_base_tenant_model_possui_tenant_id` | BaseTenantModel tem tenant_id |
| 2 | `test_all_business_tables_have_tenant_id_column` | TODAS tabelas de negócio têm coluna tenant_id |
| 3 | `test_tenant_id_is_not_nullable_in_business_tables` | tenant_id é NOT NULL |
| 4 | `test_business_models_inherit_base_tenant_model` | Models herdam BaseTenantModel |
| 5 | `test_isolamento_produtos_entre_tenants` | Produtos isolados entre tenants |
| 6 | `test_isolamento_usuarios_entre_tenants` | Usuários isolados (LGPD) |
| 7 | `test_tenant_id_automatico_em_novo_registro` | tenant_id injetado automaticamente |
| 8 | `test_query_sem_contexto_retorna_vazio` | Query sem contexto não vaza dados |
| 9 | `test_tenant_id_nao_pode_ser_none` | Banco rejeita tenant_id=None |
| 10 | `test_venda_item_herda_tenant_id_da_venda` | Relacionamentos respeitam tenant |

---

## 🚀 COMO EXECUTAR

### **Pré-requisitos**

```powershell
# Instalar pytest (se ainda não tiver)
pip install pytest pytest-cov
```

### **Executar TODOS os testes de contrato**

```powershell
cd backend
python -m pytest tests/test_multitenant_contract.py -v
```

**Saída esperada:**
```
tests/test_multitenant_contract.py::test_base_tenant_model_possui_tenant_id PASSED
tests/test_multitenant_contract.py::test_all_business_tables_have_tenant_id_column PASSED
tests/test_multitenant_contract.py::test_tenant_id_is_not_nullable_in_business_tables PASSED
...
========== 10 passed in 2.34s ==========
```

### **Executar teste específico**

```powershell
# Testar apenas isolamento de produtos
python -m pytest tests/test_multitenant_contract.py::test_isolamento_produtos_entre_tenants -v -s

# Testar apenas estrutura de tabelas
python -m pytest tests/test_multitenant_contract.py::test_all_business_tables_have_tenant_id_column -v -s
```

### **Executar com relatório de cobertura**

```powershell
python -m pytest tests/test_multitenant_contract.py --cov=app --cov-report=html
```

### **Gerar relatório de segurança**

```powershell
# Executa teste que gera relatório de auditoria
python -m pytest tests/test_multitenant_contract.py::test_generate_multitenant_security_report -v -s
```

---

## ❌ QUANDO OS TESTES FALHAM

### **CENÁRIO 1: Tabela sem tenant_id**

**Erro:**
```
❌ CRÍTICO: Tabelas de negócio SEM tenant_id: ['nova_tabela']
```

**AÇÃO OBRIGATÓRIA:**
1. Adicionar tenant_id à tabela
2. Fazer model herdar `BaseTenantModel`
3. Criar migração Alembic
4. Executar backfill de dados (se necessário)

**Exemplo de correção:**
```python
# ❌ ERRADO
class NovaTabela(Base):
    __tablename__ = "nova_tabela"
    id = Column(Integer, primary_key=True)

# ✅ CORRETO
class NovaTabela(BaseTenantModel):
    __tablename__ = "nova_tabela"
    # id e tenant_id vêm automaticamente de BaseTenantModel
```

---

### **CENÁRIO 2: Vazamento cross-tenant**

**Erro:**
```
🚨 VAZAMENTO CRÍTICO DE SEGURANÇA!
Tenant B conseguiu acessar produto do Tenant A!
```

**AÇÃO OBRIGATÓRIA:**
1. **PARAR SISTEMA IMEDIATAMENTE** ❌
2. Revisar `app/tenancy/filters.py`
3. Revisar middleware de tenant
4. Executar auditoria completa de segurança
5. Notificar DPO/LGPD (se em produção)

**Causas comuns:**
- Filtros automáticos desabilitados
- Middleware não está setando contexto
- Query manual ignorando tenant_id

---

### **CENÁRIO 3: tenant_id pode ser NULL**

**Erro:**
```
❌ CRÍTICO: Tabelas com tenant_id NULLABLE: ['produtos']
```

**AÇÃO OBRIGATÓRIA:**
1. Identificar registros com `tenant_id = NULL`
2. Atribuir tenant_id correto (ou deletar se inválido)
3. Executar migração:
   ```sql
   ALTER TABLE produtos ALTER COLUMN tenant_id SET NOT NULL;
   ```

---

## 📊 INTEGRAÇÃO COM CI/CD

### **GitHub Actions (exemplo)**

```yaml
name: Testes de Segurança Multi-Tenant

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Executar Testes de Contrato Multi-Tenant
        run: |
          cd backend
          python -m pytest tests/test_multitenant_contract.py -v --tb=short
      
      - name: Falhar se houver vazamento
        if: failure()
        run: |
          echo "🚨 BLOQUEADO: Testes de isolamento multi-tenant falharam!"
          exit 1
```

---

## 🎯 CHECKLIST DE VALIDAÇÃO

### **Antes de Fazer Deploy**

- [ ] Todos os testes de contrato passam
- [ ] Nenhum teste ignorado (skip)
- [ ] Relatório de segurança revisado
- [ ] Novas tabelas têm tenant_id
- [ ] Novos models herdam BaseTenantModel

### **Após Adicionar Nova Tabela**

- [ ] Herda `BaseTenantModel`
- [ ] Possui constraint NOT NULL em tenant_id
- [ ] Testes de isolamento passam
- [ ] Adicionada ao `business_tables` (se aplicável)

### **Após Modificar Middleware/Filtros**

- [ ] Testes de isolamento passam
- [ ] Query sem contexto retorna vazio
- [ ] tenant_id injetado automaticamente

---

## 📚 DOCUMENTAÇÃO RELACIONADA

- [AGENT_CONTRACT.md](../../docs/AGENT_CONTRACT.md) - Contrato de desenvolvimento seguro
- [TESTE_MIDDLEWARE_TENANT.md](../TESTE_MIDDLEWARE_TENANT.md) - Testes de middleware
- [base_models.py](../app/base_models.py) - BaseTenantModel
- [tenancy/filters.py](../app/tenancy/filters.py) - Filtros automáticos

---

## 🆘 SUPORTE

### **Testes falhando?**

1. Verificar logs detalhados: `pytest -v -s`
2. Revisar `AGENT_CONTRACT.md` para regras
3. Executar relatório de segurança
4. Consultar documentação de multi-tenant

### **Dúvidas sobre isolamento?**

```python
# Como funciona o isolamento?
from app.tenancy.context import set_current_tenant

# 1. Middleware seta contexto automaticamente
set_current_tenant(tenant_id)  # Vem do JWT

# 2. Filtros automáticos aplicam tenant_id
produtos = db.query(Produto).all()  # Já filtrado por tenant!

# 3. Event listeners injetam tenant_id
produto = Produto(nome="Test")  # tenant_id injetado automaticamente
db.add(produto)
db.commit()
```

---

## 🔐 STATUS ATUAL

✅ **10 testes de contrato implementados**  
✅ **0 erros de sintaxe**  
✅ **Cobertura de cenários críticos**  
✅ **Documentação completa**  
✅ **Pronto para integração CI/CD**  

---

**Última atualização:** 2026-01-27  
**Autor:** Sistema Pet Shop Pro - Arquitetura Multi-Tenant  
**Criticidade:** MÁXIMA (Segurança LGPD)
