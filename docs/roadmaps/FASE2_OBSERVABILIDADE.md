# 📊 FASE 2: Observabilidade (Semana 2-4)

> **Quando implementar:** APÓS MVP em produção  
> **Por quê:** Dados reais + Sistema estável = Insights valiosos

---

## 🎯 Objetivo

Ter visibilidade completa do sistema para:
1. Detectar problemas antes do usuário reclamar
2. Diagnosticar bugs rapidamente
3. Otimizar performance com dados

---

## 🛠️ Stack Recomendada

| Ferramenta | Propósito | Custo |
|------------|-----------|-------|
| **Sentry** | Error tracking | Grátis até 5K events/mês |
| **Prometheus** | Métricas | Open source (self-host) |
| **Grafana** | Dashboards | Open source (self-host) |
| **Uptime Robot** | Availability monitoring | Grátis até 50 monitors |
| **Papertrail** | Log aggregation | Grátis até 100MB/mês |

**Custo total:** $0-20/mês (início)

---

## 📋 Implementação (Ordem Priorizada)

### 1️⃣ **Sentry: Error Tracking (2-3h)**

**Por quê primeiro?** Bugs em produção = prioridade máxima

```python
# backend/app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "production"),
    traces_sample_rate=0.1,  # 10% das transações
    profiles_sample_rate=0.1,
    integrations=[FastApiIntegration()]
)
```

**Frontend:**
```javascript
// frontend/src/main.jsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "YOUR_SENTRY_DSN",
  environment: import.meta.env.MODE,
  tracesSampleRate: 0.1,
});
```

**Alertas:**
- Email quando erro novo
- Slack quando rate > 1%
- PagerDuty quando erro crítico (500) > 10/min

---

### 2️⃣ **Uptime Robot: Availability (30min)**

**Por quê?** Saber se sistema está no ar

```
Monitors:
1. https://api.seupet.com/health → 5min intervals
2. https://seupet.com/login → 5min intervals
3. https://seupet.com/dashboard → 5min intervals

Alertas:
→ Email quando down
→ SMS quando down > 5min (premium)
→ Webhook para Slack
```

**Endpoint de health:**
```python
# backend/app/main.py
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
```

---

### 3️⃣ **Prometheus + Grafana: Métricas (4-6h)**

**Por quê?** Ver tendências de performance

```python
# backend/requirements.txt
prometheus-fastapi-instrumentator==6.1.0

# backend/app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

**Métricas automáticas:**
- Requests/segundo
- Response times (p50, p95, p99)
- Erros 4xx/5xx
- Request duration histogramas

**Dashboard Grafana:**
```
Painéis:
1. Traffic (requests/min)
2. Latency (p95, p99)
3. Errors (rate, count)
4. Saturation (CPU, RAM, DB connections)
```

---

### 4️⃣ **Structured Logging: Papertrail (2h)**

**Por quê?** Logs centralizados = debug fácil

```python
# backend/app/config.py
import logging
from pythonjsonlogger import jsonlogger

handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(name)s %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
```

**Já temos structured logging!** Só precisa enviar para Papertrail.

**Queries úteis:**
```
- "error" AND tenant_id:abc123
- status_code:500 last 1 hour
- endpoint:/api/vendas response_time:>1000
```

---

### 5️⃣ **Custom Metrics: Negócio (3-4h)**

**Por quê?** Métricas de negócio = ROI visível

```python
# backend/app/metrics.py
from prometheus_client import Counter, Histogram

# Métricas de negócio
vendas_criadas = Counter(
    'vendas_criadas_total',
    'Total de vendas criadas',
    ['tenant_id', 'status']
)

receita_total = Counter(
    'receita_total_reais',
    'Receita total em reais',
    ['tenant_id']
)

ticket_medio = Histogram(
    'venda_valor_reais',
    'Valor de cada venda',
    ['tenant_id']
)

