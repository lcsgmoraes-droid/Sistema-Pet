# Ficha de entrega — idempotencia de mensagens WhatsApp

## Identificacao

| Campo | Valor |
|---|---|
| Titulo | Bloqueio persistente de mensagens WhatsApp repetidas |
| Data | 2026-08-27 |
| Responsavel de negocio | Responsavel pelo Sistema Pet |
| Executor tecnico | IA |
| Prioridade | P1 |
| Risco | Medio: altera persistencia e adiciona indice unico |
| Dominio afetado | Webhook e orquestrador interno do WhatsApp |

## 1. Necessidade e requisitos

- Problema: o provedor pode reenviar o mesmo evento e o backend salvava e
  processava novamente a mensagem, com risco de resposta ou acao duplicada.
- Usuarios afetados: empresas com atendimento automatizado pelo WhatsApp.
- Resultado esperado: o mesmo identificador externo e processado uma unica vez
  dentro de cada empresa.
- Criterios de aceite:
  - repeticao sequencial nao cria outra mensagem nem chama novamente o processador;
  - duas execucoes concorrentes sao fechadas pelo banco;
  - o mesmo identificador pode existir em empresas diferentes;
  - mensagem sem identificador externo continua sendo processada;
  - historico existente nao e apagado.

## 2. Arquitetura e integracoes

- A primeira barreira consulta `tenant_id + whatsapp_message_id` antes de gravar.
- A barreira definitiva e um indice unico parcial no banco com a mesma chave.
- Se dois processos passarem juntos pela primeira consulta, apenas um confirma a
  gravacao; o outro reconhece a colisao e encerra sem acionar IA, resposta ou pedido.
- O ponto publico `process_incoming_message` permanece igual e agora mantem o
  contexto da empresa ativo durante toda a transacao.
- O orquestrador interno deixou de inventar uma chave fixa por telefone quando o
  provedor nao envia ID. Nessa situacao o campo fica nulo e mensagens legitimas nao
  sao confundidas entre si.

## 3. Dados, banco e migracao

- Migration: `zxj20260827a1_whatsapp_message_idempotency.py`.
- Indice: `ux_whatsapp_ia_messages_tenant_provider_message`.
- Escopo da unicidade: empresa + identificador externo nao vazio.
- Copias historicas sao preservadas; somente o identificador repetido das copias
  posteriores vira nulo antes da criacao do indice.
- IDs nulos ou vazios nao participam da trava porque nao identificam um evento do
  provedor com seguranca.
- Nao ha copia de dados entre empresas nem alteracao de retencao.

## 4. Seguranca e privacidade

- Toda consulta e gravacao permanece no contexto do tenant.
- A chave unica inclui `tenant_id`, permitindo o mesmo ID externo em empresas
  diferentes sem mistura de dados.
- Logs registram somente tenant e identificador tecnico; conteudo da conversa e
  dados pessoais nao sao adicionados ao log de duplicidade.

## 5. Qualidade e testes

- Replay sequencial coberto.
- Corrida simultanea simulada com `IntegrityError` coberta.
- Mensagens sem ID externo cobertas.
- Migration executada em banco temporario, incluindo limpeza historica, indice,
  bloqueio de nova duplicacao e downgrade.
- Suite completa do WhatsApp: 151 testes aprovados.
- Ruff, compilacao Python, fluxo do repositorio e head unico de migration aprovados.

## 6. Ambientes e homologacao

- Validacao local usa somente dados sinteticos.
- A migration ainda deve passar pelo Migration Smoke do Pull Request.
- Homologacao funcional recomendada antes de producao: enviar duas vezes o mesmo
  ID externo e confirmar uma mensagem salva, uma resposta e um incremento de sessao.

## 7. Publicacao, observabilidade e rollback

- Tipo de mudanca: backend + migration; sem frontend e sem aplicativo mobile.
- Deploy deve usar o fluxo oficial, com backup automatico antes da migration.
- Sinais de sucesso: log de duplicidade sem nova resposta e contagem da sessao
  permanecendo estavel no replay.
- Sinais de aborto: falha ao criar o indice, migration bloqueada por duplicatas ou
  rejeicao de mensagens com IDs distintos.
- Rollback: remover o indice pela migration de downgrade e voltar o backend para a
  versao anterior. Os registros historicos continuam preservados.

## 8. Sustentacao e incidentes

- Duplicidade de resposta ou pedido apos esta protecao deve ser tratada como P1 e
  investigada pelo ID externo, tenant e horario.
- Mensagens sem ID nao podem ser deduplicadas com seguranca; recorrencia nesse canal
  deve levar o provedor/orquestrador a sempre fornecer `external_message_id`.

## 9. Mudanca e treinamento

- Nao ha mudanca visual ou nova rotina para usuarios.
- Operacao deve conhecer o log de duplicidade e preservar o ID externo ao integrar
  novos provedores.

## 10. Fechamento

- [x] Requisito e risco documentados.
- [x] Tenant, privacidade e integridade preservados.
- [x] Testes de replay, concorrencia e migration aprovados.
- [x] Rollback definido.
- [ ] Pull Request e checks remotos aprovados.
- [ ] Deploy de producao autorizado e executado.
