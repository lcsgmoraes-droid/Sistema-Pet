# Catálogo de integrações do Sistema Pet

Atualizado em: 2026-08-26

Status: fonte oficial para conhecer as integrações externas implementadas no
código, seus controles e os modos de falha que precisam ser considerados na
operação e na evolução do produto.

## Como interpretar este catálogo

Este documento descreve capacidade existente no repositório. A presença de uma
integração no código **não comprova que a integração está habilitada em
produção** para uma empresa. O estado efetivo depende da configuração segura do
ambiente, das credenciais e da habilitação por tenant.

As classificações usadas são:

| Estado | Significado |
|---|---|
| Implementada | Existe fluxo executável e protegido por configuração. |
| Condicional | Existe no código, mas só deve ser considerado ativo após habilitação explícita. |
| Arquivo | A comunicação ocorre por arquivo importado, não por API em tempo real. |
| Compatibilidade | Código preservado para um provedor legado ou futuro; não pressupõe uso atual. |

Criticidade indica o impacto potencial de indisponibilidade, e não o estado da
produção:

- **Alta:** pode interromper venda, pedido, pagamento, faturamento ou documento
  fiscal de quem usa a integração;
- **Média:** degrada operação, comunicação, catálogo ou observabilidade, mas há
  caminho manual ou o sistema continua como fonte de verdade;
- **Baixa:** fonte auxiliar ou capacidade opcional, sem efeito transacional
  direto.

## Regra de segurança e responsabilidade

Nunca registrar segredo, token, certificado, senha, chave de API ou dado pessoal
desnecessário neste catálogo, em logs, evidências ou Pull Requests. O catálogo
registra apenas o nome das configurações e o mecanismo usado.

Enquanto não houver equipe técnica formal:

- **responsável de negócio:** responsável de negócio do Sistema Pet, que decide
  prioridade, fornecedor e regra de negócio;
- **responsável técnico:** IA, que analisa, implementa, testa, documenta e
  prepara o Pull Request seguindo os gates do repositório;
- **validação operacional:** usuário autorizado que homologa o comportamento;
- produção continua exigindo autorização explícita e separada.

Uma futura pessoa desenvolvedora assume a responsabilidade técnica sem depender
de conversas privadas: código, Git, CI, este catálogo e os documentos citados
formam a trilha de conhecimento.

## Visão executiva

| ID | Integração | Estado no código | Criticidade | Uso principal |
|---|---|---|---|---|
| INT-001 | Bling | Implementada | Alta | ERP, pedidos, produtos, estoque e notas fiscais. |
| INT-002 | iFood | Condicional | Alta | Pedidos e operações do canal de delivery. |
| INT-003 | SEFAZ NF-e | Condicional | Alta | Consulta e importação de documentos fiscais. |
| INT-004 | Mercado Pago | Condicional | Alta | Checkout e confirmação de pagamento do e-commerce. |
| INT-005 | Asaas | Condicional | Alta | Cobrança das assinaturas do SaaS. |
| INT-006 | WhatsApp, 360dialog e WAHA | Condicional | Média | Atendimento e mensagens por empresa. |
| INT-007 | EcommerceAI | Condicional | Média | Catálogo e eventos entre plataformas. |
| INT-008 | Provedor de IA OpenAI | Condicional | Baixa | Recursos auxiliares com fallback determinístico. |
| INT-009 | E-mail SMTP | Condicional | Média | Mensagens transacionais e alertas. |
| INT-010 | Expo Push | Condicional | Média | Notificações do aplicativo móvel. |
| INT-011 | Google Maps | Condicional | Média | Geocodificação, distância e rotas. |
| INT-012 | Storage S3 compatível | Condicional | Média | Imagens públicas de produtos. |
| INT-013 | Webhook/e-mail de alertas Ops | Condicional | Alta | Avisos externos de degradação operacional. |
| INT-014 | PubMed, DailyMed e VMD | Condicional | Baixa | Evidência clínica e catálogo regulatório. |
| INT-015 | Operadoras e bancos por arquivo | Arquivo | Alta | Conciliação por CSV/OFX. |
| INT-016 | XML/CSV e SimplesVet | Arquivo | Média | Entrada fiscal, produtos e migração controlada. |
| INT-017 | Pagar.me | Compatibilidade | Alta | Webhook de pagamento legado/condicional. |

