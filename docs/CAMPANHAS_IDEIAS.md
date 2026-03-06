# Sistema de Campanhas — Análise e Estrutura

> Documento de planejamento — não é especificação técnica final.  
> Data: Março 2026

---

## 1. Visão Geral — O que você quer

Criar um motor de campanhas que:
- Roda automaticamente em background (disparadores por evento ou agendamento)
- Gera cupons/créditos/notificações sem intervenção manual
- Funciona nos 3 canais: **PDV, App, Ecommerce**
- Tem unificação de cadastros via CPF
- Permite ao dono do petshop parametrizar tudo (sem mexer em código)

---

## 2. Análise de Complexidade — Honesta

### O que é simples e vale muito
| Campanha | Complexidade | Por quê |
|---|---|---|
| Aniversário do cliente | ⭐ Baixa | Só precisa de job diário + e-mail/push |
| Aniversário do pet | ⭐ Baixa | Mesmo mecanismo |
| Clientes inativos (30/60/90 dias) | ⭐⭐ Média | Job recorrente + controle "já enviado" |
| Primeiro cadastro no app | ⭐ Baixa | Disparo único no evento de cadastro |
| Primeiro cadastro no ecommerce | ⭐ Baixa | Mesmo mecanismo |
| Comprou hoje → desconto se voltar em 7 dias | ⭐⭐ Média | Lógica de janela de tempo |

### O que é médio e precisa de atenção
| Campanha | Complexidade | Por quê |
|---|---|---|
| Cartão fidelidade virtual | ⭐⭐ Média | Gatilho na venda + controle de carimbos + geração de crédito |
| Cashback por canal | ⭐⭐⭐ Média-Alta | % dinâmico por canal + geração de crédito automática |
| Ranking de clientes (bronze/prata/ouro/diamante) | ⭐⭐ Média | Recalculo periódico + regras configuráveis |
| Cliente que mais gastou no mês | ⭐⭐ Média | Ranking mensal + disparo único por mês |
| Pesquisa de satisfação | ⭐⭐⭐ Média-Alta | UI de formulário + lógica de resposta + geração de cupom |

### O que é complexo e pode travar tudo se feito errado
| Item | Complexidade | Por quê |
|---|---|---|
| **Unificação via CPF entre PDV/App/Ecommerce** | 🔴 Alta | É o coração de tudo. Migração de dados, deduplicação, sincronização contínua. Se errado, um cliente vira dois e perde histórico |
| **Sorteios** | ⭐⭐⭐ Média-Alta | Lógica de elegibilidade + aleatoriedade auditável + comunicação |
| **Notificações push em escala** | ⭐⭐ Média | Infraestrutura de fila (hoje tem FCM, ok) |
| **Controle de "não notificar duplicado"** | ⭐⭐ Média | Tabela de log por campanha+cliente — essencial para não irritar cliente |

---

## 3. O Problema Central: Unificação via CPF

Este é o ponto mais crítico de todo o projeto.

**Situação atual:** um cliente pode ter 3 cadastros diferentes:
- Cadastro no PDV (ERP) — CPF opcional hoje
- Cadastro no App — sem campo de CPF ainda
- Cadastro no Ecommerce — tem CPF, mas não obrigatório

**Estratégia definida — vinculação manual com sugestão automática:**
1. CPF nunca será obrigatório para comprar, mas será o "passaporte" para campanhas cross-canal
2. No app: adicionar campo CPF no cadastro inicial
3. No ecommerce: tornar CPF obrigatório
4. No PDV: funcionário incentiva o cliente a informar CPF na hora do cadastro
5. O sistema compara nome + telefone + e-mail entre os canais e, ao encontrar similaridade alta, **sugere o vínculo** — o usuário do sistema ou o próprio cliente confirma o merge
6. Após vínculo confirmado, todo o histórico de compras de todos os canais passa a contar junto para campanhas

**Comunicação para o cliente:** ao se cadastrar no app ou ecommerce, sistema avisa:  
*"Informe seu CPF para participar de promoções exclusivas e acumular benefícios em todos os nossos canais."*

**Riscos sob controle:**
- Sem unificação automática: nenhum merge acontece sem confirmação
- CPF errado: o vínculo pode ser desfeito manualmente pelo operador
- Clientes sem CPF: participam apenas das campanhas do canal onde estão cadastrados

---

## 4. Estrutura das Campanhas — Minha Sugestão de Organização

### Categoria A — Campanhas Globais (sempre ativas enquanto ligadas)
São vinculadas a TODOS os clientes automaticamente.

```
┌─────────────────────────────────────────────────────────┐
│  Cartão Fidelidade Virtual                               │
│  - X reais por carimbo                                   │
│  - N carimbos para completar                             │
│  - Recompensa ao completar (crédito ou brinde)           │
│  - Recompensa intermediária (ex: brinde com 5 carimbos)  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Cashback                                                │
│  - % por nº de canais ativos (1 canal = 1%, 2 = 2%...)  │
│  - Gera crédito automático após cada compra              │
└─────────────────────────────────────────────────────────┘
```

> **Nota:** As duas podem coexistir. O usuário ativa/desativa cada uma independentemente.

---

### Categoria B — Campanhas Sazonais (disparo único por evento)
Cada uma dispara uma vez para cada cliente elegível.

| # | Nome | Gatilho | Recompensa |
|---|------|---------|-----------|
| 1 | Aniversário do cliente | Data de nascimento = hoje | Cupom de R$ X válido no dia |
| 2 | Aniversário do pet | Data de nasc. do pet = hoje | Cupom ou brinde |
| 9 | 1ª compra no App | Cadastro no app | Cupom de boas-vindas |
| 10 | 1ª compra no Ecommerce | Cadastro no site | Cupom de boas-vindas |

---

### Categoria C — Campanhas de Retenção (disparo por inatividade)
O usuário cria quantas quiser (botão +).

| Gatilho | Recompensa |
|---------|-----------|
| Não compra há 30 dias | Cupom de desconto |
| Não compra há 60 dias | Cupom maior |
| Não compra há 90 dias + pesquisa | Cupom + formulário "Por que sumiu?" |

> **Controle importante:** o sistema não pode reenviar para quem já recebeu na mesma "rodada".

---

### Categoria D — Campanhas de Destaque Mensal
Disparo no dia 1 de cada mês para os vencedores do mês anterior.

| # | Critério | Recompensa |
|---|---------|----------|
| 4 | Maior gasto no mês | Brinde (mensagem parametrizável) |
| 5 | Mais compras no mês | Brinde (mensagem parametrizável) |
| 6 | Mais unidades compradas | Brinde (mensagem parametrizável) |

**Regra anti-duplicidade entre campanhas D:** um cliente nunca ganha mais de 1 brinde neste grupo no mesmo mês.
- Sistema calcula o ranking completo (1º, 2º, 3º…) para cada critério
- Ao montar os vencedores, verifica se o 1º de uma campanha já foi premiado em outra
- Se sim, passa para o 2º colocado; se o 2º também repetir, passa para o 3º — e assim sucessivamente
- Mensagem enviada ao cliente é neutra e positiva: sem revelar o critério técnico

**Fluxo operacional:**
- Dia 1: sistema calcula e exibe os vencedores sugeridos na tela
- Usuário pode enviar automaticamente (parametrizado) ou clicar em "Enviar" manualmente
- Mensagem informa o prazo de retirada do brinde (ex: *"retire do dia 3 ao dia 10"*)
- Funcionário tem tempo para preparar; cliente passa e retira
- Brinde: usuário define a mensagem livremente — sistema sugere modelos, pode editar a qualquer tempo

---

### Categoria E — Campanhas de Recompra Rápida
| # | Gatilho | Janela | Recompensa |
|---|---------|--------|-----------|
| 8 | Comprou hoje | Voltar em 7 dias | Cupom |

---

### Categoria F — Sorteios e Exclusivos por Ranking
(Ver seção de Rankings abaixo)

---

## 5. Ranking de Clientes — Minha Proposta de Critérios

**Níveis:** Bronze → Prata → Ouro → Diamante → Platina

**Sugestão de critérios combinados** (recalculado mensalmente, todos os valores parametrizáveis):

| Nível | Gasto acumulado (12 meses) | Compras (12 meses) | Recorrência mínima |
|-------|--------------------------|-------------------|-------------------|
| Bronze | R$ 0 – R$ 299 | 1–3 | — |
| Prata | R$ 300 – R$ 999 | 4–9 | ≥ 2 meses distintos |
| Ouro | R$ 1.000 – R$ 2.999 | 10–19 | ≥ 4 meses distintos |
| Diamante | R$ 3.000 – R$ 7.999 | 20–39 | ≥ 6 meses distintos |
| Platina | R$ 8.000+ | 40+ | ≥ 10 meses distintos |

> **Você define os valores.** Os números acima são ponto de partida.

**O ranking é um filtro para benefícios — cada nível desbloqueia mais:**

| Benefício | Bronze | Prata | Ouro | Diamante | Platina |
|-----------|--------|-------|------|----------|---------|
| Cartão fidelidade | ✓ | ✓ | ✓ | ✓ | ✓ |
| Cashback | — | 1% | 2% | 3% | 5% |
| Regra do carimbo | R$ 50 | R$ 50 | R$ 45 | R$ 42 | R$ 40 |
| Sorteio mensal | — | ✓ | ✓ | ✓ VIP | ✓ VIP |
| Campanhas exclusivas | — | — | ✓ | ✓ | ✓ |

> Todos os valores e ativações são parametrizáveis. Usuário pode ativar ou desativar cada benefício por nível.

**Sorteios por ranking:**
- Cada nível pode ter seu próprio sorteio mensal (ativado/desativado independentemente)
- O prêmio é definido pelo usuário (ex: Bronze = brinde básico, Platina = experiência ou produto de alto valor)
- Sistema sorteia automaticamente no dia configurado, ou gera lista com código dos clientes elegíveis para sorteio manual (recortar + sortear)
- Resultado registrado e comunicado por e-mail + notificação

**Envio em lote por nível:**
- Usuário filtra clientes por nível de ranking
- Digita uma mensagem personalizada
- Sistema envia e-mail + notificação push para todos do grupo
- Sistema sugere horário de envio escalonado para não disparar tudo ao mesmo tempo (ex: *"enviar em lotes de 50 a cada 30 minutos"*)

---

## 6. Cupons — Como Funcionariam

Todo cupom gerado teria:
- Código único (ex: `ANIV2026-XK92`)
- Tipo: percentual, valor fixo, brinde, frete grátis
- Validade (data fixa ou "indeterminado")
- Canal onde pode ser usado: PDV, app, ecommerce, ou todos
- Status: ativo, utilizado, expirado
- Vínculo com qual campanha gerou

**No PDV:** campo para inserir código → sistema valida e aplica desconto  
**No App:** aba "Meus Cupons" com lista + QR code para mostrar no caixa  
**No Ecommerce:** campo no checkout

**Controle de não-duplicidade:** tabela `campanha_cliente_log` — registra qual cliente recebeu qual campanha e quando. Antes de disparar, sistema consulta se já enviou.

---

## 7. O que fica fora do escopo

| Item | Motivo |
|------|--------|
| **Pesquisa de satisfação (campanha 7)** | Descartada — fora do escopo deste projeto |
| **Unificação automática de CPF** | Risco de dados — merge só com confirmação manual, nunca automático |
| **Notificações push em escala** | Precisa testar FCM no app em produção antes de escalar |

> Sorteios e Campanhas 4/5/6 estão **dentro do escopo** — veja seções 4D e 5.

---

## 8. Fases Sugeridas

### Fase 1 — Base e campanhas simples
1. **Infraestrutura base:** tabelas de campanhas, cupons, log de envios por cliente
2. **Tela de campanhas** no sistema (sidebar + subpáginas)
3. **Campo CPF no app** — cadastro inicial
4. **Campanhas de aniversário** (cliente + pet)
5. **Boas-vindas** (1ª compra no app + ecommerce)
6. **Clientes inativos** (configuráveis, botão +)
7. **Dashboard básico de campanhas** — cupons emitidos, utilizados, taxa de retorno

### Fase 2 — Fidelidade e ranking
1. **Cartão fidelidade virtual** (com lançamento manual de carimbos para quem ainda usa o físico)
2. **Ranking de clientes** (Bronze → Platina) com recalculo mensal
3. **Cashback** integrado ao sistema de crédito existente
4. **Sorteios por nível** (automático ou lista para sorteio manual)
5. **Envio em lote por segmento** de ranking

### Fase 3 — Destaque mensal e retenção avançada
1. **Campanhas de destaque mensal** (4, 5, 6) com regra anti-duplicidade
2. **Campanha de recompra rápida** (comprou hoje → voltar em 7 dias)
3. **Integração CPF cross-canal** com sugestão de merge + confirmação manual
4. **Pesquisa de satisfação** (escopo próprio)

---

## 9. Estrutura de Telas (proposta)

```
Sidebar: Campanhas
├── Visão Geral
│   ├── Resumo: campanhas ativas (por nome), cupons emitidos/utilizados/expirados hoje
│   ├── Alertas do dia (aniversários de hoje, clientes que atingiram inatividade, sorteios pendentes)
│   └── Próximos eventos (aniversários amanhã, destaque mensal em X dias)
│
├── Campanhas Globais
│   ├── Cartão Fidelidade Virtual
│   │   ├── Configurar regras (valor por carimbo, total carimbos, recompensa, brindes intermediários)
│   │   └── Lançamento manual de carimbos (para quem usa o físico)
│   └── Cashback
│       └── Configurar % por nível de ranking
│
├── Campanhas Sazonais
│   ├── Aniversário do Cliente
│   └── Aniversário do Pet
│
├── Boas-vindas
│   ├── 1ª compra no App
│   └── 1ª compra no Ecommerce
│
├── Retenção (lista dinâmica — botão + para adicionar)
│   ├── Ex: inativos 30 dias
│   ├── Ex: inativos 60 dias
│   └── Ex: inativos 90 dias
│
├── Destaque Mensal
│   ├── Maior gasto
│   ├── Mais compras
│   └── Mais unidades
│       → Exibe vencedores sugeridos (com anti-duplicidade)
│       → Botão "Enviar" manual ou envio automático configurável
│
├── Ranking de Clientes
│   ├── Configurar critérios de cada nível
│   ├── Ver lista de clientes por nível (com filtro)
│   ├── Enviar mensagem em lote para nível selecionado
│   └── Configurar sorteio por nível (ativar/desativar, definir prêmio, data)
│
├── Recompra Rápida
│   └── Comprou hoje → desconto se voltar em X dias
│
└── Cupons
    ├── Lista geral (emitidos, utilizados, expirados)
    ├── Filtro por campanha, data, cliente
    └── Criar cupom manual (para casos especiais)
```

**Lembretes integrados:** a aba de lembretes existente pode mostrar, com antecedência configurável (ex: 1 dia antes):
- Aniversários de amanhã
- Destaque mensal prestes a ser calculado
- Sorteios agendados
- Brindes pendentes de retirada (campanhas D)

---

## 10. Respostas das perguntas técnicas

| # | Pergunta | Resposta |
|---|---------|----------|
| 1 | CPF é obrigatório no PDV? | Não, é opcional. Para campanhas cross-canal, será incentivado (não obrigado). |
| 2 | App tem CPF? | Não ainda — precisa ser adicionado no cadastro inicial. |
| 3 | Ecommerce tem CPF? | Tem, mas não é obrigatório — precisa tornar obrigatório. |
| 4 | Sistema de crédito existente serve para cashback/cartão? | O atual é o cartão físico com carimbo manual. O digital substitui com lançamento manual possível. Crédito gerado (recompensa/cashback) entra no mesmo sistema de crédito que já existe no ERP. |
| 5 | Provedor de e-mail? | Tem configurado (não Digital Ocean — outro foi cadastrado por bloqueio). Funciona. Usar o mesmo. |
| 6 | Push notifications funcionam? | FCM configurado. App ainda não publicado na Play Store (em desenvolvimento). Precisa publicar e testar antes de usar push em produção. |
| 7 | Como funciona "brinde" operacionalmente? | Mensagem parametrizável pelo usuário. Sistema sugere modelos. Usuário pode editar e colocar o nome do produto/brinde a qualquer tempo. O sistema apenas comunica — não desconta do estoque automaticamente (por ora). |

---

## 11. Resumo da Opinião (atualizado)

**O projeto está bem definido.** As respostas eliminaram as principais dúvidas técnicas.

**O que mudou em relação à análise inicial:**
- Sorteios: mais simples do que parecia — entram na Fase 2
- Campanhas 4/5/6: o fluxo operacional está claro — entram na Fase 3
- Ranking com 5 níveis (incluindo Platina): excelente como alavanca de benefícios escalonados
- Pesquisa de satisfação: confirmado para depois

**Próximo passo concreto:** criar a página de Campanhas no frontend (tela base + sidebar), as tabelas no banco de dados, e as primeiras 2 campanhas funcionando (aniversário do cliente + boas-vindas no app).

---

*Documento atualizado em Março 2026.*

---
---

# PARTE II — Arquitetura Técnica

> Análise de engenharia antes de codar. Contextualizada para este sistema: FastAPI + PostgreSQL + React + Docker/DigitalOcean + multi-tenant.

---

## A1. Arquitetura Geral do Motor de Campanhas

### Modelo recomendado: Event-Driven com Jobs Agendados

Dois caminhos de disparo, dependendo do tipo de campanha:

```
TEMPO REAL (evento de sistema)
  Compra finalizada
  Cliente cadastrado
  1ª compra no app/ecommerce
        │
        ▼
  [Fila de eventos — Redis/RQ]
        │
        ▼
  [Campaign Engine — avalia campanhas ativas]
        │
        ▼
  [Action Executor — gera cupom / crédito / notificação]

AGENDAMENTO (job recorrente — Celery Beat ou APScheduler)
  Todo dia às 08h → job de aniversários
  Todo dia às 09h → job de clientes inativos
  Dia 1 de cada mês → job de destaque mensal + recalculo de ranking
  Data configurada → job de sorteios
        │
        ▼
  [Mesmo Campaign Engine]
        │
        ▼
  [Mesmo Action Executor]
```

### Como evitar problemas críticos

| Problema | Solução |
|----------|---------|
| **Disparo duplicado** | Tabela `campaign_customer_log` — antes de executar, verifica se já foi disparado para aquele cliente naquele período |
| **Reprocessamento de job** | Chave de idempotência por `(campanha_id + cliente_id + período)` — se já existe, ignora |
| **Corrida de concorrência** | Lock por chave no Redis ou `SELECT FOR UPDATE SKIP LOCKED` no PostgreSQL — garante que 2 workers não processem o mesmo cliente ao mesmo tempo |
| **Job que falhou a metade** | Transação de banco envolve todas as operações de uma campanha — ou tudo é salvo, ou nada é. Sem estado parcial. |

### O que este sistema NÃO precisa (por ora)

Kafka, RabbitMQ, microsserviços, event sourcing completo. Para o volume atual, **PostgreSQL como fila + Redis + RQ/Celery** é suficiente e muito mais simples de operar.

---

## A2. Modelo de Dados — Tabelas Sugeridas

### Visão geral das tabelas

```
campaigns                  ← definição da campanha (tipo, regras, status, validade)
campaign_rules             ← parâmetros configuráveis (ex: valor por carimbo, % cashback)
campaign_triggers          ← o que dispara: evento ou agendamento
campaign_rewards           ← o que é entregue: cupom, crédito, brinde
campaign_customer_log      ← registro de cada disparo por cliente (anti-duplicidade)
coupons                    ← cupons gerados (código único, tipo, validade, status)
coupon_usage               ← quando e onde cada cupom foi usado
customer_ranking           ← nível atual + histórico mensal
loyalty_cards              ← cartão fidelidade virtual por cliente
loyalty_stamps             ← cada carimbo (quando, qual venda, qual canal)
cashback_wallet            ← saldo de cashback por cliente + movimentações
drawings                   ← sorteios (data, critério de elegibilidade, resultado)
drawing_entries            ← clientes elegíveis para cada sorteio
campaign_events            ← log de eventos do sistema para auditoria
customer_identities        ← vinculação de cadastros cross-canal via CPF
```

### Detalhamento das principais tabelas

```sql
-- Campanha
campaigns
  id, tenant_id, nome, tipo (ENUM), status (ativo/pausado/encerrado)
  data_inicio, data_fim (NULL = indeterminado)
  envio_automatico (bool), created_at, updated_at

-- Regras parametrizáveis (uma campanha pode ter N regras)
campaign_rules
  id, campaign_id, chave (ex: "valor_por_carimbo"), valor (ex: "50.00")
  -- Flexível: permite adicionar novos parâmetros sem alterar schema

-- Gatilhos e agendamentos
campaign_triggers
  id, campaign_id
  tipo (ENUM: evento | agendamento)
  evento (ex: "purchase_completed", "customer_created")
  cron_expression (ex: "0 8 * * *" = todo dia às 8h)
  dia_do_mes (ex: 1 = dia 1 de cada mês)

-- Recompensas
campaign_rewards
  id, campaign_id
  tipo (ENUM: cupom_percentual | cupom_valor_fixo | credito | brinde)
  valor, descricao_brinde
  validade_dias (NULL = sem expiração)
  canal_uso (ENUM: pdv | app | ecommerce | todos)
  mensagem_template (texto parametrizável pelo usuário)

-- Log de disparos — coração do anti-duplicidade
campaign_customer_log
  id, tenant_id, campaign_id, cliente_id
  status (ENUM: enviado | falhou | pendente_manual)
  periodo_referencia (ex: "2026-03" para campanhas mensais, "2026-03-04" para diárias)
  reward_id (FK para o cupom ou crédito gerado)
  created_at
  UNIQUE(campaign_id, cliente_id, periodo_referencia)  ← impede duplicata

-- Cupons
coupons
  id, tenant_id, campaign_id, cliente_id
  codigo (VARCHAR único, gerado automaticamente)
  tipo, valor, descricao
  validade (NULL = sem expiração)
  canal_uso, status (ativo | usado | expirado)
  created_at
  UNIQUE(tenant_id, codigo)

-- Cartão fidelidade
loyalty_cards
  id, tenant_id, cliente_id
  carimbos_atual, carimbos_meta
  status (ativo | completo | cancelado)
  iniciado_em, completado_em

loyalty_stamps
  id, loyalty_card_id, venda_id, canal (pdv | app | ecommerce)
  lancado_manualmente (bool), usuario_id (quem lançou se manual)
  created_at

-- Cashback
cashback_wallet
  id, tenant_id, cliente_id
  saldo_disponivel (Numeric)
  saldo_a_expirar (Numeric)
  updated_at

cashback_transactions
  id, wallet_id, tipo (ENUM: credito | debito | expiracao)
  valor, origem (campanha_id ou venda_id)
  expira_em (NULL = não expira)
  created_at

-- Ranking
customer_ranking
  id, tenant_id, cliente_id
  nivel_atual (ENUM: bronze | prata | ouro | diamante | platina)
  pontuacao_gasto_12m, total_compras_12m, meses_distintos_12m
  nivel_anterior, data_ultimo_recalculo

customer_ranking_history
  id, cliente_id, nivel, mes_referencia (ex: "2026-03")
  gasto_periodo, compras_periodo
  created_at

-- Sorteios
drawings
  id, tenant_id, campaign_id
  nivel_ranking_eligivel (ENUM ou ALL)
  data_sorteio, status (agendado | realizado | cancelado)
  premio_descricao
  resultado_cliente_id (FK, preenchido após sorteio)
  metodo (automatico | lista_manual)
  created_at

drawing_entries
  id, drawing_id, cliente_id
  elegivel (bool), motivo_inelegivel
  created_at

-- Vinculação cross-canal
customer_identities
  id, tenant_id, cliente_id (FK → cliente principal no ERP)
  canal (ENUM: pdv | app | ecommerce)
  canal_cliente_id (ID do cliente naquele canal)
  cpf, email, telefone
  vinculo_confirmado (bool)
  vinculado_em, vinculado_por_usuario_id
```

### Índices críticos

```
campaign_customer_log: (campaign_id, cliente_id, periodo_referencia) — UNIQUE
coupons: (tenant_id, codigo) — UNIQUE
loyalty_cards: (tenant_id, cliente_id, status) — para busca do cartão ativo
cashback_wallet: (tenant_id, cliente_id) — UNIQUE
customer_ranking: (tenant_id, cliente_id) — UNIQUE
customer_identities: (tenant_id, cpf) — para busca de merge
customer_identities: (tenant_id, canal, canal_cliente_id) — para lookup cross-canal
```

---

## A3. Motor de Campanhas (Campaign Engine)

### Fluxo de avaliação

```
1. Evento chega (ex: purchase_completed, cliente_id=42, valor=150.00)
2. Engine busca todas as campanhas ativas para o tenant
3. Para cada campanha:
   a. Verifica se o gatilho corresponde ao evento recebido
   b. Verifica se o cliente é elegível (ranking, canal, CPF vinculado?)
   c. Consulta campaign_customer_log — já foi disparado neste período?
   d. Se passou em tudo → executa a recompensa
   e. Registra em campaign_customer_log (status = enviado)
4. Se falhou → registra status = falhou, agenda retry
```

### Priorização de campanhas

Quando múltiplas campanhas são elegíveis para o mesmo evento, a ordem de execução é:
1. Campanhas globais (cartão fidelidade, cashback) — sempre processam
2. Campanhas sazonais (aniversário) — processam se for o dia
3. Campanhas de boas-vindas — processam apenas 1 vez por cliente
4. Campanhas de retenção — processam apenas se não houver compra recentemente

Campanhas do mesmo tipo não se bloqueiam entre si (um cliente pode ganhar cashback E um carimbo na mesma compra).

---

## A4. Sistema de Eventos

### Eventos principais

| Evento | Quando dispara | Payload mínimo |
|--------|---------------|----------------|
| `purchase_completed` | Ao finalizar venda em qualquer canal | cliente_id, venda_id, valor_total, canal, data |
| `customer_created` | Novo cadastro no app/ecommerce/PDV | cliente_id, canal, cpf (se informado) |
| `first_purchase_app` | 1ª compra via app | cliente_id, venda_id |
| `first_purchase_ecommerce` | 1ª compra via ecommerce | cliente_id, venda_id |
| `customer_birthday` | Job diário detecta aniversário | cliente_id, data_nascimento |
| `pet_birthday` | Job diário detecta aniversário do pet | cliente_id, pet_id |
| `customer_inactive` | Job diário detecta inatividade | cliente_id, dias_sem_compra, ultima_compra |
| `month_closed` | Job dia 1 de cada mês | mes_referencia, tenant_id |
| `drawing_scheduled` | Data de sorteio atingida | drawing_id |

### Estratégia de persistência

Não é necessário event sourcing completo. Estratégia mais simples e eficaz para este volume:

- Eventos de **tempo real** → entram numa fila **Redis/RQ** → processados por worker → descartados após confirmação
- Eventos de **agendamento** → gerados pelo job no momento de execução → não precisam ser persistidos separadamente
- `campaign_customer_log` já é o registro auditável de tudo que aconteceu — funciona como "event log" suficiente

Se no futuro quiser replay (reprocessar eventos), a tabela `campaign_events` pode guardar todos os eventos com payload. Mas **não é necessário na Fase 1**.

---

## A5. Integração Cross-Canal

### Modelo de identidade

```
clientes (tabela principal do ERP)
    id, tenant_id, nome, cpf, email, telefone
    └── é o "cliente verdade" do sistema

customer_identities
    cliente_id → aponta para clientes.id
    canal = pdv | app | ecommerce
    canal_cliente_id = ID naquele canal específico
    cpf, email, telefone (do cadastro naquele canal)
    vinculo_confirmado = false até aprovação manual
```

### Fluxo de merge

1. Cliente se cadastra no app com CPF
2. Sistema busca em `customer_identities` se aquele CPF já existe em outro canal
3. Se encontrar → cria sugestão de merge (vinculo_confirmado = false), exibe no painel do operador
4. Operador confirma → `vinculo_confirmado = true` → a partir daí, compras de qualquer canal do cliente somam para o mesmo histórico
5. Se CPF não encontrado → cria apenas a identidade do canal atual, sem vínculo

### Regras de segurança

- Merge **nunca acontece automaticamente**, sempre passa por confirmação
- Um cliente principal pode ter no máximo 1 identidade por canal
- Desfazer merge é possível: basta mudar `vinculo_confirmado = false` e criar novo `cliente_id`
- CPF em formato hash no banco (não texto puro) — boa prática de LGPD

---

## A6. Ranking de Clientes

### Cálculo

O ranking é recalculado no dia 1 de cada mês pelo job `month_closed`. Para cada cliente:

```
gasto_12m     = SUM(vendas.valor_total) dos últimos 12 meses
compras_12m   = COUNT(vendas) dos últimos 12 meses
meses_12m     = COUNT(DISTINCT DATE_TRUNC('month', data_venda)) últimos 12 meses
```

Com base nos 3 critérios + parâmetros configurados pelo usuário → determina o nível.

### Eficiência com muitos clientes

- O job roda com `LIMIT + OFFSET` ou cursor paginado — nunca carrega todos de uma vez
- Usa `UPDATE customer_ranking SET ...` em batch (não insert por insert)
- Índice em `vendas(cliente_id, data_venda, tenant_id)` — já deve existir ou criar
- Estimativa: 10.000 clientes recalculados em menos de 30 segundos com PostgreSQL bem indexado

### Histórico

- Antes de atualizar o nível, salva o estado atual em `customer_ranking_history`
- Permite mostrar "você subiu de Bronze para Prata este mês"

---

## A7. Sistema de Fidelidade (Cartão Virtual)

### Garantia de consistência — o problema das compras simultâneas

Se dois pedidos chegam ao mesmo tempo para o mesmo cliente, ambos podem tentar criar/atualizar o cartão. Solução: usar `SELECT FOR UPDATE` na tabela `loyalty_cards` — o banco faz o lock da linha, o segundo worker espera o primeiro terminar.

```
BEGIN;
  SELECT * FROM loyalty_cards WHERE cliente_id = X AND status = 'ativo' FOR UPDATE;
  -- calcula carimbos a adicionar
  -- atualiza ou cria o cartão
  -- se completou: gera recompensa e cria novo cartão
COMMIT;
```

### Regras por ranking

O campo `campaign_rules` da campanha de fidelidade terá entradas por nível:
```
bronze_valor_por_carimbo = 50.00
prata_valor_por_carimbo  = 50.00
ouro_valor_por_carimbo   = 45.00
diamante_valor_por_carimbo = 42.00
platina_valor_por_carimbo  = 40.00
```
O engine consulta o nível atual do cliente e aplica a regra correspondente.

---

## A8. Cashback

### Wallet por cliente

Cada cliente tem exatamente 1 `cashback_wallet` (criado na primeira vez que ganha cashback). O saldo é sempre calculado como:

```
saldo_disponivel = SUM(creditos) - SUM(debitos) - SUM(expirados)
```

Nunca atualizar o saldo diretamente — sempre inserir em `cashback_transactions` e recalcular. Isso garante auditoria financeira completa.

### Expiração

Um job diário varre `cashback_transactions` com `expira_em <= HOJE` e `tipo = credito` + ainda não debitados → gera transação de `expiracao`. O saldo is recalculado.

### Uso no PDV/App/Ecommerce

Ao aplicar cashback como forma de pagamento:
- Verifica saldo disponível
- Debita `cashback_transactions` tipo `debito` vinculado à venda
- Nunca permite saldo negativo

---

## A9. Cupons

### Geração de código único

```python
import secrets
import string

def gerar_codigo_cupom(prefixo: str = "") -> str:
    chars = string.ascii_uppercase + string.digits
    aleatorio = ''.join(secrets.choice(chars) for _ in range(8))
    return f"{prefixo}{aleatorio}"  # ex: "ANIV2026-XK92J7RM"
```

Após gerar, verifica unicidade no banco antes de salvar. Na prática, colisão é virtualmente impossível com 8 caracteres aleatórios.

### Validação no PDV/App/Ecommerce

```
1. Recebe código digitado
2. Busca coupons WHERE codigo = X AND tenant_id = Y AND status = 'ativo'
3. Verifica validade (data_expiracao >= HOJE ou NULL)
4. Verifica canal (canal_uso = canal_atual ou 'todos')
5. Verifica se pertence ao cliente que está comprando (se vinculado)
6. Se tudo ok → aplica desconto → atualiza status = 'usado' + data_uso + venda_id
```

### Anti-fraude básico

- Cupom é vinculado ao `cliente_id` → não pode ser usado por outro cliente
- Status é atualizado dentro de transação junto com a venda → não há janela para uso duplo
- Log de tentativas de cupom inválido (para detectar força bruta de códigos)

### Conflito entre cupons

Regra simples: **1 cupom por venda**. Não acumula cupom com cupom. Pode acumular cupom com cashback (a critério do usuário, configurável).

---

## A10. Sorteios

### Fluxo

```
1. Usuário cria sorteio: define data, nível elegível, prêmio, método (auto ou lista)
2. No dia do sorteio, job gera drawing_entries com todos os clientes elegíveis
3. Método automático:
   - Sistema sorteia 1 entrada aleatória usando função determinística com seed auditável
   - Registra: resultado_cliente_id + seed_utilizado + timestamp_exato
4. Método lista manual:
   - Sistema gera PDF/lista com código dos clientes elegíveis
   - Usuário sorteia fisicamente e informa o vencedor no sistema
5. Sistema notifica o vencedor (e-mail + push)
```

### Auditabilidade do sorteio automático

```python
import random, hashlib, datetime

seed = hashlib.sha256(
    f"{drawing_id}{datetime.datetime.utcnow().isoformat()}{len(entries)}".encode()
).hexdigest()

rng = random.Random(seed)
vencedor = rng.choice(entries)
# seed é salvo junto com o resultado — qualquer um pode verificar
```

Isso garante que o resultado não pode ser alterado retroativamente sem mudar o seed.

---

## A11. Notificações

### Arquitetura de envio

```
Campaign Engine gera ação de notificação
        │
        ▼
Insere em fila notification_queue (tabela PostgreSQL ou Redis)
        │
        ▼
Worker de notificações processa em lotes (ex: 50 por vez)
  ├── E-mail → provedor SMTP já configurado
  └── Push   → FCM (Firebase Cloud Messaging)
        │
        ▼
Registra resultado (enviado / falhou / bounce) em notification_log
```

### Controle de taxa (rate limiting)

- Nunca enviar mais de X notificações por minuto por tenant (configurável)
- Escalonamento: ao processar uma lista grande (ex: ranking inteiro), o worker distribui os envios em lotes com intervalo, sugerindo horário de envio espaçado
- Push em massa: envia em batches de 100 via FCM (limite da API do Firebase)

### Retry automático