# Uso
@router.post("/vendas")
def criar_venda(venda: VendaCreate):
    # ... criar venda ...
    vendas_criadas.labels(tenant_id=tenant_id, status="finalizada").inc()
    receita_total.labels(tenant_id=tenant_id).inc(venda.total)
    ticket_medio.labels(tenant_id=tenant_id).observe(venda.total)
    return venda
```

**Dashboard de Negócio:**
- Vendas/hora
- Receita/hora
- Ticket médio
- Taxa de conversão
- Clientes ativos

---

## 🚨 Alertas Críticos

### Configurar no Grafana:

```yaml
Alertas:
  - name: "API Down"
    condition: up == 0 for 2min
    action: PagerDuty (SMS)
  
  - name: "High Error Rate"
    condition: error_rate > 5% for 5min
    action: Slack + Email
  
  - name: "Slow Responses"
    condition: p95_latency > 2s for 10min
    action: Slack
  
  - name: "High CPU"
    condition: cpu_usage > 80% for 15min
    action: Email
  
  - name: "Database Slow"
    condition: db_query_time > 1s for 5min
    action: Slack
```

---

## 📊 Dashboards Essenciais

### 1. **Overview Dashboard**
- Requests/min (agora)
- Error rate (últimas 24h)
- P95 latency (últimas 24h)
- Active users (agora)

### 2. **Performance Dashboard**
- Response times (p50, p95, p99)
- Database query times
- Slow endpoints (top 10)
- Cache hit rate

### 3. **Business Dashboard**
- Vendas/hora
- Receita/hora
- Novos clientes/dia
- Produtos mais vendidos
- Tenants ativos

### 4. **Errors Dashboard**
- Error rate por endpoint
- Errors por tipo (500, 400, etc)
- Top errors (Sentry link)
- Error timeline

---

## ✅ Checklist de Implementação

**Semana 2:**
- [ ] Configurar Sentry (backend + frontend)
- [ ] Criar conta Uptime Robot
- [ ] Adicionar monitors (/health, /login, /dashboard)
- [ ] Configurar alertas Sentry → Slack
- [ ] Testar alertas (forçar erro)

**Semana 3:**
- [ ] Instalar Prometheus + Grafana (Docker)
- [ ] Instrumentar FastAPI
- [ ] Criar dashboard "Overview"
- [ ] Criar dashboard "Performance"
- [ ] Configurar alertas críticos

**Semana 4:**
- [ ] Configurar Papertrail
- [ ] Enviar logs structured
- [ ] Criar métricas de negócio custom
- [ ] Dashboard "Business"
- [ ] Treinamento time: Como usar dashboards

---

## 🎯 Métricas de Sucesso

Após implementação, você terá:

✅ **MTTD** (Mean Time To Detect): < 5 min  
✅ **MTTR** (Mean Time To Resolve): < 30 min  
✅ **Uptime**: 99.9%+ visível  
✅ **Error budget**: 0.1% (52min downtime/mês)  
✅ **Alertas falsos**: < 5% (configuração refinada)

---

## 💰 Custos Estimados

| Tier | Usuários | Custo/Mês |
|------|----------|-----------|
| **MVP** | < 100 | $0 (tiers free) |
| **Growth** | 100-1000 | $20-50 |
| **Scale** | 1000-10K | $100-300 |
| **Enterprise** | 10K+ | $500+ (APM full) |

---

## 🚀 Quick Start (Mín Viável)

**1 dia de trabalho:**

```bash
# 1. Sentry (2h)
pip install sentry-sdk
# Configurar DSN
# Deploy

# 2. Uptime Robot (30min)
# Criar conta
# Adicionar 3 monitors
# Configurar email

# 3. Health endpoint (30min)
# Adicionar /health
# Testar
# Deploy

# PRONTO: Alertas básicos funcionando
```

**Próxima iteração:** Prometheus + Grafana (fim de semana)

---

🎯 **Início recomendado:** Após 1 semana em produção  
⏱️ **Tempo total:** 2-3 semanas part-time  
💰 **Custo inicial:** $0