## Contrato mínimo por integração

Toda integração nova ou alterada deve registrar, antes da homologação:

1. finalidade, dados enviados/recebidos, direção, protocolo e criticidade;
2. **Autenticação e segredos**;
3. **Timeout**;
4. **Retry** e backoff;
5. **Idempotência** e proteção contra replay;
6. **Fallback** ou modo degradado;
7. **Reconciliação** e recuperação após indisponibilidade;
8. **Observabilidade**, correlação, métricas e alertas;
9. **Responsável** de negócio, técnico e de homologação;
10. **Lacuna** conhecida, plano de rollback e teste de falha.

## Integrações transacionais e de operação

### INT-001 — Bling

- **Finalidade e direção:** comunicação bidirecional com o ERP para pedidos,
  produtos, estoque e notas; webhooks entram no Sistema Pet e APIs do Bling são
  chamadas pelo backend.
- **Autenticação e segredos:** OAuth 2.0 com token bearer, credenciais de cliente
  e refresh token fora do Git. Webhooks de pedido e nota validam o cabeçalho
  oficial `X-Bling-Signature-256` por HMAC-SHA256 sobre o corpo bruto usando o
  `BLING_CLIENT_SECRET`. `BLING_WEBHOOK_TENANT_ID` fixa o tenant de destino.
- **Timeout:** chamadas HTTP usam limite de 30 segundos.
- **Retry:** a API renova token expirado e tenta novamente; respostas `429`
  possuem até cinco tentativas com espera progressiva. A fila de pedidos usa
  retry exponencial configurável e seis tentativas por padrão.
- **Idempotência:** a fila usa identificador do evento do provedor ou hash
  SHA-256 canônico do payload; o processamento usa bloqueio de linha para evitar
  concorrência duplicada.
- **Fallback:** se a fila não aceitar o evento, existe fallback síncrono
  configurável; quando desabilitado, a API retorna indisponibilidade sem fingir
  sucesso.
- **Reconciliação:** serviços de reconciliação e monitor da fila permitem
  localizar divergências, eventos pendentes e falhas definitivas.
- **Observabilidade:** correlação por evento/job, estados da fila, contagem por
  tenant e logs operacionais.
- **Responsável:** negócio do ERP pelo responsável do Sistema Pet; execução
  técnica pela IA; homologação pelo operador autorizado da empresa integrada.
- **Lacuna prioritária:** acompanhar rejeições de assinatura, exercitar replay e
  indisponibilidade em homologação e consolidar/aposentar rotas legadas para
  existir uma única entrada oficial.
- **Evidência no código:** `backend/app/bling_integration_parts/core.py`,
  `backend/app/integracao_bling_pedido_routes.py`,
  `backend/app/services/bling_pedido_webhook_queue_service.py`,
  `backend/app/services/bling_sync_reconciliation.py` e
  `backend/app/security/module_access.py`.

### INT-002 — iFood

- **Finalidade e direção:** consulta de eventos e operação de pedidos do iFood;
  escrita de catálogo, operações de pedido e polling possuem flags separadas.
- **Autenticação e segredos:** OAuth por `client_id`/`client_secret`, token em
  cache com margem de expiração e acesso sincronizado.
- **Timeout:** configurável por `IFOOD_REQUEST_TIMEOUT_SECONDS`, padrão de 15
  segundos.
- **Retry:** o polling posterior recupera falhas transitórias; `429` é tratado
  sem vazar resposta sensível, mas ainda não há política central de retry
  exponencial por tipo de chamada.
- **Idempotência:** eventos são persistidos antes do ACK e têm unicidade por
  tenant e identificador iFood; pedidos também são únicos por tenant e pedido.
- **Fallback:** flags permitem manter funcionalidades de escrita desligadas; o
  Sistema Pet conserva o evento não processado para reprocessamento.
- **Reconciliação:** eventos persistidos não processados podem ser retomados por
  tenant sob RLS.
