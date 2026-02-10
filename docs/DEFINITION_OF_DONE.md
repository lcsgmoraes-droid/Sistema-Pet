# ✅ DEFINITION OF DONE

> **Uma tarefa só está completa quando atende TODOS os critérios**

---

## 🎯 BACKEND - Novo Endpoint/Módulo

### 🧪 Testes (Obrigatório)

- [ ] **Funcional:** Mínimo 5 testes de casos normais
  - [ ] GET: Lista recursos
  - [ ] GET: Busca por ID
  - [ ] POST: Cria recurso (se aplicável)
  - [ ] PUT: Atualiza recurso (se aplicável)
  - [ ] DELETE: Remove recurso (se aplicável)

- [ ] **Resiliente:** Mínimo 4 testes de erros
  - [ ] Erro interno não quebra (500 retorna JSON válido)
  - [ ] Requisições concorrentes (10+ simultâneas)
  - [ ] Unicode e caracteres especiais
  - [ ] Parâmetros extremos (números grandes, strings longas)

- [ ] **Seguro:** Mínimo 6 testes de segurança
  - [ ] Token expirado retorna 401
  - [ ] Token inválido retorna 401
  - [ ] SQL injection bloqueado/sanitizado
  - [ ] XSS payload bloqueado/sanitizado
  - [ ] Isolamento de tenant validado
  - [ ] Rate limiting funciona (100+ requests)

- [ ] **Contrato:** Mínimo 1 teste de schema
  - [ ] Campos obrigatórios presentes
  - [ ] Tipos corretos (int, str, float, date)
  - [ ] Datas em formato ISO 8601
  - [ ] Valores não-negativos onde aplicável

- [ ] **Total:** Mínimo 16 testes PASSANDO (100%)

### 📝 Código (Obrigatório)

- [ ] **Schemas Pydantic:** Request e Response definidos
- [ ] **JWT:** Usa `Depends(get_current_user)`
- [ ] **Tenant:** Usa `Depends(get_tenant_context())`
- [ ] **Service Layer:** Lógica de negócio separada de routes
- [ ] **Error Handling:** Try/catch onde aplicável
- [ ] **Docstrings:** Endpoints documentados (aparecem no Swagger)
- [ ] **Type Hints:** Todos os parâmetros tipados
- [ ] **Helpers:** Usa `tests/helpers` (não reinventa)

### 📁 Estrutura (Obrigatório)

```
backend/app/<modulo>/
├── __init__.py
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic schemas
├── routes.py          # FastAPI endpoints
└── service.py         # Business logic

backend/tests/
└── test_<modulo>_routes.py  # 16+ testes
```

### 🔍 Validações Automáticas (CI)

- [ ] **Lint:** `ruff check app/` passa sem erros
- [ ] **Type Check:** `mypy app/` passa sem erros
- [ ] **Coverage:** Cobertura ≥ 80%
- [ ] **Tests:** Todos os testes passam
- [ ] **Security:** Testes de segurança passam
- [ ] **Contracts:** Testes de contrato passam

---

## 🎨 FRONTEND - Nova Tela/Componente

### 🧪 Testes (Opcional mas Recomendado)

- [ ] **Funcional:** Renderiza corretamente
- [ ] **Interação:** Botões e formulários funcionam
- [ ] **Estados:** Loading, erro, vazio testados
- [ ] **Integração:** API calls mockadas

### 📝 Código (Obrigatório)

- [ ] **TypeScript:** Tipos definidos para props/state
- [ ] **Error Handling:** Try/catch em API calls
- [ ] **Loading States:** Indicadores de carregamento
- [ ] **Error States:** Mensagens de erro amigáveis
- [ ] **Empty States:** Mensagens quando sem dados
- [ ] **Responsivo:** Funciona em mobile e desktop
- [ ] **Acessibilidade:** Labels, alt texts, ARIA (quando aplicável)

### 📁 Estrutura (Obrigatório)

