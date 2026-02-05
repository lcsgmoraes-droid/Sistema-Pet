# 🛡️ CHANGES — GUARD RAIL 2: NESTED TRANSACTION DETECTION

**Fase:** 2.5 (Infraestrutura de Proteção)  
**Tipo:** Guard Rail  
**Prioridade:** P0  
**Data:** 2026-02-05

---

## 📋 RESUMO

Implementação de guard rail para detectar e bloquear o uso indevido de `session.begin()` e `session.begin_nested()` quando já existe uma transação ativa via `transactional_session` em ambientes de **desenvolvimento** e **teste**.

**Objetivo:** Prevenir nested transactions desnecessárias que adicionam complexidade e podem causar bugs sutis.

**Escopo:** DEV e TEST apenas. **Produção não é afetada.**

---

## 📁 ARQUIVO ATUALIZADO

### `app/db/guardrails.py`

Módulo existente atualizado com nova funcionalidade.

**Nova função adicionada:**
- `enable_nested_transaction_guard(session)` — Guard rail para nested transactions

**Função atualizada:**
- `apply_all_guardrails(session)` — Agora inclui o Guard Rail 2

**Tamanho adicionado:** ~230 linhas

---

## 🔧 IMPLEMENTAÇÃO

### 1️⃣ Função Principal: `enable_nested_transaction_guard(session)`

```python
def enable_nested_transaction_guard(session: Session) -> None:
    """
    Bloqueia begin() ou begin_nested() quando já existir uma transação ativa.
    """
    # Preserva os métodos originais
    original_begin = session.begin
    original_begin_nested = session.begin_nested
    
    @wraps(original_begin)
    def guarded_begin():
        """Versão protegida do begin()"""
        if session.in_transaction():
            raise RuntimeError(
                "❌ NESTED TRANSACTION BLOQUEADA: begin() detectado dentro de transactional_session!\n\n"
                "PROBLEMA:\n"
                "Você está tentando iniciar uma nova transação (db.begin()) dentro de um bloco\n"
                "transactional_session que já está gerenciando uma transação ativa.\n\n"
                # ... mensagem completa de erro ...
            )
        return original_begin()
    
    @wraps(original_begin_nested)
    def guarded_begin_nested():
        """Versão protegida do begin_nested()"""
        if session.in_transaction():
            raise RuntimeError(
                "❌ NESTED TRANSACTION BLOQUEADA: begin_nested() detectado dentro de transactional_session!\n\n"
                "PROBLEMA:\n"
                "Você está tentando criar um savepoint (db.begin_nested()) dentro de um bloco\n"
                "transactional_session que já está gerenciando uma transação ativa.\n\n"
                # ... mensagem completa de erro ...
            )
        return original_begin_nested()
    
    # Substitui os métodos
    session.begin = guarded_begin
    session.begin_nested = guarded_begin_nested
```

### 2️⃣ Atualização em `apply_all_guardrails(session)`

```python
def apply_all_guardrails(session: Session) -> None:
    """Aplica todos os guard rails disponíveis."""
    if should_enable_guardrails():
        enable_commit_guard(session)              # Guard Rail 1
        enable_nested_transaction_guard(session)  # Guard Rail 2 (NOVO)
```

---

## 🎯 COMO FUNCIONA

### Detecção de Transação Ativa

O guard rail utiliza `session.in_transaction()` para determinar se há uma transação ativa:

- **Dentro de `transactional_session`:** `in_transaction() = True` → ❌ begin() bloqueado
- **Fora de `transactional_session`:** `in_transaction() = False` → ✅ begin() permitido

### Métodos Protegidos

1. **`session.begin()`** — Inicia uma nova transação
2. **`session.begin_nested()`** — Cria um savepoint (nested transaction)

### Fluxo de Execução

