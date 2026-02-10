# 🚀 FASE 3: Telemetria & Feature Flags (Mês 2-3)

> **Quando implementar:** Após observabilidade básica + 1 mês em produção  
> **Por quê:** Sistema estável + Dados reais = Experimentos seguros

---

## 🎯 Objetivos

1. **Telemetria de Uso:** Entender COMO usuários usam o sistema
2. **Métricas de Negócio Real-Time:** Dashboard executivo atualizado
3. **Feature Flags:** Deploy features sem riscos
4. **A/B Testing:** Validar hipóteses com dados

---

## 🛠️ Stack Recomendada

| Ferramenta | Propósito | Custo |
|------------|-----------|-------|
| **PostHog** | Product Analytics | Grátis até 1M events/mês |
| **LaunchDarkly** | Feature flags | Grátis até 1K MAU |
| **Mixpanel** | Event tracking (alt) | Grátis até 100K events/mês |
| **WebSockets** | Real-time metrics | Self-hosted (grátis) |
| **Redis** | Cache metrics | Self-hosted (grátis) |

**Custo total:** $0-50/mês (início)

---

## 📊 PARTE 1: Telemetria de Uso (Semana 1-2)

### Por Que Telemetria?

**Sem telemetria:**
- "Acho que os usuários gostam da feature X"
- "Parece que ninguém usa Y"
- "Não sei onde otimizar"

**Com telemetria:**
- "87% dos usuários clicam em X nas primeiras 2 horas"
- "Feature Y tem 3% de adoção → deprecar ou melhorar?"
- "Página Z leva 5s → prioridade de otimização"

---

### PostHog Implementation

**Backend:**
```python
# backend/requirements.txt
posthog==3.0.0

# backend/app/telemetry.py
import posthog
from app.config import POSTHOG_API_KEY, ENVIRONMENT

posthog.api_key = POSTHOG_API_KEY
posthog.host = 'https://app.posthog.com'
posthog.disabled = ENVIRONMENT == "development"

def track_event(user_id: int, event: str, properties: dict = None):
    """Track user event"""
    if properties is None:
        properties = {}
    
    posthog.capture(
        distinct_id=str(user_id),
        event=event,
        properties={
            **properties,
            "environment": ENVIRONMENT
        }
    )

def identify_user(user_id: int, tenant_id: str, email: str):
    """Set user properties"""
    posthog.identify(
        distinct_id=str(user_id),
        properties={
            "email": email,
            "tenant_id": tenant_id,
            "environment": ENVIRONMENT
        }
    )
```

**Usage em Routes:**
```python
# backend/app/vendas/routes.py
from app.telemetry import track_event

@router.post("/vendas")
def criar_venda(venda: VendaCreate, current_user = Depends(get_current_user)):
    # ... criar venda ...
    
    track_event(
        user_id=current_user.id,
        event="venda_criada",
        properties={
            "valor": venda.total,
            "itens_count": len(venda.itens),
            "metodo_pagamento": venda.metodo_pagamento,
            "tenant_id": current_user.tenant_id
        }
    )
    
    return venda
```

**Frontend:**
```javascript
// frontend/src/lib/telemetry.js
import posthog from 'posthog-js'

export function initTelemetry() {
  posthog.init('YOUR_POSTHOG_KEY', {
    api_host: 'https://app.posthog.com',
    capture_pageview: true,
    capture_pageleave: true
  })
}

export function trackEvent(eventName, properties) {
  posthog.capture(eventName, properties)
}

export function identifyUser(userId, userProperties) {
  posthog.identify(userId, userProperties)
}

// Usage
trackEvent('botao_nova_venda_clicado', { origem: 'dashboard' })
trackEvent('filtro_aplicado', { tipo: 'data', valor: '2026-02' })
```

---

### Eventos Críticos para Rastrear

**Autenticação:**
```
- login_sucesso
- login_falha
- logout
- reset_senha_solicitado
- reset_senha_completo
```

**Vendas:**
```
- venda_criada
- venda_editada
- venda_cancelada
- venda_visualizada
- busca_venda (query)
- filtro_aplicado (tipo, valor)
- relatorio_gerado (tipo)
```

**Analytics:**
```
- dashboard_acessado
- grafico_visualizado (tipo)
- periodo_alterado (de, ate)
- exportacao_dados (formato)
```

**Onboarding:**
```
- primeiro_login
- tutorial_iniciado
- tutorial_completo
- tutorial_pulado
- feature_descoberta (qual)
```

