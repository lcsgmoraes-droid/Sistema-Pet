# Ficha de entrega — segurança dos webhooks prioritários

## Identificação

| Campo | Valor |
|---|---|
| Título | Autenticação fail-closed de webhooks Bling e WhatsApp |
| Data | 2026-08-26 |
| Responsável de negócio | Responsável pelo Sistema Pet |
| Executor técnico | IA |
| Issue/PR | Branch `fix/20260826-1559-seguranca-webhooks-prioritarios`; PR registrado no GitHub |
| Prioridade | P1 |
| Risco | Médio: rejeita eventos sem autenticação e exige rollout coordenado com o provedor |
| Domínios afetados | Integração Bling e atendimento WhatsApp |

## 1. Necessidade e requisitos

- Problema: endpoints públicos aceitavam evento Bling sem comprovar origem e o
  WhatsApp aceitava cabeçalho ausente em algumas configurações.
- Usuários afetados: empresas que habilitarem Bling ou WhatsApp.
- Resultado esperado: somente eventos autenticados chegam ao processamento.
- Requisitos funcionais:
  - validar `X-Bling-Signature-256` sobre o corpo bruto antes do handler;
  - aceitar no WhatsApp HMAC compatível ou token secreto configurado como
    cabeçalho personalizado no 360dialog;
  - falhar explicitamente quando o segredo não estiver configurado;
  - preservar payload, fila, processamento e respostas após autenticação válida.
- Requisitos não funcionais: comparação em tempo constante, nenhum segredo em
  log, validação antes de parse/persistência e compatibilidade com o contrato
  oficial de cada provedor.
- Comportamentos preservados: fila e deduplicação do Bling, processamento de NF,
  sessões/mensagens WhatsApp e contexto por tenant.
- Fora do escopo: deduplicação persistente por `wamid`, replay operacional,
  alertas por limiar e deploy.
- Critérios de aceite:
  - evento corretamente autenticado é aceito pela barreira;
  - assinatura/token ausente ou inválido recebe `403`;
  - segredo ausente recebe `503`;
  - alteração de um byte invalida a assinatura Bling;
  - rotas de pedido e NF usam a mesma dependência de segurança;
  - testes existentes das áreas continuam passando.

## 2. Regras de negócio e dados

- Nenhuma regra comercial, entidade ou dado de negócio foi alterado.
- O segredo do Bling permanece fora do Git e o segredo WhatsApp continua por
  tenant.
- Não há migration, mudança de retenção ou cópia de dados.
- O isolamento por tenant ocorre somente depois da autenticação da origem.

## 3. Arquitetura e integrações

- Foi criado um serviço único de verificação Bling, compartilhado por pedido e
  NF, usando o mesmo client secret do OAuth.
- A validação usa o corpo HTTP bruto; parse e persistência ocorrem depois.
- Para 360dialog, o token estático em cabeçalho personalizado foi escolhido por
  ser um recurso documentado do provedor. HMAC continua disponível para conexão
  direta compatível.
- Timeout, retry, idempotência, fallback e reconciliação existentes não mudam.
- Quando credencial externa estiver ausente ou incorreta, o endpoint falha
  fechado e o provedor pode repetir conforme sua política; não há processamento
  parcial silencioso.

## 4. Segurança e privacidade

- Autenticação Bling: HMAC-SHA256 oficial, prefixo `sha256=` e comparação em
  tempo constante.
- Autenticação WhatsApp: token estático em comparação de tempo constante ou
  HMAC-SHA256 válido.
- Nenhum valor de segredo, corpo ou dado pessoal é registrado ao rejeitar.
- Risco residual: um token estático depende de HTTPS e rotação segura; o rollout
  precisa configurar o cabeçalho no 360dialog antes do deploy.
- Não há nova finalidade ou retenção de dado pessoal.

## 5. Desenvolvimento e qualidade

- Fatia 1: catálogo e risco formalizados no PR anterior.
- Fatia 2: serviço Bling, barreiras de rota e autenticação WhatsApp.
- Testes unitários/de contrato cobrem validade, ausência, adulteração,
  configuração ausente e uso da dependência nas duas rotas Bling.
- Regressão focada: 42 testes aprovados em 2026-08-26.
- Validação final focada: 16 testes aprovados, Ruff sem falhas, estrutura do
  repositório OK e `git diff --check` sem erro.

## 6. Ambientes e homologação

- Ambiente usado: DEV controlado, sem segredo ou dado real.
- Dependências externas: HMAC e headers simulados localmente.
- Homologação real: pendente e obrigatória antes de produção, conforme a seção
  “Ativação segura da autenticação de webhook” em
  `docs/CATALOGO_INTEGRACOES.md`.
- Pendência aceita para merge: não há chamada real a Bling/360dialog nesta
  branch. Isso bloqueia deploy, não bloqueia integração do código protegido.

## 7. Publicação e rollback

- Tipo: backend, segurança e documentação; sem frontend, mobile ou migration.
- Compatibilidade: evento autenticado mantém o contrato; evento inseguro passa a
  ser rejeitado intencionalmente.
- Ordem futura:
  1. configurar/testar os headers nos provedores em ambiente controlado;
  2. registrar homologação;
  3. pedir autorização explícita de produção;
  4. publicar e executar smoke válido/inválido;
  5. monitorar rejeições e filas.
- Critério de aborto: integração oficial não envia o header esperado, aumento
  inesperado de `403/503` ou parada de eventos válidos.
- Rollback: reverter o commit desta entrega e restaurar a versão anterior; nunca
  registrar segredos como tentativa de diagnóstico.

## 8. Observabilidade e sustentação

- Logs esperados: configuração ausente ou autenticação inválida, sem valor do
  segredo e sem payload.
- Sucesso: eventos válidos continuam chegando e eventos de teste inválidos são
  rejeitados antes da fila/processamento.
- Incidente aplicável: P1 se bloquear operação integrada relevante; P0 apenas se
  houver parada crítica ampla sem alternativa operacional.
- Alternativa segura: operação/manualização existente enquanto a configuração é
  corrigida; não liberar endpoint inseguro.
- Recorrência vira melhoria estrutural quando exigir rotação automática,
  métricas por provedor ou gateway dedicado.

## 9. Mudança, comunicação e treinamento

- Não há mudança visível na interface ou rotina comum do usuário.
- Operação precisa conhecer a ordem de configuração, teste e rollback.
- Não exige material de treinamento ao cliente nesta fase.

## 10. Fechamento

- [x] Critérios técnicos de aceite atendidos.
- [x] Testes e evidências locais registrados.
- [x] Tenant, permissões, dados e auditoria preservados.
- [x] Documentação oficial atualizada.
- [ ] Homologação externa registrada — obrigatória antes do deploy.
- [x] Publicação, observabilidade e rollback definidos.
- [x] Comunicação/treinamento avaliados.
- [x] PR revisável, sem segredo, backup, dump ou artefato indevido.

Decisão final: aprovado para merge com deploy bloqueado até homologação externa
e autorização explícita de produção.

Pendências: deduplicação persistente do WhatsApp em tarefa posterior; homologação
assistida Bling/360dialog antes de qualquer publicação.