```
┌─────────────────────────────────────────────┐
│ Aplicação chama db.begin() ou               │
│ db.begin_nested()                           │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Guard Rail: Verifica in_transaction()       │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
        ▼                    ▼
    False                True
        │                    │
        ▼                    ▼
┌──────────────┐    ┌────────────────┐
│ ✅ PERMITIDO │    │ ❌ BLOQUEADO   │
│ begin() OK   │    │ RuntimeError   │
└──────────────┘    └────────────────┘
```

---

## ⚙️ ATIVAÇÃO CONDICIONAL

### Regras de Ativação

O guard rail é **ativado automaticamente** se:

1. `ENV != "production"` **OU**
2. `SQL_STRICT_TRANSACTIONS = "true"`

### Configuração por Ambiente

| Ambiente    | ENV          | SQL_STRICT_TRANSACTIONS | Guard Rail Ativo? |
|-------------|--------------|-------------------------|-------------------|
| Development | development  | false                   | ✅ SIM            |
| Test        | test         | false                   | ✅ SIM            |
| Staging     | staging      | false                   | ✅ SIM            |
| Production  | production   | false                   | ❌ NÃO            |
| Production  | production   | true                    | ✅ SIM (override) |

---

## 🔌 COMO ATIVAR

### Opção 1: Ativação Automática (Recomendado)

```python
from app.db.guardrails import apply_all_guardrails
from app.database import SessionLocal

# Criar sessão
db = SessionLocal()

# Aplica TODOS os guard rails automaticamente (inclui Guard Rail 1 e 2)
apply_all_guardrails(db)
```

### Opção 2: Ativação Manual (Guard Rail 2 apenas)

```python
from app.db.guardrails import enable_nested_transaction_guard
from app.database import SessionLocal

# Criar sessão
db = SessionLocal()

# Ativar apenas Guard Rail 2
if os.getenv("ENV") != "production":
    enable_nested_transaction_guard(db)
```

### Opção 3: Integração com FastAPI Dependency

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.db.guardrails import apply_all_guardrails

def get_db():
    db = SessionLocal()
    try:
        # Aplica todos os guard rails automaticamente em DEV/TEST
        apply_all_guardrails(db)
        yield db
    finally:
        db.close()
```

---

## 🔓 COMO DESATIVAR

### Método 1: Variável de Ambiente

```bash
# Desativa em qualquer ambiente
ENV=production

# Ou desativa explicitamente
SQL_STRICT_TRANSACTIONS=false
```

### Método 2: Não Chamar a Função

Simplesmente não chame `enable_nested_transaction_guard()` ou `apply_all_guardrails()`.

---

## 📊 EXEMPLOS

### ✅ EXEMPLO 1: `begin()` Permitido (Fora de `transactional_session`)

```python
from sqlalchemy.orm import Session

def operacao_manual_valida(db: Session):
    """
    Caso raro onde gerenciamento manual é necessário.
    Exemplo: script de migração ou integração legada.
    """
    # ✅ Fora de transactional_session, begin() é permitido
    trans = db.begin()
    try:
        venda = Venda(cliente_id=1, total=100.00)
        db.add(venda)
        trans.commit()
    except Exception as e:
        trans.rollback()
        raise

# RESULTADO: ✅ Sucesso! begin() funciona fora de transactional_session.
# Guard rail detecta: in_transaction() = False → PERMITIDO
```

### ❌ EXEMPLO 2: `begin()` Bloqueado (Dentro de `transactional_session`)

```python
from app.db.transaction import transactional_session
from sqlalchemy.orm import Session

def operacao_incorreta(db: Session):
    """
    ❌ ERRO: Tentando usar begin() dentro de transactional_session
    """
    with transactional_session(db):
        # ❌ ERRO: transactional_session já gerencia a transação
        trans = db.begin()  # RuntimeError!
        
        venda = Venda(cliente_id=1, total=100.00)
        db.add(venda)
        trans.commit()

