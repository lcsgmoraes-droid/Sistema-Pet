---
tipo: roadmap
atualizado: 2026-09-12
---

# Fase 5 — Produto e Negócio

Parte de [[Roadmap]]. Base: conhecimento geral de SaaS multi-tenant vertical, cruzado com [[Matriz-de-Cobertura]], [[Asaas]], [[Funcionalidades]]. Diferente das Fases 1-4, esta não descreve um achado confirmado no código — é uma camada de recomendação estratégica, sem evidência de "código não faz X", então cada item aqui é uma pergunta a validar com o responsável antes de virar trabalho.

## Por que esta fase é diferente das outras

As Fases 1-4 têm uma dependência lógica clara (organizar base → mapear telas → organizar integrações → endurecer segurança). Produto e negócio não dependem dessa sequência da mesma forma — podem rodar em paralelo a qualquer uma delas. Por isso não está numerada como pré-requisito de nada, e nada nas Fases 1-4 depende dela. Ela aparece depois na numeração só porque foi formulada depois, não porque deva esperar as outras quatro.

## 5.1 — Reduzir o tempo entre "assinou" e "operando"

- [ ] Mapear quantos passos manuais existem hoje entre a venda de uma nova conta e o primeiro uso real do tenant (rebranding recente para CorePet e catálogo mestre centralizado sugerem que ainda há trabalho manual de implantação). Reduzir esse tempo costuma ser a alavanca de crescimento mais direta em SaaS vertical.
- [ ] Avaliar um fluxo de onboarding self-service (mesmo que parcial) para tenants novos de menor complexidade, reservando o onboarding assistido para contas maiores/mais customizadas.

## 5.2 — Telemetria de uso por tenant

- [ ] [[Matriz-de-Cobertura]] mostra várias funcionalidades sem profundidade de documentação — decidir onde investir a próxima rodada de trabalho (tanto de documentação quanto de produto) fica mais confiável com dado real de uso por tenant do que só por intuição.
- [ ] Não identificado nesta análise se já existe algum tipo de analytics de uso interno — confirmar antes de propor uma ferramenta nova.

## 5.3 — Billing self-service

- [ ] Já existe integração Asaas para billing (ver [[Asaas]]). Confirmar se upgrade/downgrade de plano já é self-service hoje ou ainda depende de intervenção manual — afeta diretamente o custo de operação por cliente conforme a base cresce.

## 5.4 — API pública / marketplace de parceiros (horizonte mais longo)

- [ ] O projeto já tem um catálogo mestre de produtos centralizado e múltiplas integrações — base natural para uma futura API/marketplace de parceiros (ex.: outros sistemas de petshop, agenda de veterinários parceiros). Não é urgente; o pré-requisito técnico é o item de contratos de API já previsto em [[Fase-2-Funcionalidades-e-Skills]] (2.2) — não iniciar isso antes daquele estar avançado.

## 5.5 — Escuta do cliente

- [ ] Considerar NPS ou pesquisa de satisfação simples embutida no produto. Com o sistema em operação real e o rebranding em andamento, é um bom momento para capturar sinal direto de satisfação dos lojistas antes de decidir a próxima onda de investimento de produto — complementa (não substitui) a telemetria de uso do item 5.2, que mostra *o quê* é usado, não *o que o usuário sente* sobre isso.

## 5.6 — Governança da própria documentação de roadmap

- [ ] **Roadmap único, fonte da verdade.** Hoje existem `docs/ROADMAP_MASTER.md` (documento anterior) e este [[Roadmap]] em `Documentacao/` (construído em 2026-09-12). Os dois podem divergir com o tempo se não houver decisão explícita sobre qual é o oficial e o que acontece com o outro (arquivar, redirecionar, ou manter os dois com escopos diferentes e documentados). Vale decidir enquanto a divergência ainda é pequena, em vez de deixar dois roadmaps concorrentes se acumularem.

## Não identificado

- ❓ Se já existe alguma métrica de negócio (churn, ativação, NPS) sendo acompanhada fora do código-fonte (ex.: planilha, ferramenta externa) — esta análise só olhou o repositório, não processos de negócio fora dele.
- ❓ Apetite de investimento/prazo para qualquer um dos itens acima — são oportunidades, não compromissos assumidos.