- Se falhou: tenta novamente após 5 min, depois 30 min, depois 2h
- Após 3 falhas: marca como `falha_definitiva`, não tenta mais
- Não há spam: o `campaign_customer_log` garante que mesmo se o retry reprocessar, o cupom/crédito não é gerado novamente

---

## A12. Controle de Não Duplicidade

### A tabela é o guardião central

```sql
-- Antes de qualquer disparo, o engine executa:
SELECT id FROM campaign_customer_log
WHERE campaign_id = $1
  AND cliente_id  = $2
  AND periodo_referencia = $3  -- ex: '2026-03' ou '2026-03-04'
  AND status != 'falhou'       -- se falhou, pode tentar de novo
LIMIT 1;

-- Se retornou resultado → NÃO dispara. Fim.
-- Se não retornou → dispara e insere o log atomicamente.
```

### Período de referência por tipo de campanha

| Tipo | periodo_referencia | Significado |
|------|-------------------|-------------|
| Aniversário | `2026-03-04` | 1 por dia de aniversário |
| Boas-vindas | `unico` | Disparado 1 única vez na vida |
| Inativo 30 dias | `2026-03` | 1 por mês |
| Destaque mensal | `2026-03` | 1 por mês |
| Cartão fidelidade | por `loyalty_card_id` | Controlado pelo próprio cartão |
| Recompra rápida | `2026-03-04` | 1 após a compra do dia |

---

## A13. Jobs e Workers

### Stack recomendada para este sistema

**Celery + Redis** — é a combinação mais madura para FastAPI/Python, tem retry nativo, agendamento (Celery Beat) e monitoramento (Flower).

Se quiser mais simples: **APScheduler** para jobs agendados + **RQ** para fila de eventos. Menor complexidade de configuração, suficiente para o volume atual.

### Estrutura de workers

```
worker_events          ← processa eventos em tempo real (purchase_completed, etc.)
worker_scheduled       ← roda jobs agendados (aniversários, inativos, ranking)
worker_notifications   ← envia e-mails e pushes em fila
worker_monthly         ← dia 1 de cada mês: ranking, destaque, sorteios
```

### Jobs agendados sugeridos

| Job | Horário | O que faz |
|-----|---------|-----------|
| `job_birthdays` | Todo dia 08h | Busca clientes/pets com aniversário hoje, dispara campanha |
| `job_inactive` | Todo dia 09h | Busca clientes sem compra há X dias, dispara campanha |
| `job_quick_repurchase` | Todo dia 10h | Verifica clientes da janela de recompra rápida |
| `job_coupon_expiry` | Todo dia 00h | Marca cupons vencidos como expirado |
| `job_cashback_expiry` | Todo dia 00h30 | Processa expiração de cashback |
| `job_monthly_close` | Dia 1, 07h | Recalcula ranking, gera destaque, prepara sorteios |

---

## A14. Escalabilidade (Multi-Tenant SaaS)

### Isolamento atual

O sistema já usa `tenant_id` em todas as tabelas — isso é o correto. Todas as queries do motor de campanhas **sempre** filtram por `tenant_id` antes de tudo.

### Potencial problema: campanhas pesadas em tenants grandes

Se um tenant tiver 50.000 clientes e disparar uma campanha de retenção para todos, o worker pode travar processando uma lista enorme. Mitigação:
- Jobs processam em batches paginados (1000 clientes por vez)
- Cada batch é uma task separada na fila → se uma falha, não afeta as outras
- Tenant grande → mais tasks na fila → processamento mais demorado, mas não trava

### Não precisa de particionamento agora

Para um petshop (dezenas de tenants, milhares de clientes cada), PostgreSQL com índices bem definidos aguenta sem sharding. Revisitar quando atingir > 1 milhão de registros em tabelas críticas.

---

## A15. Observabilidade

### O que monitorar

| Métrica | Onde registrar |
|---------|---------------|
| Campanhas disparadas por período | `campaign_customer_log` |
| Taxa de sucesso de notificações | `notification_log` |
| Cupons emitidos vs utilizados | `coupons` |
| Latência de processamento de eventos | Log do worker |
| Jobs que falharam | Log do Celery / tabela `job_log` |

### Estratégia simples e eficaz

- **Logs estruturados:** já existe no sistema (`structlog` / JSON). Adicionar campos: `campaign_id`, `cliente_id`, `event_type`, `duration_ms`
- **Dashboard no próprio sistema:** a tela "Visão Geral" de campanhas já é o monitoramento mais útil para o usuário
- **Alertas para o operador:** se um job falhou 3 vezes → registrar em tabela `system_alerts` → mostrar na tela como aviso vermelho

Não é necessário Prometheus/Grafana/Jaeger neste momento. Adicionar quando o volume justificar.

---

## A16. Organização do Backend (FastAPI)

### Estrutura sugerida

```
backend/app/
├── campaigns/
│   ├── models.py          ← models SQLAlchemy (campaigns, rules, rewards, logs)
│   ├── schemas.py         ← pydantic schemas (request/response)
│   ├── routes.py          ← endpoints REST da tela de campanhas
│   ├── service.py         ← lógica de negócio (criar, editar, pausar campanha)
│   ├── engine.py          ← Campaign Engine (avaliar + executar)
│   ├── actions.py         ← Action Executor (gerar cupom, crédito, notificação)
│   └── repository.py      ← queries ao banco
│
├── loyalty/
│   ├── models.py          ← loyalty_cards, loyalty_stamps
│   ├── service.py         ← lógica de carimbos e recompensas
│   └── repository.py
│
├── cashback/
│   ├── models.py          ← cashback_wallet, cashback_transactions
│   ├── service.py         ← crédito, débito, expiração
│   └── repository.py
│
├── coupons/
│   ├── models.py
│   ├── service.py         ← geração, validação, uso
│   └── repository.py
│
├── ranking/
│   ├── models.py
│   ├── service.py         ← cálculo, recalculo, histórico
│   └── repository.py
│
├── drawings/
│   ├── models.py
│   ├── service.py         ← elegibilidade, sorteio, resultado
│   └── repository.py
│
├── notifications/
│   ├── service.py         ← coordena e-mail + push
│   ├── email_provider.py  ← abstração do provedor SMTP
│   └── push_provider.py   ← abstração do FCM
│
├── workers/
│   ├── celery_app.py      ← configuração Celery
│   ├── event_workers.py   ← workers de eventos em tempo real
│   ├── scheduled_jobs.py  ← todos os jobs agendados
│   └── monthly_jobs.py    ← jobs do dia 1
│
└── events/
    ├── dispatcher.py      ← publica evento na fila
    └── handlers.py        ← mapeia evento → engine
```

### Responsabilidades por camada

| Camada | Responsabilidade |
|--------|----------------|
| `routes.py` | Recebe HTTP, valida input, chama service |
| `service.py` | Lógica de negócio, regras, orquestração |
| `engine.py` | Avalia qual campanha dispara, em qual ordem |
| `actions.py` | Executa a recompensa (usa coupon service, cashback service) |
| `repository.py` | Apenas queries ao banco, sem lógica |
| `workers/` | Consome fila e chama engine; nenhuma lógica de negócio aqui |
| `events/dispatcher.py` | Qualquer parte do sistema chama `dispatch("purchase_completed", payload)` |

---

## A17. Riscos Técnicos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| **Carimbo duplicado em compra rápida** | Média | Alto | `SELECT FOR UPDATE` em `loyalty_cards` durante o processamento |
| **Cupom gerado 2x para o mesmo evento** | Baixa | Médio | `UNIQUE(campaign_id, cliente_id, periodo_referencia)` em `campaign_customer_log` |
| **Crédito de cashback inconsistente** | Baixa | Alto | Nunca atualizar saldo direto — só via `cashback_transactions`; saldo calculado na leitura |
| **Merge de CPF errado une clientes diferentes** | Média | Alto | Merge sempre manual, com confirmação; desfazível; log de quem aprovou |
| **Push em massa trava o servidor** | Média | Médio | Fila com rate limiting; batches de 100; worker separado |
| **Job de aniversário rodando 2x no mesmo dia** | Baixa | Médio | Chave de idempotência por `(job_type, data, tenant_id)` em tabela de controle |
| **Sorteio manipulado** | Baixa | Alto (reputação) | Seed auditável salvo + opção de sorteio manual com lista impressa |
| **Tenant A vê dados do Tenant B** | Muito baixa | Crítico | Todas as queries obrigatoriamente filtram `tenant_id`; cobertura de testes |
| **E-mail de campanha vai para spam** | Média | Médio | Usar provedor já configurado e funcionando; não enviar em massa sem aquecimento de domínio |

---

## A18. Diagrama Conceitual de Fluxo

```
┌─────────────────────────────────────────────────────────────────────┐
│  CANAIS DE ENTRADA                                                   │
│  PDV ──────────────┐                                                │
│  App ──────────────┼──► dispatch("purchase_completed", {...})       │
│  Ecommerce ────────┘           │                                    │
│                                ▼                                    │
│              ┌─────────────────────────────┐                        │
│              │   Fila Redis (RQ/Celery)    │                        │
│              └─────────────┬───────────────┘                        │
│                            │                                        │
│                            ▼                                        │
│              ┌─────────────────────────────┐                        │
│              │   Campaign Engine           │                        │
│              │  1. Busca campanhas ativas  │                        │
│              │  2. Avalia gatilhos         │                        │
│              │  3. Verifica elegibilidade  │                        │
│              │  4. Checa anti-duplicidade  │                        │
│              └─────────────┬───────────────┘                        │
│                            │                                        │
│              ┌─────────────▼──────────────┐                        │
│              │   Action Executor          │                        │
│              │  ├── Gera cupom            │                        │
│              │  ├── Gera crédito/cashback │                        │
│              │  ├── Adiciona carimbo      │                        │
│              │  └── Enfileira notificação │                        │
│              └─────────────┬──────────────┘                        │
│                            │                                        │
│  ┌─────────────────────────▼──────────────────────┐                │
│  │  Notification Worker                           │                │
│  │  ├── E-mail (SMTP configurado)                 │                │
│  │  └── Push (FCM → App do cliente)               │                │
│  └────────────────────────────────────────────────┘                │
│                                                                     │
│  JOBS AGENDADOS (Celery Beat)                                       │
│  08h → job_birthdays ──────────► Campaign Engine ► Action Executor │
│  09h → job_inactive ───────────► Campaign Engine ► Action Executor │
│  Dia 1, 07h → job_monthly ─────► Ranking + Destaque + Sorteios     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## A19. Pontos de Atenção Antes de Começar

1. **Redis não está na infraestrutura atual** — precisará ser adicionado ao `docker-compose.prod.yml`. É simples, mas é uma dependência nova.

2. **Celery Beat precisa de persistência** — o agendador de jobs precisa de um backend para não perder o estado ao reiniciar o container. Usar `django-celery-beat` (adaptado) ou `redisBeat`.

3. **CPF no app** — antes de cualquer campanha cross-canal funcionar, o campo CPF no cadastro do app precisa existir. É pré-requisito de dados.

4. **FCM deve ser testado** antes de campanhas com notificação serem lançadas. Um push que falha silenciosamente não é detectado sem o `notification_log`.

5. **Cartão fidelidade físico ainda em uso** — o sistema deve oferecer lançamento manual de carimbos desde o dia 1, para que o dono possa migrar clientes progressivamente.

6. **Fase 1 não precisa de Celery** — para aniversários e boas-vindas, um simples `APScheduler` embutido no processo FastAPI já funciona. Celery entra quando o volume de eventos em tempo real justificar.

---

*Arquitetura revisada em Março 2026.*

---
---

# PARTE III — Revisão Técnica Crítica

> Análise imparcial dos riscos arquiteturais antes de codar.  
> Formato: concordo/discordo + justificativa + recomendação final.

---

## A1) Campaign Engine — "imperativo simples" ou rule engine?

**Veredito: imperativo modular. Sem rule engine por agora. Mas com uma condição.**

O alerta está correto no diagnóstico mas errado na solução para este volume. Um rule engine (Rete, DSL, JSON rules) traz custo real: você precisa manter o interpretador, depurar regras em formato não-Python, e o usuário *não* cria regras customizadas — ele apenas parametriza valores predefinidos (valor do carimbo, % de cashback, dias de inatividade). Isso não é um caso de uso de rule engine.

O risco real é diferente: **a engine virar spaghetti por crescimento sem estrutura**, não por falta de um interpretador de regras.

**A condição para não virar monstro:** usar o padrão Strategy com uma interface comum.

```
CampaignHandler (interface)
  ├── BirthdayCampaignHandler
  ├── LoyaltyStampCampaignHandler
  ├── InactiveCampaignHandler
  ├── CashbackCampaignHandler
  ├── WelcomeCampaignHandler
  └── MonthlyHighlightCampaignHandler
```

Cada handler tem exatamente 3 métodos: `is_eligible(cliente, contexto)`, `should_trigger(evento)`, `execute(cliente, contexto)`. O engine itera os handlers registrados. Novo tipo de campanha = nova classe, zero mudança nas existentes.

**Limite concreto:** esta arquitetura aguenta bem até ~20 tipos de campanha distintos sem refatoração. Se o usuário um dia quiser criar regras totalmente customizadas ("se cliente tem pet de grande porte E comprou ração E está inativo há X dias"), aí sim você avalia um micro DSL interno. Mas isso é Fase 5 ou 6, não agora.

---

## A2) Redis como dependência crítica — é necessário?

**Veredito: discordo da adição do Redis na Fase 1. Concordo para Fase 2+.**

O alerta está correto: Redis seria single point of failure e uma dependência nova na infraestrutura. A questão é que **não é necessário na Fase 1**.

**PostgreSQL + SKIP LOCKED como fila** é a alternativa correta para este volume:

```sql
-- Worker pega próximo evento disponível sem conflito com outros workers
SELECT * FROM campaign_event_queue
WHERE status = 'pendente'
  AND tenant_id = $1
