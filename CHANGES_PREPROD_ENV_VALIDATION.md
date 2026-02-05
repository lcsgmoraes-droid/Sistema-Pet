# 📄 CHANGES_PREPROD_ENV_VALIDATION.md

## PRÉ-PRODUÇÃO — BLOCO 1: VALIDAÇÃO DE AMBIENTE

**Data:** 2026-02-05  
**Fase:** Pré-Produção  
**Prioridade:** P0 (Crítico)

---

## 🎯 OBJETIVO

Implementar validação rigorosa de variáveis de ambiente críticas na inicialização do sistema, garantindo que:

1. Todas as variáveis obrigatórias estejam presentes
2. O ambiente (DEV/TEST/PROD) esteja configurado corretamente
3. Guard rails e configurações de segurança estejam adequados para produção
4. A aplicação **falhe imediatamente** se algo estiver incorreto

---

## ✅ ARQUIVOS CRIADOS

### 1. `app/core/settings_validation.py`

**Propósito:** Módulo dedicado de validação de settings críticos

**Estrutura:**

```
app/core/settings_validation.py
├── validate_settings()                    # Função principal de validação
├── _validate_production_settings()        # Validações específicas de PROD
├── _validate_test_settings()              # Validações específicas de TEST
├── _validate_development_settings()       # Validações específicas de DEV
├── _format_error_message()                # Formatação de erros
├── get_validation_summary()               # Resumo de validações (health check)
└── EnvironmentValidationError             # Exceção customizada
```

**Funcionalidades:**

- ✅ Validação de variáveis obrigatórias
- ✅ Validação específica por ambiente (DEV/TEST/PROD)
- ✅ Mensagens de erro claras e diretas
- ✅ Logging estruturado
- ✅ Função auxiliar para health checks

---

## 🔒 VARIÁVEIS VALIDADAS

### Variáveis Obrigatórias (Todos os Ambientes)

| Variável                    | Descrição                                  | Padrão      |
|-----------------------------|--------------------------------------------|-------------|
| `ENV` / `ENVIRONMENT`       | Ambiente de execução                       | `development` |
| `DATABASE_URL`              | URL de conexão com banco de dados          | *obrigatório* |
| `SQL_AUDIT_ENFORCE`         | Flag de enforcement de auditoria SQL       | `true`      |
| `SQL_AUDIT_ENFORCE_LEVEL`   | Nível de enforcement (warn/error/strict)   | `warn`      |

### Variáveis Adicionais (Contextuais)

| Variável                | Descrição                               | Padrão  |
|-------------------------|-----------------------------------------|---------|
| `DEBUG`                 | Modo debug                              | `false` |
| `ENABLE_GUARDRAILS`     | Guard rails de segurança                | `false` |
| `LOG_LEVEL`             | Nível de logging                        | `INFO`  |

---

## 📋 REGRAS POR AMBIENTE

### 🔒 PRODUCTION (`ENV=production`)

**Regras Obrigatórias:**

1. ❌ `DEBUG = False` (debug DEVE estar desativado)
2. ❌ `ENABLE_GUARDRAILS = False` (guard rails DEVEM estar desativados)
3. ✅ `LOG_LEVEL >= INFO` (INFO, WARNING, ERROR ou CRITICAL)
4. ✅ `SQL_AUDIT_ENFORCE_LEVEL = "error"` ou `"strict"`

**Justificativa:**
- Debug ativado expõe informações sensíveis
- Guard rails impactam performance em produção
- Logs DEBUG geram volume excessivo
- Auditoria SQL deve ser rigorosa

### 🧪 TEST (`ENV=test`)

**Regras Obrigatórias:**

1. ✅ `DATABASE_URL` não pode conter "production" ou "prod"
2. ✅ Guard rails PODEM estar ativos (recomendado)
3. ✅ Debug pode estar ativo

**Justificativa:**
- Evitar acidentalmente usar banco de produção
- Guard rails auxiliam na detecção de problemas

### 🛠️ DEVELOPMENT (`ENV=development`)

**Regras Obrigatórias:**

1. ✅ `DATABASE_URL` não pode conter "production" ou "prod"
2. ✅ Guard rails PODEM estar ativos (recomendado)
3. ✅ Debug pode estar ativo
4. ✅ Logs podem estar em DEBUG

**Justificativa:**
- Evitar acidentalmente usar banco de produção
- Guard rails auxiliam desenvolvimento seguro
- Debug facilita desenvolvimento

---

## 🚨 EXEMPLOS DE ERRO

### Exemplo 1: Variável Obrigatória Ausente

```
================================================================================
❌ FALHA NA VALIDAÇÃO DE SETTINGS
================================================================================

Ambiente: production
Total de erros: 1

Erro 1:
[CRITICAL] Variável SQL_AUDIT_ENFORCE não está definida
           Descrição: Flag de enforcement de auditoria SQL
           Esta variável é OBRIGATÓRIA para inicialização do sistema

================================================================================
⚠️  O sistema NÃO PODE iniciar com estes erros.
    Corrija as configurações e tente novamente.
================================================================================
```