- **Observabilidade:** configuração da loja registra falhas e o polling produz
  logs protegidos pelo contexto do tenant.
- **Responsável:** negócio de delivery pelo responsável do Sistema Pet; execução
  técnica pela IA; homologação por empresa com credencial de teste.
- **Lacuna prioritária:** definir backoff e limite de alerta para rate limit e
  falhas repetidas, além de exercitar recuperação/replay em homologação.
- **Evidência no código:** `backend/app/integrations/ifood/client.py`,
  `backend/app/integrations/ifood/orders.py` e
  `backend/app/integrations/ifood/poller.py`.

### INT-003 — SEFAZ NF-e

- **Finalidade e direção:** consulta documentos destinados ao CNPJ e importa XML
  fiscal para o Sistema Pet.
- **Autenticação e segredos:** certificado A1 em formato PFX e senha fora do Git,
  com CNPJ, UF e ambiente de homologação/produção por configuração.
- **Timeout:** `SEFAZ_TIMEOUT_SECONDS`, mínimo de 10 e padrão de 30 segundos.
- **Retry:** coordenador aplica intervalo adaptativo quando não há documentos,
  penalidade específica para consumo indevido e novo ciclo após erro genérico.
- **Idempotência:** NSU funciona como checkpoint e documentos já importados são
  reconhecidos para não duplicar a entrada.
- **Fallback:** upload manual de XML e modo simulado permitem continuidade
  controlada sem bombardear a SEFAZ.
- **Reconciliação:** sincronização manual, diagnóstico, último NSU e estados da
  configuração permitem recuperar a sequência.
- **Observabilidade:** horários, estado, erro mais recente e próxima execução
  ficam disponíveis para diagnóstico.
- **Responsável:** negócio fiscal pelo responsável do Sistema Pet; execução
  técnica pela IA; homologação por usuário fiscal autorizado.
- **Lacuna prioritária:** alertar centralmente falhas consecutivas e validade do
  certificado, e registrar exercício de recuperação do checkpoint.
- **Evidência no código:** `backend/app/services/sefaz_service.py`,
  `backend/app/services/sefaz_sync_coordinator.py` e
  `backend/app/routes/sefaz_routes.py`.

### INT-004 — Mercado Pago

- **Finalidade e direção:** cria checkout/pagamento e recebe confirmação do
  provedor para o e-commerce.
- **Autenticação e segredos:** OAuth por tenant ou cliente global; tokens
  criptografados; chave exclusiva de criptografia obrigatória em produção.
  Webhook usa token opaco por tenant e assinatura HMAC do Mercado Pago.
- **Timeout:** chamadas principais possuem limite de 20 segundos.
- **Retry:** não há fila durável de retry para falha transitória de chamada
  externa.
- **Idempotência:** registro de evento/chave/hash impede aplicar duas vezes o
  mesmo webhook e detecta conflito de conteúdo.
- **Fallback:** o pedido permanece como fonte de verdade e não é confirmado
  apenas pelo payload recebido; o backend consulta o pagamento real no provedor.
- **Reconciliação:** a consulta ao provedor valida o estado antes da transição;
  falta rotina periódica formal para pagamentos sem confirmação.
- **Observabilidade:** eventos, conflito de idempotência e falhas ficam
  correlacionados ao tenant resolvido pelo token do webhook.
- **Responsável:** negócio de pagamento pelo responsável do Sistema Pet;
  execução técnica pela IA; homologação por operador do e-commerce.
- **Lacuna prioritária:** criar reconciliação agendada, retry seguro para falhas
  transitórias e alerta de pagamentos pendentes além do limite operacional.
- **Evidência no código:** `backend/app/services/mercado_pago_checkout.py`,
  `backend/app/services/ecommerce_payment_config.py` e
  `backend/app/routes/ecommerce_webhooks.py`.

### INT-005 — Asaas

- **Finalidade e direção:** cria/consulta cliente e assinatura do SaaS e recebe
  eventos de cobrança.
- **Autenticação e segredos:** chave da API fora do Git, ambientes sandbox e
  produção separados e token compartilhado do webhook comparado em tempo
  constante.
