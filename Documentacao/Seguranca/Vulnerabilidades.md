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

### 9. Groq e Gemini recebem CPF/CNPJ e dado de saúde do pet — decisão de negócio pendente
- **Onde:** `backend/app/cliente_info_pdv_chat.py:327-375` (chat do PDV) e `backend/app/veterinario_ia.py:642-706` (copiloto clínico veterinário).
- **Evidência:** quando `GROQ_API_KEY` ou `GEMINI_API_KEY` estão configuradas, o fallback de IA envia nome, CPF/CNPJ, telefone e histórico de compras do cliente (PDV) e, no fluxo veterinário, alergias, doenças crônicas, medicamentos em uso e histórico clínico do pet.
- **Status em 21/09/2026:** ✅ **disclosure resolvido** — os dois provedores já são nomeados na Política de Privacidade (`frontend/src/pages/LegalPage.jsx`, seção 10, versão 21/09/2026), junto com o tipo de dado enviado. **Resta só a decisão de negócio**: manter os dois no fallback de IA (já documentados) ou removê-los.
- **Impacto potencial:** enquanto a decisão não for tomada, compartilhamento de dado sensível (saúde) e identificador (CPF/CNPJ) com dois subprocessadores adicionais segue ativo — agora divulgado, mas ainda não decidido se é o desenho definitivo.
- **Recomendação:** decisão de negócio do Lucas — manter e formalizar, ou remover do fallback. Detalhe: [[Terceiros-Dados-LGPD]].
- **Prioridade:** Alta.

### 10. Google Analytics 4 ativo sem consentimento prévio; `.env.production` versionado no git
- **Onde:** `frontend/index.html:52-70`, ID real em `frontend/.env.production` (`G-WPC2ZCFNWW`, arquivo versionado no git apesar de constar no `.gitignore` — adicionado depois do arquivo já estar rastreado).
- **Evidência:** o script carrega incondicionalmente ao renderizar a loja online, sem banner de consentimento prévio; envia IP, user-agent, cookies e eventos de navegação/compra (incluindo `pedido_id`) ao Google.
- **Status em 21/09/2026:** ✅ **disclosure resolvido** — o Google Analytics já é nomeado na seção 10 da Política de Privacidade (versão 21/09/2026). **Restam duas pendências técnicas**, não de texto: (a) o script continua carregando sem consentimento prévio; (b) `frontend/.env.production` com o ID real continua versionado no git.
- **Impacto potencial:** coleta de dado pessoal (IP, identificador de cookie) por terceiro sem mecanismo de consentimento demonstrável, mesmo já divulgado na política.
- **Recomendação:** `git rm --cached frontend/.env.production`; decidir se o GA4 continua ativo e, se sim, implementar banner de consentimento antes do carregamento do script.
- **Prioridade:** Alta.

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

### 11. Outros pontos de contato com terceiros — disclosure já resolvido em 21/09/2026
- **Onde:** ver tabela completa em [[Terceiros-Dados-LGPD]].
- **Evidência:** chamadas diretas do navegador a ViaCEP e BrasilAPI, carregamento de Google Fonts em toda tela, tiles do OpenStreetMap numa página pública de rastreio, localização na seleção de loja e na confirmação pontual de entrega do app mobile, e verificação de atualização via EAS Update.
- **Status em 21/09/2026:** ✅ todos os itens acima já estão nomeados na Política de Privacidade (`LegalPage.jsx`, seção 10, versão 21/09/2026) — item mantido só como registro histórico do achado original.
- **Prioridade:** Baixa (já resolvido).

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