```
frontend/src/
├── pages/
│   └── <Modulo>.jsx       # Página principal
├── components/
│   └── <Modulo>/          # Componentes específicos
│       ├── <Component>.jsx
│       └── ...
└── services/
    └── <modulo>Service.js  # API calls
```

### 🎨 UI/UX (Obrigatório)

- [ ] **Design:** Segue Tailwind classes do sistema
- [ ] **Consistência:** Usa componentes reutilizáveis
- [ ] **Feedback:** Toasts/alertas para sucesso/erro
- [ ] **Validação:** Formulários validam antes de enviar
- [ ] **Navegação:** Breadcrumbs/voltar onde aplicável

---

## 🗄️ BANCO DE DADOS - Nova Tabela/Schema

### 📝 Migration (Obrigatório)

- [ ] **Alembic:** Migration criada (`alembic revision`)
- [ ] **Up:** Script de criação completo
- [ ] **Down:** Script de rollback funcional
- [ ] **Constraints:** PKs, FKs, índices definidos
- [ ] **Defaults:** Valores padrão onde aplicável
- [ ] **Tenant:** Coluna `tenant_id` presente (multi-tenant)
- [ ] **Timestamps:** `created_at`, `updated_at` presentes
- [ ] **Testado:** Migration roda sem erros

### 🔍 Validações (Obrigatório)

- [ ] **Performance:** Índices em colunas de busca/join
- [ ] **Segurança:** RLS (Row Level Security) se PostgreSQL
- [ ] **Integridade:** FKs com ON DELETE apropriado
- [ ] **Docs:** Comentários explicando campos não-óbvios

---

## 🔒 SEGURANÇA - Nova Feature/Endpoint

### ✅ Checklist de Segurança (Obrigatório)

- [ ] **Autenticação:** JWT obrigatório
- [ ] **Autorização:** Verifica permissões do usuário
- [ ] **Tenant Isolation:** Dados isolados por tenant
- [ ] **Input Validation:** Pydantic schemas validam inputs
- [ ] **SQL Injection:** Usa ORMs (não SQL raw)
- [ ] **XSS:** Sanitiza outputs (FastAPI faz automaticamente)
- [ ] **Rate Limiting:** Middleware aplicado
- [ ] **Error Handling:** Erros sanitizados em produção
- [ ] **Logging:** Eventos de segurança logados
- [ ] **Secrets:** Nenhuma senha/chave hardcoded

---

## 📚 DOCUMENTAÇÃO - Nova Feature

### 📝 Docs (Obrigatório)

- [ ] **API Docs:** Swagger atualizado automaticamente
- [ ] **README:** Atualizado se feature muda setup
- [ ] **Changelog:** Entry adicionada (se versionado)
- [ ] **Docstrings:** Funções/classes documentadas

### 🎓 Conhecimento (Recomendado)

- [ ] **Demo:** Apresentação da feature para o time
- [ ] **Tutorial:** Guia rápido de uso (se complexo)
- [ ] **Troubleshooting:** Problemas comuns documentados

---

## 🚀 DEPLOY - Pronto para Produção

### ✅ Checklist de Deploy (Obrigatório)

- [ ] **Tests:** 100% passando em CI
- [ ] **Migrations:** Rodadas em staging
- [ ] **Env Vars:** Configuradas em produção
- [ ] **Logs:** Monitoramento configurado
- [ ] **Rollback Plan:** Plano B documentado
- [ ] **Load Test:** Performance validada (se crítico)
- [ ] **Backup:** Backup recente disponível
- [ ] **Team:** Time notificado sobre deploy

---

## 🎯 CRITÉRIOS POR TIPO DE TAREFA

### 🐛 Bug Fix
- [ ] Bug reproduzido em teste
- [ ] Fix implementado
- [ ] Teste de regressão adicionado
- [ ] Root cause documentada

### ✨ Feature Nova
- [ ] Todos os critérios de Backend/Frontend aplicáveis
- [ ] Mínimo 16 testes no backend
- [ ] UI funcional no frontend
- [ ] Documentação atualizada