- **Timeout:** chamadas usam limite de 20 segundos.
- **Retry:** não existe retry automático durável na chamada de cobrança.
- **Idempotência:** recibo do webhook é persistido antes da alteração de estado,
  com unicidade por provedor/evento e hash quando o evento não traz ID.
- **Fallback:** evento duplicado retorna de forma segura; falha fica registrada
  para reenvio pelo provedor ou tratamento controlado.
- **Reconciliação:** cliente é pesquisado por referência externa do tenant e uma
  assinatura existente é reutilizada; ainda falta varredura agendada de estados.
- **Observabilidade:** recibos possuem status e erro; o payload pessoal bruto não
  é preservado no recibo operacional.
- **Responsável:** negócio de assinatura pelo responsável do Sistema Pet;
  execução técnica pela IA; homologação administrativa autorizada.
- **Lacuna prioritária:** adicionar reconciliação programada, fila/retry para
  falhas e alerta para recibos que não terminam com sucesso.
- **Evidência no código:** `backend/app/services/asaas_billing_service.py`,
  `backend/app/routes/asaas_billing_routes.py` e
  `backend/app/billing_models.py`.

### INT-006 — WhatsApp, 360dialog e WAHA

- **Finalidade e direção:** envia e recebe mensagens de atendimento por tenant;
  inclui ponte interna protegida para o orquestrador n8n/WAHA.
- **Autenticação e segredos:** chave de API do 360dialog ou WAHA, segredo de
  webhook por tenant e token interno dedicado, todos fora do Git. A entrada
  aceita HMAC-SHA256 quando o provedor o fornece ou o cabeçalho personalizado
  `X-CorePet-Webhook-Token`, suportado na configuração do 360dialog.
- **Timeout:** envio externo usa limite de 30 segundos.
- **Retry:** processamento recebido pode ocorrer em segundo plano, mas não há
  contrato único de fila durável/retry para toda saída.
- **Idempotência:** mensagens e sessões são persistidas; não foi localizado um
  contrato explícito e único de deduplicação pelo `wamid` para toda entrada.
- **Fallback:** falha externa não deve alterar dados transacionais; o fluxo pode
  encaminhar o atendimento para pessoa e preservar o contexto.
- **Reconciliação:** histórico e sessão ajudam no diagnóstico, porém falta rotina
  formal de replay das mensagens pendentes.
- **Observabilidade:** logs incluem correlação, provedor, tenant e resultado de
  envio sem registrar credenciais.
- **Responsável:** negócio de atendimento pelo responsável do Sistema Pet;
  execução técnica pela IA; homologação por operador autorizado do canal.
- **Lacuna prioritária:** a autenticação agora é fail-closed: segredo ausente
  causa indisponibilidade explícita e token/assinatura ausente ou inválido é
  rejeitado. Ainda
  falta adicionar deduplicação persistente por `wamid`, teste de replay e alerta
  de falha acumulada.
- **Evidência no código:** `backend/app/whatsapp/sender.py`,
  `backend/app/whatsapp/webhook.py` e
  `backend/app/api/whatsapp_orchestrator_internal_routes.py`.

### INT-007 — EcommerceAI

- **Finalidade e direção:** conexão controlada para leitura de catálogo e escrita
  de eventos entre o Sistema Pet e a plataforma externa.
- **Autenticação e segredos:** bootstrap assinado por HMAC com timestamp e nonce;
  origem de callback restrita e HTTPS obrigatório em staging/produção. A conexão
  usa bearer token armazenado somente como hash e escopos mínimos.
- **Timeout:** callback usa limite de 15 segundos.
- **Retry:** nova aprovação pode repetir callback com falha, mas não existe fila
  em segundo plano com backoff exponencial.
- **Idempotência:** nonce é único; evento recebido é único por conexão/ID e
  conflito de hash é rejeitado.
- **Fallback:** falha de callback mantém estado explícito `callback_failed`, sem
  conceder conexão silenciosamente.
- **Reconciliação:** reaprovação permite retomar callback e catálogo é paginado;
  eventos preservam estado processado/erro.
- **Observabilidade:** pedidos de conexão e eventos mantêm estado e identificador
  rastreável.