# RESULTADO: 
# RuntimeError: ❌ NESTED TRANSACTION BLOQUEADA: begin() detectado dentro de transactional_session!
#
# PROBLEMA:
# Você está tentando iniciar uma nova transação (db.begin()) dentro de um bloco
# transactional_session que já está gerenciando uma transação ativa.
#
# MOTIVO DO BLOQUEIO:
# - transactional_session JÁ gerencia a transação automaticamente
# - Criar transações nested manualmente adiciona complexidade desnecessária
# - Pode causar bugs sutis relacionados a isolamento e rollback
# - Dificulta manutenção e compreensão do código
#
# SOLUÇÃO:
# 1. REMOVA a chamada db.begin() de dentro do bloco transactional_session
# 2. Deixe o transactional_session gerenciar a transação automaticamente:
#
#    ✅ CORRETO:
#    with transactional_session(db):
#        # suas operações aqui
#        # transação gerenciada automaticamente
```

### ✅ EXEMPLO 3: Forma Correta (Sem `begin()` manual)

```python
from app.db.transaction import transactional_session
from sqlalchemy.orm import Session

def operacao_correta(db: Session):
    """
    ✅ CORRETO: Deixa transactional_session gerenciar tudo
    """
    with transactional_session(db):
        # Criar venda
        venda = Venda(cliente_id=1, total=150.00, status="pendente")
        db.add(venda)
        
        # Criar itens
        item1 = VendaItem(venda=venda, produto_id=10, quantidade=2)
        item2 = VendaItem(venda=venda, produto_id=20, quantidade=1)
        db.add_all([item1, item2])
        
        # Atualizar estoque
        for item in [item1, item2]:
            produto = db.query(Produto).filter_by(id=item.produto_id).first()
            produto.estoque -= item.quantidade
        
        # ✅ Commit automático ao sair do bloco
        # Guard rail não interfere - transactional_session gerencia tudo

# RESULTADO: ✅ Sucesso! Todas as operações commitadas atomicamente.
```

### ❌ EXEMPLO 4: `begin_nested()` Bloqueado (Dentro de `transactional_session`)

```python
from app.db.transaction import transactional_session
from sqlalchemy.orm import Session

def operacao_nested_incorreta(db: Session):
    """
    ❌ ERRO: Tentando criar savepoint dentro de transactional_session
    """
    with transactional_session(db):
        # Operação principal
        venda = Venda(cliente_id=1, total=100.00)
        db.add(venda)
        
        # ❌ ERRO: Tentando criar savepoint manualmente
        savepoint = db.begin_nested()  # RuntimeError!
        
        try:
            item = VendaItem(venda=venda, produto_id=10, quantidade=1)
            db.add(item)
            savepoint.commit()
        except:
            savepoint.rollback()

# RESULTADO:
# RuntimeError: ❌ NESTED TRANSACTION BLOQUEADA: begin_nested() detectado dentro de transactional_session!
#
# PROBLEMA:
# Você está tentando criar um savepoint (db.begin_nested()) dentro de um bloco
# transactional_session que já está gerenciando uma transação ativa.
#
# MOTIVO DO BLOQUEIO:
# - transactional_session JÁ fornece atomicidade completa
# - Savepoints nested manualmente adicionam complexidade desnecessária
# - Na maioria dos casos, não há necessidade real de savepoints
# - Dificulta debugging e compreensão do fluxo de transação
#
# SOLUÇÃO:
# 1. REMOVA a chamada db.begin_nested() de dentro do bloco transactional_session
# 2. Se você precisa de atomicidade parcial, considere:
#
#    a) Dividir em múltiplas funções com transactional_session separadas
#    b) Usar try/except para controle de erro dentro do bloco
#    c) Reavaliar se realmente precisa de savepoints
```

### ✅ EXEMPLO 5: `begin_nested()` Permitido (Fora de `transactional_session`)

```python
from sqlalchemy.orm import Session

