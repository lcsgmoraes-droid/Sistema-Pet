# Continuidade operacional e acompanhamento de cobranca

Data: 2026-10-21
Responsavel de negocio: Lucas
Executor tecnico: Codex
Prioridade: P1
Ambiente da correcao: DEV; producao depende de autorizacao de deploy.

## 1. Necessidade e aceite

O fim de um periodo de teste impediu uma empresa de finalizar vendas. A regra
anterior tambem suspendia acesso depois de 15 dias de atraso. Lucas determinou
que cobranca e vencimento de teste gerem avisos graduais, com bloqueio comercial
somente depois de sua autorizacao explicita.

Aceite: teste vencido e eventos financeiros nao interrompem a operacao;
suspensao cadastral administrativa continua impedindo acesso; os estados e
valores financeiros permanecem disponiveis para acompanhamento.

## 2. Regras e dados

- `billing_status` continua descrevendo teste, pendencia, atraso, estorno ou
  cancelamento financeiro. Nao determina suspensao operacional.
- `tenants.status` continua sendo o controle cadastral: `active` permite
  operacao; `inactive`/`suspended` impedem acesso. Uma suspensao comercial exige
  confirmacao explicita da autorizacao de Lucas e justificativa no painel
  administrativo. A API recusa a transicao sem esses dados e sem identificar
  o administrador. A nota imutavel de acompanhamento registra a declaracao,
  autor, data e motivo na mesma transacao da mudanca cadastral.
- Avisos de atraso: lembrete ate 7 dias, atencao de 8 a 15 dias e revisao manual
  depois de 15 dias. Nenhuma etapa agenda bloqueio.
- Teste registrado preserva seus recursos e limites de experiencia completa
  ate ativacao do plano ou decisao manual, mesmo quando um evento financeiro
  muda o estado de cobranca antes da ativacao. Pagamento/ativacao ja confirmados
  impedem que um atraso futuro reabra o teste. Planos ja ativos mantem seus
  limites contratuais.
- Webhooks atualizam os fatos financeiros e a proposta; eventos financeiros
  nao suspendem os modulos extras da proposta vigente.
- Nao ha migration, nova variavel de ambiente ou mudanca de dados de DEV para
  producao. A regra padrao e compartilhada entre empresas.

## 3. Arquitetura e integracoes

A politica comum fica em `billing_access.py`, usada pelo resumo de assinatura
e pelos limites de vendas/sessoes. O gate de modulos/recursos respeita suspensao
cadastral. O frontend compartilha a construcao dos avisos entre Layout e Meu
plano. O recebimento e a idempotencia dos webhooks Asaas permanecem no fluxo
existente. Indisponibilidade do provedor nao gera suspensao operacional.

## 4. Seguranca e privacidade

Autenticacao, verificacao de usuario, isolamento por tenant e permissoes
administrativas permanecem. A confirmacao no painel e uma declaracao auditavel
do administrador de que obteve autorizacao de Lucas; nao solicita nem valida
uma assinatura digital de Lucas. Nao se cria token, sessao ou acesso entre empresas.
Fixtures e testes usam dados ficticios. Secrets, extratos e dados privados de
cobranca consultados na investigacao nao integram esta entrega.

## 5. Desenvolvimento e qualidade

Validar regras de vendas, modulos, recursos e sessoes em teste vencido, atraso
prolongado, eventos do provedor e suspensao manual, incluindo isolamento por
tenant. Validar mensagens graduais e build frontend. Os comandos e resultados
finais devem constar no PR desta correcao.

Resultado local: 139 testes backend passaram, incluindo autorizacao/rollback e
isolamento; 11 testes dos utils Ops e testes dos avisos passaram. Ruff, ESLint,
Prettier e build frontend passaram. As regressões de continuidade/avisos foram
incluidas nos workflows CI e no gate local de release.

## 6. Ambientes e homologacao

Testes locais com dados ficticios; nenhuma venda real e criada para validar o
gate. Em producao, a contencao pontual anterior foi registrada pelo wrapper
`scripts/auditar_comando_producao.sh`, e as duas contas indicadas por Lucas
foram verificadas com acesso ativo. Isso nao substitui o deploy da regra geral.

## 7. Publicacao e rollback

Entrega backend/frontend, sem alteracao mobile. Publicar pelo fluxo oficial
depois do PR, checks e autorizacao explicita de Lucas. Rebuild backend e build
frontend sao necessarios. Conferir health/watchdog e as funcoes reais de acesso
em transacao curta com rollback, sem emitir venda, cobranca ou token.

Reverter ao commit anterior somente com autorizacao e avaliacao do risco de
retorno dos bloqueios automaticos. Nao remover nem reescrever dados financeiros.

## 8. Observabilidade e sustentacao

Manter recibos dos webhooks e logs operacionais. O resumo da assinatura expoe
que nao existe bloqueio automatico e qual aviso/revisao esta indicado. A
existencia de pendencia deve orientar acompanhamento humano, nunca ser
interpretada como autorizacao de suspensao.

## 9. Comunicacao e rotina

Lucas acompanha pendencias e decide qualquer suspensao comercial. O usuario da
loja recebe avisos com continuidade de acesso. Nao ha envio novo automatico de
WhatsApp/e-mail nesta entrega. A regra foi registrada tambem no `AGENTS.md`.

## 10. Fechamento

Implementacao e revisao em DEV. Validacoes, PR e decisao de publicacao serao
registrados na conclusao. A consulta de pagamentos e uma leitura separada:
nao quita, altera ou cria cobrancas.