- **Responsável:** negócio da parceria pelo responsável do Sistema Pet; execução
  técnica pela IA; homologação conjunta com operador autorizado.
- **Lacuna prioritária:** adicionar fila de callback, retry controlado, alerta e
  exercício de replay.
- **Evidência no código:** `backend/app/routes/ecommerceai_integration_routes.py`
  e `backend/app/ecommerceai_integration_models.py`.

## Integrações auxiliares

### INT-008 — Provedor de IA OpenAI

- **Finalidade e direção:** provedor opcional para funções auxiliares de IA; não
  é fonte de verdade para venda, estoque ou finanças.
- **Autenticação e segredos:** chave de API por variável segura.
- **Timeout:** configuração da camada de IA, com padrão de 5 segundos.
- **Retry:** quantidade configurável, com padrão de duas novas tentativas.
- **Idempotência:** não se aplica a decisão transacional; toda função que vier a
  escrever negócio deve criar contrato próprio antes de ser habilitada.
- **Fallback:** engine pode usar resultado simulado/determinístico; falha do
  provedor não autoriza alteração insegura de negócio.
- **Reconciliação:** não aplicável ao uso auxiliar atual.
- **Observabilidade:** latência, tokens, custo e provedor são metadados previstos
  pela engine.
- **Responsável:** produto de IA pelo responsável do Sistema Pet; execução
  técnica pela IA; homologação funcional por usuário autorizado.
- **Lacuna prioritária:** formalizar minimização/retenção dos dados enviados e
  limites de custo e qualidade por funcionalidade antes de ampliar o uso.
- **Evidência no código:** `backend/app/ai/providers/openai_provider.py`,
  `backend/app/ai/engine.py` e `backend/app/ai/settings.py`.

### INT-009 — E-mail SMTP

- **Finalidade e direção:** envio de mensagens transacionais e alertas.
- **Autenticação e segredos:** usuário e senha SMTP fora do Git; STARTTLS exige
  TLS 1.2 e validação de certificado.
- **Timeout:** 10 segundos.
- **Retry:** não há fila durável ou retry central de entrega.
- **Idempotência:** `message_id` e correlação ajudam a rastrear, mas não formam
  garantia de envio único entre novas tentativas.
- **Fallback:** alguns chamadores podem simular envio quando não configurado;
  fluxos críticos devem desabilitar simulação e mostrar falha real.
- **Reconciliação:** não há consulta de bounce/entrega.
- **Observabilidade:** resultado, correlação e identificação da mensagem são
  registrados sem senha.
- **Responsável:** comunicação pelo responsável do Sistema Pet; execução técnica
  pela IA; homologação pelo destinatário de teste autorizado.
- **Lacuna prioritária:** fila de saída, retry, bounce e distinção visível entre
  envio real e simulado em jornadas críticas.
- **Evidência no código:** `backend/app/services/email_service.py`.

### INT-010 — Expo Push

- **Finalidade e direção:** envio de notificações para dispositivos do app.
- **Autenticação e segredos:** token do dispositivo; nenhum segredo deve aparecer
  em log público.
- **Timeout:** chamada HTTPS limitada a 10 segundos.
- **Retry:** falha é registrada, mas não existe política durável única de retry.
- **Idempotência:** não há garantia geral de envio único; a tela do aplicativo e
  o estado do pedido continuam sendo a fonte de verdade.
- **Fallback:** perda de push não altera o pedido; usuário consulta o app.
- **Reconciliação:** resultado/ticket fica associado ao alvo, mas não há polling
  geral de recibos.
- **Observabilidade:** estado enviado, ticket e erro são preservados por alvo.
- **Responsável:** comunicação móvel pelo responsável do Sistema Pet; execução
  técnica pela IA; homologação em dispositivo autorizado.
- **Lacuna prioritária:** consultar recibos, remover tokens inválidos e aplicar
  retry limitado para falhas transitórias.
- **Evidência no código:**
  `backend/app/services/order_push_notifications.py`.

### INT-011 — Google Maps

