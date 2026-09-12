---
tipo: indice
atualizado: 2026-09-12
---

# Sistema Pet / CorePet — Cérebro do Sistema

Índice executivo e técnico. Construído por análise direta de código (backend, frontend), migrations, workflows de CI e cruzamento com a documentação já existente em `docs/` — não é uma reescrita da documentação antiga, é uma camada de navegação interligada (Obsidian) que aponta para evidência real e sinaliza o que ainda precisa de validação humana.

**Regra de leitura destes documentos:** ✅/texto normal = confirmado no código. ❓ = necessita validação com o responsável. ⚠️ = achado/divergência que merece atenção. 🔴🟠🟡🔵⚪ = severidade de risco (crítico → informativo). Ver critério completo nos próprios documentos de [[Seguranca]].

## 1. Visão geral

- **Nome:** o produto está em rebranding de "Sistema Pet"/"Petshop Pro" para **CorePet** (marca já visível em `frontend/index.html`, mas o pacote npm ainda se chama `petshop-pro-frontend` — rebranding parcial, confirmado).
- **Finalidade:** ERP multiempresa (SaaS) para pet shops — PDV, estoque, financeiro, banho e tosa, clínica veterinária, e-commerce, campanhas, integrações fiscais e de mercado.
- **Tipo de produto:** monólito modular (backend único, FastAPI, dividido por domínio) — não microsserviços. Ver [[Arquitetura]].
- **Público-alvo:** pet shops e clínicas veterinárias multiempresa, com tutores/clientes finais acessando via app mobile e loja e-commerce.
- **Situação atual:** sistema em operação real, desenvolvido majoritariamente por uma pessoa com assistência de IA (Codex/OpenAI, confirmado por `AGENTS.md`, `.github/copilot-instructions.md` e instruções específicas para agentes na raiz do repositório). Governança documental já é madura — ver `docs/GOVERNANCA_ENTERPRISE.md` (14 áreas avaliadas, nenhuma "reescrita total" recomendada).
- **Observação importante:** o próprio time já mantém uma documentação extensa e honesta em `docs/` (mais de 100 arquivos). Esta pasta `/Documentacao` não substitui aquele acervo — organiza-o como grafo navegável e adiciona verificação direta contra o código onde havia apenas declaração.

## 2. Arquitetura

- [[Arquitetura]] — monólito modular, componentes, fluxo de requisição, processamento em background (com divergência corrigida em relação a `docs/ARQUITETURA.md`)
- [[Tecnologias]] — stack completa com versões confirmadas
- [[Banco-de-Dados]] — modelos, migrations, isolamento multi-tenant (RLS + filtro ORM)
- [[API]] — índice de endpoints por domínio

## 3. CI/CD

- [[CI-CD]] — branches, hooks, pipeline de CI (8 workflows), gate de release, deploy manual auditado, rollback

## 4. Funcionalidades

- [[Funcionalidades]] — mapa completo do menu real do frontend, com 10 módulos documentados em profundidade nesta fase:
  [[PDV-Vendas]] · [[Produtos-Estoque]] · [[Financeiro]] · [[Comissoes]] · [[Compras]] · [[Banho-e-Tosa]] · [[Veterinario]] · [[Campanhas]] · [[E-commerce]] · [[Entregas]]

## 5. Segurança

- [[Seguranca]] — resumo executivo
  - [[Autenticacao]] · [[Autorizacao]] · [[API-Security]] · [[Secrets]] · [[Vulnerabilidades]]

## 6. Integrações

- [[Integracoes]] — 8 integrações com documento próprio ([[Bling]], [[WhatsApp-WAHA]], [[Mercado-Pago]], [[Fiscal-IntNFe-SEFAZ]], [[iFood]], [[Stone]], [[OpenAI-IA]], [[Asaas]]) + outras confirmadas de menor complexidade

## 7. Entidades e domínio

- [[Dominio]] — [[Tenant]] · [[Usuario]] · [[Role-Permission]] · [[Cliente]] · [[Pet]] · [[Produto]] · [[Venda]] · [[ContaPagar]] · [[ContaReceber]]

## 8. Tecnologias

Ver [[Tecnologias]] para a tabela completa. Resumo: Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL (backend); React 18 + Vite + Tailwind (frontend web); React Native + Expo (mobile); Docker Compose (todos os ambientes); GitHub Actions (CI).

## 9. Pendências

Ver [[Pendencias]] para a lista completa organizada por área. Os 3 itens mais urgentes:

