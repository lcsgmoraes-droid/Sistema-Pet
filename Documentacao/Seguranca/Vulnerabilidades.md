---
tipo: seguranca
atualizado: 2026-09-12
---

# Vulnerabilidades e achados de segurança

Parte do eixo [[Seguranca]]. Lista consolidada, mais severo primeiro. Ver também [[Matriz-de-Riscos]] (visão tabular incluindo riscos não só de segurança). Nenhuma exploração ofensiva foi realizada — análise baseada em código, configuração e arquitetura disponíveis, por agentes de exploração dedicados em 2026-09-12.

## 🟠 Alto

### 1. MFA não é aplicável a nenhuma conta hoje
- **Onde:** `backend/app/auth_routes.py` (legado, não registrado) vs. `auth_multitenant_account_routes.py` (ativo, sem checagem de 2FA).
- **Evidência:** campo `two_factor_enabled`/`two_factor_secret` existe no modelo (`models.py:115-117`), mas só é verificado em rota morta; endpoints de habilitar/desabilitar 2FA nunca foram implementados (`auth_routes.py:255-262`, comentário `PLACEHOLDER`).
- **Impacto potencial:** conta de administrador comprometida por vazamento de senha não tem segunda barreira.
- **Recomendação:** implementar 2FA no fluxo real ou remover a expectativa do schema. Detalhe: [[Autenticacao]].
- **Prioridade:** Alta.

### 2. Rate limiting não é efetivo em deploy multi-processo
- **Onde:** `backend/app/middlewares/rate_limit.py`.
- **Evidência:** armazenamento em memória, limitação documentada no próprio código-fonte (linhas 5-8); cada processo/réplica mantém contador próprio.
- **Impacto potencial:** em produção com múltiplos workers Uvicorn, o limite de 5 req/min por IP em login é multiplicado pelo número de processos — reduz proteção contra força bruta.
- **Recomendação:** migrar para armazenamento compartilhado (Redis, já disponível no projeto).
- **Prioridade:** Alta antes de escalar horizontalmente a API.
- Detalhe: [[API-Security]].

### 3. Campo de senha criptografada da Stone sem implementação confirmada
- **Onde:** `backend/app/stone_models.py:242` (`conciliacao_password_enc`).
- **Evidência:** nenhum código encontrado que leia/escreva o campo; `pycryptodome` instalado mas não importado em lugar nenhum.
- **Impacto potencial:** se o campo estiver em uso real por caminho não coberto por esta análise, pode haver senha em texto plano onde deveria haver criptografia — não confirmado, apenas não descartado.
- **Recomendação:** ❓ confirmar com o responsável se esse campo está em uso; se sim, auditar o caminho real de cifragem antes de considerar seguro.
- **Prioridade:** Alta até confirmação. Detalhe: [[Secrets]].

## 🟡 Médio

### 4. Upload de XML de NF-e sem limite de tamanho
- **Onde:** `backend/app/notas_entrada/upload_routes_parts/xml_route.py`.
- **Evidência:** valida apenas extensão `.xml`; sem limite de bytes (diferente do upload de imagem de produto, que tem 10MB); parser stdlib sem `defusedxml`.
- **Impacto potencial:** negação de serviço por arquivo muito grande ou expansão de entidades internas.
- **Recomendação:** aplicar limite de tamanho equivalente ao já existente para imagens.
- **Prioridade:** Média. Detalhe: [[API-Security]].

### 5. Maioria das rotas sem rate limit dedicado
- **Onde:** ~90 routers registrados; apenas os grupos `AUTH_ROUTES`/`API_ROUTES` explícitos têm limite real.
- **Impacto potencial:** endpoints pesados (relatórios, IA, envio de e-mail) sem throttling específico.
- **Recomendação:** priorizar rate limit dedicado para rotas de custo computacional alto.
- **Prioridade:** Média. Detalhe: [[API-Security]].

### 6. Log em nível DEBUG inclui e-mail do usuário
- **Onde:** `backend/app/auth/dependencies.py:63-64,87-89`.
- **Evidência:** `logger.debug` registra `user_email` e `tenant_id`.
- **Impacto potencial:** PII em log, risco baixo/médio se logs DEBUG forem persistidos sem controle de acesso/retenção conforme LGPD.
- **Recomendação:** confirmar que nível DEBUG não roda em produção, ou mascarar o e-mail no log.
- **Prioridade:** Média.

## 🔵 Baixo / dívida técnica

### 7. Rota de webhook Bling sem assinatura — código morto, não exposto
- **Onde:** `backend/app/integracao_bling_webhook_routes.py` (`POST /integracoes/bling/webhook`).
- **Evidência:** **confirmado que NÃO está registrada** em `main_routers.py`/`main.py` — não é acessível hoje.
- **Recomendação:** remover o arquivo para evitar registro acidental futuro por alguém que reative a rota sem notar a ausência de validação.
- **Prioridade:** Baixa (higiene de código, não é uma vulnerabilidade ativa). Detalhe: [[API-Security]].

### 8. Divergência entre padrão de módulo documentado e código legado
- Não é uma vulnerabilidade de segurança, mas afeta auditabilidade: código legado "flat" dificulta localizar rapidamente toda a superfície de um domínio. Ver [[Arquitetura]].

## ⚪ Informativo / pontos fortes confirmados (para contexto, não são achados negativos)

- Isolamento multi-tenant em dupla camada (RLS + filtro ORM fail-closed) — ver [[Banco-de-Dados]], [[Autorizacao]].
- CORS fechado por padrão, sem wildcard, com comentário explícito no código contra usar `*` em produção.
- Senha de usuário com bcrypt (truncamento de 72 bytes é limitação conhecida do algoritmo, não falha de implementação).
- Upload de imagem de produto bem protegido (revalidação real do arquivo, nome gerado pelo servidor, limite de tamanho).
- Nenhum secret hardcoded encontrado no código-fonte.
- Revogação de sessão server-side real (não depende só da expiração do JWT).
- Webhooks de pagamento (Mercado Pago) reconsultam o provedor em vez de confiar cegamente no payload recebido.

## Dependências — nota sobre CVE

Este projeto está ambientado com datas de 2026 e usa versões de bibliotecas correspondentemente futuras (ex. FastAPI 0.137.2, Starlette 1.3.1). Não foi realizada consulta a bases de CVE nesta análise — qualquer biblioteca desatualizada deve ser tratada como "necessita verificação de CVE" no momento da auditoria, não como vulnerabilidade automática por ser antiga. Dependabot já está configurado (`\.github/dependabot.yml`) para as 4 stacks (pip backend/mcp, npm frontend, github-actions) com atualização semanal — ver [[CI-CD]].

## Não identificado

- Auditoria exaustiva de mass assignment em schemas Pydantic (ver [[API-Security]]).
- Varredura completa de SQL bruto fora do ORM (ver [[Autorizacao]]).
- Auditoria linha a linha dos ~21 arquivos de integração quanto a log de credenciais completas.