**Erros:**
```
- erro_frontend (tipo, mensagem)
- erro_validacao (campo)
- erro_permissao (endpoint)
- timeout_request (endpoint)
```

---

### Dashboards PostHog

**1. User Journey:**
- Funil de conversão (login → primeira venda)
- Taxa de abandono por tela
- Tempo médio por tarefa
- Retention (D1, D7, D30)

**2. Feature Adoption:**
- Top 10 features mais usadas
- Features nunca usadas (candidatas a remover)
- Tempo até primeira adoção
- Power users vs casual users

**3. Performance UX:**
- Páginas mais lentas (tempo de carregamento)
- Erros mais comuns
- Navegadores/devices com problemas
- Rage clicks (cliques frustrados)

**4. Business Impact:**
- Conversão login → venda
- Correlação feature X → receita
- Churn prediction
- NPS score tracking

---

## 🔄 PARTE 2: Métricas Real-Time (Semana 3-4)

### Dashboard Executivo Live

**Stack:**
- WebSockets (FastAPI)
- Redis (cache)
- Chart.js (frontend)

**Backend:**
```python
# backend/app/realtime/websocket.py
from fastapi import WebSocket
import asyncio
import redis
from app.analytics.service import AnalyticsService

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket, current_user = Depends(get_current_user)):
    await websocket.accept()
    
    try:
        while True:
            # Ler métricas do Redis (atualizadas por workers)
            metrics = {
                "vendas_hora": redis_client.get(f"metrics:vendas_hora:{current_user.tenant_id}"),
                "receita_hora": redis_client.get(f"metrics:receita_hora:{current_user.tenant_id}"),
                "usuarios_online": redis_client.get(f"metrics:online:{current_user.tenant_id}"),
                "conversao_rate": redis_client.get(f"metrics:conversao:{current_user.tenant_id}")
            }
            
            await websocket.send_json(metrics)
            await asyncio.sleep(5)  # Update a cada 5s
            
    except WebSocketDisconnect:
        pass
```

**Worker para atualizar Redis:**
```python
# backend/app/workers/metrics_worker.py
import asyncio
from app.analytics.service import AnalyticsService
import redis

redis_client = redis.Redis(host='localhost', port=6379)

async def update_metrics_loop():
    while True:
        # Para cada tenant ativo
        tenants = get_active_tenants()
        
        for tenant_id in tenants:
            # Calcular métricas
            vendas_hora = AnalyticsService.vendas_ultima_hora(tenant_id)
            receita_hora = AnalyticsService.receita_ultima_hora(tenant_id)
            usuarios_online = AnalyticsService.usuarios_online(tenant_id)
            
            # Salvar no Redis (TTL 10 min)
            redis_client.setex(f"metrics:vendas_hora:{tenant_id}", 600, vendas_hora)
            redis_client.setex(f"metrics:receita_hora:{tenant_id}", 600, receita_hora)
            redis_client.setex(f"metrics:online:{tenant_id}", 600, usuarios_online)
        
        await asyncio.sleep(30)  # Recalcular a cada 30s

# Run worker
asyncio.run(update_metrics_loop())
```

**Frontend:**
```javascript
// frontend/src/components/RealtimeMetrics.jsx
import { useEffect, useState } from 'react'

export function RealtimeMetrics() {
  const [metrics, setMetrics] = useState(null)
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/metrics')
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setMetrics(data)
    }
    
    return () => ws.close()
  }, [])
  
  if (!metrics) return <div>Carregando...</div>
  
  return (
    <div className="grid grid-cols-4 gap-4">
      <MetricCard
        title="Vendas/Hora"
        value={metrics.vendas_hora}
        icon="📈"
        trend="+12%"
      />
      <MetricCard
        title="Receita/Hora"
        value={`R$ ${metrics.receita_hora}`}
        icon="💰"
        trend="+8%"
      />
      <MetricCard
        title="Usuários Online"
        value={metrics.usuarios_online}
        icon="👥"
        trend="stable"
      />
      <MetricCard
        title="Taxa Conversão"
        value={`${metrics.conversao_rate}%`}
        icon="🎯"
        trend="-2%"
      />
    </div>
  )
}
```

---

## 🎛️ PARTE 3: Feature Flags (Semana 5-6)

### Por Que Feature Flags?