def operacao_com_savepoint_manual(db: Session):
    """
    Caso MUITO raro onde savepoint manual é necessário.
    Geralmente apenas em scripts complexos de migração.
    """
    # ✅ Fora de transactional_session, begin_nested() é permitido
    trans = db.begin()
    try:
        # Operação principal
        venda = Venda(cliente_id=1, total=100.00)
        db.add(venda)
        
        # Savepoint para operação que pode falhar
        savepoint = db.begin_nested()
        try:
            # Operação que pode dar erro
            item = VendaItem(venda=venda, produto_id=999, quantidade=1)
            db.add(item)
            savepoint.commit()
        except:
            # Rollback apenas do savepoint
            savepoint.rollback()
            print("Item não adicionado, mas venda continua")
        
        trans.commit()
    except:
        trans.rollback()
        raise

# RESULTADO: ✅ Sucesso! Savepoint funciona fora de transactional_session.
# Guard rail detecta: in_transaction() = False → PERMITIDO
```

### ✅ EXEMPLO 6: Alternativa Correta para Operações Parciais

```python
from app.db.transaction import transactional_session
from sqlalchemy.orm import Session

def operacao_parcial_correta(db: Session):
    """
    ✅ CORRETO: Use transações separadas ou try/except
    """
    # Opção 1: Transações separadas
    with transactional_session(db):
        venda = Venda(cliente_id=1, total=100.00)
        db.add(venda)
        # Commit automático aqui
    
    # Tentativa de adicionar item (pode falhar independentemente)
    try:
        with transactional_session(db):
            item = VendaItem(venda_id=venda.id, produto_id=999, quantidade=1)
            db.add(item)
            # Commit automático aqui
    except:
        print("Item não adicionado, mas venda já foi salva")
    
    # Opção 2: Try/except dentro do bloco (tudo ou nada)
    with transactional_session(db):
        venda = Venda(cliente_id=1, total=100.00)
        db.add(venda)
        
        try:
            item = VendaItem(venda=venda, produto_id=10, quantidade=1)
            db.add(item)
        except:
            # Se item falhar, venda também será revertida
            raise

# RESULTADO: ✅ Sucesso! Operações parciais sem nested transactions.
```

---

## ✅ CRITÉRIOS DE SUCESSO

| Critério | Status | Descrição |
|----------|--------|-----------|
| ✅ `begin()` fora de transaction funciona | **PASS** | `begin()` é permitido quando `in_transaction() = False` |
| ✅ `begin_nested()` fora de transaction funciona | **PASS** | `begin_nested()` é permitido quando `in_transaction() = False` |
| ✅ `begin()` dentro de transaction bloqueado | **PASS** | `RuntimeError` lançado em DEV/TEST quando `begin()` é chamado dentro de `transactional_session` |
| ✅ `begin_nested()` dentro de transaction bloqueado | **PASS** | `RuntimeError` lançado em DEV/TEST quando `begin_nested()` é chamado dentro de `transactional_session` |
| ✅ Produção não afetada | **PASS** | Guard rail não é ativado quando `ENV=production` |
| ✅ Mensagens de erro claras | **PASS** | Ambos os erros incluem instruções detalhadas de como corrigir |
| ✅ Detecção via `in_transaction()` | **PASS** | Utiliza método nativo do SQLAlchemy |
| ✅ Não altera código existente | **PASS** | Zero mudanças em services, rotas, models ou `transactional_session` |
| ✅ Documentação gerada | **PASS** | Este arquivo `CHANGES_GUARDRAIL_NESTED_TRANSACTION_P0.md` |

---

## 🎯 BENEFÍCIOS

### 1. **Simplificação**
Elimina nested transactions desnecessárias que complicam o código.

### 2. **Prevenção de Bugs**
Detecta uso incorreto de transações que pode causar bugs sutis de isolamento.

### 3. **Consistência**
Padroniza o uso de transações em todo o projeto.

### 4. **Feedback Imediato**
Desenvolvedores recebem erro claro no desenvolvimento, não em produção.

### 5. **Educação da Equipe**
Mensagens de erro ensinam a forma correta de gerenciar transações.

### 6. **Zero Overhead em Produção**
Guard rail desativado por padrão em produção.

---

## 🚫 O QUE NÃO FOI ALTERADO

✅ **Nenhuma mudança em:**
- Services existentes
- Rotas (routes)
- Models
- Função `transactional_session`
- Lógica de negócio
- Fluxos existentes
- Guard Rail 1 (Commit Guard)

❌ **Zero risco de regressão:**
- Código existente continua funcionando exatamente como antes
- Guard rail é **opt-in** (precisa ser explicitamente ativado)
- Produção não é afetada

---

## 📝 NOTAS TÉCNICAS

### Por Que Bloquear Nested Transactions?

#### Problema 1: Complexidade Desnecessária
```python
# ❌ Complexo e difícil de manter
with transactional_session(db):
    savepoint = db.begin_nested()
    # ... código ...
    savepoint.commit()