- **Finalidade e direção:** geocodificação, distância e rota para entregas.
- **Autenticação e segredos:** chave de API fora do Git e restrita no provedor.
- **Timeout:** 15 segundos.
- **Retry:** não há retry ou cache central identificado.
- **Idempotência:** consultas são somente leitura.
- **Fallback:** cálculo/manualização da entrega deve continuar disponível quando
  mapa ou estimativa falhar.
- **Reconciliação:** não se aplica a transação; endereço permanece no Sistema
  Pet.
- **Observabilidade:** erros sobem para o chamador; faltam métricas de quota e
  latência consolidadas.
- **Responsável:** logística pelo responsável do Sistema Pet; execução técnica
  pela IA; homologação por operador de entrega.
- **Lacuna prioritária:** cache seguro, limite de quota, alerta e apresentação
  explícita do modo manual.
- **Evidência no código:** `backend/app/services/google_maps_service.py`.

### INT-012 — Storage S3 compatível

- **Finalidade e direção:** grava e lê imagens públicas de produtos em storage
  compatível com S3; backend local continua disponível por configuração.
- **Autenticação e segredos:** access key/secret fora do Git, região, endpoint,
  owner esperado e bucket configuráveis; assinatura S3 v4.
- **Timeout:** usa a política do cliente Boto; não há limite explícito próprio no
  serviço atual.
- **Retry:** usa o comportamento do SDK, sem política documentada específica do
  produto.
- **Idempotência:** chave contém tenant/produto/token e separa original de
  thumbnail; normalização impede leitura fora do prefixo permitido.
- **Fallback:** `PRODUCT_IMAGE_STORAGE_BACKEND=local` mantém storage local como
  alternativa configurável, sem migração automática entre backends.
- **Reconciliação:** não há inventário periódico banco versus objetos.
- **Observabilidade:** erros do SDK são propagados e 404 é convertido em não
  encontrado; falta health dedicado.
- **Responsável:** catálogo de produtos pelo responsável do Sistema Pet;
  execução técnica pela IA; homologação por usuário de catálogo.
- **Lacuna prioritária:** health, política de timeout/retry, inventário de objetos,
  backup/lifecycle e procedimento testado para trocar backend.
- **Evidência no código:**
  `backend/app/services/product_image_storage.py` e `backend/app/config.py`.

### INT-013 — Webhook/e-mail de alertas Ops

- **Finalidade e direção:** envia alertas técnicos para webhook externo e/ou
  destinatários de e-mail.
- **Autenticação e segredos:** URL do webhook e credenciais SMTP ficam fora do
  Git; payload expõe apenas visão pública/sanitizada do alerta.
- **Timeout:** webhook usa `OPS_ALERT_WEBHOOK_TIMEOUT_SECONDS`, padrão de 5
  segundos; e-mail segue o timeout SMTP.
- **Retry:** uma execução tenta cada canal uma vez; nova coleta pode reenviar o
  que não foi marcado como entregue.
- **Idempotência:** chave de notificação entregue é guardada em log e evita
  reenvio duplicado.
- **Fallback:** webhook e e-mail podem coexistir; sucesso parcial é distinguido
  de sucesso completo e falha total.
- **Reconciliação:** chaves não enviadas continuam elegíveis em execução futura;
  o log local é a memória de deduplicação.
- **Observabilidade:** contadores por canal, falha, duplicata e severidade mínima.
- **Responsável:** operação pelo responsável do Sistema Pet; execução técnica
  pela IA; homologação por destinatário de alerta.
- **Lacuna prioritária:** smoke periódico dos canais e alarme independente para
  detectar quando o próprio mecanismo de alerta falhar.
- **Evidência no código:** `backend/app/services/ops_alert_notifier.py` e
  `backend/app/services/email_service.py`.

### INT-014 — PubMed, DailyMed e VMD

- **Finalidade e direção:** importa fontes públicas de evidência clínica e dados
  regulatórios; não toma decisão clínica automaticamente.
- **Autenticação e segredos:** APIs/arquivos públicos; não há credencial de
  negócio no fluxo atual.
- **Timeout:** PubMed e DailyMed usam 45 segundos por padrão; snapshot VMD usa 90
  segundos.
- **Retry:** jobs posteriores podem repetir a sincronização; não há retry HTTP
  exponencial comum.