1. ❓ Confirmar se o campo de senha criptografada da Stone (`conciliacao_password_enc`) está em uso real — ver [[Secrets]].
2. ❓ Decidir sobre reativar MFA (existe no schema, não está ativo em nenhum login real) — ver [[Autenticacao]].
3. ❓ Confirmar topologia de deploy (processos/réplicas) para dimensionar o real impacto do rate limiting in-memory — ver [[API-Security]].

## 10. Riscos

Ver [[Matriz-de-Riscos]] (tabela completa, 13 itens) e [[Vulnerabilidades]] (detalhe de segurança). Resumo por severidade:

- 🟠 **Alto (3):** MFA não aplicado, rate limiting não escalável, campo de senha Stone sem cifragem confirmada.
- 🟡 **Médio (4):** upload de XML sem limite, rotas sem rate limit dedicado, log DEBUG com PII, dois sistemas fiscais paralelos sem relação documentada.
- 🔵 **Baixo/dívida técnica (3):** webhook Bling legado não exposto (código morto), documentação de arquitetura desatualizada, padrão de módulo não seguido pelo código legado.
- ⚪ **Informativo (1)+:** reaproveitamento da entidade `Cliente` para múltiplos papéis.

**Pontos fortes que também são achado desta análise** (não apenas ausência de problema): isolamento multi-tenant em dupla camada (RLS + filtro ORM fail-closed) é o controle de segurança mais maduro do sistema; nenhum secret hardcoded encontrado; CORS fechado por padrão.

## Roadmap de organização e evolução

Um roadmap de trabalho foi construído em cima desta análise: [[Roadmap]] — 5 fases: 4 em ordem de dependência lógica ([[Fase-1-CI-CD-e-Padronizacao]] → [[Fase-2-Funcionalidades-e-Skills]] → [[Fase-3-Integracoes]] → [[Fase-4-Seguranca]]) mais uma fase contínua de produto/negócio que roda em paralelo ([[Fase-5-Produto-e-Negocio]]). É o documento a seguir para transformar os achados abaixo em trabalho executado.

A execução tela por tela da padronização visual (itens 1.6-1.9) é registrada em [[RefatoracaoV2]] — uma linha por tela, com data e resumo do que mudou.

## 11. Próximas ações

### Crítico
- Validar com o responsável o achado do campo `conciliacao_password_enc` (Stone) antes de usar esse fluxo com dados reais em produção — [[Secrets]].

### Alto
- Decidir sobre MFA (implementar de fato ou remover expectativa do schema) — [[Autenticacao]].
- Migrar rate limiting crítico (login) para armazenamento compartilhado antes de escalar horizontalmente — [[API-Security]].

### Médio
- Aplicar limite de tamanho no upload de XML de nota de entrada — [[API-Security]].
- Documentar a relação entre os dois sistemas fiscais (`intnfe/` vs. `nfe/`) — [[Fiscal-IntNFe-SEFAZ]].
- Atualizar `docs/ARQUITETURA.md` oficial com o worker do catálogo mestre e os jobs in-process — [[Arquitetura]].

### Baixo
- Remover o arquivo de webhook Bling legado sem assinatura (`integracao_bling_webhook_routes.py`), já confirmado não registrado — [[Vulnerabilidades]].

### Melhoria futura
- Aprofundar as 7 funcionalidades ainda não documentadas em detalhe (Dashboard, Lembretes, Calculadora de Ração, Cadastros auxiliares, RH, Configurações, painel `/ops`) — ver [[Pendencias]] e [[Matriz-de-Cobertura]].
- Extrair contratos de request/response por endpoint (nenhum domínio tem essa coluna ✅ completa hoje) — [[API]].
- Cobrir o aplicativo mobile (`app-mobile/src/`), fora do escopo desta primeira rodada.

## Metodologia desta análise

Realizada em 2026-09-12 por 5 agentes de exploração especializados (rotas/módulos do backend, modelos de banco/migrations, estrutura do frontend, integrações externas, segurança) rodando em paralelo sobre o código real, mais verificação manual pontual de 2 achados específicos (rota Bling não registrada; ausência de código de cifragem Stone). Nenhuma modificação foi feita no código-fonte da aplicação — apenas leitura. A documentação pré-existente em `docs/` foi lida, aproveitada e usada como base de comparação, nunca descartada.

## Lacunas explícitas desta análise

- Contratos de API request/response não foram extraídos endpoint a endpoint.
- App mobile (`app-mobile/`) não foi analisado nesta rodada.
- 7 funcionalidades de menu identificadas mas não aprofundadas (ver seção 11).
- Auditoria de segurança foi amostral em alguns pontos (SQL bruto fora do ORM, mass assignment em schemas, log de credenciais em módulos de integração) — marcados explicitamente como não identificado nos respectivos documentos, não afirmados como seguros por omissão.
