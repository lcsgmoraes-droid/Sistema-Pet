---
tipo: roadmap
atualizado: 2026-09-12
---

# Template — Spec/Skill de Funcionalidade

Parte de [[Roadmap]] ([[Fase-2-Funcionalidades-e-Skills]]). Formato único a ser usado tanto para os documentos em [[Funcionalidades]] quanto — se a decisão da Fase 2 for adiante — para as Skills reais em `.claude/skills/`. Já é o formato aplicado (de forma resumida) às 10 funcionalidades existentes; este documento formaliza e completa os campos que ainda faltam nelas.

## Campos obrigatórios

```markdown
# <Nome da funcionalidade>

## Identificação
- Menu: <grupo> → <item>
- Rota frontend: <path>
- Módulo de rota (arquivo): <ex. SalesMarketingRoutes.jsx>
- Módulo de plano/SaaS (se houver flag de módulo contratável): <nome da flag>

## Objetivo
O que a tela resolve, em 1-3 frases, só com base no que o código confirma (nome de rotas, schemas, docstrings) — nunca aspiracional.

## Usuários
Quais perfis/roles acessam (ver [[Role-Permission]]) e se há regra de permissão específica além do padrão.

## Fluxo
Diagrama texto simples: Usuário → Tela → Componente → API → Service → Banco. Adaptar aos nomes reais de arquivo.

## Frontend
- Página(s)/componente(s) principais (caminho de arquivo)
- Chamadas HTTP (via `frontend/src/api.js` ou outro client)
- Validações client-side confirmadas
- Regra de permissão aplicada na tela (`ProtectedRoute`, filtro de menu)

## Backend
- Rota(s), arquivo(s) de serviço, arquivo(s) de query
- Regra de negócio confirmada (não inferida)
- Jobs/eventos disparados, se houver

## Banco de dados
Entidades envolvidas (link para [[Dominio]] quando existir documento da entidade), relacionamentos relevantes só desta funcionalidade.

## APIs
Endpoint, método, autenticação, parâmetros/payload confirmados (não inventados — se não foi extraído, marcar ⚠️ não identificado).

## Integrações
Quais integrações de [[Integracoes]] esta tela usa, e em que ponto do fluxo.

## Segurança
- O que esta tela PODE fazer (ações permitidas por permissão)
- O que esta tela NÃO PODE fazer (limite explícito — ex.: "Caixa não pode excluir venda", já confirmado em `docs/PERFIS_ACESSO_PADRAO.md`)
- Dado sensível exposto nesta tela, se houver (ver `docs/CATALOGO_DADOS_CRITICOS_LGPD.md`)

## Dependências
Outras funcionalidades/entidades que esta tela usa ou que dependem dela (links Obsidian).

## Observações
Comportamento não óbvio confirmado no código (ex.: coluna extra de proteção, campo reaproveitado para outro propósito).

## Pontos de atenção
Dívida técnica, duplicação conhecida, dependência frágil — sempre com evidência (arquivo:linha) ou marcado como ❓ necessita validação.

## Não identificado
Lista explícita do que não foi confirmado nesta rodada.
```

## Frontmatter sugerido, se virar Skill real (`.claude/skills/<nome>/SKILL.md`)

```yaml
---
name: <slug-da-funcionalidade>
description: Use ao mexer em <área> — <gatilho resumido de quando carregar esta skill>.
---
```

A `description` é o que decide se a skill é carregada automaticamente — deve ser específica o bastante para disparar no momento certo (ex.: "Use ao mexer em cálculo de comissão, fechamento de comissão ou demonstrativo de vendedor", não só "comissões").

## Regra de manutenção

Toda vez que uma funcionalidade for alterada de forma relevante (nova regra de negócio, nova integração, mudança de permissão), o documento correspondente deve ser atualizado no mesmo PR — mesmo critério já usado pelo projeto para `docs/templates/FICHA_ENTREGA.md` (ver `docs/GOVERNANCA_ENTERPRISE.md`, "gate proporcional por mudança"). Documentação desatualizada é pior do que ausência de documentação, porque engana em vez de admitir a lacuna.
