# 🔒 CONTRATO OFICIAL DE DESENVOLVIMENTO — ERP PET SHOP (MULTI-TENANT)

> **Status:** ATIVO E OBRIGATÓRIO
> **Escopo:** Backend, Banco de Dados, Testes, IA Agents
> **Este documento NÃO descreve intenções. Ele descreve REGRAS.**

---

## 🎯 OBJETIVO DESTE CONTRATO

Garantir que **nenhuma evolução do sistema**:

* quebre o isolamento multi-tenant
* introduza vazamento de dados entre empresas
* viole padrões arquiteturais já validados

Este contrato serve como:

* 📜 referência humana
* 🧠 guia para agentes de IA
* 🛡️ proteção contra regressões

---

## 🧠 PRINCÍPIO FUNDAMENTAL

> **TODO dado de negócio pertence a exatamente UM tenant.**

Se um dado pertence a um tenant:

* ele **DEVE** ter `tenant_id`
* ele **NUNCA** pode ser acessado fora do contexto do tenant

---

## 🏗️ REGRAS ESTRUTURAIS (INQUEBRÁVEIS)

### 1️⃣ BaseTenantModel

**REGRA:**

* TODO model de negócio **DEVE** herdar de `BaseTenantModel`

`BaseTenantModel` garante:

* `tenant_id NOT NULL`
* `created_at`
* `updated_at`

❌ **PROIBIDO:**

* criar model de negócio sem herdar BaseTenantModel

---

### 2️⃣ Banco de Dados

**REGRA:**

* TODA tabela de negócio **DEVE** possuir:

  * coluna `tenant_id`
  * `tenant_id NOT NULL`

**EXCEÇÕES PERMITIDAS (globais):**

* tenants
* permissions
* alembic_version

Qualquer nova exceção:

* DEVE ser documentada
* DEVE ser justificada

---

## 🔐 CONTEXTO DE TENANT

### 3️⃣ Contexto é OBRIGATÓRIO

**REGRA:**

* Nenhuma operação de negócio ocorre sem contexto de tenant

O contexto pode vir de:

* `TenantSecurityMiddleware`
* `get_current_user_and_tenant()`

❌ **PROIBIDO:**

* query direta sem tenant
* lógica de negócio fora de contexto

---

### 4️⃣ Middleware de Segurança

**TenantSecurityMiddleware é obrigatório**:

* bloqueia JWT sem tenant_id
* retorna 403 se tenant estiver ausente
* limpa contexto após cada request

Nenhuma rota protegida pode bypassar isso.

---

## 🧪 CONTRATO DE TESTES (GUARDRAIL)

### 5️⃣ Testes de Contrato Multi-Tenant

Arquivo oficial:

```
backend/tests/test_multitenant_contract.py
```

**REGRA:**

* TODOS os testes DEVEM passar
* Se 1 falhar → sistema está em violação

Esses testes garantem:

* isolamento entre tenants
* inexistência de tenant_id NULL
* herança correta de BaseTenantModel
* segurança contra vazamento cross-tenant

---

### 6️⃣ Antes de qualquer MERGE ou DEPLOY

Checklist obrigatório:

* [ ] Todos os testes multi-tenant passaram
* [ ] Nenhuma tabela de negócio sem tenant_id
* [ ] Nenhuma coluna tenant_id nullable
* [ ] Nenhuma rota sem contexto

Se algum item falhar → **BLOQUEAR**

---

## 🤖 REGRAS PARA AGENTES DE IA

### 7️⃣ Comportamento Esperado do Agent

O Agent DEVE:

* assumir sistema multi-tenant por padrão
* SEMPRE perguntar sobre tenant se houver dúvida
* NUNCA gerar código sem tenant_id em dados de negócio
* SEMPRE sugerir testes quando mexer em models

Prompt padrão recomendado:

> "Siga obrigatoriamente o CONTRATO_DE_DESENVOLVIMENTO_MULTI_TENANT.md deste projeto."

---

## 🚨 VIOLAÇÕES

Qualquer violação deste contrato é considerada:

* 🚨 ERRO CRÍTICO
* 🔒 BLOQUEIO DE EVOLUÇÃO
* ⚠️ RISCO DE SEGURANÇA / LGPD

A correção é **obrigatória e imediata**.

---

## 🏁 STATUS FINAL

Este contrato:

* NÃO substitui testes
* NÃO substitui código
* **COMPLEMENTA** ambos

📌 **O código executa o contrato**
📌 **Este documento explica o contrato**

---

**Assinado por:**

* Fundador do ERP Pet Shop
* Arquitetura validada
* Multi-tenant confirmado

**Status:** 🔒 ATIVO
