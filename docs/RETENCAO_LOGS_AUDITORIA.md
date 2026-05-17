# Retencao de logs e auditoria

Atualizado em: 2026-05-16

Este documento define a politica operacional de retencao para logs, auditoria,
incidentes e eventos de recuperacao do Sistema Pet.

Ele nao substitui validacao juridica ou contabil. Sempre que houver conflito
entre esta politica, contrato, obrigacao legal, investigacao aberta ou orientacao
do contador/juridico, vale a regra mais conservadora.

Referencias externas:

- LGPD compilada no Planalto: https://www.planalto.gov.br/ccivil_03/_Ato2015-2018/2018/Lei/L13709compilado.htm
- Guia de Seguranca da Informacao da ANPD para agentes de tratamento de pequeno porte: https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-publica-guia-de-seguranca-para-agentes-de-tratamento-de-pequeno-porte

## Objetivos

- Preservar trilha suficiente para investigacao, suporte, LGPD, conciliacao e
  auditoria operacional.
- Reduzir exposicao de dados pessoais e sensiveis em logs antigos.
- Evitar crescimento ilimitado de arquivos JSONL e tabelas de observabilidade.
- Definir o que deve ser automatizado antes de declarar observabilidade 10/10.

## Principios

- Dados de auditoria devem ser minimizados, rastreaveis e segregados por tenant.
- Senhas, tokens, cookies, chaves de API, autorizacoes e payloads secretos nao
  devem ser gravados em log.
- Eventos devem carregar `request_id` ou `correlation_id` sempre que existir
  uma operacao rastreavel.
- Retencao pode ser suspensa por "legal hold" quando houver incidente, disputa,
  auditoria externa, investigacao de fraude ou necessidade comercial justificada.
- Pedidos LGPD devem preferir anonimizacao de campos pessoais quando o registro
  precisa ser preservado por obrigacao legal, seguranca, defesa de direito ou
  auditoria operacional.

## Matriz de retencao

| Fonte | Conteudo | Local atual | Retencao quente | Retencao arquivada | Acao final |
|---|---|---|---:|---:|---|
| `audit_logs` | Login, acesso, alteracoes sensiveis, eventos de negocio | Banco principal | 24 meses | 7 anos | Anonimizar ou purgar campos pessoais quando nao houver base de conservacao |
| `ops_error_events` | Erros, 5xx, lentidao e incidentes por request | Banco principal | 180 dias | 24 meses agregado | Purgar payload bruto e manter agregados sem dado pessoal |
| `ops_alerts` | Alertas operacionais e estado de resolucao | Banco principal | 24 meses | 36 meses agregado | Purgar alertas resolvidos antigos ou manter somente estatistica |
| `ops_recovery_actions` | Watchdog e recuperacoes automaticas | Banco principal | 24 meses | 36 meses agregado | Purgar payload bruto, manter resumo operacional |
| `backend/logs/error_events.jsonl` | Espelho local de erros de request | Servidor/producao | 30 dias | 90 dias compactado | Rotacionar e apagar arquivo antigo |
| `backend/logs/deploy_events.jsonl` | Deploys, falhas e rollbacks | Servidor/producao | 24 meses | Historico resumido em docs | Compactar antigo; registro essencial fica no checklist |
| `backend/logs/ops_command_events.jsonl` | Comandos manuais sensiveis em producao | Servidor/producao | 24 meses | Historico resumido em docs | Compactar antigo; preservar eventos de incidente |
| `backend/logs/ops_alert_notifications.jsonl` | Deduplicacao de notificacao de alerta Ops | Servidor/producao | 24 meses | Historico resumido em docs | Compactar antigo; preservar eventos de incidente |
| `backend/logs/watchdog_events.jsonl` | Watchdog interno do backend | Servidor/producao | 90 dias | 24 meses agregado | Rotacionar e apagar bruto antigo |
| `backend/logs/host_watchdog_events.jsonl` | Watchdog externo do host | Servidor/producao | 90 dias | 24 meses agregado | Rotacionar e apagar bruto antigo |
| `backend/logs/disk_guard_events.jsonl` | Guardiao preventivo de disco | Servidor/producao | 90 dias | 24 meses agregado | Rotacionar e apagar bruto antigo |
| Logs de container/nginx | Acesso HTTP, erros de proxy e runtime | Docker/nginx/host | 30 dias | 90 dias se houver incidente | Rotacionar no host |