- **Idempotência:** fontes e identificadores oficiais alimentam upsert, evitando
  criar novo registro para o mesmo item conhecido.
- **Fallback:** a última base válida permanece disponível se a fonte estiver
  fora; schema inválido deve falhar sem substituir dados confiáveis.
- **Reconciliação:** resumo de sincronização contabiliza inclusão, atualização,
  descarte e erro.
- **Observabilidade:** origem, termos e identificadores oficiais preservam
  rastreabilidade até a fonte.
- **Responsável:** conteúdo veterinário pelo responsável do Sistema Pet;
  execução técnica pela IA; validação de conteúdo por profissional habilitado.
- **Lacuna prioritária:** meta de atualização, alerta de fonte/schema e teste de
  recuperação sem apagar a última base válida.
- **Evidência no código:** `backend/app/services/vet_clinical_evidence.py` e
  `backend/app/services/vet_regulatory_catalog_import.py`.

## Integrações por arquivo

### INT-015 — Operadoras e bancos por CSV/OFX

- **Finalidade e direção:** importa arquivos de adquirentes como Stone, Cielo e
  Rede e extratos bancários OFX para conciliação; não executa pagamento.
- **Autenticação e segredos:** upload exige usuário autenticado, tenant e
  permissão; arquivo é dado sensível e segue retenção/acesso do sistema.
- **Timeout:** não há chamada de rede ao provedor.
- **Retry:** usuário pode corrigir e reenviar arquivo rejeitado.
- **Idempotência:** hashes MD5/SHA-256 detectam arquivo já importado e NSU é
  validado por tenant/operadora para evitar duplicidade.
- **Fallback:** parser informa erro e preserva conciliação manual; não confirma
  transação automaticamente quando a evidência é insuficiente.
- **Reconciliação:** registros importados são comparados e confirmados no fluxo
  de conciliação.
- **Observabilidade:** evidência guarda hashes, tipo, tenant, contagens e erros.
- **Responsável:** financeiro pelo responsável do Sistema Pet; execução técnica
  pela IA; homologação por operador financeiro autorizado.
- **Lacuna prioritária:** manter arquivos de exemplo anonimizados, contrato por
  layout/versão e teste de mudança de coluna de cada operadora suportada.
- **Evidência no código:**
  `backend/app/conciliacao_services_importacao.py`,
  `backend/app/conciliacao_models.py`, `backend/app/parsers/ofx_parser.py` e
  `backend/app/conciliacao_operadora_detector.py`.

### INT-016 — XML/CSV fiscal, produtos e SimplesVet

- **Finalidade e direção:** recebe XML de NF-e, CSV de estoque/produtos e export
  de sistema anterior para carga controlada no Sistema Pet.
- **Autenticação e segredos:** rotas exigem usuário/tenant/permissão; scripts de
  migração usam configuração local segura e não versionam dados reais.
- **Timeout:** processamento de arquivo é local; limites de tamanho e execução
  devem ser definidos por tipo de importação.
- **Retry:** simulação/dry-run e nova execução após correção; não há retry cego.
- **Idempotência:** os fluxos fiscais identificam documento; cada importador deve
  manter sua própria chave natural e evidência de arquivo.
- **Fallback:** rejeição estruturada, correção do arquivo e entrada manual quando
  necessária.
- **Reconciliação:** dry-run, contagens, hashes e recibo são exigidos na migração
  SimplesVet; notas e produtos seguem validação de domínio.
- **Observabilidade:** relatório de erros e resultado da importação sem guardar
  arquivo real no Git.
- **Responsável:** dados/importação pelo responsável do Sistema Pet; execução
  técnica pela IA; homologação pelo proprietário autorizado dos dados.
- **Lacuna prioritária:** unificar limite, idempotência, recibo e amostras
  anonimizadas para todos os importadores, não apenas os mais maduros.
- **Evidência no código:** `backend/app/notas_entrada/xml_parser.py`,
  `backend/app/estoque_importacao_csv_routes.py`,
  `scripts/importar_simplesvet_seguro.ps1` e
  `docs/IMPORTACAO_SIMPLESVET_SEGURA.md`.

## Compatibilidade preservada

