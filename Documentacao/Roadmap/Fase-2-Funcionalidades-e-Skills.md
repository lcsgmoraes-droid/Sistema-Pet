---
tipo: roadmap
atualizado: 2026-09-12
---

# Fase 2 — Mapeamento Tela por Tela + Skills de IA + Eliminação de Duplicação

Parte de [[Roadmap]]. Base: [[Funcionalidades]], [[Matriz-de-Cobertura]], [[Template-Skill-Funcionalidade]].

## Objetivo da fase

Terminar de documentar toda tela do sistema no formato padrão, e transformar essa documentação em algo que uma IA (Claude Code ou outra) consegue **carregar automaticamente** ao trabalhar numa área específica — sabendo o que a funcionalidade faz, com o que ela se conecta, quais componentes usa, e o que ela **não pode** fazer. No caminho, resolver duplicação de lógica e o oposto (métodos genéricos demais que deveriam ser separados).

## 2.1 — Completar o mapeamento (15 telas restantes)

[[Matriz-de-Cobertura]] já mostra o que falta. Ordem sugerida (por criticidade de negócio e por já estarem referenciadas por outras áreas já documentadas):

> Em paralelo a este mapeamento, começou em 2026-09-12 uma frente de execução visual tela por tela usando os componentes de `components/v2/` (itens 1.6-1.9) — registro vivo em [[RefatoracaoV2]], não é o mesmo trabalho deste item 2.1 (que é mapear/documentar), mas os dois cobrem as mesmas telas e devem se referenciar.

**Prioridade alta (referenciadas por múltiplas integrações/funcionalidades já mapeadas):**
1. Configurações (fiscal, parâmetros gerais, grupos de empresas) — toca [[Fiscal-IntNFe-SEFAZ]], [[Bling]], multiempresa
2. Cadastros auxiliares (bancos, formas de pagamento, categorias) — usado por [[Financeiro]], [[PDV-Vendas]]
3. Painel `/ops` (plataforma) — toca [[Asaas]] (billing), autenticação separada

**Prioridade média:**
4. Dashboard — agrega dados de quase todas as áreas já mapeadas
5. RH — toca [[Comissoes]] (vendedor/funcionário)
6. Calculadora de Ração — toca [[OpenAI-IA]]

**Prioridade baixa (isoladas, menor dependência cruzada):**
7. Lembretes, Alertas do gestor

Para cada uma, usar exatamente o formato de [[Template-Skill-Funcionalidade]] (o mesmo já aplicado às 10 funcionalidades existentes em [[Funcionalidades]]) — não inventar um formato novo por tela.

**Critério alternativo a considerar (não decidido, proposta desta camada):** a ordem acima prioriza por dependência técnica (quantas outras áreas já mapeadas referenciam aquela tela). Um critério concorrente é priorizar por **impacto operacional diário** — Dashboard e Alertas do gestor são as telas que um dono de pet shop olha todo dia para decidir algo (e já há intenção de produto documentada em `docs/CAIXA_ALERTAS_GESTOR.md`), o que os colocaria antes de Cadastros auxiliares ou RH. Os dois critérios divergem principalmente na posição de Dashboard/Alertas do gestor (hoje "prioridade média/baixa") vs. Configurações e painel `/ops` (que continuam prioridade alta nos dois critérios — risco de compliance e maior privilégio de acesso, respectivamente). Fica como decisão do responsável qual critério pesa mais ao começar 2.1, não uma correção da ordem já registrada.

## 2.2 — Aprofundar as 10 telas já documentadas

As 10 já criadas ([[PDV-Vendas]], [[Produtos-Estoque]], [[Financeiro]], [[Comissoes]], [[Compras]], [[Banho-e-Tosa]], [[Veterinario]], [[Campanhas]], [[E-commerce]], [[Entregas]]) foram documentadas a partir de reconhecimento estrutural — nenhuma tem a coluna "API" completa em [[Matriz-de-Cobertura]]. Ação: para cada uma, extrair contrato real de request/response dos 3-5 endpoints mais usados (via `/docs` OpenAPI do próprio backend, que é a fonte mais confiável), e listar explicitamente os componentes React reais usados na tela (não apenas o arquivo de rota).

## 2.3 — Formalizar como Skills de IA

> ✅ **Piloto criado em 2026-09-12: `.claude/skills/login/SKILL.md`**, para a tela de Login (a primeira migrada em [[RefatoracaoV2]]). Confirma que o mecanismo funciona (skill carrega pelo `description`) e prova o formato na prática — ainda não decidido se generaliza para as outras ~24 telas ou só para as de maior tráfego de mudança (ver itens abaixo, ainda em aberto).

Proposta concreta: transformar cada documento de [[Funcionalidades]] em uma **Claude Code Skill** real (`.claude/skills/<nome-da-funcionalidade>/SKILL.md`), não apenas um Markdown de referência. Diferença prática: uma Skill é carregada sob demanda quando alguém (humano ou IA) está trabalhando naquela área, em vez de exigir que a IA leia toda a `/Documentacao` toda vez.

Estrutura sugerida por skill (baseada no que [[Template-Skill-Funcionalidade]] já define):
```yaml
---
name: pdv-vendas
description: Use ao mexer no fluxo de PDV/vendas — criação, finalização, pagamento, cancelamento de venda.
---
```
Corpo da skill: objetivo, fluxo, arquivos-chave (backend e frontend), integrações usadas, **o que pode e o que não pode** (ex.: "nunca calcular preço final no frontend, a autoridade é o backend" — regra já confirmada em [[Arquitetura]]), armadilhas conhecidas (ex.: `VendaItem` tem `tenant_id` explícito além do padrão automático, não remover essa coluna sem entender por quê).