ORDER BY created_at
LIMIT 10
FOR UPDATE SKIP LOCKED;
```

Isso é o que bibliotecas como `pg-boss`, `django-pg-queue` e `good-job` usam. É battle-tested, sem dependência extra, com durabilidade imediata (transação normal do banco).

**Quando Redis entra de verdade:**
- Rate limiting de notificações em escala (tokens por segundo)
- Cache de configurações de campanha (evita N queries por evento)
- Session/cache do frontend (já pode já existir para isso)

**Fallback se Redis cair:** se você usar Redis apenas para cache (não para fila nem locks), o sistema degrada graciosamente — fica mais lento (queries ao banco), mas não para.

**Resumo da recomendação:**
| Componente | Fase 1 | Fase 2+ |
|------------|--------|---------|
| Fila de eventos | PostgreSQL SKIP LOCKED | Manter (não trocar) |
| Locks de fidelidade | PostgreSQL FOR UPDATE | Manter |
| Rate limit notificações | Contador em tabela | Redis leaky bucket |
| Cache de configs | Nenhum / LRU em memória | Redis com TTL |

---

## A3) LGPD — CPF: hash, criptografia ou texto puro?

**Veredito: criptografia reversível + hash separado. Texto puro é aceitável agora com condições, mas já estruture a camada certa.**

O alerta está bem formulado. Três opções reais para este sistema:

**Opção 1 — Texto puro (aceitável no curto prazo se):**
- Banco em servidor próprio com acesso restrito ✓ (DigitalOcean com firewall)
- Conexão sempre via TLS ✓
- Logs mascarados (nunca logar CPF em texto) ✓
- RBAC: apenas funções que precisam veem CPF ✓

**Opção 2 — Criptografia em repouso (recomendada para o médio prazo):**
- `cpf_encrypted`: valor Fernet/AES com chave em variável de ambiente (não no banco)
- `cpf_hash`: SHA-256 com salt fixo por tenant (para JOIN e lookup eficiente)
- Descriptografa apenas quando necessário: NF-e, suporte, exportação fiscal

**Opção 3 — Vault/tokenização:** overkill para um petshop SaaS. Descarta.

**Recomendação concreta:** implemente já a coluna como `cpf_hash` (para matching cross-canal) e `cpf_masked` (exibição: `***.123.456-**`). Adicione `cpf_encrypted` quando o volume de tenants justificar. Nunca logar CPF em texto em nenhuma condição — isso é gratuito e obrigatório.

**Risco que o alerta não mencionou:** CPF sendo enviado em query string / URL (ex: `/clientes?cpf=123...`). Isso expõe em logs de nginx. Sempre receber CPF em body POST ou header, nunca em query param.

---

## A4) Idempotência — UNIQUE em campaign_customer_log é suficiente?

**Veredito: não é suficiente sozinho. Faltam 2 camadas.**

O UNIQUE `(campaign_id, cliente_id, periodo_referencia)` protege contra disparo duplicado da *campanha*, mas não protege contra:

**Problema 1 — Mesmo evento enviado 2x para a fila:**  
Se a venda dispara o evento `purchase_completed` e o worker falha *depois* de gerar o cupom mas *antes* de confirmar o log, no retry o cupom é gerado de novo.

Solução: adicionar `venda_id` (ou `evento_id` único) na checagem da fidelidade/cashback:
```sql
-- Antes de adicionar carimbo:
SELECT id FROM loyalty_stamps WHERE venda_id = $1 LIMIT 1;
-- Se existe → skip. Se não → insere dentro de transação.
```

**Problema 2 — Job de aniversário executando 2x no mesmo dia:**  
O UNIQUE no log protege, mas a query de "buscar elegíveis" pode rodar duas vezes e criar 2 tasks para o mesmo cliente. Se as tasks rodam em paralelo, ambas chegam ao INSERT do log ao mesmo tempo — a segunda vai falhar com constraint violation. Isso é o comportamento *correto* (nenhuma duplicata), mas gera erro no log do worker.

Solução: envolver o check + insert em `INSERT ... ON CONFLICT DO NOTHING` e verificar se inseriu (rowcount = 1). Se não inseriu, a outra task venceu — encerra silenciosamente.

**Problema 3 — Retry de notificação regenerando recompensa:**  
O retry da notificação deve retransmitir a notificação existente, não executar a campanha novamente. As etapas de "gerar recompensa" e "enviar notificação" devem ser separadas no log, com IDs distintos.

```
campaign_customer_log.id     ← prova que a recompensa foi gerada (única)
notification_log.id           ← rastreia tentativas de envio separadamente
notification_log.campaign_log_id → FK para o log da campanha
```

---

## A5) Concorrência — Postgres locks vs Redis locks

**Veredito: padronize em PostgreSQL. Redis lock para este caso é complexidade desnecessária.**

O alerta está bem colocado. A escolha entre os dois tem implicações práticas:

| Critério | PostgreSQL FOR UPDATE | Redis SETNX |
|----------|----------------------|-------------|
| Durabilidade | Automática (transação) | Manual (TTL + refresh) |
| Rollback em falha | Automático | Manual (pode vazar lock) |
| Dependência extra | Nenhuma | Redis ativo e acessível |
| Deadlock | Detectado pelo banco | Não detectado automaticamente |
| Granularidade | Por linha | Qualquer chave arbitrária |

Para este sistema, **todos os locks necessários são sobre linhas do banco** (cartão fidelidade, wallet de cashback, entrada de sorteio). PostgreSQL FOR UPDATE cobre isso com zero risco de lock vazado.

**Risco de deadlock:** acontece quando Worker A trava linha X e tenta travar Y, enquanto Worker B travou Y e tenta travar X. Mitigação: **sempre adquirir locks na mesma ordem** (ex: sempre travar `loyalty_cards` antes de `cashback_wallet`, nunca o contrário).

**Starvation:** um worker esperando lock indefinidamente. Mitigação: usar `FOR UPDATE SKIP LOCKED` onde possível — se a linha está travada, pula para o próximo cliente em vez de esperar.

---

## A6) Multi-tenant — fairness e limites

**Veredito: o alerta está correto e subestimado. É o risco operacional mais real desta arquitetura.**

Se um tenant com 30.000 clientes dispara uma campanha de retenção, e o worker processa 1 cliente por vez, os outros tenants ficam esperando na fila. Sem fairness, o tenant "gordo" monopoliza o worker.

**O que implementar desde o começo (não é opcional):**

1. **Processamento paginado obrigatório:** nunca select sem LIMIT. Máximo 500 clientes por batch.

2. **Uma task por batch, não uma task por campanha inteira:**  
   ```
   Campanha X → Task(campanha_x, clientes 1-500)
                Task(campanha_x, clientes 501-1000)
                Task(campanha_x, clientes 1001-1500)
   ```
   Assim o scheduler intercala tasks de tenants diferentes.

3. **Rate limit de notificações por tenant** — configurável, padrão conservador:
   - E-mail: máximo 200/hora por tenant
   - Push: máximo 1.000/hora por tenant
   - Armazenar contadores em tabela `tenant_rate_limits` com janela deslizante de 1h

4. **Métricas mínimas desde o dia 1:**
   - `campaign_customer_log.created_at` + `campaign_id` → já dá throughput por campanha
   - Coluna `processing_duration_ms` no log do job → detecta campanhas lentas
   - Alertar se batch demorar mais de 30s

---

## A7) Notificações — backpressure e anti-duplicidade

**Veredito: o plano está correto na estrutura. Faltam 3 detalhes críticos.**

**Detalhe 1 — Idempotência de envio:**  
O campo mais importante que falta em `notification_log` é a `idempotency_key`:
```
notification_log
  idempotency_key = hash(campaign_log_id + tipo + cliente_id)
  UNIQUE(idempotency_key)
```
No retry, o worker tenta INSERT com `ON CONFLICT DO NOTHING` — se já existe, pula sem reenviar.

**Detalhe 2 — Dead letter queue:**  
Após 3 tentativas com falha, mover para `notification_dead_letter` e parar de tentar. Mostrar na tela de campanhas como "X notificações não entregues" com opção de reenviar manualmente.

**Detalhe 3 — Reputação de domínio de e-mail:**  
O alerta não mencionou, mas é o risco mais prático para campanhas: **se você disparar 500 e-mails de uma vez sem aquecimento, o domínio vai para spam**. SPF, DKIM e DMARC precisam estar configurados no provedor atual. Verificar antes de qualquer envio em massa.

**Sobre ordering:** notificações de marketing não precisam de ordem garantida. O que precisa é que o mesmo cliente não receba 2x — isso está coberto pelo idempotency_key acima.

**FCM em lote:** a API do Firebase aceita até 500 mensagens por requisição (não 100 como mencionado na arquitetura — corrigir). Mas cada mensagem deve ter TTL configurado (ex: 24h) — push que chega 3 dias depois de uma promoção de aniversário é pior do que não chegar.

---

## A8) Sorteios — seed auditável é suficiente?

**Veredito: o alerta está correto. O seed proposto tem uma fraqueza exploitável. Mas não precisa de blockchain.**

**A fraqueza:** `hash(drawing_id + timestamp + len(entries))`. O `drawing_id` e `len(entries)` são conhecidos com antecedência. O `timestamp` é o único elemento imprevisível — mas quem tem acesso ao servidor pode, teoricamente, disparar o sorteio em momentos diferentes até obter o resultado desejado.

**Solução mais robusta sem complexidade excessiva:**

1. **Congelar a lista de elegíveis antecipadamente** (ex: 24h antes do sorteio). Hash SHA-256 da lista ordenada é publicado/salvo antes do sorteio. Isso prova que a lista não foi alterada na hora.

2. **Usar UUID4 gerado na criação do sorteio como parte do seed** — não pode ser previsto nem controlado depois.

3. **Registrar no `drawings`:**
   - `entries_hash`: SHA-256 da lista ordenada de `cliente_id`s
   - `seed_uuid`: UUID4 gerado na criação
   - `timestamp_sorteio`: timestamp UTC exato da execução
   - `seed_final`: `hash(seed_uuid + timestamp_sorteio + entries_hash)`
   - `resultado_cliente_id`: quem ganhou

Qualquer auditoria externa pode verificar: dado o seed_final e a lista (entries_hash), reproduzir o sorteio e confirmar o resultado.

**Para prêmios grandes:** a opção de lista manual (imprimir, recortar, sortear ao vivo) é genuinamente mais confiável socialmente do que qualquer algoritmo. Oferecer as duas opções é a decisão certa.

---

## B) Riscos que não foram mencionados nos alertas

### B1) Esgotamento de conexões ao banco durante fan-out de campanhas
**Risco:** workers processando batches de 1.000 clientes podem abrir muitas conexões simultâneas ao PostgreSQL, especialmente se houver múltiplos workers.  
**Por que importa:** PostgreSQL tem limite de conexões (padrão 100). Com Docker + vários workers, é fácil estourar.  
**Mitigação:** usar `PgBouncer` como pool de conexões (já é boa prática para produção com Uvicorn + múltiplos workers). Ou configurar `pool_size` no SQLAlchemy engine com limites conservadores por worker.  
**Impacto no roadmap:** configurar PgBouncer antes de campanhas em produção.

### B2) Dados de aniversário ausentes quebram campanhas silenciosamente
**Risco:** dados_nascimento NULL para muitos clientes cadastrados antes do sistema existir. Job roda, encontra 0 elegíveis, parece que funcionou.  
**Mitigação:** dashboard mostrando "% de clientes com data de nascimento cadastrada" + alerta se < 30%.

### B3) App ainda não publicado na Play Store
**Risco:** o app está em desenvolvimento e ainda não foi submetido à Play Store. A primeira publicação passa por revisão do Google (1-7 dias). Isso significa que qualquer campanha cross-canal (push notification, CPF tracking via app) só funciona após aprovação e instalação pelos clientes — o que pode levar semanas ou meses de adoção.  
**Oportunidade:** como ainda não foi publicado, o campo CPF pode entrar já na primeira versão, sem necessidade de atualização posterior. Não há risco de "campo faltando em versão antiga instalada".  
**Impacto:** não bloquear implementação backend/frontend esperando publicação. Desenvolver com flag de feature desativada. Planejar campanha de incentivo à instalação do app (ex: cupom para quem instalar e cadastrar CPF).

### B4) Cashback aplicado junto com cupom pode dar desconto duplo inconsistente
**Risco:** cliente usa cupom de 10% + cashback de 50 reais na mesma venda. Pode resultar em venda com valor negativo se não houver validação.  
**Mitigação:** regra clara: desconto máximo = valor do produto. Validação no backend antes de confirmar venda, independente do canal.

---

## C) Recomendação Final — O que mudar no plano antes de codar

| Item | Decisão atual | Mudança recomendada | Prioridade |
|------|---------------|---------------------|------------|
| Redis na Fase 1 | Incluído | Remover. Usar PostgreSQL SKIP LOCKED. Redis entra na Fase 2 para rate limit. | Alta |
| Campaign Engine | Loop + ifs | Strategy pattern com handlers por tipo de campanha | Alta |
| CPF no banco | Hash puro | `cpf_hash` (lookup) + `cpf_masked` (exibição). `cpf_encrypted` na Fase 2. | Média |
| Idempotência de recompensa | UNIQUE no log | Adicionar verificação por `venda_id` em loyalty_stamps e cashback_transactions | Alta |
| Idempotência de notificação | Não explícita | `idempotency_key` UNIQUE em `notification_log` | Alta |
| Locks | Menção a Redis lock | Padronizar em PostgreSQL FOR UPDATE. Sem Redis lock. | Média |
| Fairness multi-tenant | Batches paginados | Confirmar: 1 task por batch (500 clientes), rate limit por tenant desde o dia 1 | Alta |
| Sorteio seed | `hash(id + ts + len)` | Adicionar UUID do sorteio + entregar hash da lista congelada antes do sorteio | Baixa |
| FCM batch size | 100 mencionado | Corrigir para 500 (limite real da API Firebase) | Baixa |
| PgBouncer | Não mencionado | Adicionar ao docker-compose antes de campanhas em produção | Média |
| Dead letter de notificações | Não explícito | Tabela `notification_dead_letter` + exibição na tela de campanhas | Média |
| E-mail em massa | Não mencionado | Verificar SPF/DKIM/DMARC antes de qualquer envio em lote | Alta |

---

*Revisão técnica adicionada em Março 2026.*

---

# PARTE IV — Pontos de Atenção de Arquitetura — Revisão Final

*Análise imparcial antes da implementação. Nível: arquiteto de software.*

---

## P1) Observabilidade do motor de campanhas

**Posição: concordo que é necessário. Discordo do escopo proposto para Fase 1.**

### O que vale agora (custo baixo, retorno alto):

**Sentry — sim, obrigatório desde o dia 1.**
- Captura exceções não tratadas com stack trace, contexto e request
- Plano gratuito é suficiente para 1-10 petshops
- Integração com FastAPI é 3 linhas de código
- Sem Sentry, erros silenciosos em workers nunca aparecem no radar

**Logs estruturados (JSON) — sim, obrigatório desde o dia 1.**
- Custo zero — é só disciplina de formato
- `{"event": "campaign_triggered", "tenant_id": 5, "campaign_type": "birthday", "customer_id": 123, "duration_ms": 42}`
- Permite grep, filtro por tenant, auditoria retroativa
- Em Docker, cai direto em `docker logs` ou qualquer agregador futuro

**Coluna `last_error` + `retry_count` nas tabelas de jobs — sim.**
- Isso não é observabilidade de infra, é rastreabilidade de negócio
- O dono do sistema consegue ver "campanha X falhou 3 vezes com erro Y" sem precisar acessar logs técnicos
- Tela de admin pode exibir isso

### O que NÃO vale agora:

**Prometheus + Grafana — não.**
- Requer containerização de exporter, datasource configurado, dashboards criados, alertas manutenidos
- Para 1 petshop: você passa mais tempo mantendo o infra de monitoramento do que resolvendo o problema real
- Adicione quando passar de 5 tenants ou tiver SLA formal com clientes

**OpenTelemetry — não.**
- É uma abstração para quando você tem múltiplos serviços (microserviços) e precisa rastrear uma requisição por todos eles
- Com um backend monolítico FastAPI, não agrega valor agora

### Monitoramento de filas específico:

Com PostgreSQL SKIP LOCKED (sem Redis nas filas), monitorar é trivial:
```sql
SELECT status, COUNT(*) FROM campaign_event_queue
GROUP BY status;
-- pending / processing / done / failed
```
Isso pode virar uma linha no painel de admin. Sem ferramenta externa. Sem custo.

Se Redis for usado para cache (Fase 2+), aí `redis-cli INFO stats` ou RedisInsight resolve.

**Decisão recomendada:** Sentry + logs JSON estruturados + colunas de rastreabilidade nas tabelas. Prometheus/Grafana em Fase 3, quando houver múltiplos tenants pagantes.

---

## P2) Replay de eventos — Event Store

**Posição: concordo com o problema. Discordo da solução de event sourcing completo.**

### Por que event store completo é exagero aqui:

Event sourcing resolve: "Quero reconstruir o estado do sistema a partir de eventos puros, sem depender do banco relacional."

Isso faz sentido quando:
- O estado muda de forma complexa e auditável (sistemas bancários, ERP financeiro)
- Você tem múltiplos consumidores do mesmo evento
- Você precisa time-travel (ver o estado em qualquer ponto no tempo)

Para campanhas de petshop, nenhum desses casos se aplica com força suficiente agora.

### O que o problema real pede:

O problema real é: **"worker falhou, como reprocesso o evento sem reprocessar dois vezes?"**

Isso já é resolvido com a estrutura proposta na Parte III (SKIP LOCKED + status na fila):

```
campaign_event_queue:
  id, tenant_id, event_type, payload, status
  (pending → processing → done | failed)
  retry_count, last_error, next_retry_at
```

Se o worker falha:
1. Transação reverte → status volta para `pending` automaticamente (SKIP LOCKED libera o row)
2. Outro worker pega na próxima rodada
3. Após N tentativas → `failed`, aparece na tela de admin

Isso é replay. Sem event store. Sem complexidade adicional.

### Quando event store faria sentido neste sistema:

Se você quiser responder "em que campanhas o cliente João participou ao longo de toda a sua vida de compras, incluindo dados de antes do sistema de campanhas existir" — aí você precisaria de event sourcing retroativo. Mas isso é requisito de analytics avançado, não de Fase 1.

**Decisão recomendada:** não criar `event_store` separado. Usar `campaign_event_queue` com status + retry como fonte de verdade. Guardar o resultado final em `campaign_customer_log` para auditoria histórica.

---

## P3) Rate limiting global de notificações

**Posição: rate limit por tenant é suficiente agora. Rate limit global é prematuro.**

### Por que rate limit global não é necessário para 1-10 petshops:

Com 10 petshops, o volume total de notificações é baixo. O risco não é esgotar o limite global do provedor — o risco é um único tenant mandar mensagem para 5.000 clientes de uma vez e esperar resposta instantânea.

Isso já é coberto pelo rate limit por tenant (500 por batch, intervalo entre batches).

### O que é real agora:

**SMTP:** a maioria dos provedores transacionais (SendGrid, Mailgun, Brevo) tem limites por conta, não por IP. Com 10 tenants, cada um com base pequena, você não chega perto do limite mensal de nenhum plano pago razoável.

**FCM:** sem limite que importe para essa escala. O limite é por projeto Firebase, e 10 petshops com até 10k usuários combinados é trivial.

**Reputação de domínio:** esse é o risco real de email em massa — não o rate limit técnico. SPF/DKIM/DMARC mal configurados ou envio de emails para bases antigas e frias derrubam o domínio. Isso não se resolve com rate limit de arquitetura — se resolve com configuração prévia de DNS e warm-up de domínio.

### Se rate limit global fosse necessário (Fase 2+):

Estrutura mais simples que token bucket: tabela `notification_global_counter` com janela deslizante de 1 hora por tipo. Atomic update via PostgreSQL `FOR UPDATE`. Redis só se a latência de escrita virar problema (improvável com <50 tenants).

**Decisão recomendada:** rate limit por tenant agora. Nenhum rate limit global. Priorizar configuração correta de SPF/DKIM/DMARC antes do primeiro envio em lote.

---

## P4) Estratégia de filas — filas separadas por tenant?

**Posição: uma fila global resolve agora. Filas separadas por tenant são overengineering para essa escala.**

### O problema real que filas separadas resolvem:

**Noisy neighbor:** tenant A com 50.000 clientes submete job de ranking às 23h. Bloqueia processamento do tenant B por 40 minutos.

Para isso, a solução não é necessariamente fila separada — é **fair scheduling dentro da fila única.**

### Abordagem recomendada: fila única com fair scheduling leve

```
campaign_event_queue:
  tenant_id, priority, created_at
  
Worker query:
  SELECT ... FROM campaign_event_queue
  WHERE status = 'pending'
    AND tenant_id NOT IN (
      SELECT tenant_id FROM campaign_event_queue
      WHERE status = 'processing'
      GROUP BY tenant_id HAVING COUNT(*) >= 3  -- máx 3 jobs simultâneos por tenant
    )
  FOR UPDATE SKIP LOCKED
  LIMIT 1
