---
tipo: funcionalidade
atualizado: 2026-09-12
---

# Veterinário / Clínica

Ver [[Funcionalidades]], [[Pet]], [[OpenAI-IA]]. Fonte pré-existente: `docs/PLANEJAMENTO_MODULO_VETERINARIO.md`, `docs/VETERINARIO_BASE_CONHECIMENTO_E_IA.md`, `docs/GUIA_DEMO_VETERINARIO_CLINICA.md`.

## Identificação
- **Menu:** Atendimento → Veterinário (submenu: Agenda, Consultas/Prontuário, Exames, Assistente IA Vet, Calculadora de Doses, Vacinas, Internações, Catálogos, Repasse Parceiro, Config. Vet)
- **Rota frontend:** `/veterinario`
- **Módulo de rota:** `frontend/src/app/routes/VeterinaryRoutes.jsx`
- **Módulo de plano (SaaS):** habilitado por tenant via flag `veterinario`

## Objetivo
Prontuário clínico, consultas, exames, internações, vacinas, calculadora de doses e um assistente de IA especializado, com base em evidência clínica sincronizada de fontes externas.

## Backend (confirmado — ~25 arquivos `veterinario_*`)
`veterinario_routes.py` + módulos de consultas, exames, internação, orçamentos; `evolucao_models.py`; `ai_core/` (analyzers/engines de evidência clínica).

## Integrações
[[OpenAI-IA]] (assistente clínico, calculadora de doses); jobs semanais (desligados por padrão) de sincronização de evidência via PubMed e catálogo regulatório DailyMed/VMD — ver [[Arquitetura#Processamento fora da requisição]].

## Parceria (repasse)
`VetPartnerLink` (`veterinario_models.py`) — modelo de veterinário parceiro com repasse financeiro, possivelmente ligado ao compartilhamento seletivo de estoque entre grupos de empresas (`empresa_grupo_models.py`).

## Dependências
[[Pet]], [[Cliente]] (tutor), [[Produto]] (medicamentos/insumos).

## Não identificado
- ⚠️ Conteúdo funcional interno de `ai_core/domain`, `ai_core/engines`, `ai/governance`, `ai/versioning` não foi auditado em profundidade (apenas existência confirmada).
- ❓ Regras de repasse financeiro ao veterinário parceiro (percentual, periodicidade) não confirmadas no código nesta rodada.