⚠️ **Esta é uma proposta desta fase, ainda não implementada.** Antes de criar os arquivos reais em `.claude/skills/`, decidir com o responsável:
- [ ] Confirmar que o formato de Skill do Claude Code é o mecanismo certo (vs. manter só os Markdown de `/Documentacao` e contar com o agente carregá-los por link).
- [ ] Definir se as skills ficam com escopo por funcionalidade (1 por tela, ~25 no total) ou por domínio maior (ex.: uma skill "financeiro" cobrindo Financeiro+Comissões).
- [ ] Piloto: começar por 2-3 funcionalidades de alto tráfego de mudança (PDV/Vendas, Produtos/Estoque) antes de generalizar para as 25.

## 2.4 — Duplicação de lógica (minimizar pontos de contato)

Achados já confirmados nesta análise que são candidatos diretos:

- **`Venda` (PDV) vs. `Pedido` (e-commerce)** — dois modelos de "venda" paralelos por canal (ver [[Venda]]). Antes de qualquer unificação, mapear exatamente onde a mesma regra de negócio (cálculo de total, aplicação de desconto, baixa de estoque) está implementada duas vezes — uma para cada canal — e decidir se centraliza num serviço compartilhado ou se a separação é deliberada (❓ já está em [[Pendencias]]).
- **Arquivos-facade de compatibilidade** (`produtos_models.py`, `financeiro_models.py`) — confirmar que só reexportam, não duplicam lógica (ver Fase 1, item 1.4).
- **Validação de regra de negócio em frontend E backend** — esperado e correto ter validação nos dois lados (UX + segurança, ver [[Arquitetura]]: "regra de negócio financeira, fiscal ou de estoque não deve existir apenas no frontend"). O que precisa checar é se a regra do frontend e a do backend **divergem** (ex.: uma valida um limite e a outra valida um limite diferente) — isso é bug, não defesa em profundidade. Levantamento pontual a fazer por funcionalidade ao aprofundar (2.2).
- **Padrão de retry/timeout repetido em cada integração** (ver [[Integracoes]] — cada uma implementa o próprio timeout/retry do zero, sem um helper HTTP compartilhado) — candidato a um cliente HTTP base único com timeout/retry/log padronizados, usado por todas as integrações. Ver também [[Fase-3-Integracoes]].

## 2.5 — Over-parametrização (o oposto: separar o que virou genérico demais)

Sem levantamento específico ainda (não fazia parte do escopo da análise estrutural). Processo para esta fase, por funcionalidade:
- [ ] Ao abrir cada arquivo de serviço/rota grande (candidato natural: os mesmos da campanha 700-linhas da Fase 1), procurar funções com muitos parâmetros opcionais/flags booleanas controlando comportamento diferente (`def processar(tipo=None, forcar=False, ignorar_x=False, modo=...)`) — esses são candidatos a virar 2-3 métodos nomeados em vez de 1 método com ramificação interna.
- [ ] Priorizar isso nos domínios que já serão tocados pela Fase 1 (migração para pasta por domínio) — é o momento natural de já separar o método, em vez de fazer isso como um segundo passe depois.

## 2.6 — UX/UI nas telas de uso diário (proposta nova, fora da auditoria original)

A Conciliação de Cartões já é um bom exemplo interno de simplicidade deliberada (semáforo verde/amarelo/vermelho, uma decisão por vez, texto explicando reversibilidade — ver `docs/PROXIMO_PASSO.md`). Vale usar esse padrão como referência ao revisar o resto do sistema, em vez de reinventar um princípio de UI a cada tela nova:

- [ ] Rodar `/ui-review` (ou `rams quick_review`) nas telas de maior uso — PDV, Financeiro (Contas a Pagar/Receber), Banho e Tosa — focando em: uma ação primária clara por tela, estados de carregamento/erro visíveis, mensagens de erro em linguagem de lojista.
- [ ] **Checagem de acessibilidade específica para uso em balcão/tablet** (não avaliado na auditoria técnica original): contraste de cor e alvo de toque ≥ 44px nas telas de PDV — funcionários de loja costumam operar em tablet, muitas vezes com luz de ambiente ruim.
- [ ] **"Tradutor" central de erros técnicos** para os módulos fiscal/financeiro — hoje um erro mal explicado (`Erro 500`, código de rejeição cru da SEFAZ, erro de adquirente de cartão) trava a operação de um lojista sem contexto técnico. Um mapeamento central de erros comuns (SEFAZ, adquirentes, Bling) para mensagem acionável evita reimplementar essa tradução tela por tela conforme 2.1 avança.

## Critério de avanço para a Fase 3

- [[Matriz-de-Cobertura]] com 100% das áreas de menu pelo menos com documento base (mesmo que "Segurança"/"API" ainda fiquem 🟡 em algumas).
- Decisão tomada sobre o mecanismo de Skills (item 2.3).
- Lista de duplicações confirmadas (2.4) documentada, com decisão registrada para cada uma (unificar, manter separado por design, ou pendente — decisões maiores como `Venda` vs. `Pedido` são boas candidatas a virar um ADR em `docs/adr/`, não só uma linha de pendência).
- Telas de maior uso diário (2.6) com pelo menos uma passada de revisão de UI registrada.

## Não identificado

- ❓ Se o time prefere Skills por funcionalidade individual ou por domínio agrupado — decisão de produto/processo, não técnica.