```

Isso garante que nenhum tenant monopoliza os workers sem precisar de múltiplas filas.

### Quando filas separadas por tenant fazem sentido:

Quando você tem SLAs diferentes por tenant (plano básico vs premium com processamento prioritário). Nesse caso, Redis + RQ com `queue = f"tenant_{id}"` resolve com pouco código. Mas isso é Fase 2.

### Redis + RQ vs PostgreSQL SKIP LOCKED:

Para essa escala: PostgreSQL SKIP LOCKED é preferível.
- Menos componentes na infra (sem Redis para fila)
- Transações ACID integradas com o restante do sistema
- Sem risco de fila Redis perder mensagens (in-memory sem persistência padrão)
- Redis fica reservado para cache e rate limiting quando necessário

**Decisão recomendada:** fila única no PostgreSQL com fair scheduling por tenant_id (limite de N jobs simultâneos por tenant). Redis+RQ entra se o volume justificar, não antes.

---

## P5) Batch processing — estratégia para campanhas sobre todos os clientes

**Posição: opção B (subtasks paginadas) desde o início, mesmo na escala pequena.**

### Por que não opção A (job único):

Funciona até ~500 registros sem problema. Acima disso:
- Job longo bloqueia o worker por minutos
- Se falhar no meio, recomeça do zero
- Sem visibilidade de progresso
- Não tem como pausar ou cancelar

Mesmo com 1 petshop e 2.000 clientes, um job de aniversário que roda em loop sem paginação tem esses problemas.

### Por que não opção C (event streaming):

Event streaming (Kafka, Kinesis) resolve "preciso processar eventos em ordem com múltiplos consumidores em tempo real." Para campanhas batch agendadas, é overengineering completo. Descarte.

### Opção B — implementação correta:

A chave não é "criar subtasks dinamicamente" — isso adiciona complexidade de orquestração. A implementação certa é **cursor-based pagination dentro do job**:

```python
async def run_birthday_campaign(tenant_id, campaign_id):
    cursor_id = 0
    while True:
        batch = await get_eligible_customers(
            tenant_id, cursor_id, limit=500
        )
        if not batch:
            break
        for customer in batch:
            await trigger_campaign_for_customer(customer)
            # cada trigger registra em campaign_customer_log
            # idempotente — ON CONFLICT DO NOTHING
        cursor_id = batch[-1].id
```

Benefícios:
- Se falhar no meio, reexecuta a partir do cursor (ou do começo com idempotência)
- Memória constante (não carrega todos os clientes de uma vez)
- Worker fica responsivo (pode ser interrompido entre batches)
- Adicionando `cursor_id` na tabela de jobs, dá para retomar do ponto exato após falha

**Decisão recomendada:** cursor-based pagination dentro do job desde o primeiro job de campanha. Limite de 500 clientes por iteração. Cursor persistido na tabela de jobs para retomada após falha.

---

## P6) Proteção contra explosão de campanhas simultâneas

**Posição: concordo que o risco existe. A proteção é mais simples do que parece.**

### O risco real:

Não é rodar 6 campanhas ao mesmo tempo em geral — é rodar o mesmo tipo de campanha em paralelo para o mesmo tenant, gerando duplo disparo.

Exemplo concreto: job de aniversário começa às 08:00 e ainda está rodando às 08:05 quando o cron dispara de novo.

### Solução mínima eficaz:

```sql
-- Tabela de locks de campanha
CREATE TABLE campaign_locks (
    tenant_id     INT,
    campaign_type VARCHAR(50),
    locked_at     TIMESTAMP DEFAULT NOW(),
    expires_at    TIMESTAMP,
    PRIMARY KEY (tenant_id, campaign_type)
);
```

Antes de executar uma campanha:
1. Tenta `INSERT INTO campaign_locks ... ON CONFLICT DO NOTHING`
2. Se inseriu → obteve o lock → executa
3. Se não inseriu → já está rodando → skip
4. `expires_at` = NOW() + 30 minutos (evita deadlock se worker morrer)
5. Worker limpa o lock ao terminar (ou expiração automática via job de limpeza)

Isso resolve o problema sem throttling global complexo.

### O que não fazer:

Não usar semáforo Redis para isso — PostgreSQL já tem o mecanismo. Não criar sistema de filas de "prioridade de campanh" — overengineering para o volume atual.

**Decisão recomendada:** tabela `campaign_locks` com `INSERT ON CONFLICT DO NOTHING` + `expires_at`. Custo: uma tabela pequena, 3 linhas de código no worker. Valor: elimina o risco de duplo disparo completamente.

---

## P7) Escalabilidade até 50 petshops + 100k clientes

**Posição: sim, consegue. Com 4 cuidados que precisam ser implementados desde o início.**

### O que a arquitetura atual aguenta sem refatoração:

50 petshops com 2.000 clientes cada (100k total) é completamente viável com FastAPI + PostgreSQL + 1 worker bem escrito. Não é necessário Redis obrigatório, Kafka, microserviços ou sharding.

Para referência: PostgreSQL bem indexado aguenta dezenas de milhões de linhas em tabelas de log antes de precisar de particionamento. 100k clientes com histórico de campanhas é uma tabela pequena.

### Os 4 cuidados obrigatórios desde o início:

**1. Índices compostos corretos — este é o mais crítico.**

Toda query de campanha filtra por `tenant_id` primeiro. Sem índice composto em `(tenant_id, status)` ou `(tenant_id, created_at)`, o banco faz full scan na tabela inteira conforme ela cresce.

Tabelas que precisam de índice composto obrigatório:
- `campaign_event_queue (tenant_id, status, created_at)`
- `campaign_customer_log (tenant_id, campaign_id, customer_id)`
- `loyalty_stamps (tenant_id, customer_id, created_at)`
- `cashback_transactions (tenant_id, customer_id, status)`
- `coupons (tenant_id, code)` — UNIQUE

Sem isso, a query que roda bem para 1 petshop começa a degradar a partir do 10º.

**2. PgBouncer — connection pooling antes de campanhas em produção.**

FastAPI com workers assíncronos + campanhas batch pode abrir dezenas de conexões simultâneas com o PostgreSQL. PostgreSQL tem custo de conexão alto (processo por conexão). Sem PgBouncer, acima de ~20 conexões simultâneas você começa a ver latência aumentar.

PgBouncer no modo `transaction` resolve isso com 1 container adicional e configuração mínima.

**3. Cursor-based pagination — nunca OFFSET em queries de campanha.**

`OFFSET 5000` em uma tabela com 100k linhas faz o banco varrer 5.000 linhas para descartar. Com cursor (`WHERE id > last_id`), é sempre O(1) via índice. Essa diferença é invisível com 1.000 clientes e dolorosa com 50.000.

**4. Nunca buscar todos os tenants de uma vez no worker.**

```python
# Errado — carrega todos os tenants em memória
tenants = await get_all_tenants()
for tenant in tenants:
    await run_campaign(tenant)

# Certo — processa um por vez, com cursor
async for tenant in iter_tenants_cursor():
    await run_campaign(tenant)
```

Com 50 tenants isso ainda funciona do jeito errado. Com 500, quebra.

### O que mudaria apenas em escala maior (>50 petshops):

- Particionamento de tabelas por `tenant_id` (PostgreSQL nativo, sem reescrever queries)
- Workers separados por fila de prioridade (planos premium)
- Read replica para queries de relatório

Nenhum desses requer reescrita de arquitetura — são adições incrementais ao que já existe.

**Decisão recomendada:** implementar os 4 cuidados desde o início (índices compostos, PgBouncer, cursor pagination, iteração de tenants via cursor). Não é overengineering — é fundação. O resto da escalabilidade vem de graça.

---

## Resumo das Decisões (Parte IV)

| Ponto | Decisão |
|-------|---------|
| Observabilidade | Sentry + logs JSON estruturados agora. Prometheus/Grafana em Fase 3. |
| Event Store | Não criar. Usar `campaign_event_queue` com status + retry como replay. |
| Rate limit global | Não necessário agora. Rate limit por tenant é suficiente. SPF/DKIM/DMARC primeiro. |
| Filas por tenant | Fila única com fair scheduling (limite de N jobs simultâneos por tenant). |
| Batch processing | Cursor-based pagination dentro do job. Cursor persistido para retomada após falha. |
| Explosão de campanhas | Tabela `campaign_locks` com `INSERT ON CONFLICT DO NOTHING` + `expires_at`. |
| Escalabilidade | Arquitetura atual aguenta 50 petshops + 100k clientes com 4 cuidados: índices compostos, PgBouncer, cursor pagination, iteração de tenants via cursor. |

---

*Parte IV adicionada em Março 2026.*

---

# PARTE V — Revisão Fria com Sub-questões Técnicas

*Segunda passada nos mesmos 7 pontos — respostas mais granulares por sub-pergunta. Análise imparcial.*

---

## P1) Observabilidade

**Concordo com a proposta. Com dois ajustes.**

**Sub-pergunta 1 — Sentry + logs JSON cobrem 80%? O que mais é obrigatório?**

Sim, cobrem 80%. O 20% restante obrigatório desde o início:

- **`correlation_id` nos logs** — cada execução de campanha recebe um UUID gerado no início. Todos os logs daquela execução (recompensa gerada, notificação enviada, erro parcial) carregam esse mesmo ID. Sem isso, é impossível reconstruir o que aconteceu num evento específico filtrando apenas por `tenant_id` + timestamp.

- **Coluna `last_error` + `retry_count` nas tabelas de jobs** — Sentry captura exceções não tratadas, mas não captura "campanha rodou, não achou nenhum elegível e o dono não sabe por quê." Isso é estado de negócio, não exceção técnica.

- **Tabela `campaign_run_log`** — registro por execução: `campaign_id`, `started_at`, `finished_at`, `customers_evaluated`, `customers_rewarded`, `notifications_sent`, `errors_count`, `status`. É o "livro de bordo" do motor, exibível na tela de admin. Custo: uma inserção por execução de campanha.

**Sub-pergunta 2 — Prometheus/Grafana deveria entrar agora com 1–10 tenants?**

Não. O argumento não é só custo de setup — é custo de manutenção contínua. Dashboard Grafana desatualizado que ninguém olha é pior do que não ter dashboard (cria falsa confiança). Com 1–10 tenants, painel admin do SaaS + Sentry + `docker logs` cobrem 100% dos casos reais. Prometheus entra quando você tiver SLA formal com clientes ou time dedicado a monitoração.

---

## P2) Replay de eventos / idempotência

**Concordo com `campaign_event_queue` no Postgres. Com precisão importante na sub-pergunta 3.**

**Sub-pergunta 1 — `campaign_event_queue` resolve replay nessa escala?**

Sim. SKIP LOCKED + status + `retry_count` + `next_retry_at` resolve completamente. Condição obrigatória: a transação do worker deve ser atômica — o `status` só muda para `done` depois que o efeito colateral (recompensa, notificação) foi persistido. Se o worker morrer no meio, rollback reverte o status para `pending` automaticamente.

**Sub-pergunta 2 — Quando recomendar `event_store` separado?**

Dois cenários reais — nenhum se aplica aqui agora:

1. **Múltiplos consumidores independentes do mesmo evento** — "compra finalizada" precisa disparar campanhas E atualizar ranking E acionar contabilidade E avisar ERP externo, cada um com cursor próprio. Com a fila única atual, você escreve um dispatcher que chama todos os handlers em sequência — simples e suficiente para este caso.

2. **Auditoria imutável por regulamentação** — sistemas financeiros, planos de saúde. Não se aplica aqui.

O que vale considerar agora é o **Outbox Pattern simplificado**: na mesma transação que confirma a venda, inserir na `campaign_event_queue`. Garante que se a venda confirmar, a entrada na fila também existe — sem risco de venda confirmada sem campanha disparada.

**Sub-pergunta 3 — Idempotência entre recompensa gerada vs notificação enviada.**

Este é o ponto mais delicado. **Os dois logs devem ser separados e independentes, com mecanismos de idempotência próprios.**

Fluxo correto:
```
venda finalizada
  → [1] gera recompensa
        UNIQUE(tenant_id, customer_id, venda_id) → ON CONFLICT DO NOTHING
        registra em: loyalty_stamps / cashback_transactions

  → [2] agenda notificação (separado do [1])
        idempotency_key = hash(reward_id + channel + template)
        UNIQUE(idempotency_key) → ON CONFLICT DO NOTHING
        registra em: notification_queue

  → [3] worker envia notificação
        só pega status = 'pending'
        marca 'sent', registra em notification_log
```

Se o evento da venda for reprocessado: etapa 1 não duplica recompensa, etapa 2 não enfileira segunda notificação, etapa 3 não reenvia. Cada etapa é idempotente de forma independente.

O erro clássico é usar o mesmo log para recompensa e notificação, ou checar idempotência da notificação pela `venda_id` (que não existe na tabela de notificações).

---

## P3) Rate limit de notificações

**Concordo com rate limit por tenant sem global agora. Com adição importante.**

**Sub-pergunta 1 — Rate limit global é necessário com 1–10 tenants?**

Não. Com 10 tenants e base pequena (500–2.000 clientes por petshop), o volume combinado é irrelevante para qualquer provedor transacional moderno. O que pode explodir é um único tenant mandando 3.000 push em 2 segundos — e isso é rate limit por tenant.

**Sub-pergunta 2 — Qual modelo e onde armazenar?**

**Janela deslizante no Postgres**, não token bucket.

Token bucket é mais eficiente para sistemas de altíssima frequência (milhares de req/s). Para campanhas de petshop (dezenas de notificações por minuto por tenant), é overengineering e mais difícil de depurar.

Janela deslizante simples:
```sql
SELECT COUNT(*) FROM notification_log
WHERE tenant_id = $1
  AND sent_at > NOW() - INTERVAL '1 hour'