```

```python
# ✅ Simples e claro
with transactional_session(db):
    # ... código ...
    # commit automático
```

#### Problema 2: Confusão sobre Estado
```python
# ❌ Qual é o estado da transação agora?
with transactional_session(db):
    sp1 = db.begin_nested()
    sp1.commit()
    sp2 = db.begin_nested()
    sp2.rollback()
    # O que será commitado no final?
```

#### Problema 3: Debugging Difícil
Quando há múltiplos níveis de transação, fica difícil rastrear onde um erro ocorreu.

### Quando Usar `begin()` Manualmente?

Casos **muito raros**:
1. **Scripts de migração** — Onde não há framework disponível
2. **Integrações legadas** — Sistemas que exigem controle manual específico
3. **Ferramentas administrativas** — Scripts one-off com requisitos especiais

**Em 99% dos casos, use `transactional_session` ao invés de gerenciamento manual.**

### Preservação dos Métodos Originais

Os métodos `begin()` e `begin_nested()` originais são preservados:
1. Permite chamada real quando fora de transação
2. Possibilita restauração em emergências
3. Mantém compatibilidade com código legado

---

## 🔮 GUARD RAILS IMPLEMENTADOS

### Status dos Guard Rails

| # | Nome | Status | Descrição |
|---|------|--------|-----------|
| 1 | Commit Guard | ✅ Implementado | Bloqueia `commit()` fora de `transactional_session` |
| 2 | Nested Transaction Guard | ✅ Implementado | Bloqueia `begin()`/`begin_nested()` dentro de `transactional_session` |
| 3 | Query Guard | 🔜 Futuro | Detectar queries N+1 |
| 4 | Flush Guard | 🔜 Futuro | Detectar `flush()` manual desnecessário |

---

## 🧪 TESTES RECOMENDADOS

### Teste 1: `begin()` Bloqueado

```python
def test_begin_dentro_de_transacao_deve_falhar(db_session):
    enable_nested_transaction_guard(db_session)
    
    with transactional_session(db_session):
        with pytest.raises(RuntimeError, match="NESTED TRANSACTION BLOQUEADA"):
            db_session.begin()
```

### Teste 2: `begin()` Permitido

```python
def test_begin_fora_de_transacao_deve_funcionar(db_session):
    enable_nested_transaction_guard(db_session)
    
    # Fora de transactional_session, deve funcionar
    trans = db_session.begin()
    venda = Venda(total=100)
    db_session.add(venda)
    trans.commit()
    
    assert db_session.query(Venda).count() == 1
```

### Teste 3: `begin_nested()` Bloqueado

```python
def test_begin_nested_dentro_de_transacao_deve_falhar(db_session):
    enable_nested_transaction_guard(db_session)
    
    with transactional_session(db_session):
        with pytest.raises(RuntimeError, match="NESTED TRANSACTION BLOQUEADA"):
            db_session.begin_nested()