### INT-017 — Pagar.me

- **Finalidade e direção:** endpoint compatível com webhook de pagamento. Deve
  ser tratado como legado/condicional até haver decisão explícita de fornecedor.
- **Autenticação e segredos:** assinatura/segredo é exigível conforme a
  configuração do gateway; nunca habilitar sem segredo válido.
- **Timeout:** processamento de entrada não depende de nova consulta obrigatória
  ao provedor no contrato legado atual.
- **Retry:** o provedor pode reenviar; não há fila própria documentada.
- **Idempotência:** chave por evento e hash do request evita repetição e rejeita
  conteúdo conflitante.
- **Fallback:** manter desabilitado quando não for o gateway contratado.
- **Reconciliação:** não há processo atual formalizado para operação ativa.
- **Observabilidade:** recibo e conflito de idempotência são registrados.
- **Responsável:** decisão do gateway pelo responsável do Sistema Pet; execução
  técnica pela IA; homologação obrigatória antes de qualquer ativação.
- **Lacuna prioritária:** decidir entre aposentar o código ou formalizar cliente,
  consulta ao provedor, reconciliação, alertas e testes completos antes do uso.
- **Evidência no código:** `backend/app/routes/ecommerce_webhooks.py`.

## Itens não classificados como integração ativa

- menções em comentários ou rascunhos, como Z-API, não entram como integração
  enquanto não houver caminho executável, configuração, teste e responsável;
- URLs internas entre componentes do próprio Sistema Pet são infraestrutura
  interna, salvo quando atravessam um orquestrador externo já catalogado;
- a existência de variável no `.env.example` não prova ativação no ambiente.

## Ordem de endurecimento recomendada

1. concluir deduplicação/replay do WhatsApp e monitorar rejeições de assinatura
   nos webhooks Bling e WhatsApp;
2. criar reconciliação e alertas de pagamentos/assinaturas para Mercado Pago e
   Asaas;
3. formalizar backoff, fila e recuperação de iFood e EcommerceAI;
4. alertar validade/falha continuada da SEFAZ;
5. consolidar entrega/recibo de e-mail, push e alertas Ops;
6. decidir formalmente pela aposentadoria ou ativação do Pagar.me.

Essas mudanças devem ser pequenas e separadas. Uma integração só avança de
controle documentado para controle comprovado quando houver teste automatizado,
homologação de falha/recuperação e evidência operacional.

## Ativação segura da autenticação de webhook

Esta mudança de segurança precisa de rollout coordenado; merge de código não é
autorização de produção.

1. Em homologação, confirmar que `BLING_CLIENT_SECRET` está disponível ao
   backend e enviar um payload assinado como `X-Bling-Signature-256`.
2. No 360dialog, configurar o cabeçalho `X-CorePet-Webhook-Token` com o mesmo
   segredo forte já cadastrado para o tenant. O valor não entra no Git, URL,
   print ou evidência.
3. Provar no Bling: assinatura válida aceita, cabeçalho ausente rejeitado e
   corpo adulterado rejeitado. Provar no WhatsApp: token válido aceito e token
   ausente ou incorreto rejeitado, sempre por HTTPS.
4. Só então autorizar deploy; acompanhar respostas `403`, `503`, fila e chegada
   de eventos reais durante a janela assistida.
5. Em caso de erro, corrigir primeiro a credencial/configuração do provedor. O
   rollback é voltar ao commit anterior; não deixar validação permanentemente
   desabilitada como atalho.

## Manutenção e revisão

O catálogo deve ser atualizado no mesmo PR que:

- adiciona ou remove provedor, endpoint externo, webhook ou importador;
- muda credencial, escopo, timeout, retry, idempotência ou fallback;
- altera os dados pessoais enviados/recebidos;
- cria job de reconciliação, alerta ou nova dependência operacional;
- habilita em produção uma capacidade antes apenas condicional.

Revisão mínima: trimestralmente e após incidente P0/P1 de integração. O incidente
segue `docs/GESTAO_INCIDENTES_SUSTENTACAO.md`; mudanças relevantes usam
`docs/templates/FICHA_ENTREGA.md` e homologação registrada.