```
Índice em `(tenant_id, sent_at)` torna a query trivial. Threshold configurável por tenant. Sem Redis, sem infra adicional. Redis só entra se a checagem virar gargalo de latência — improvável com < 50 tenants.

**Adição crítica — warm-up de domínio de e-mail:**

SPF/DKIM/DMARC são necessários mas não suficientes. Provedores de e-mail (Gmail, Outlook) classificam por histórico de reputação do domínio. Um domínio novo que manda 2.000 e-mails na segunda-feira vai para spam em massa.

Warm-up correto: semana 1 → máx 100/dia → semana 2 → 500/dia → semana 3 → 2.000/dia. Sem warm-up, a funcionalidade de e-mail marketing vai parecer quebrada para todos os tenants mesmo com tudo configurado corretamente.

---

## P4) Estratégia de filas

**Concordo com Postgres-queue na Fase 1. Com detalhe sobre fairness.**

**Sub-pergunta 1 — Postgres vs Redis como fila. Posição?**

Concordo com Postgres. Os argumentos são sólidos:
- Redis padrão não é ACID. RDB/AOF precisam de configuração explícita e mesmo assim há janela de perda de dados.
- Job perdido na queda do container = recompensa não gerada = bug impossível de reproduzir em produção.
- Postgres já está na infra. Redis para fila = mais um container, mais uma dependência, mais um ponto de falha.

Contra-argumento real mas irrelevante nessa escala: Postgres como fila coloca carga extra no banco. Para tens de milhares de jobs/s, importa. Para campanhas de 1–10 tenants com dezenas de eventos por minuto, não importa.

**Sub-pergunta 2 — Fairness simples sem overengineering?**

Via query SKIP LOCKED com limite por tenant:

```sql
SELECT id FROM campaign_event_queue
WHERE status = 'pending'
  AND tenant_id NOT IN (
    SELECT tenant_id FROM campaign_event_queue
    WHERE status = 'processing'
    GROUP BY tenant_id HAVING COUNT(*) >= 2
  )
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 1
```

O `2` vira uma constante `MAX_CONCURRENT_JOBS_PER_TENANT = 2` no código. Zero infra adicional.

---

## P5) Batch processing

**Concordo com cursor pagination desde o início. Com precisão sobre tamanho e retomada.**

**Sub-pergunta 1 — Cursor pagination desde o primeiro dia?**

Sim, obrigatório. O motivo vai além de performance: é comportamento determinístico em falhas. Com OFFSET, se um cliente novo entrar na base entre o batch 1 e o batch 2, o OFFSET pode pular ou duplicar um cliente. Com cursor (`WHERE id > last_id`), o resultado é estável mesmo com inserts concorrentes.

**Sub-pergunta 2 — Tamanho de batch?**

500 é um bom padrão geral, mas o número certo depende da operação por cliente:
- Apenas verificar elegibilidade + gravar log → 500–1.000 por batch
- Verificar + enviar notificação + gravar recompensa → 100–200 por batch (mais I/O por cliente)

Implementar como `BATCH_SIZE` configurável por tipo de campanha. Não hardcodar 500 em 10 lugares — quando precisar ajustar, vai precisar ajustar em todos.

**Sub-pergunta 3 — Subtasks por batch vs loop interno com cursor?**

Loop interno com cursor, sem subtasks. Motivo: subtasks requerem orquestração (job pai precisa saber quando todos os filhos terminaram, lidar com falhas parciais, agregar resultados). Para 100k clientes em 200 batches de 500, complexidade de subtasks é injustificada. A exceção seria paralelismo real entre batches com múltiplos workers — mas para campanhas rodando de madrugada, velocidade não é requisito.

**Sobre retomada:** persistir o cursor é mais robusto do que confiar só em idempotência. Idempotência garante que reprocessar um cliente não duplica a recompensa. Mas processar 9.000 clientes de novo quando faltavam 1.000 é desperdício. Cursor de retomada resolve com uma coluna `cursor_last_id` na tabela de jobs.

---

## P6) Explosão de campanhas simultâneas

**Concordo com `campaign_locks` no Postgres. Com detalhe sobre deadlock e starvation.**

**Sub-pergunta 1 — Postgres lock vs Redis lock?**

Postgres é melhor por durabilidade. Redis lock (Redlock) tem problema fundamental: se Redis reiniciar enquanto o job ainda está rodando, dois jobs vão acreditar ter o lock simultaneamente — exatamente o caso que você queria evitar. Com `campaign_locks` no Postgres + `expires_at`, se o worker morreu o `expires_at` passa e o próximo job obtém o lock normalmente. ACID garante que dois workers nunca inserem o mesmo lock ao mesmo tempo.

**Sub-pergunta 2 — Risco de deadlock ou starvation?**

**Deadlock:** não existe nesse design. `INSERT ON CONFLICT DO NOTHING` é uma operação atômica sem dependência entre dois locks — não cria ciclo.

**Starvation:** existe um cenário real — job trava sem limpar o lock e `expires_at` é muito longo. Mitigações:
- `expires_at` = NOW() + duração máxima esperada do job + 20% de margem (ex: job de ranking que leva 10 min → `expires_at` = NOW() + 15 min)
- Job de limpeza rodando a cada 5 minutos deletando locks expirados
- Alerta no painel admin: "Campanha X está com lock ativo há N minutos" — sinal de job travado

---

## P7) Escalabilidade

**Concordo com o teto de 50 tenants / 100k clientes sem refatoração. Com precisão nos must-haves.**

**Sub-pergunta 1 — Confirma 50 tenants / 100k clientes sem refatoração estrutural?**

Sim. "Sem refatoração estrutural" significa: queries, modelos, lógica de negócio e workers não precisam mudar. O que pode ser adicionado incrementalmente:
- Índices que ficaram faltando (`CREATE INDEX CONCURRENTLY` — sem downtime)
- Particionamento de tabelas históricas por `tenant_id` ou range de data (Postgres nativo, sem alterar queries)
- Read replica para relatórios (sem mudar queries — só apontar leitura para a replica)
- Aumentar connection pool size

**Sub-pergunta 2 — Os 3 must-haves antes de codar?**

**1. Índices compostos com `tenant_id` na primeira posição — antes de qualquer dado entrar em produção.**

Toda query de campanha começa com `WHERE tenant_id = $1`. Sem índice composto, PostgreSQL faz sequential scan em toda a tabela. Com 1 tenant e 1.000 clientes: invisível. Com 20 tenants e 5.000 clientes cada: a query de "verificar elegíveis" demora segundos. Tabelas críticas:

- `campaign_event_queue (tenant_id, status, created_at)`
- `campaign_customer_log (tenant_id, campaign_id, customer_id)` — UNIQUE
- `loyalty_stamps (tenant_id, customer_id, created_at)`
- `cashback_transactions (tenant_id, customer_id, status)`
- `coupons (tenant_id, code)` — UNIQUE

**2. PgBouncer no docker-compose antes de workers em produção.**

FastAPI assíncrono + múltiplos workers abre conexões com o Postgres. Cada conexão usa ~5MB de RAM e um processo separado. Com campanhas batch em paralelo, pode chegar a 30–50 conexões pico. Sem PgBouncer, o Postgres começa a rejeitar conexões. PgBouncer: 1 container, 10 linhas de config, zero mudança no código da aplicação.

**3. `tenant_id` em TODA tabela nova de campanhas — sem exceção.**

Não existe "essa tabela é global e não precisa de tenant_id" nesse sistema. Qualquer tabela nova de dados de negócio sem `tenant_id` desde o início vai exigir migração de dados + refatoração de queries depois. Isso inclui: `campaign_locks`, `campaign_run_log`, `notification_queue`, `campaign_event_queue`, `coupons`, tudo.

**Risco adicional não citado — N+1 no loop do motor:**

O padrão mais fácil de introduzir ao iterar sobre clientes:
```python
for customer in batch:
    reward = get_reward_config(campaign_id)  # 1 query por cliente!