### Exemplo 2: Debug Ativado em Produção

```
================================================================================
❌ FALHA NA VALIDAÇÃO DE SETTINGS
================================================================================

Ambiente: production
Total de erros: 1

Erro 1:
[PRODUCTION] Debug está ATIVADO em produção (valor: True)
             Debug DEVE estar DESATIVADO em produção por segurança

================================================================================
⚠️  O sistema NÃO PODE iniciar com estes erros.
    Corrija as configurações e tente novamente.
================================================================================
```

### Exemplo 3: Guard Rails Ativados em Produção

```
================================================================================
❌ FALHA NA VALIDAÇÃO DE SETTINGS
================================================================================

Ambiente: production
Total de erros: 2

Erro 1:
[PRODUCTION] Guard rails estão ATIVADOS em produção (valor: True)
             Guard rails DEVEM estar DESATIVADOS em produção

Erro 2:
[PRODUCTION] Log level inadequado para produção (valor: DEBUG)
             Log level em produção DEVE ser INFO, WARNING, ERROR ou CRITICAL

================================================================================
⚠️  O sistema NÃO PODE iniciar com estes erros.
    Corrija as configurações e tente novamente.
================================================================================
```

### Exemplo 4: ENV Inválido

```
================================================================================
❌ FALHA NA VALIDAÇÃO DE SETTINGS
================================================================================

Ambiente: staging
Total de erros: 1

Erro 1:
[CRITICAL] ENV inválido: 'staging'
           Valores permitidos: development, test, production

================================================================================
⚠️  O sistema NÃO PODE iniciar com estes erros.
    Corrija as configurações e tente novamente.
================================================================================
```

---

## 🔧 ARQUIVOS MODIFICADOS

### 1. `backend/app/config.py`

**Mudanças:**

```python
class Settings(BaseSettings):
    # ... campos existentes ...
    
    # ✅ NOVOS CAMPOS (Pré-Prod Block 1)
    SQL_AUDIT_ENFORCE: bool = True
    SQL_AUDIT_ENFORCE_LEVEL: str = "warn"
    ENABLE_GUARDRAILS: bool = False
    LOG_LEVEL: str = "INFO"
    
    @property
    def ENV(self) -> str:
        """Alias para ENVIRONMENT"""
        return self.ENVIRONMENT
```

**Exports adicionados:**

```python
SQL_AUDIT_ENFORCE = settings.SQL_AUDIT_ENFORCE
SQL_AUDIT_ENFORCE_LEVEL = settings.SQL_AUDIT_ENFORCE_LEVEL
ENABLE_GUARDRAILS = settings.ENABLE_GUARDRAILS
LOG_LEVEL = settings.LOG_LEVEL
ENV = settings.ENV  # Alias
```

### 2. `backend/app/main.py`

**Mudanças:**

1. **Import adicionado:**
   ```python
   from app.config import settings  # Objeto completo de settings
   from app.core.settings_validation import validate_settings
   ```

2. **Função `validate_environment()` modificada:**
   ```python
   def validate_environment():
       """
       Valida configurações críticas antes do startup.
       
       NOVO (Pré-Prod Block 1):
       - Usa validate_settings() do módulo settings_validation
       - Validações rigorosas de ENV, DATABASE_URL, SQL_AUDIT_*
       - Validações específicas por ambiente (DEV/TEST/PROD)
       - Falha imediatamente se algo estiver incorreto
       """
       
       try:
           validate_settings(settings)
           logger.info("✅ [PRÉ-PROD] Validação de settings concluída com sucesso")
       except Exception as e:
           raise  # Bloqueia inicialização
       
       # ... validações legacy mantidas para compatibilidade ...
   ```

3. **Chamada em `@app.on_event("startup")`:**
   ```python
   @app.on_event("startup")
   def on_startup():
       """Inicialização do sistema"""
       validate_environment()  # ✅ Validação executada ANTES de aceitar requests
       logger.info("\n" + "="*60)
       print_config()
       logger.info("="*60 + "\n")
       # ... resto da inicialização ...
   ```

---

## 🛡️ GARANTIAS FORNECIDAS

### 1️⃣ Inicialização Segura

- ✅ Sistema **NÃO inicia** sem variáveis críticas
- ✅ Sistema **NÃO inicia** com configurações inadequadas para produção
- ✅ Sistema **NÃO inicia** com debug ativado em produção
- ✅ Sistema **NÃO inicia** com guard rails ativados em produção

### 2️⃣ Diferenciação de Ambientes

- ✅ DEV, TEST e PROD têm validações específicas
- ✅ Impossível acidentalmente usar banco de produção em DEV/TEST
- ✅ Configurações de segurança obrigatórias em PROD

### 3️⃣ Auditoria e Rastreabilidade

- ✅ Todas as validações são logadas
- ✅ Erros claros e acionáveis
- ✅ Função `get_validation_summary()` para health checks

### 4️⃣ Compatibilidade