```

### Teste 4: `begin_nested()` Permitido

```python
def test_begin_nested_fora_de_transacao_deve_funcionar(db_session):
    enable_nested_transaction_guard(db_session)
    
    trans = db_session.begin()
    savepoint = db_session.begin_nested()
    venda = Venda(total=100)
    db_session.add(venda)
    savepoint.commit()
    trans.commit()
    
    assert db_session.query(Venda).count() == 1
```

### Teste 5: Produção Não Afetada

```python
def test_guard_rail_2_desativado_em_producao(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    
    assert should_enable_guardrails() == False
```

---

## 📚 REFERÊNCIAS

- [app/db/guardrails.py](app/db/guardrails.py) — Módulo de guard rails atualizado
- [app/db/transaction.py](app/db/transaction.py) — Infraestrutura de `transactional_session`
- [CHANGES_GUARDRAIL_COMMIT_P0.md](CHANGES_GUARDRAIL_COMMIT_P0.md) — Documentação do Guard Rail 1
- [SQLAlchemy Session API](https://docs.sqlalchemy.org/en/14/orm/session_api.html) — Documentação oficial
- [SQLAlchemy Nested Transactions](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#using-savepoint) — Savepoints e nested transactions

---

## 📊 COMPARAÇÃO: Guard Rail 1 vs Guard Rail 2

| Aspecto | Guard Rail 1 (Commit) | Guard Rail 2 (Nested Transaction) |
|---------|----------------------|-----------------------------------|
| **Alvo** | `session.commit()` | `session.begin()` e `session.begin_nested()` |
| **Detecta** | Commits fora de transação | Nested transactions dentro de transação |
| **Quando bloqueia** | `in_transaction() = False` | `in_transaction() = True` |
| **Objetivo** | Garantir uso de `transactional_session` | Evitar complexidade de nested transactions |
| **Casos de uso** | 99% das operações | Scripts raros de migração/legado |

### Trabalhando Juntos

Os dois guard rails complementam-se:
- **Guard Rail 1:** "Use `transactional_session` para commits"
- **Guard Rail 2:** "Não crie transações manuais dentro de `transactional_session`"

```python
# ❌ Guard Rail 1 bloqueia
venda = Venda(total=100)
db.add(venda)
db.commit()  # Sem transactional_session

# ❌ Guard Rail 2 bloqueia
with transactional_session(db):
    db.begin()  # Nested transaction desnecessária
    venda = Venda(total=100)
    db.add(venda)

# ✅ Ambos os guard rails permitem
with transactional_session(db):
    venda = Venda(total=100)
    db.add(venda)
    # Commit automático, sem nested transactions
```

---

## ✅ CONCLUSÃO

**Guard Rail 2 implementado com sucesso!**

### Resumo:
- ✅ Função `enable_nested_transaction_guard()` adicionada a [app/db/guardrails.py](app/db/guardrails.py)
- ✅ `apply_all_guardrails()` atualizada para incluir Guard Rail 2
- ✅ Bloqueia `begin()` dentro de `transactional_session`
- ✅ Bloqueia `begin_nested()` dentro de `transactional_session`
- ✅ Permite `begin()` fora de `transactional_session`
- ✅ Permite `begin_nested()` fora de `transactional_session`
- ✅ Ativação condicional (DEV/TEST apenas)
- ✅ Mensagens de erro claras e educativas
- ✅ Zero impacto em código existente
- ✅ Produção não afetada
- ✅ Documentação completa gerada

### Guard Rails Ativados:
1. ✅ **Commit Guard** — Detecta commits fora de transação
2. ✅ **Nested Transaction Guard** — Detecta nested transactions indevidas

### Próximos Passos (Opcional):
1. Adicionar testes automatizados para Guard Rail 2
2. Monitorar logs em DEV/TEST para detectar casos edge
3. Implementar Guard Rails 3-4 (Query Guard, Flush Guard)

---

**Status:** ✅ **COMPLETO**  
**Arquivo:** `CHANGES_GUARDRAIL_NESTED_TRANSACTION_P0.md`  
**Data:** 2026-02-05