```
Com 500 clientes → 500 queries para buscar a mesma config. Não aparece em testes nem com volume pequeno. Aparece em produção quando o batch demora 10x mais. Regra desde o início: **carregar configs e dados estáticos da campanha uma vez antes do loop**.

---

## Resumo das Decisões (Parte V)

| Ponto | Posição | Adição em relação à Parte IV |
|-------|---------|------------------------------|
| P1 Observabilidade | Concordo: Sentry + logs JSON, sem Prometheus agora | `correlation_id` obrigatório; tabela `campaign_run_log` para auditoria de negócio |
| P2 Replay | Concordo: Postgres-queue resolve | Outbox Pattern: inserir na fila na mesma transação que confirma a venda; logs de recompensa e notificação separados e independentes |
| P3 Rate limit | Concordo: por tenant apenas, sem global | Janela deslizante no Postgres (não token bucket); warm-up de domínio é pré-requisito antes do primeiro envio em lote |
| P4 Filas | Concordo: Postgres-queue na Fase 1 | Fair scheduling via `HAVING COUNT(*) >= 2` por tenant; Redis só para cache em Fase 2+ |
| P5 Batch | Concordo: cursor desde o dia 1 | `BATCH_SIZE` configurável por tipo de campanha; loop interno sem subtasks; cursor persistido para retomada eficiente |
| P6 Locks | Concordo: Postgres `campaign_locks` | Deadlock impossível nesse design; starvation prevenido com `expires_at` ajustado + alerta no admin |
| P7 Escalabilidade | Concordo: 50 tenants / 100k sem refatoração | 3 must-haves: índices compostos antes de qualquer dado, PgBouncer antes de workers em prod, `tenant_id` em toda tabela nova; risco de N+1 no loop de campanha |

---

*Parte V adicionada em Março 2026.*

---

# PARTE VI — Refinamentos Finais de Engenharia

*Análise imparcial dos 8 pontos de refinamento antes da implementação.*

---

## P1) Separar avaliação de elegibilidade e execução de recompensa

**Concordo com a separação. Com ressalva sobre o momento.**

### Por que a separação faz sentido:

`campaign_customer_log` em uma tabela única mistura dois conceitos fundamentalmente diferentes:

- **Avaliação:** "esse cliente foi considerado para a campanha e não era elegível" — serve para debug, métricas de alcance e análise de conversão
- **Execução:** "esse cliente recebeu a recompensa" — é o fato de negócio com consequência financeira/operacional

Sem separação, você não consegue responder "de 1.200 clientes avaliados, quantos foram recompensados?" sem processar os registros individualmente. Com separação, é uma query de COUNT por tabela.

### A ressalva — custo de armazenamento de avaliações:

Avaliações incluem clientes **não elegíveis**. Para um job de aniversário que avalia 1.000 clientes por mês e recompensa 30 (3%), a tabela `campaign_evaluations` vai crescer 33x mais rápido que `campaign_executions`. Com 10 tenants e 12 campanhas rodando mensalmente, são centenas de milhares de linhas de avaliação por ano sem valor operacional direto — só analítico.

### Decisão recomendada: abordagem híbrida

- `campaign_executions` — criar desde o início. Cada recompensa concedida tem um registro. É o fato de negócio.
- **Não criar** `campaign_evaluations` linha por linha. Em vez disso, agregar no `campaign_run_log` (já proposto na Parte V): `customers_evaluated`, `customers_rewarded`, `conversion_rate`. Isso dá a métrica sem o custo de armazenamento individual de cada avaliação negativa.
- Se surgir necessidade de debug específico ("por que o cliente X não recebeu?"), registrar **somente avaliações que resultaram em exclusão por regra específica** (`evaluation_result = 'excluded_inactive'`, `'excluded_low_score'` etc.) — não todos os 1.000.

### Índices necessários para `campaign_executions`:
- `UNIQUE(tenant_id, campaign_id, customer_id, reference_period)` — idempotência por período
- `(tenant_id, campaign_id, executed_at)` — queries de relatório
- `(tenant_id, customer_id, executed_at)` — histórico do cliente

---

## P2) Tabela de uso de cupons (`coupon_redemptions`)

**Concordo. Essa tabela é obrigatória, não opcional.**

### Por que separar do registro do cupom:

A tabela `coupons` representa a existência e configuração do cupom (código, desconto, validade, limite de usos). `coupon_redemptions` representa cada uso real. São entidades diferentes com ciclos de vida diferentes.

Sem separação:
- Para checar se um cupom com `max_uses = 3` já foi usado 3 vezes, você faz UPDATE em `coupons.current_uses` com risco de race condition
- Você não sabe em qual canal cada uso aconteceu
- Não tem como rastrear qual venda usou o cupom sem join complexo

Com `coupon_redemptions`:
- Cada uso é um registro imutável (append-only) — sem UPDATE, sem race condition
- `COUNT(id) WHERE coupon_id = X` resolve a contagem de usos
- Filtrar por `channel` e `order_id` é direto

### Campos adicionais que valem incluir além dos sugeridos:

- `tenant_id` — obrigatório (multi-tenant)
- `discount_value_applied` — o valor real de desconto que foi aplicado (pode diferir do configurado em cupons percentuais)
- `voided_at` / `voided_by` — para cancelamento de venda reverter o uso do cupom

### Proteção contra uso duplo no mesmo cupom de uso único:

`UNIQUE(coupon_id)` não resolve sozinho porque entre o SELECT (verificar se foi usado) e o INSERT (registrar o uso) outro processo pode inserir primeiro. A proteção correta: `INSERT INTO coupon_redemptions ... ON CONFLICT (coupon_id) DO NOTHING` retorna 0 rows afetadas → a aplicação rejeita a venda. Isso é safe sem SELECT prévio.

---

## P3) Proteção contra replay em fidelidade

**Concordo com `UNIQUE(tenant_id, customer_id, purchase_id)`. Isso é obrigatório, não opcional.**

### Por que `FOR UPDATE` sozinho não é suficiente:

`SELECT FOR UPDATE` protege contra concorrência simultânea dentro da mesma transação. Mas não protege contra reprocessamento do mesmo evento em momentos diferentes — ex: o job de fidelidade roda duas vezes por bug, ou o evento `purchase_completed` é reprocessado manualmente para corrigir um erro anterior.

Nesses casos, não há concorrência — há dois requests sequenciais, cada um bem-sucedido por conta própria. Sem UNIQUE, ambos inserem registros duplicados sem erro.

### `UNIQUE(tenant_id, customer_id, purchase_id)` resolve:

O segundo insert vai falhar com violação de constraint. O código usa `ON CONFLICT DO NOTHING` → operação idempotente. A compra pode ser reprocessada N vezes sem duplicar carimbos.

### Atenção ao nome do campo:

Chamar de `purchase_id` é correto, mas verificar se o sistema usa `venda_id` consistentemente. O campo na constraint deve mapear direto para `vendas.id` — não para um ID de evento externo que pode não existir para vendas antigas.

### Índice implícito:

Uma constraint UNIQUE em PostgreSQL cria automaticamente um índice B-tree. Não é preciso criar índice separado para `(tenant_id, customer_id, purchase_id)` — ele vem de graça com a constraint.

---

## P4) Auditoria de cashback com `source_event_id`

**Concordo com o conceito. Com precisão sobre como estruturar.**

### O campo `source_event_id` está correto mas incompleto:

`source_event_id = "purchase_completed_87423"` como string concatenada tem problemas:
- Não é foreign key — não dá para checar integridade referencial
- Parsing de strings para entender a origem é frágil (e se o padrão mudar?)
- Não indexa bem para queries do tipo "todos os cashbacks desta venda"

### Estrutura mais robusta:

Dois campos separados em vez de um composto:
- `source_type` (enum): `'purchase'`, `'manual_adjustment'`, `'campaign_reward'`, `'refund_reversal'`
- `source_id` (integer): o ID da entidade de origem — `venda_id`, `campaign_execution_id` etc.

Com isso: `WHERE source_type = 'purchase' AND source_id = 87423` → indexável, sem parsing de string, com possibilidade de foreign key condicional.

### O modelo ledger (já adotado) já é o certo:

Nunca atualizar um saldo diretamente — sempre inserir uma linha de transação. O saldo atual é `SUM(amount)` sobre as transações. Isso garante auditoria completa, permite estornos (transação negativa), e permite reconstruir o histórico em qualquer ponto no tempo. Não mudar essa decisão.

### Campo adicional recomendado:

`reversed_by_transaction_id` — quando um cashback é estornado (ex: venda cancelada), a transação de estorno aponta de volta para a transação original. Cria uma corrente auditável sem deletar nada.

---

## P5) Histórico de ranking

**Concordo. Vale manter desde o início.**

### Por que desde o início:

Se ranking começa sem histórico e depois alguém pede "mostre a evolução do meu ranking nos últimos 6 meses no app", você não tem os dados retroativos — eles foram sobrescritos. Histórico de ranking é uma de três coisas que são impossíveis de recuperar depois: os outros dois são logs de eventos apagados e dados de uso de cupom sem tabela de redemptions. O custo de armazenar histórico de ranking é baixo (uma linha por cliente por mês por tenant).

### Estrutura recomendada:

Os campos sugeridos (`customer_id`, `rank`, `score`, `month`) estão corretos. Acrescentar:
- `tenant_id` — obrigatório
- `level` (`'bronze'`, `'prata'`, `'ouro'`, `'platina'`) — para mostrar mudança de nível no app ("você subiu para Ouro!")
- `previous_rank` — para mostrar "subiu 3 posições" sem precisar de query no período anterior

### Estratégia de armazenamento:

**INSERT no final do job de recálculo de ranking**, nunca UPDATE. Após calcular o ranking do mês, inserir uma linha por cliente com o resultado. A tabela `customers_ranking` (ou equivalente) mantém o ranking atual; `customer_rank_history` mantém o histórico. Não usar a mesma tabela para os dois propósitos com flag `is_current` — isso complica as queries.

### Volume: não é problema.

10 tenants × 500 clientes × 12 meses = 60.000 linhas/ano. Trivial.

---

## P6) Deduplicação de notificações

**Concordo. Deduplicação é obrigatória desde o primeiro dia.**

Isso já foi abordado nas Partes III e V, mas a pergunta merece precisão sobre a estrutura.

### Por que é obrigatória:

Sem deduplicação, os cenários de falha mais comuns causam reenvio:
- Worker enviou push, confirmação do FCM demorou, transação fez timeout, job é reprocessado → segundo push enviado para o mesmo cliente
- Campanha de aniversário roda às 00:00 e de novo às 00:05 por bug no cron → dois emails de feliz aniversário

Ambos são visíveis para o cliente final e prejudicam a reputação do sistema.

### Campo `idempotency_key` vs tabela separada:

**Campo `idempotency_key` com UNIQUE na `notification_queue`** é suficiente e mais simples que tabela separada.

Construção do key: `hash(tenant_id + customer_id + campaign_execution_id + channel + template_id)`. Assim, a mesma execução de campanha nunca gera dois inserts na notification_queue para o mesmo cliente no mesmo canal com o mesmo template.

Tabela separada de deduplicação (`notification_dedup`) só faria sentido se você precisasse verificar deduplicação em canais que saem do ciclo da `notification_queue` (ex: SMS via API externa sem fila interna). Para o sistema atual, UNIQUE na própria fila resolve.

### Adição: deduplicação pós-envio.

`UNIQUE` na `notification_queue` protege contra reenvio antes do envio. Mas se o worker enviar, registrar em `notification_log` e então falhar antes de marcar `status = 'sent'` na fila, o job vai tentar reenviar. Para isso: `UNIQUE(idempotency_key)` também em `notification_log` + `ON CONFLICT DO NOTHING`. Se já está no log, o worker marca a fila como `sent` e avança — sem reenvio.

---

## P7) Tabela de métricas diárias (`campaign_metrics_daily`)

**Discordo — para esta fase. A abordagem de métricas dinâmicas é preferível.**

### Por que não criar `campaign_metrics_daily` agora:

Tabelas de métricas pré-agregadas fazem sentido quando as queries de agregação dinâmica ficam lentas demais. Com 1–10 tenants e histórico de meses, as tabelas de origem (`campaign_executions`, `campaign_run_log`, `notification_log`) são pequenas. Queries como `COUNT(*) WHERE campaign_id = X AND DATE(executed_at) = Y` rodam em milissegundos com índice em `(campaign_id, executed_at)`.

Criar `campaign_metrics_daily` agora adiciona:
- Job de agregação que roda diariamente (mais um worker para manter)
- Risco de métricas desincronizadas com a realidade se o job falhar
- Complexidade de decidir quando re-agregar (e se dados retroativos forem corrigidos?)
- Uma fonte de verdade extra que pode divergir das tabelas de origem

### Quando `campaign_metrics_daily` faria sentido:

Quando o painel admin começar a demorar para carregar — ex: `COUNT` sobre `campaign_executions` com 5 milhões de linhas leva segundos. Isso não vai acontecer com 10 tenants.

### O que fazer em vez disso:

- `campaign_run_log` (já definido) já agrega por execução: `customers_evaluated`, `customers_rewarded`, `notifications_sent`, `errors_count`
- O painel admin soma essas colunas por campanha/período → query simples, sem job adicional
- `campaign_run_log` é inserido pelo próprio worker ao final de cada run — sincronizado por definição

### Quando reavaliar:

Se o dashboard admin começar a demorar visualmente (> 2 segundos para carregar), aí cria-se `campaign_metrics_daily` com job de agregação noturno. Não antes.

---

## P8) Índices multi-tenant obrigatórios

**Concordo que índices compostos são o item de maior impacto arquitetural. Com lista definitiva.**

### Regra geral:

Em sistema multi-tenant, qualquer query sem `tenant_id` como primeiro filtro é um full scan em toda a tabela de todos os tenants. Isso é aceitável com 1 tenant e nenhum dado. É catastrófico com 10 tenants e meses de histórico.

A Parte V já cobriu os principais. Aqui a lista definitiva e consolidada:

**Tabelas de campanhas:**

| Tabela | Índice composto | Tipo | Motivo |
|--------|----------------|------|--------|
| `campaign_event_queue` | `(tenant_id, status, created_at)` | B-tree | Worker query principal — filtra pending por tenant |
| `campaign_executions` | `(tenant_id, campaign_id, customer_id, reference_period)` | UNIQUE | Idempotência de execução |
| `campaign_executions` | `(tenant_id, customer_id, executed_at)` | B-tree | Histórico do cliente no app |
| `campaign_run_log` | `(tenant_id, campaign_id, started_at)` | B-tree | Painel admin por campanha/período |
| `campaign_locks` | `(tenant_id, campaign_type)` | PRIMARY KEY | Já cobre — não precisa de índice adicional |
| `loyalty_stamps` | `(tenant_id, customer_id, purchase_id)` | UNIQUE | Idempotência + lookup por cliente |
| `loyalty_stamps` | `(tenant_id, customer_id, created_at)` | B-tree | Contagem de carimbos vigentes |
| `cashback_transactions` | `(tenant_id, customer_id, source_type, source_id)` | B-tree | Auditoria de origem |
| `cashback_transactions` | `(tenant_id, customer_id, created_at)` | B-tree | Saldo do cliente |
| `coupons` | `(tenant_id, code)` | UNIQUE | Lookup de cupom no PDV/ecommerce |
| `coupon_redemptions` | `(tenant_id, coupon_id)` | B-tree (ou UNIQUE se uso único) | Contagem de usos |
| `coupon_redemptions` | `(tenant_id, customer_id, used_at)` | B-tree | Histórico do cliente |
| `notification_queue` | `(tenant_id, status, scheduled_at)` | B-tree | Worker query de envio |
| `notification_queue` | `(idempotency_key)` | UNIQUE | Deduplicação |
| `notification_log` | `(tenant_id, customer_id, sent_at)` | B-tree | Rate limit por tenant |
| `notification_log` | `(idempotency_key)` | UNIQUE | Deduplicação pós-envio |
| `customer_rank_history` | `(tenant_id, customer_id, month)` | UNIQUE | Um registro por cliente por mês |

### Existe padrão melhor para multi-tenant?

Há dois padrões mais avançados — ambos desnecessários agora:

1. **Row-Level Security (RLS) no PostgreSQL** — define policies que o banco aplica automaticamente, garantindo isolamento de tenant mesmo em queries que esquecem o `WHERE tenant_id`. Muito útil, mas adiciona complexidade de configuração e pode surpreender com performance se policies forem mal escritas. Considerar quando o número de tenants crescer e o risco de vazamento de dados entre tenants passar a ser uma preocupação real.

2. **Schema separado por tenant** — cada tenant tem seu próprio schema no Postgres (`tenant_5.loyalty_stamps`). Isolamento total, sem necessidade de `tenant_id` nas tabelas. Mas: migrações precisam rodar em todos os schemas, queries cross-tenant são complexas, não escala bem acima de dezenas de tenants. Não recomendar para este sistema.

O padrão atual (tabela compartilhada + `tenant_id` em tudo + índices compostos) é o correto para essa fase e escala.

---

## Resumo das Decisões (Parte VI)

| Ponto | Posição | Decisão |
|-------|---------|---------|
| P1 Separar avaliação/execução | Concordo parcialmente | `campaign_executions` desde o início; **não** `campaign_evaluations` por cliente — agregar em `campaign_run_log` |
| P2 `coupon_redemptions` | Concordo, obrigatório | Tabela separada append-only; adicionar `discount_value_applied`, `voided_at`; usar `ON CONFLICT` para proteção contra uso duplo |
| P3 UNIQUE em fidelidade | Concordo, obrigatório | `UNIQUE(tenant_id, customer_id, purchase_id)` + `ON CONFLICT DO NOTHING` — não depender só de `FOR UPDATE` |
| P4 `source_event_id` em cashback | Concordo com conceito, ajuste na estrutura | Usar `source_type` (enum) + `source_id` (int) em vez de string concatenada; adicionar `reversed_by_transaction_id` |
| P5 Histórico de ranking | Concordo, desde o início | INSERT mensal em `customer_rank_history`; incluir `level` e `previous_rank`; não usar flag `is_current` |
| P6 Deduplicação de notificações | Concordo, obrigatório | `UNIQUE(idempotency_key)` em `notification_queue` + em `notification_log`; não criar tabela separada |
| P7 `campaign_metrics_daily` | Discordo para esta fase | Métricas dinâmicas via `campaign_run_log` são suficientes; criar tabela pré-agregada só quando dashboard ficar lento |
| P8 Índices multi-tenant | Concordo, obrigatório | Lista definitiva de 17 índices — todos obrigatórios antes do primeiro deploy de campanhas |

---

*Parte VI adicionada em Março 2026.*

---

# PARTE VII — Arestas Finais Antes de Codar

*10 pontos de inconsistência ou lacuna identificados. Análise imparcial por item.*

---

## P1) Conflito: Fase 1 sem Celery vs menção a Redis/RQ/Celery

**Concordo que existe inconsistência. Aqui está o fechamento definitivo.**

### O conflito real:

Em partes anteriores do documento aparecem referências a "Redis + RQ" como opção de fila e a "APScheduler embutido" como alternativa para Fase 1. As duas aparecem sem deixar claro qual é o padrão. Isso vai travar na hora de implementar.

### Decisão fechada:

**Fase 1 (1–10 tenants):**
- Agendamento: **APScheduler embutido no processo FastAPI** (ou script Python simples rodando em loop com `asyncio.sleep`). Zero infra adicional.
- Fila de jobs: **tabela `campaign_event_queue` no PostgreSQL + SKIP LOCKED**. Zero Redis.
- Workers: **processo Python separado** (não thread dentro do FastAPI) rodando com `docker-compose` como serviço adicional. Simples, reiniciável, logável.

**Fase 2+ (>10 tenants ou necessidade de paralelismo real):**
- Agendamento: **Celery Beat** substitui APScheduler (mantém mesmas tarefas, só troca o scheduler)
- Fila: **Celery + Redis** substitui Postgres-queue (migração incremental — uma tarefa por vez)
- Workers: **Celery workers** substituem o processo Python manual

### Por que essa transição não cria refatoração estrutural:

A lógica de negócio de cada campanha (Strategy Pattern, handlers) não muda. O que muda é só o "transporte" — de onde o handler é chamado (APScheduler → Celery Beat) e onde os jobs ficam enfileirados (Postgres → Redis). Se os handlers forem funções puras sem dependência do scheduler, a migração é trocar 1 arquivo de configuração e as declarações `@celery.task` em vez de `@scheduler.scheduled_job`.

**Regra de ouro:** nunca colocar lógica de campanha dentro do agendador. O scheduler só chama `run_birthday_campaign(tenant_id)`. A lógica fica no handler.

---

## P2) Ranking: OFFSET deve sair do documento

**Concordo. OFFSET não deve aparecer como opção. Remover.**

### Por que OFFSET é problemático especificamente em ranking:

Ranking é recalculado sobre todos os clientes ordenados por score. Um job que usa OFFSET para paginar assim:
- `LIMIT 500 OFFSET 0` → processa clientes 1-500
- `LIMIT 500 OFFSET 500` → processa clientes 501-1000

Se um novo cliente entra ou um score muda entre o batch 1 e o batch 2, o OFFSET desloca os resultados — clientes são pulados ou processados duas vezes. Em ranking isso é grave: o cliente 501 pode nunca ser processado se um cliente novo entrar antes dele.

### Padrão de cursor recomendado:

**Cursor por `id`** é o mais simples e correto para ranking:
```
WHERE id > last_processed_id
ORDER BY id
LIMIT 500
```

Por que `id` e não `score` ou `created_at`:
- `id` é único e estável — nunca muda para um registro existente
- `score` pode empatar e não é único — cursor por score pode pular clientes com score igual
- `created_at` pode ter resolução insuficiente (microsegundos) e não é garantidamente único

**Cursor composto** (`score DESC, id ASC`) só faz sentido se você precisar processar os clientes em ordem de score — ex: calcular rankings com desempate por antiguidade. Para a maioria dos jobs de campanha, ordem de processamento não importa — só o resultado importa. Use `id` simples.

---

## P3) Sorteios — seed auditável

**Concordo que é necessário. Não é paranoia.**

### Por que o seed atual é insuficiente:

`hash(drawing_id + timestamp_execucao + len(entries))` tem dois problemas:

1. **`timestamp_execucao` é controlável** — quem opera o sistema pode rodar o sorteio em momentos diferentes até obter o resultado desejado. Sem prova de que o timestamp foi fixado antes do sorteio, qualquer resultado pode ser questionado.

2. **`len(entries)` não identifica quem participou** — dois sorteios com 50 participantes cada teriam o mesmo fator `len`, mesmo que os participantes sejam completamente diferentes.

### Estrutura mínima auditável:

Três momentos separados e imutáveis:

1. **Na criação do sorteio:** gerar `seed_uuid` (UUID aleatório) e gravar. Isso garante que o sorteio tem uma semente que não pode ser calculada antecipadamente por ninguém.

2. **24h antes do sorteio (ou no momento de fechamento das inscrições):** congelar a lista de participantes e gravar `entries_hash = SHA256(sorted list of participant IDs)`. Publicar esse hash para os participantes se quiserem verificar.

3. **No momento do sorteio:** `seed_final = SHA256(seed_uuid + timestamp_execucao + entries_hash)`. O resultado é determinístico dado os três inputs, mas nenhum deles pode ser manipulado individualmente sem alterar os outros.

### O que isso resolve:

- Operador não consegue "testar" seeds diferentes rodando na hora certa (seed_uuid já estava fixado antes)
- Participantes podem verificar que a lista de participantes não foi alterada após fechamento (entries_hash publicado antes)
- Resultado é reproduzível — dado os três inputs, qualquer pessoa pode recalcular e conferir

### Impacto na implementação:

Adicionar dois campos em `drawings`: `seed_uuid` (gerado na criação) e `entries_hash` (gerado no fechamento). Nenhuma mudança na lógica de seleção do vencedor — só na geração do seed.

---

## P4) FCM: limite de batch e TTL padrão

**Discordo parcialmente da premissa. Esclarecimento necessário.**

### O limite depende da API usada:

A Firebase Cloud Messaging tem três APIs diferentes com limites diferentes:

| API | Limite por chamada | Uso recomendado |
|-----|-------------------|-----------------|
| `send` (individual) | 1 mensagem | Alta personalização |
| `sendEach` / `sendAll` | 500 mensagens por batch | Mensagens diferentes por destinatário |
| Topics | Ilimitado (assinantes do topic) | Mensagem idêntica para muitos |

O documento anterior mencionou 500 — isso é correto para `sendEach`. Se o sistema usa `send` individual em loop, o limite relevante é o de requisições por segundo (não de batch). Se usar Topics, o "batch" não existe.

**Recomendação:** para campanhas de petshop (mensagens personalizadas com nome do cliente), usar `sendEach` com batches de 500. Não usar Topics (perde personalização).

### TTL recomendado por tipo de notificação:

| Tipo | TTL sugerido | Motivo |
|------|-------------|--------|
| Aniversário | 48h | Urgência média — cliente ainda está no aniversário no dia seguinte |
| Brinde mensal / destaque | 72h | Pode ser resgatado em alguns dias |
| Cashback gerado | 7 dias | Crédito não expira em 1 dia — cliente precisa de tempo para usar |
| Lembrete de recompra | 24h | Oferta pode mudar — não faz sentido manter por muito tempo |
| Promoção relâmpago | 6–12h | Urgência alta — se chegou atrasado, não tem valor |
| Ranking/nível | 7 dias | É informativo, não urgente |
| Cupom gerado | = validade do cupom, máx 30 dias | Não faz sentido chegar o push depois que o cupom venceu |

TTL de 0 (entrega imediata ou ignora) só para notificações absolutamente time-sensitive. Para promoções, TTL zero significa que o cliente recebe push de uma oferta que acabou se o celular estava sem internet.

---

## P5) Deduplicação de notificações — formalização

**Concordo, obrigatório desde o dia 1. Já coberto na Parte VI — mas consolidando a estrutura aqui.**

### O `idempotency_key` como estabelecido é correto:

`hash(tenant_id + customer_id + campaign_execution_id + channel + template_id)`

- `campaign_execution_id` (ou `campaign_log_id`) é o vínculo entre a notificação e a execução que a gerou
- `channel` garante que push e e-mail do mesmo evento são tratados separadamente
- `template_id` garante que dois templates diferentes para o mesmo evento (ex: A/B test) não conflitam

### Onde guardar `campaign_execution_id`:

Na tabela `notification_queue`, campo `campaign_execution_id FK → campaign_executions.id`. Isso cria a ligação bidirecional:
- A partir da execução: "quais notificações foram geradas por esta recompensa?"
- A partir da notificação: "qual recompensa originou este envio?"

Essa ligação é obrigatória para auditoria e para o painel admin mostrar "campanha X → recompensou 30 clientes → enviou 28 notificações (2 falharam)".

### Os dois UNIQUE necessários:

1. `notification_queue(idempotency_key)` — impede criar segunda notificação para o mesmo evento
2. `notification_log(idempotency_key)` — impede que um retry marque como enviado se já foi enviado

---

## P6) `campaign_customer_log` mistura recompensa e comunicação

**Concordo com a separação. É a mesma conclusão da Parte VI — aqui o refinamento.**

### A separação correta e definitiva:

| Tabela | Responsabilidade | Quando inserir |
|--------|-----------------|---------------|
| `campaign_executions` | Recompensa concedida (cupom, crédito, carimbo, brinde) | Quando a recompensa é gerada — antes de qualquer notificação |
| `notification_queue` | Notificação a enviar | Logo após gerar a recompensa, na mesma transação ou imediatamente depois |
| `notification_log` | Notificação efetivamente enviada | Após confirmação do provedor (FCM, SMTP) |
| `campaign_run_log` | Resumo de cada execução do job | Ao final de cada run do worker |

**Remover** o conceito de `campaign_customer_log` genérico. Ele existia como "log de tudo" — que é exatamente o que causa confusão. Cada entidade tem sua tabela com responsabilidade única.

### O que mais separar além do que já está definido:

- **`loyalty_stamps`** separado de `cashback_transactions` — já está assim. Correto.
- **`coupon_redemptions`** separado de `coupons` — já está assim. Correto.
- **`drawing_entries`** separado de `drawings` — participação é uma entidade própria, não uma coluna JSON em `drawings`.

---

## P7) Cashback: SUM on read vs saldo materializado

**Para 1–10 tenants, SUM on read é aceitável. Com uma condição.**

### Por que SUM on read funciona agora:

Com 10 tenants e, digamos, 500 clientes cada, você tem no máximo 5.000 clientes. Um cliente com histórico de 2 anos de transações tem ~200 linhas em `cashback_transactions`. `SUM(amount) WHERE tenant_id = X AND customer_id = Y AND status = 'active'` sobre 200 linhas com índice `(tenant_id, customer_id)` retorna em microssegundos. Sem materialização, sem complexidade, sem risco de divergência.

### A condição: índice composto correto.

Sem `(tenant_id, customer_id, status)` indexado, o SUM vai fazer sequential scan conforme a tabela cresce. Com o índice, permanece trivial mesmo com 10 anos de histórico.

### Quando materializar o saldo:

Dois triggers reais — qualquer um deles justifica:

1. **Latência visível no PDV:** o caixa tenta aplicar cashback e espera > 500ms para ver o saldo. Isso provavelmente não acontece antes de 50.000 transações na tabela.

2. **Query de listagem de clientes com saldo:** ex: "mostrar todos os clientes com saldo > R$ 50" — essa query exige SUM por cliente para todos os clientes. Com 5.000 clientes, são 5.000 SUMs. Isso sim pode ser lento sem materialização. Solução alternativa: view materializada do PostgreSQL, que pode ser atualizada sob demanda sem código adicional.

### Como evitar divergência quando materializar:

A única forma segura: **atualizar o saldo materializado dentro da mesma transação** que insere em `cashback_transactions`. Nunca em um job separado assíncrono. Se a transação reverter, o saldo reverte junto. Se um job externo atualiza o saldo, você tem uma janela de inconsistência entre o ledger e o saldo.

**Regra:** ledger é a fonte da verdade. Saldo materializado é um cache, sempre derivado do ledger, nunca fonte primária de nada.

---

## P8) Cupons: formalizar tabela `coupon_redemptions`

**Já coberto na Parte VI. Consolidando decisões aqui.**

### Nome e estrutura definitivos:

Tabela: `coupon_redemptions` (padrão inglês já adotado no resto do schema).

Campos obrigatórios:
- `tenant_id` — multi-tenant
- `coupon_id FK → coupons.id`
- `customer_id FK → customers.id` (nullable se cupom usado sem cliente identificado)
- `order_id` — ID da venda no canal correspondente
- `channel` (enum: `'pdv'`, `'ecommerce'`, `'app'`)
- `discount_value_applied` — valor real descontado (não o configurado — pode diferir em cupons percentuais com teto)
- `used_at`
- `voided_at` (nullable) — preenchido quando a venda associada é cancelada
- `voided_by` (nullable) — `order_id` do cancelamento

### Proteção contra fraude (uso duplo):

Para cupom de uso único: `UNIQUE(coupon_id)` em `coupon_redemptions`.
Para cupom de uso múltiplo com limite por cliente: `UNIQUE(coupon_id, customer_id)`.
Para cupom com limite global de usos: não usar UNIQUE — usar `COUNT(*) WHERE coupon_id = X` comparado ao `max_uses` em `coupons`, dentro de transação com `SELECT ... FOR UPDATE` na linha do cupom.

### Cancelamento de venda (void/reversal):

Nunca deletar a linha de redemption. Preencher `voided_at` e `voided_by`. Isso mantém auditoria completa e permite reconstruir "quantas vezes este cupom foi realmente usado (não cancelado)":
```sql
SELECT COUNT(*) FROM coupon_redemptions
WHERE coupon_id = X AND voided_at IS NULL
```

---

## P9) Fidelidade: UNIQUE por venda além do FOR UPDATE

**Concordo, obrigatório. Já coberto na Parte VI. Precisão sobre a chave aqui.**

### `loyalty_card_id` vs `customer_id` na constraint:

**Usar `customer_id`, não `loyalty_card_id`.**

Motivo: cartão de fidelidade pode ser perdido, substituído ou migrado do físico para o digital. Se a constraint usar `loyalty_card_id`, uma compra feita com o cartão antigo (ID 100) e o mesmo cliente fazendo a migração para cartão digital (ID 200) teriam constraints diferentes para a mesma compra — permitindo dois registros para a mesma venda. A compra pertence ao cliente, não ao cartão.

**Constraint definitiva:**

`UNIQUE(tenant_id, customer_id, venda_id)`

### Caso especial: cliente sem CPF / sem identificação

Se fidelidade é por cartão físico e o cliente não está identificado por CPF, `customer_id` pode ser `NULL` temporariamente. Nesse caso a constraint `(tenant_id, customer_id, venda_id)` não funciona para NULL (PostgreSQL não considera NULL = NULL em UNIQUE). Solução: fidelidade sem identificação de cliente não conta para o sistema digital — exige identificação prévia. Ou: `customer_id` nunca é NULL em `loyalty_stamps` (apenas clientes identificados têm carimbos digitais).

---

## P10) PgBouncer como pré-requisito de produção

**Concordo. PgBouncer é pré-requisito, não otimização.**

### Por que é pré-requisito e não "depois se precisar":

Com workers de campanha rodando em paralelo, cada worker abre conexões com o PostgreSQL de forma assíncrona. FastAPI com `asyncpg` ou `psycopg3` no modo async pode manter conexões abertas por toda a vida do processo. Com:
- 1 worker de campanha + 4 conexões no pool
- 1 servidor FastAPI + 10 conexões no pool
- 1 worker de notificações + 4 conexões no pool

= 18 conexões abertas constantemente, mesmo sem tráfego. Cada conexão PostgreSQL usa ~5MB de RAM + 1 processo. Ao adicionar campanhas batch rodando simultaneamente, pico pode chegar a 40–60 conexões.

PostgreSQL começa a degradar performance e rejeitar conexões novas acima do `max_connections` configurado (padrão: 100, mas em produção em container pequeno recomenda-se 50).

### Quando especificamente adicionar:

**Antes de subir o primeiro worker de campanha em produção** — não antes do FastAPI, que com 1 petshop tem volume baixo. O momento crítico é quando você ativa o worker que vai rodar jobs de fidelidade/cashback/ranking em paralelo.

### Configuração mínima:

PgBouncer no modo `transaction` (não `session`) para compatibilidade com asyncpg. Pool size: `(N_connections_postgres - 5_reservadas) / N_serviços`. Com `max_connections = 50` e 3 serviços: ~15 por serviço. Sem mudança de código na aplicação — apenas trocar a connection string de `postgres://...` para `pgbouncer://...`.

