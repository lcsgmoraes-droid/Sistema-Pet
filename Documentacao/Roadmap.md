---
tipo: roadmap
atualizado: 2026-09-12
---

# Roadmap de Organização e Evolução

Roadmap de trabalho, não uma auditoria — construído em cima do que já foi confirmado em [[README]], [[Arquitetura]], [[Funcionalidades]], [[Integracoes]], [[Seguranca]] e [[Matriz-de-Riscos]]. Serve como base viva: cada fase referencia evidência real já levantada, não repete a análise.

**Ordem definida pelo responsável do sistema, com motivo:** organizar a base (CI/CD, padrão de código, componentização) antes de mapear tela por tela; mapear funcionalidade por funcionalidade antes de mexer em integrações; só endurecer segurança depois do código já estar bem estruturado — porque é mais fácil (e mais barato) proteger um sistema organizado do que proteger um sistema em refatoração constante.

## As 5 fases

| Fase | Nome | Documento | Depende de |
|---|---|---|---|
| 1 | CI/CD, boas práticas, padronização, componentização, confiabilidade/observabilidade | [[Fase-1-CI-CD-e-Padronizacao]] | — (ponto de partida) |
| 2 | Mapeamento tela por tela + skills de IA + eliminação de duplicação/over-parametrização + UX das telas de uso diário | [[Fase-2-Funcionalidades-e-Skills]] | Fase 1 (padrão de componente definido) |
| 3 | Organização das integrações | [[Fase-3-Integracoes]] | Fase 2 (funcionalidades mapeadas, dependências claras) |
| 4 | Segurança | [[Fase-4-Seguranca]] | Fases 1-3 (código e integrações já organizados) |
| 5 | Produto e negócio | [[Fase-5-Produto-e-Negocio]] | Contínua — roda em paralelo às Fases 1-4, não bloqueia nem é bloqueada por elas |

Um documento de apoio único para todas as fases: [[Template-Skill-Funcionalidade]] — o formato padrão para documentar/instrumentar cada tela.

As Fases 1, 2 e 4 incluem seções marcadas como "proposta nova, fora da auditoria original" — são recomendações de camada estratégica (segurança, confiabilidade, UX, produto), não achados re-confirmados em código como o restante do roadmap. Tratadas com o mesmo rigor de rastreabilidade (cada item aponta o motivo e, quando aplicável, o documento relacionado), mas sem a mesma evidência direta de código que as demais seções.

## Por que essa ordem faz sentido (evidência, não só opinião)

- Já existe uma campanha ativa de redução de arquivos grandes em backend e frontend (dezenas de "batches", ver [[Fase-1-CI-CD-e-Padronizacao]]) — começar por CI/CD e padronização **aproveita um esforço que já está em curso**, em vez de competir com ele.
- [[Matriz-de-Cobertura]] já mostra que 10 de ~25 telas têm documentação profunda e 15 não — mapear o restante (Fase 2) antes de mexer em integrações evita redocumentar a mesma tela duas vezes se a estrutura de componente mudar no meio do caminho.
- [[Integracoes]] já tem 8 integrações mapeadas com lacunas conhecidas (retry, timeout, assinatura de webhook) — vale endurecer isso (Fase 3) só depois que as funcionalidades que as usam estiverem com contrato estável (Fase 2), para não re-trabalhar o mesmo ponto de integração duas vezes.
- [[Matriz-de-Riscos]] já tem 13 riscos catalogados, a maioria de segurança — tratá-los (Fase 4) depois do código estar organizado significa que a correção de segurança mexe em menos lugares por vez, e o teste de regressão é mais confiável.

## Como usar este roadmap

- Cada fase tem uma lista de ações concretas com evidência/arquivo de origem, não tarefas genéricas.
- Cada ação referencia, quando aplicável, o item correspondente em [[Pendencias]] ou [[Matriz-de-Riscos]] — resolver a ação deve atualizar o status lá, não duplicar informação.
- Este não é um cronograma com datas — são fases com **dependência lógica**, para serem executadas na velocidade real do time (hoje, uma pessoa + IA, conforme `docs/GOVERNANCA_ENTERPRISE.md`).
- Ao fechar uma fase, atualizar a tabela acima (coluna "Depende de" pode virar "Status: concluída em AAAA-MM-DD") e revisar se a fase seguinte ainda faz sentido como planejada.

## Não identificado

- ❓ Prioridade relativa entre fases quando houver conflito de tempo (ex.: um bug de segurança crítico durante a Fase 1) — a regra geral do projeto (`AGENTS.md`) já cobre isso: correção urgente não espera roadmap, mas deve ser registrada e o roadmap retomado depois.