**Benefícios:**
1. **Deploy sem medo:** Feature vai mas fica desligada
2. **Rollout gradual:** 10% users → 50% → 100%
3. **Kill switch:** Problema? Desliga sem redeploy
4. **A/B testing:** 50% vê versão A, 50% vê B
5. **Beta testers:** Só certos usuários veem feature

---

### LaunchDarkly Implementation

**Backend:**
```python
# backend/requirements.txt
launchdarkly-server-sdk==8.0.0

# backend/app/feature_flags.py
import ldclient
from ldclient.config import Config
from app.config import LAUNCHDARKLY_SDK_KEY

ldclient.set_config(Config(LAUNCHDARKLY_SDK_KEY))
ld_client = ldclient.get()

def is_feature_enabled(flag_key: str, user_id: int, tenant_id: str, default: bool = False) -> bool:
    """Check if feature flag is enabled for user"""
    user = {
        "key": str(user_id),
        "custom": {
            "tenant_id": tenant_id
        }
    }
    
    return ld_client.variation(flag_key, user, default)

def get_feature_variant(flag_key: str, user_id: int, tenant_id: str, default: str = "control") -> str:
    """Get feature flag variant (for A/B testing)"""
    user = {
        "key": str(user_id),
        "custom": {
            "tenant_id": tenant_id
        }
    }
    
    return ld_client.variation(flag_key, user, default)
```

**Usage:**
```python
# backend/app/vendas/routes.py
from app.feature_flags import is_feature_enabled, get_feature_variant

@router.get("/vendas")
def listar_vendas(current_user = Depends(get_current_user)):
    vendas = VendasService.listar(current_user.tenant_id)
    
    # Feature flag: Nova UI de listagem
    if is_feature_enabled("nova_ui_vendas", current_user.id, current_user.tenant_id):
        return formatar_vendas_v2(vendas)  # Nova versão
    else:
        return formatar_vendas_v1(vendas)  # Versão antiga
    
@router.post("/vendas")
def criar_venda(venda: VendaCreate, current_user = Depends(get_current_user)):
    # A/B test: Algoritmo de desconto
    variant = get_feature_variant("algoritmo_desconto", current_user.id, current_user.tenant_id)
    
    if variant == "experimental":
        desconto = calcular_desconto_v2(venda)  # Novo algoritmo
    else:
        desconto = calcular_desconto_v1(venda)  # Algoritmo atual
    
    venda.desconto = desconto
    return VendasService.criar(venda)
```

**Frontend:**
```javascript
// frontend/src/lib/featureFlags.js
import { initialize } from 'launchdarkly-js-client-sdk'

let ldClient = null

export async function initFeatureFlags(user) {
  ldClient = initialize('YOUR_CLIENT_KEY', {
    key: user.id.toString(),
    custom: {
      tenant_id: user.tenant_id
    }
  })
  
  await ldClient.waitForInitialization()
}

export function isFeatureEnabled(flagKey, defaultValue = false) {
  if (!ldClient) return defaultValue
  return ldClient.variation(flagKey, defaultValue)
}

// Usage
import { isFeatureEnabled } from '@/lib/featureFlags'

function VendasPage() {
  const novaUI = isFeatureEnabled('nova_ui_vendas', false)
  
  return novaUI ? <VendasListV2 /> : <VendasListV1 />
}
```

---

### Estratégias de Rollout

**1. Canary Release (10% → 100%)**
```
Dia 1: 10% usuários (beta testers)
Dia 3: 25% usuários
Dia 5: 50% usuários
Dia 7: 100% usuários
```

**2. Ring Deployment**
```
Ring 1: Equipe interna (1%)
Ring 2: Beta users (5%)
Ring 3: Tenants específicos (20%)
Ring 4: Todos (100%)
```

**3. Targeted Rollout**
```
- Apenas tenant X (early adopter)
- Apenas usuários com plano premium
- Apenas região Sul
- Apenas usuários ativos (login últimos 7 dias)
```

---

### Feature Flags Úteis

```yaml
Flags:
  # UI
  - nova_ui_vendas: bool
  - dark_mode: bool
  - layout_compacto: bool
  
  # Features
  - integracao_whatsapp: bool
  - relatorios_avancados: bool
  - multi_moeda: bool
  
  # Performance
  - cache_agressivo: bool
  - lazy_loading: bool
  - infinite_scroll: bool
  
  # Experimental
  - algoritmo_desconto: string (control | experimental)
  - recomendacao_produtos: string (off | v1 | v2)
  - checkout_flow: string (single | multi_step)
```

---