### 🔧 Refactoring
- [ ] Testes existentes ainda passam
- [ ] Comportamento externo idêntico
- [ ] Cobertura de testes mantida/aumentada
- [ ] Performance mantida/melhorada

### 📈 Performance
- [ ] Benchmark antes/depois documentado
- [ ] Melhoria ≥ 20% em métrica alvo
- [ ] Nenhuma regressão em outras áreas
- [ ] Load test validado

---

## 🚫 NÃO ESTÁ DONE SE...

- ❌ Testes falhando
- ❌ Lint/Type errors
- ❌ Código comentado/debug prints
- ❌ TODOs sem issue criada
- ❌ Warnings no console
- ❌ Falta autenticação/autorização
- ❌ Falta isolamento de tenant
- ❌ Erro 500 sem tratamento
- ❌ Migration sem rollback
- ❌ Hardcoded secrets/configs
- ❌ Breaking changes sem comunicação

---

## 💡 DICAS PARA VELOCIDADE

### 🚀 Como Completar Mais Rápido

1. **Use os Helpers:** `tests/helpers` economiza 70% do tempo
2. **Copy-Paste Inteligente:** Copie `test_analytics_routes.py` como base
3. **Test First:** Escreva testes antes (TDD)
4. **Paralelizar:** Rode `pytest -n auto` (múltiplos cores)
5. **Incremental:** Commite funcional → resiliente → seguro → contrato

### ⚡ Exemplo de Velocidade Real

Com helpers + blueprint:
- **Antes:** 2-3 dias para módulo completo
- **Agora:** 4-6 horas para módulo completo
- **Ganho:** 4x mais rápido

---

## 🎓 TREINAMENTO

### Para Novos Devs

1. Ler `docs/BLUEPRINT_BACKEND.md`
2. Estudar `tests/test_analytics_routes.py` (referência)
3. Praticar com módulo simples (ex: `categorias`)
4. Code review com dev senior
5. Deploy primeiro módulo

**Tempo estimado:** 1-2 semanas para autonomia completa

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Meta |
|---------|------|
| Testes passando | 100% |
| Cobertura de código | ≥ 80% |
| Tempo de CI | < 5 min |
| Bugs em produção | < 1/sprint |
| Tenant leaks | 0 |
| Security issues | 0 |
| Response time p95 | < 200ms |
| Uptime | ≥ 99.9% |

---

## 🏆 EXEMPLOS REAIS

### ✅ Feature Completa (Definition of Done 100%)

- `tests/test_analytics_routes.py`
  - 53 testes (100% passing)
  - Funcional + Resiliente + Seguro + Contrato
  - Usa helpers
  - Schemas Pydantic
  - JWT + Tenant
  - Middlewares ativos
  - Docs no Swagger

### ❌ Feature Incompleta (Não seguiu DoD)

- Endpoint sem testes
- Sem validação de JWT
- Sem isolamento de tenant
- SQL raw injection
- Erro 500 expõe stack trace
- Sem schema Pydantic

**Resultado:** Vulnerabilidades, bugs, dívida técnica

---

## 🔄 PROCESSO DE REVIEW

### Checklist do Reviewer

1. [ ] Rodar testes localmente (devem passar)
2. [ ] Verificar cobertura (≥ 80%)
3. [ ] Validar uso de helpers
4. [ ] Conferir schemas Pydantic
5. [ ] Testar JWT/Tenant manualmente
6. [ ] Verificar error handling
7. [ ] Conferir Swagger docs
8. [ ] Validar migrations (se aplicável)
9. [ ] Code style consistente
10. [ ] Sem TODOs/commented code

**Se falhar qualquer item → Request Changes**

---

## 💬 Contato

Dúvidas sobre Definition of Done?

- Consulte: `docs/BLUEPRINT_BACKEND.md`
- Exemplo: `tests/test_analytics_routes.py`
- Helpers: `tests/helpers/`

---

🎯 **Última atualização:** 08/02/2026  
📋 **Versão:** 1.0  
✅ **Enforcement:** Obrigatório para todos os PRs