- ✅ Validações legacy mantidas
- ✅ Nenhuma funcionalidade existente quebrada
- ✅ DEV e TEST continuam funcionando normalmente

---

## 🚀 COMO USAR

### Uso Padrão (Automático)

A validação é executada automaticamente no startup:

```python
# backend/app/main.py
@app.on_event("startup")
def on_startup():
    validate_environment()  # ✅ Executado automaticamente
```

### Health Check

Para verificar status das validações sem levantar exceções:

```python
from app.core.settings_validation import get_validation_summary
from app.config import settings

summary = get_validation_summary(settings)

# Retorna:
{
    'environment': 'production',
    'validations': {
        'ENV': {'present': True, 'value': 'production'},
        'DATABASE_URL': {'present': True, 'value': '[HIDDEN]'},
        'SQL_AUDIT_ENFORCE': {'present': True, 'value': True},
        'SQL_AUDIT_ENFORCE_LEVEL': {'present': True, 'value': 'strict'}
    },
    'warnings': [],
    'is_valid': True
}
```

---

## 📊 TESTE DE VALIDAÇÃO

### Teste 1: Ambiente Válido (Development)

```bash
ENV=development
DATABASE_URL=postgresql://user:pass@localhost/petshop_dev
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=warn
DEBUG=true
ENABLE_GUARDRAILS=true
LOG_LEVEL=DEBUG
```

**Resultado:** ✅ Validação passa

### Teste 2: Ambiente Válido (Production)

```bash
ENV=production
DATABASE_URL=postgresql://user:pass@prod-server/petshop
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=strict
DEBUG=false
ENABLE_GUARDRAILS=false
LOG_LEVEL=INFO
```

**Resultado:** ✅ Validação passa

### Teste 3: Ambiente Inválido (Debug em Produção)

```bash
ENV=production
DATABASE_URL=postgresql://user:pass@prod-server/petshop
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=strict
DEBUG=true  # ❌ ERRO
ENABLE_GUARDRAILS=false
LOG_LEVEL=INFO
```

**Resultado:** ❌ `EnvironmentValidationError: Debug está ATIVADO em produção`

### Teste 4: Variável Ausente

```bash
ENV=production
# DATABASE_URL ausente ❌
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=strict
```

**Resultado:** ❌ `EnvironmentValidationError: Variável DATABASE_URL não está definida`

---

## 🔄 PRÓXIMOS PASSOS (FUTUROS BLOCOS)

### Bloco 2: Validação de Banco de Dados
- Validar conexão com banco antes de aceitar requests
- Validar schema/migrations aplicadas
- Validar permissões de usuário do banco

### Bloco 3: Validação de Integrações
- Validar chaves de API externas (se obrigatórias)
- Validar conectividade com serviços externos
- Validar configurações de email/SMS

### Bloco 4: Health Checks Avançados
- Endpoint `/health` com validações completas
- Endpoint `/ready` para Kubernetes
- Métricas de validação

---

## 📝 CHECKLIST DE VALIDAÇÃO

- [x] Arquivo `app/core/settings_validation.py` criado
- [x] Função `validate_settings()` implementada
- [x] Validações obrigatórias implementadas (ENV, DATABASE_URL, SQL_AUDIT_*)
- [x] Validações por ambiente implementadas (DEV/TEST/PROD)
- [x] Mensagens de erro claras e acionáveis
- [x] Logging estruturado
- [x] Integração com `backend/app/main.py`
- [x] Chamada em `@app.on_event("startup")`
- [x] Validações legacy mantidas
- [x] Função `get_validation_summary()` para health checks
- [x] Documentação completa gerada

---

## ✅ CRITÉRIOS DE SUCESSO ATENDIDOS

1. ✅ App não sobe sem variáveis críticas
2. ✅ DEV/TEST continuam funcionando
3. ✅ Produção fica segura
4. ✅ Markdown gerado corretamente

---

## 🎯 IMPACTO

### Segurança
- ⬆️ **ALTO**: Sistema não pode iniciar com configurações inseguras
- ⬆️ **ALTO**: Impossível acidentalmente rodar em produção com debug ativo
- ⬆️ **MÉDIO**: Auditoria SQL garantida em todos os ambientes

### Confiabilidade
- ⬆️ **ALTO**: Erros de configuração detectados imediatamente
- ⬆️ **ALTO**: Mensagens de erro claras e acionáveis
- ⬆️ **MÉDIO**: Logging estruturado facilita diagnóstico

### Operacional
- ⬆️ **MÉDIO**: Redução de incidentes de configuração
- ⬆️ **MÉDIO**: Tempo de diagnóstico reduzido
- ⬆️ **BAIXO**: Overhead mínimo (validação apenas no startup)

---

## 📚 REFERÊNCIAS

- [ARQUITETURA_SISTEMA.md](ARQUITETURA_SISTEMA.md)
- [GUIA_AMBIENTES.md](GUIA_AMBIENTES.md)
- [MULTI_TENANCY_HARDENING.md](MULTI_TENANCY_HARDENING.md)

---

**FIM DO DOCUMENTO**