## 📊 PARTE 4: A/B Testing (Semana 7-8)

### Experimentos com Dados

**Exemplo 1: Botão de CTA**
```javascript
// Variante A: "Criar Venda" (verde)
// Variante B: "Nova Venda" (azul)
// Métrica: Taxa de cliques

const variant = getFeatureVariant('cta_nova_venda', 'control')

<button 
  className={variant === 'experimental' ? 'bg-blue-500' : 'bg-green-500'}
  onClick={() => {
    trackEvent('botao_nova_venda_clicado', { variant })
    criarVenda()
  }}
>
  {variant === 'experimental' ? 'Nova Venda' : 'Criar Venda'}
</button>
```

**Exemplo 2: Algoritmo de Recomendação**
```python
variant = get_feature_variant("recomendacao_produtos", user_id, tenant_id)

if variant == "collaborative_filtering":
    produtos = RecomendacaoService.collaborative_filtering(user_id)
elif variant == "content_based":
    produtos = RecomendacaoService.content_based(user_id)
else:  # control
    produtos = RecomendacaoService.mais_vendidos()

# Track para análise posterior
track_event(user_id, "produtos_recomendados_exibidos", {
    "variant": variant,
    "produtos_count": len(produtos)
})
```

**Análise:**
```python
# Após 2 semanas de experimento
conversao_control = 12.5%
conversao_collaborative = 15.8%
conversao_content = 11.2%

# Collaborative filtering vence! (+26% conversão)
# → Fazer rollout 100%
# → Deprecar content_based
```

---

## ✅ Checklist Completo

### Semana 1-2: Telemetria
- [ ] Criar conta PostHog
- [ ] Configurar backend SDK
- [ ] Configurar frontend SDK
- [ ] Instrumentar 20+ eventos críticos
- [ ] Criar dashboards principais
- [ ] Configurar retention cohorts
- [ ] Treinar time em análise

### Semana 3-4: Real-Time Metrics
- [ ] Setup Redis
- [ ] Criar WebSocket endpoint
- [ ] Implementar metrics worker
- [ ] Dashboard executivo frontend
- [ ] Alertas de anomalias
- [ ] Otimizar performance (cache)
- [ ] Load testing (1000+ usuários simultâneos)

### Semana 5-6: Feature Flags
- [ ] Criar conta LaunchDarkly
- [ ] Configurar SDK backend/frontend
- [ ] Migrar 5 features para flags
- [ ] Criar flags de experimentos
- [ ] Documentar processo rollout
- [ ] Treinar time em uso
- [ ] Definir kill switch automático

### Semana 7-8: A/B Testing
- [ ] Definir 3 experimentos prioritários
- [ ] Configurar tracking de métricas
- [ ] Rodar experimentos (min 2 semanas)
- [ ] Análise estatística (significance)
- [ ] Decisão: ship/kill features
- [ ] Documentar learnings
- [ ] Roadmap próximos experimentos

---

## 🎯 Métricas de Sucesso

Após Fase 3, você terá:

✅ **Telemetria:** 20+ eventos rastreados, 90%+ cobertura  
✅ **Real-time:** Dashboard executivo atualizado < 30s  
✅ **Feature Flags:** 100% features novas com flags  
✅ **A/B Testing:** 1 experimento/mês, decisões data-driven  
✅ **MTTR:** < 15min (feature flags como kill switch)  
✅ **Deploy Confidence:** 95%+ (rollout gradual)

---

## 💰 Custos Finais

| Tier | MAU | Custo/Mês |
|------|-----|-----------|
| **Startup** | < 1K | $0 (free tiers) |
| **Growth** | 1K-10K | $50-150 |
| **Scale** | 10K-100K | $300-800 |
| **Enterprise** | 100K+ | $1500+ |

---

## 🚀 ROI Esperado

**Investimento:** 8 semanas part-time (~120h)

**Retorno:**
- **Conversão:** +15-30% (otimizações baseadas em dados)
- **Churn:** -20-40% (detectar problemas antes)
- **Deploy velocity:** +50% (feature flags)
- **Bug fixes:** -60% tempo (telemetria)
- **Revenue:** +25-50% (A/B testing otimizado)

**Break-even:** 2-3 meses

---

🎯 **Início recomendado:** Mês 2-3 de produção  
⏱️ **Tempo total:** 8 semanas part-time  
💰 **Custo inicial:** $0-50/mês  
📈 **ROI esperado:** 10-20x (1 ano)