## Campos minimos por evento

Todo evento novo de auditoria ou observabilidade deve tentar registrar:

- `created_at` ou `timestamp` em UTC.
- `tenant_id` quando aplicavel.
- `user_id` quando aplicavel.
- `request_id` ou `correlation_id` quando existir.
- `event` ou `action`.
- `entity_type` e `entity_id` quando o evento altera entidade de negocio.
- `source`, `status` e `outcome` quando houver processo automatico.
- Metadados sanitizados suficientes para reconciliacao.

## Dados proibidos em log

Nao registrar em texto claro:

- Senha, hash de senha, token de sessao, refresh token ou JWT completo.
- Cookie, header `Authorization`, chave de API, segredo de webhook ou credencial SMTP.
- Documento completo, cartao, dados bancarios completos ou payload fiscal bruto
  sem necessidade operacional.
- Conteudo de mensagem privada quando o diagnostico puder usar identificadores,
  contadores ou resumo tecnico.

O servico `backend/app/services/business_audit_service.py` ja mascara chaves com
partes sensiveis como `password`, `senha`, `token`, `secret`, `jwt`,
`authorization`, `cookie`, `apikey` e `api_key`. Eventos novos devem reutilizar
esse caminho ou aplicar regra equivalente.

## Acesso e consulta

- Consulta de incidentes e auditoria operacional deve ficar restrita a usuarios
  administrativos autorizados.
- Toda tela ou endpoint de auditoria precisa respeitar isolamento por tenant.
- Exportacao manual de logs deve ter justificativa e escopo minimo.
- Em atendimento ou suporte, compartilhar preferencialmente `request_id`,
  horario, tenant e resumo, nao payload bruto.

## Legal hold e incidentes

Se houver incidente de seguranca, fraude, disputa comercial, investigacao tecnica
ou solicitacao formal:

1. Suspender purge dos registros relacionados.
2. Registrar no guia de incidente o periodo afetado, tenants, `request_id`s e
   sistemas envolvidos.
3. Liberar a retencao normal apenas quando o incidente for encerrado.

## Pedidos LGPD

Para pedido de acesso, portabilidade, correcao, anonimizacao ou eliminacao:

1. Localizar registros por titular, tenant, usuario, cliente e `request_id`.
2. Entregar ou tratar somente o escopo do titular solicitante.
3. Anonimizar campos pessoais quando o registro precisa permanecer para
   cumprimento de obrigacao legal, defesa de direito, seguranca ou auditoria.
4. Purgar dados pessoais sem base de conservacao quando a solicitacao for
   validada.
5. Registrar a propria execucao do pedido em auditoria.

## Rotina operacional recomendada

Mensal:

- Revisar crescimento de `backend/logs/*.jsonl` no servidor.
- Confirmar que backups incluem o banco, mas nao preservam logs brutos alem do
  prazo definido sem necessidade.
- Conferir se incidentes encerrados ja podem voltar ao ciclo normal de purge.

Trimestral:

- Revisar a matriz de retencao.
- Conferir se novos MCPs, workers, integracoes e rotas criticas foram incluidos.
- Validar se `request_id` e `correlation_id` aparecem nos eventos relevantes.

Apos cada deploy real:

- Registrar commit, backup, health e evento de deploy em
  `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md` ou checklist equivalente.
- Confirmar que `backend/logs/deploy_events.jsonl` recebeu sucesso ou falha.
- Para comando manual sensivel fora do deploy oficial, usar
  `scripts/auditar_comando_producao.sh` e conferir `backend/logs/ops_command_events.jsonl`.
- Se `OPS_ALERT_WEBHOOK_URL` estiver configurado, confirmar que
  `backend/logs/ops_alert_notifications.jsonl` registrou a deduplicacao da notificacao.

## Backlog para 10/10

- Criar job seguro de purge/anonimizacao para `audit_logs`,
  `ops_error_events`, `ops_alerts` e `ops_recovery_actions`.
- Adicionar logrotate ou rotina equivalente para `backend/logs/*.jsonl` no host.
- Exibir no painel Ops a idade do log mais antigo e o tamanho dos arquivos.
- Registrar metricas agregadas antes de apagar payload bruto.
- Documentar excecoes de retencao por modulo quando houver obrigacao especifica.

