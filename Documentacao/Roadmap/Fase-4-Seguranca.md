---
tipo: roadmap
atualizado: 2026-09-12
---

# Fase 4 — Segurança

Parte de [[Roadmap]]. Base: [[Seguranca]], [[Vulnerabilidades]], [[Matriz-de-Riscos]]. Esta fase não descobre riscos novos — executa o que já foi encontrado, na ordem de severidade, agora com o código mais organizado (Fases 1-3) para que a correção mexa em menos lugares.

## 4.1 — Prioridade imediata (🟠 Alto, ver [[Matriz-de-Riscos]] R01-R03)

- [ ] **R03 — Validar campo `conciliacao_password_enc` da Stone** (ver [[Secrets]]). Primeiro passo antes de qualquer código: perguntar ao responsável se esse campo está em uso em produção hoje. Se sim, tratar como incidente de segurança (senha potencialmente em texto plano) antes de seguir o roadmap normal. Se não, remover o campo/comentário morto ou implementar a cifragem antes de habilitar o fluxo.
- [ ] **R01 — Decidir sobre MFA**. Duas saídas válidas: (a) implementar a verificação real no fluxo `auth_multitenant_account_routes.py` reaproveitando o campo TOTP já existente no schema; (b) remover os campos `two_factor_*` do modelo se não houver plano de usar, para não sugerir uma proteção que não existe. Não deixar como está (schema sugerindo proteção inexistente).
- [ ] **R02 — Rate limiting compartilhado**. Migrar `middlewares/rate_limit.py` de armazenamento in-memory para Redis (já disponível no projeto, hoje uso opcional/leve — ver [[Banco-de-Dados]]). Prioridade sobe se/quando produção rodar múltiplos processos Uvicorn.

## 4.2 — Prioridade média (🟡, ver [[Matriz-de-Riscos]] R04-R06, R11)

- [ ] **R04** — Aplicar limite de tamanho no upload de XML de nota de entrada, mesmo padrão já usado no upload de imagem de produto (10MB).
- [ ] **R05** — Priorizar rate limit dedicado para rotas de custo computacional alto identificadas na Fase 2 ao mapear cada tela (relatórios pesados, IA, envio de e-mail).
- [ ] **R06** — Confirmar se logs DEBUG rodam em produção; se sim, mascarar e-mail do usuário no log ou reduzir nível de log em produção.
- [ ] **R11** — Documentar a relação SEFAZ/IntNFe (já tratado também na Fase 3, item 3.3 — mesma ação, não duplicar trabalho).

## 4.3 — Prioridade baixa / higiene (🔵, ver [[Matriz-de-Riscos]] R07-R09)

- [ ] **R07** — Remover `integracao_bling_webhook_routes.py` (código morto, já tratado na Fase 3, item 3.2).
- [ ] **R08** — Atualizar `docs/ARQUITETURA.md` oficial com o worker do catálogo mestre e os jobs in-process (achado da Fase 1/análise inicial).
- [ ] **R09** — Já em andamento, ver Fase 1 (campanha de arquivos grandes) — esta fase só acompanha, não reabre.

## 4.4 — Auditorias que ainda não foram feitas (marcadas como ❓ em [[Vulnerabilidades]])

Itens que exigem tempo dedicado de auditoria, não só decisão:

- [ ] Varredura de mass assignment em schemas Pydantic (campos que não deveriam ser setáveis pelo cliente, ex. `tenant_id`, `is_admin`, em payloads de criação).
- [ ] Varredura de SQL bruto fora do ORM (`session.execute(text(...))`) que poderia contornar o filtro automático de tenant (ver [[Autorizacao]]).
- [ ] Auditoria linha a linha dos ~21 arquivos de integração quanto a log de credenciais completas (feita amostralmente, não exaustivamente, na análise original).
- [ ] Auditoria de todas as rotas de upload de arquivo do sistema quanto a limite de tamanho (só produto e XML NF-e foram verificados).
- [ ] Auditar entropia/expiração do token de rastreamento público de entrega (`/rastreio/:token`).

## 4.5 — Governança de segurança (mais estrutural, menor urgência)

- [ ] Confirmar regras exatas de branch protection do GitHub diretamente nas configurações (não auditável via código) — formalizar/registrar independentemente do resultado.
- [ ] Avaliar CODEOWNERS (já proposto na Fase 1) também como controle de segurança — força revisão de outra pessoa em áreas sensíveis (auth, fiscal, pagamento).
- [ ] Avaliar WAF na frente do Nginx em produção, se o volume de tráfego/ataques justificar.
- [ ] Manter o ciclo do Dependabot (já configurado, semanal) como processo contínuo de CVE — não precisa de auditoria manual de versão adicional enquanto isso estiver ativo.

## 4.6 — Reforços adicionais (fora da auditoria original)

Itens que não vieram de um achado em [[Matriz-de-Riscos]], mas que somam a esta fase:

- [ ] **MFA por camada, não tudo de uma vez.** Em vez de implementar 2FA para todas as contas de tenant ao mesmo tempo (projeto maior, ligado a R01), priorizar primeiro o painel `/ops` (staff CorePet com acesso multi-tenant) — é a conta cujo comprometimento afeta todos os clientes ao mesmo tempo, não só um tenant. Depois avaliar 2FA opcional para donos de conta (role admin) por tenant.
- [ ] **LGPD — fluxo de titular de dados.** O sistema guarda dados de clientes/tutores e pets (nome, CPF, endereço, histórico de compra/saúde de pet). Confirmar se existe (ou planejar) um fluxo de autoatendimento para exportação/exclusão de dados a pedido do titular (LGPD art. 18) — não identificado em nenhum documento de `/Documentacao` nem `docs/` até agora.
- [ ] **Cabeçalhos de segurança HTTP.** Não confirmado nesta análise: CSP, `X-Content-Type-Options`, `Strict-Transport-Security`, `Referrer-Policy` no Nginx/FastAPI. Checagem rápida com uma ferramenta como Mozilla Observatory contra `corepet.com.br`.
- [ ] **Cadência leve de teste de segurança externo.** Com integrações financeiras (Stone, Mercado Pago, Asaas) e fiscais (SEFAZ/IntNFe) em produção, considerar um pentest leve anual ou um `security.txt` simples de disclosure responsável — o custo de um incidente em fluxo financeiro/fiscal é desproporcional ao custo do teste.
- [ ] **Teste real de restauração de backup** — mesma ação de [[Fase-1-CI-CD-e-Padronizacao]] item 1.5, listada aqui também porque é, na prática, um controle de segurança (continuidade/disponibilidade), não só de infraestrutura. Não duplicar o trabalho, só a referência.

## Critério de conclusão desta fase (não é "nunca mais revisar segurança")

- Todos os itens 🟠 (R01-R03) resolvidos ou formalmente aceitos como risco conhecido com justificativa registrada.
- Itens 🟡 tratados ou agendados com prazo.
- [[Matriz-de-Riscos]] com status atualizado em cada linha (não deixar "Aberto" indefinidamente sem revisão).
- Esta fase se torna **rotina contínua**, não um projeto que termina — assim como o restante do roadmap, mas segurança em particular exige revisão periódica mesmo sem mudança de código (ex.: nova CVE em dependência).

## Não identificado

- ❓ Cadência formal de revisão de segurança recorrente (trimestral? a cada release?) — decisão de processo do responsável, não técnica.
