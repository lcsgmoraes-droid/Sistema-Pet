---
tipo: base
atualizado: 2026-09-12
---

# Matriz de Riscos

Ver [[README]], [[Vulnerabilidades]] (detalhe de segurança), [[Pendencias]]. Inclui riscos de segurança e riscos estruturais/arquiteturais. Nenhuma exploração ofensiva foi realizada.

| ID | Categoria | Risco | Severidade | Evidência | Recomendação | Status |
|---|---|---|---|---|---|---|
| R01 | Segurança — Auth | MFA existe no schema mas não é verificado em nenhum login real | 🟠 Alto | `models.py:115-117` vs. rota ativa `auth_multitenant_account_routes.py` sem checagem de 2FA; endpoints de 2FA são `PLACEHOLDER` em `auth_routes.py:255-262` | Implementar 2FA no fluxo real ou remover expectativa do schema | Aberto |
| R02 | Segurança — API | Rate limiting customizado não funciona corretamente com múltiplos processos/réplicas | 🟠 Alto | `middlewares/rate_limit.py:5-8` (limitação documentada no próprio código) | Migrar para armazenamento compartilhado (Redis) antes de escalar horizontalmente | Aberto |
| R03 | Segurança — Dados | Campo `conciliacao_password_enc` (Stone) sem código de cifragem confirmado | 🟠 Alto (até validação) | `stone_models.py:242`; nenhum uso de `Crypto.Cipher` no repo | Confirmar com o responsável se o campo está em uso; implementar ou remover | ❓ Aguardando validação |
| R04 | Segurança — Upload | XML de nota de entrada sem limite de tamanho | 🟡 Médio | `notas_entrada/upload_routes_parts/xml_route.py` | Aplicar limite de bytes, igual ao já existente para imagens (10MB) | Aberto |
| R05 | Segurança — API | Maioria das rotas sem rate limit dedicado | 🟡 Médio | Apenas grupos `AUTH_ROUTES`/`API_ROUTES` cobertos em `rate_limit.py` | Priorizar rotas de custo computacional alto (relatórios, IA, e-mail) | Aberto |
| R06 | Segurança — Logs/LGPD | Log DEBUG expõe e-mail do usuário | 🟡 Médio | `auth/dependencies.py:63-64,87-89` | Confirmar que DEBUG não roda em produção, ou mascarar e-mail | Aberto |
| R07 | Segurança — Código morto | Rota de webhook Bling sem assinatura existe como arquivo | 🔵 Baixo | `integracao_bling_webhook_routes.py`; confirmado **não registrada** em `main_routers.py` | Remover arquivo por higiene, evitar registro acidental futuro | Aberto (baixo risco) |
| R08 | Arquitetura | `docs/ARQUITETURA.md` desatualizado sobre processamento em background (não cita worker do catálogo mestre nem jobs in-process) | 🔵 Baixo (risco de decisão mal informada, não de segurança) | Confirmado por agente de exploração — ver [[Arquitetura]] | Atualizar `docs/ARQUITETURA.md` oficial com os achados desta análise | Aberto |
| R09 | Dívida técnica | Padrão de módulo documentado (`docs/BLUEPRINT_BACKEND.md`) não é seguido pela maior parte do código legado | 🔵 Baixo | Confirmado — apenas domínios novos seguem a pasta padrão. **Atualização:** já existe campanha ativa de redução de arquivos grandes em ambos os lados — backend (`backend/tests/unit/test_backend_large_files_700_batch_*_refactor.py`, dezenas de batches) e frontend (`frontend/scripts/test-large-files-700-batch-*-refactor.mjs`, limite de 700-1000 linhas validado por teste) | Consolidar a campanha de tamanho de arquivo já em andamento com a adoção do padrão de pastas por domínio, para que a divisão gere módulos coesos (routes/schemas/services/queries), não apenas arquivos menores sem organização — ver [[Roadmap]] Fase 1 | Em andamento (mais avançado do que a avaliação inicial sugeria) |
| R10 | Modelagem de dados | `Cliente` reaproveitado para fornecedor/entregador/funcionário | ⚪ Informativo | `vendas_models.py`, `models_cadastros.py` | Confirmar se é decisão definitiva ou candidata a separação futura | ❓ Necessita validação |
| R11 | Modelagem de dados | Dois sistemas fiscais paralelos (`intnfe/` vs. `nfe/`) sem relação documentada | 🟡 Médio (risco de confusão operacional/manutenção) | Confirmado nos routers ativos | Documentar a relação (legado vs. novo) em `docs/ARQUITETURA.md` ou ADR | ❓ Necessita validação |
| R12 | Segurança — Sessão pública | Token de rastreamento de entrega (`/rastreio/:token`) sem auditoria de força/expiração nesta rodada | ❓ Não classificado | Rota pública confirmada, geração do token não auditada | Auditar entropia/expiração do token | ❓ Necessita validação |
| R13 | Dependências | Bibliotecas com versão fixa (ex. FastAPI 0.137.2) sem verificação de CVE nesta análise | ❓ Não classificado | `requirements.txt`, `package.json` | Tratar como rotina do Dependabot já configurado (ver [[CI-CD]]), não como achado ad-hoc | Mitigado por processo existente |

## Como este risco é revisado

Este documento deve ser revisto a cada nova rodada de análise ou quando um item de [[Pendencias]] for respondido — atualizar o campo `Status` em vez de duplicar a linha.