### Impacto de não ter:

Em 1 petshop com pouco tráfego, provavelmente invisível. No dia que o primeiro cliente real inicia com 2.000 clientes e a campanha de aniversário roda ao mesmo tempo que o job de ranking e um relatório pesado é gerado — você descobre que estava num estado frágil.

---

## Resumo das Decisões (Parte VII)

| Ponto | Posição | Decisão |
|-------|---------|---------|
| P1 Fase 1 vs Fase 2 scheduler | Conflito real, fechado | Fase 1: APScheduler + Postgres-queue. Fase 2+: Celery Beat + Redis. Handlers não mudam. |
| P2 OFFSET em ranking | Remover, concordo | Cursor por `id` sempre. OFFSET proibido em jobs de campanha. |
| P3 Sorteio seed | Necessário, não paranoia | `seed_uuid` na criação + `entries_hash` no fechamento + `seed_final` na execução |
| P4 FCM batch e TTL | Esclarecimento de API | `sendEach` para até 500 mensagens personalizadas. TTL por tipo (tabela definida). |
| P5 `idempotency_key` notificações | Obrigatório | UNIQUE em `notification_queue` + `notification_log`. `campaign_execution_id` como FK. |
| P6 Separação de logs | Concordo, regra definitiva | `campaign_executions` (recompensa) + `notification_queue/log` (comunicação) + `campaign_run_log` (resumo de job). Remover `campaign_customer_log` genérico. |
| P7 Cashback SUM on read | OK para 1–10 tenants | Índice `(tenant_id, customer_id)` obrigatório. Materializar só quando latência virar problema. Atualização sempre na mesma transação do ledger. |
| P8 `coupon_redemptions` | Obrigatório | Nome e campos definitivos. Void por `voided_at`, nunca DELETE. |
| P9 UNIQUE fidelidade | Obrigatório, usar `customer_id` | `UNIQUE(tenant_id, customer_id, venda_id)`. Não usar `loyalty_card_id` (cartão pode ser substituído). |
| P10 PgBouncer | Pré-requisito, não opcional | Adicionar antes de subir o primeiro worker de campanha em produção. Modo `transaction`. |

---

*Parte VII adicionada em Março 2026.*

---

# PARTE VIII — Princípios do Motor de Campanhas

*Regras arquiteturais imutáveis. Qualquer implementação que viole um desses princípios está errada, independentemente de funcionar localmente.*

---

## Seção A — Os Princípios

### Análise dos 6 princípios propostos

**Princípio 1 — Eventos devem ser idempotentes**
**Concordo. Correto e obrigatório.**
Sem idempotência, retries e reprocessamentos — que vão acontecer — geram recompensas duplicadas. A combinação de `idempotency_key` + `UNIQUE constraints` + `ON CONFLICT DO NOTHING` é o mecanismo correto. Uma precisão: o princípio se aplica a **operações**, não só a "eventos". Toda operação do motor (gerar recompensa, enfileirar notificação, registrar execução) deve ser idempotente individualmente.

**Princípio 2 — O scheduler nunca contém lógica de campanha**
**Concordo. Crítico para a migração Fase 1 → Fase 2.**
Se `@scheduler.scheduled_job` contiver `if customer.birthday == today and customer.purchases > 3: give_reward()`, você vai precisar reescrever tudo ao trocar para Celery. Se contiver apenas `run_birthday_campaign(tenant_id)`, a migração é trivial. Este princípio é o que torna a troca de scheduler transparente.

**Princípio 3 — Ledger é sempre a fonte da verdade financeira**
**Concordo. Com complemento.**
Adicionar explicitamente: **o saldo materializado (se existir) é um cache do ledger, nunca é lido como fonte de verdade para decisões de negócio**. Exemplo concreto: ao verificar se o cliente tem saldo suficiente para usar cashback, a query deve calcular `SUM(ledger)`, não ler `wallet.balance`. Isso evita divergência silenciosa onde o cache está errado mas ninguém percebe até o cliente reclamar.

**Princípio 4 — Logs de execução são imutáveis**
**Concordo. Com uma distinção importante.**
"Imutável" aqui significa: nenhum UPDATE em registros de `campaign_executions`, `notification_log`, `coupon_redemptions`, `loyalty_stamps`, `cashback_transactions`. Correções geram novos registros (transação de estorno, nova execução). A única exceção legítima: campos de status operacional como `notification_queue.status` (`pending → sent`) — esse campo muda por design do workflow, não é "alteração de histórico". A regra é: **dados de fato histórico nunca mudam. Dados de estado operacional podem mudar.**

**Princípio 5 — Jobs precisam ser retomáveis**
**Concordo. Com precisão sobre o que "retomável" exige.**
Retomável tem dois níveis:
- **Nível 1 (obrigatório):** recomeçar do início sem duplicar efeitos — garantido por idempotência.
- **Nível 2 (recomendado):** recomeçar do ponto onde parou — garantido por cursor persistido (`cursor_last_id` na tabela de jobs).

Nível 1 é suficiente para campanhas pequenas (< 1.000 clientes). Nível 2 é necessário quando o reprocessamento completo é custoso. Implementar Nível 2 desde o início tem custo baixo e evita surpresas.

**Princípio 6 — Nenhuma campanha pode disparar recompensas fora do Campaign Engine**
**Concordo. É o mais importante dos seis.**
Sem este princípio, regras de campanha acabam espalhadas em: endpoint de finalização de venda, hook de cadastro de cliente, lógica de cashback, lógica de fidelidade — cada um com suas próprias condições e sem consistência. Quando o dono do sistema mudar uma regra ("desconto de aniversário mudou de 10% para 15%"), vai precisar procurar em 5 lugares. Com o princípio, muda em um lugar só.

A implementação correta: qualquer código fora do Campaign Engine que precisar gerar uma recompensa deve **emitir um evento** (`purchase_completed`, `customer_registered`) e deixar o motor decidir o que fazer. Nunca chamar `give_cashback()` diretamente de um endpoint.

### Princípios que faltam

**Princípio 7 — Campanhas são configuração, não código**

Criar uma nova campanha (ex: "desconto de 10% para quem comprar 3 vezes em 30 dias") não deve exigir deploy. Os parâmetros (percentual, número de compras, janela de tempo) vivem no banco de dados. O código do handler é genérico e lê a configuração. Isso é o que permite ao dono do sistema criar e editar campanhas pelo painel admin sem envolver o desenvolvedor.

**Princípio 8 — Separação clara entre o que dispara e o que executa**

O motor tem duas fases distintas que nunca devem se misturar:
- **Fase de avaliação:** verificar se o cliente é elegível para a campanha (leitura pura — sem efeitos colaterais)
- **Fase de execução:** conceder a recompensa (escrita — com efeitos colaterais)

A avaliação pode ser feita quantas vezes quiser sem risco. A execução é idempotente mas irreversível. Misturar as duas fases num loop único é o caminho mais curto para bugs difíceis de rastrear.

**Princípio 9 — Eventos de domínio nunca são síncronos com a resposta ao usuário**

O endpoint `POST /vendas/{id}/finalizar` não deve esperar o Campaign Engine terminar para responder. A venda é confirmada, o evento é enfileirado, a resposta é retornada. O motor processa em background. Isso garante que uma campanha lenta ou com erro não impacta a experiência do caixa.

---

## Seção B — Risco de Event Storm (Cascata de Eventos)

**O risco é real. A arquitetura atual tem proteção parcial mas não completa.**

### Se o risco existe de fato nesse sistema:

Com as campanhas definidas, existe um caminho de cascata plausível:

```
compra finalizada
  → [evento] purchase_completed
  → cashback gerado (R$ 20)
  → [evento] wallet_updated (saldo aumentou)
  → campanha "saldo alto" dispara desconto
  → desconto aplicado
  → [evento] discount_applied
  → campanha "primeiro desconto" dispara brinde
  → ...
```

Cada step faz sentido isoladamente. O conjunto cria um loop ou amplificador de eventos que não foi intencionado. Com cashback + fidelidade + ranking + sorteios todos escutando eventos, o risco de subgrafos não planejados é real.

### A proteção necessária: eventos de domínio vs eventos de campanha

**Concordo que a distinção deve ser explícita e codificada.**

A separação correta:

| Tipo de evento | Pode disparar campanha? | Exemplos |
|---------------|------------------------|---------|
| `user_action` | **Sim** | `purchase_completed`, `customer_registered`, `app_login` |
| `system_scheduled` | **Sim** | `birthday_check`, `inactivity_check`, `ranking_recalc` |
| `campaign_action` | **Não** | `cashback_credited`, `coupon_issued`, `stamp_added`, `reward_granted` |

**Regra fundamental:** eventos gerados pelo próprio Campaign Engine nunca podem re-entrar no Campaign Engine como triggers.

### Campo `event_origin` — concordo, é obrigatório

Campo na tabela `campaign_event_queue`:

```
event_origin: ENUM('user_action', 'system_scheduled', 'campaign_action')
```

O worker do Campaign Engine verifica: `if event.event_origin == 'campaign_action': skip — não processa`. Isso é a barreira explícita no código.

Complemento: adicionar `triggered_by_campaign_id` (nullable) para rastreabilidade. Se um evento foi gerado como consequência de uma campanha, este campo aponta para qual campanha. Serve para debug ("por que esse evento foi ignorado?") e auditoria ("quais eventos esta campanha gerou?").

### O limite de profundidade (event depth)

O `event_origin` já previne loops diretos. Mas existe o loop indireto:

```
user_action: purchase_completed → campanha A (cashback)
user_action: purchase_completed → campanha B (fidelidade)
campanha B dispara evento system_scheduled: ranking_recalc imediato
ranking_recalc → campanha C (prêmio de ranking)
campanha C cria cupom
cupom dispara evento user_action??
```

Para fechar completamente: adicionar campo `event_depth` (inteiro, default 0) na `campaign_event_queue`. Eventos gerados por campanhas têm `event_depth = parent.event_depth + 1`. O worker recusa processar qualquer evento com `event_depth > 1`. Isso limita a propagação a exatamente **um nível** de consequência: um evento de usuário pode gerar uma recompensa, mas a recompensa nunca gera outra recompensa.

### Estratégia recomendada (combinação dos três mecanismos):

1. **`event_origin` enum** — classificação explícita de quem gerou o evento
2. **Regra no worker:** `campaign_action` não entra no motor
3. **`event_depth` com limite = 1** — proteção contra loops indiretos que escapem da classificação

Os três juntos são defense in depth. Qualquer um dos três isolado pode ser contornado por acidente. Os três juntos tornam o loop praticamente impossível sem intenção explícita.

**Regra de incremento do `event_depth`:** eventos vindos de `user_action` ou `system_scheduled` entram com `event_depth = 0`. Qualquer componente do sistema que gerar um evento derivado (em resposta a uma campanha) deve definir `event_depth = parent_event_depth + 1` e `event_origin = 'campaign_action'`. O worker descarta silenciosamente qualquer evento com `event_depth > 1` — registrando em log para auditoria. Nenhum outro componente precisa conhecer essa regra; ela vive exclusivamente no ponto de inserção na fila.

### Implicação na lista de eventos do sistema

Com essa regra, os eventos que **podem** disparar campanhas são apenas:

**Eventos de usuário (`user_action`):**
- `purchase_completed` — compra finalizada no PDV, ecommerce ou app
- `customer_registered` — novo cadastro
- `cpf_linked` — CPF associado a um cliente existente

**Eventos agendados (`system_scheduled`):**
- `daily_birthday_check` — job diário de aniversários
- `weekly_inactivity_check` — job de clientes inativos
- `monthly_ranking_recalc` — recálculo de ranking
- `drawing_execution` — execução de sorteio agendado

**Eventos que NÃO disparam campanhas (`campaign_action`):**
- `cashback_credited`
- `coupon_issued`
- `stamp_added`
- `reward_granted`
- `notification_sent`
- `ranking_updated`

Essa lista vive na constante `CAMPAIGN_TRIGGER_EVENTS` no código do worker. **O worker descarta qualquer `event_type` que não esteja nessa lista, independentemente do `event_origin`.** Isso previne o acidente de um evento novo criado com `event_origin = 'user_action'` virar trigger involuntário só pela classificação de origem. Adicionar um novo trigger ao motor exige duas ações deliberadas: adicionar à lista `CAMPAIGN_TRIGGER_EVENTS` e decidir explicitamente sua categoria.

---

## Princípios Consolidados — Lista Definitiva

| # | Princípio | Criticidade |
|---|-----------|------------|
| 1 | Toda operação do motor é idempotente | Alta |
| 2 | O scheduler nunca contém lógica de campanha | Alta |
| 3 | Ledger é fonte da verdade financeira; saldo materializado é cache | Alta |
| 4 | Logs de fato histórico são imutáveis; estados operacionais podem mudar | Alta |
| 5 | Jobs são retomáveis: Nível 1 (idempotência) obrigatório; Nível 2 (cursor) recomendado | Média |
| 6 | Toda recompensa passa pelo Campaign Engine — nunca diretamente de endpoints | Alta |
| 7 | Campanhas são configuração no banco, não código — mudança de parâmetro não exige deploy | Média |
| 8 | Avaliação de elegibilidade (read) e execução de recompensa (write) são fases separadas | Alta |
| 9 | Eventos de domínio nunca são síncronos com a resposta ao usuário | Alta |
| 10 | Eventos gerados pelo motor (`campaign_action`) nunca re-entram no motor como triggers | Alta |
| 11 | Somente `event_type`s listados em `CAMPAIGN_TRIGGER_EVENTS` entram no motor; qualquer outro é descartado — `event_origin` correto é necessário, mas não suficiente | Alta |

---

*Parte VIII adicionada em Março 2026.*

