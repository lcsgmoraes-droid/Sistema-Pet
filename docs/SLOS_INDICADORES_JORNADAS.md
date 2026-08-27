# SLOs e indicadores por jornada

Atualizado em: 2026-08-26

Status: fonte oficial para objetivos internos de confiabilidade, indicadores
técnicos e indicadores de negócio do Sistema Pet.

## Em português simples

O sistema não está saudável apenas porque a página inicial abre. Ele precisa
permitir que cada empresa entre, venda, receba, emita documentos, sincronize
integrações e recupere seus dados com segurança.

Este documento transforma essas jornadas em sinais objetivos:

- **verde:** dentro da meta;
- **amarelo:** risco ou consumo acelerado da margem de erro;
- **vermelho:** meta rompida ou controle crítico indisponível;
- **sem medição:** não há dados suficientes; nunca deve aparecer como verde.

As metas são internas e iniciais. Elas não são SLA contratual, garantia comercial
nem prova de capacidade para 100 ou 1.000 empresas. A aprovação definitiva exige
linha de base real, teste em homologação e aceite do responsável pelo negócio.

## Definições

| Termo | Significado prático |
|---|---|
| Jornada | Resultado que o usuário precisa concluir, como entrar ou finalizar uma venda. |
| SLI | Número observado, por exemplo percentual de vendas finalizadas ou latência p95. |
| SLO | Meta interna para o SLI dentro de uma janela, por exemplo 99,5% em 30 dias. |
| SLA | Compromisso contratual com consequência comercial. Não é definido por este documento. |
| p95 | Tempo abaixo do qual terminaram 95 de cada 100 operações. |
| Orçamento de erro | Parcela de falhas permitida pela meta antes de priorizar confiabilidade. |

Para um SLO mensal de 99,5%, o orçamento máximo teórico é 0,5% do período,
equivalente a aproximadamente 3 horas e 36 minutos em 30 dias. Isso não autoriza
deixar uma falha aberta: incidente P0 continua com resposta imediata.

## Regras de medição

1. Usar janela móvel de 30 dias para SLO e janelas de 5 minutos, 1 hora, 24
   horas e 7 dias para alerta e diagnóstico.
2. Exibir numerador, denominador e quantidade de amostras. Percentual sem volume
   pode esconder uma amostra pequena.
3. Com menos de 100 operações no período, mostrar o resultado como linha de base
   de baixa amostra, não como conformidade estatística.
4. Medir por tenant e no total. A soma nunca deve permitir que um tenant grande
   esconda a falha de um tenant pequeno.
5. Erro do servidor, timeout e resultado inconsistente contam como falha.
   Validação esperada do usuário, senha incorreta e operação deliberadamente
   cancelada não contam, desde que classificadas de forma verificável.
6. Indisponibilidade de fornecedor não desaparece do resultado ponta a ponta.
   Ela é classificada separadamente para mostrar a causa e a contingência.
7. Manutenção programada deve aparecer separada, mas seu impacto real ao usuário
   continua visível.
8. “Sem medição”, telemetria atrasada ou amostra incompleta nunca é “saudável”.
9. Métricas operacionais usam IDs, contagens, tempos e estados. Não devem copiar
   nomes, mensagens, documentos, endereços, valores individuais ou segredos.
10. Toda meta nova registra dono, fonte, fórmula, alerta, resposta e evidência.

## Estado atual da medição

| Capacidade | Estado | Evidência atual | Limite atual |
|---|---|---|---|
| Liveness/readiness/watchdog | Implementado | `/health`, `/ready` e `/health/watchdog` | Watchdog a cada 15 s; 4 falhas; banco degradado acima de 3.000 ms. |
| Erros HTTP e lentidão | Parcial | `ops_error_events`, JSONL e painel Ops por rota/tenant | Persiste 5xx e eventos a partir de 3.000 ms; não possui denominador de todas as requisições. |
| Incidentes por rota/tenant | Implementado | Painel Ops, alertas persistidos e notificação externa opcional | 2 eventos 5xx críticos ou 4 lentos geram limites operacionais padrão. |
| Filas e integrações | Parcial | Fila de webhook Bling e monitor de fluxo/incident | Alerta de fila Bling a partir de 50 pendentes; cobertura não é uniforme entre integrações. |
| Recursos do host | Implementado | Health detalhado e métricas protegidas | CPU, memória ou disco acima de 90% degradam o health detalhado. |
| Backup/restore | Implementado com aprovação pendente | Painel de continuidade e evidência de restore | Backup saudável até 26 h; restore até 31 dias; objetivos configurados de RPO 24 h/RTO 4 h. |
| Ativação de empresa | Implementado | Painel Ops por tenant | Marcos de acesso no dia 1, configuração no dia 3 e operação no dia 7. |
| Sucesso/latência por jornada | Parcial | `ops_journey_events` e JSONL sanitizado medem login, seleção de tenant e finalização de venda no web/app | Falta linha de base, classificação de causa mais fina e cobertura das demais jornadas. |
| Disponibilidade histórica externa | Parcial | Health, watchdog e alertas | Falta série histórica externa consolidada para calcular o percentual mensal. |

Os limites técnicos encontrados no código são guardrails operacionais, não
aprovação de SLA. RPO/RTO permanecem sujeitos a aceite do negócio e teste de
capacidade real, conforme `docs/CATALOGO_DADOS_CRITICOS_LGPD.md`.

## Objetivos técnicos iniciais

| ID | Objetivo interno inicial | Janela | Medição | Estado |
|---|---|---|---|---|
| SLO-PLT-001 | Disponibilidade ponta a ponta do sistema >= 99,5% | 30 dias por tenant e total | Probes externas autenticadas e públicas válidas / probes previstas | Proposto; falta histórico consolidado |
| SLO-PLT-002 | Requisições elegíveis sem 5xx/timeout >= 99,5% | 30 dias por rota, tenant e total | Respostas elegíveis sem falha / todas as respostas elegíveis | Proposto; falta denominador |
| SLO-PLT-003 | Latência das rotas essenciais: p95 <= 1.500 ms e p99 <= 3.000 ms | 24 h e 30 dias | Histograma por família de rota, sem body | Proposto; hoje só eventos lentos >= 3.000 ms são persistidos |
| SLO-DB-001 | Watchdog do banco saudável e latência < 3.000 ms | Contínuo | `/health/watchdog` | Guardrail implementado; meta mensal ainda não calculada |
| SLO-DATA-001 | Incidente confirmado de vazamento cross-tenant, corrupção ou duplicação financeira = 0 | Contínuo | Incidentes, auditoria e testes de contrato | Tolerância zero; qualquer ocorrência é P0 |
| SLO-OPS-001 | Backup válido com idade <= 26 h; restore comprovado nos últimos 31 dias | Contínuo/mensal | Painel de continuidade | Implementado; falta rotina mensal sustentada e aceite de RPO/RTO |
| SLO-DEP-001 | Deploy oficial concluído com health, commit servido e rollback disponível = 100% | Por deploy | Eventos de deploy e checklist | Implementado como gate, não como promessa de ausência de incidente posterior |

### Estado por objetivo

- **Ativo:** fórmula, fonte e alerta produzem evidência real.
- **Proposto:** meta escolhida para orientar a instrumentação e a linha de base.
- **Aprovado:** depois de 30 dias de dados íntegros, teste em homologação e aceite
  registrado pelo negócio.
- **Contratual:** somente por contrato próprio; não é consequência automática de
  um SLO aprovado.

## SLOs por jornada

### JRN-001 — Entrar e acessar a empresa correta

| Item | Definição |
|---|---|
| Resultado bom | Usuário com credencial válida entra, recebe o tenant correto e acessa somente módulos permitidos. |
| SLI de sucesso | Logins válidos concluídos / tentativas válidas. |
| Meta inicial | >= 99,5% em 30 dias; p95 <= 2.000 ms. |
| Falhas que contam | 5xx, timeout, sessão inválida gerada pelo sistema, tenant/permissão incorreta. |
| Exclusões | Senha incorreta, conta legitimamente bloqueada/inativa e validação esperada. |
| Fonte atual | Usuários, sessões, auditoria, último login e erros por rota. |
| Lacuna | Acumular linha de base e atribuir a seleção concluída ao tenant sem confiar em entrada não validada. |
| Dono | Operação técnica e administração SaaS. |

Incidente de acesso a tenant incorreto não espera percentual: é P0 de tolerância
zero.

### JRN-002 — Finalizar venda no PDV

| Item | Definição |
|---|---|
| Resultado bom | Venda válida é finalizada uma única vez com pagamento, estoque e financeiro consistentes. |
| SLI de sucesso | Finalizações válidas atômicas / tentativas válidas de finalizar. |
| Meta inicial | >= 99,5% em 30 dias por tenant; p95 <= 3.000 ms. |
| Indicadores de proteção | Duplicação financeira = 0; estoque negativo indevido = 0; divergência de total = 0. |
| Exclusões | Cancelamento deliberado, falta de estoque validada e dado obrigatório ausente informado ao usuário. |
| Fonte atual | `vendas`, pagamentos, estoque, transações, auditoria e erros por rota. |
| Lacuna | Acumular linha de base e refinar causas esperadas além da categoria HTTP, sem guardar dados da venda. |
| Dono | Operação do tenant e engenharia. |

Valor da venda, itens e identidade do cliente não entram na telemetria de SLO.

### JRN-003 — Criar e receber pedido do ecommerce/app

| Item | Definição |
|---|---|
| Resultado bom | Pedido válido é aceito uma única vez, pagamento recebe estado rastreável e a loja consegue processá-lo. |
| SLI de sucesso | Pedidos válidos aceitos sem duplicidade / tentativas válidas. |
| Meta inicial | >= 99,0% em 30 dias; 99% dos pedidos aceitos visíveis à operação em até 2 minutos. |
| Proteção | Efeito duplicado = 0; perda silenciosa = 0. |
| Fonte atual | Pedidos, pagamentos ecommerce, idempotência, notificações e erros. |
| Lacuna | Correlation ID ponta a ponta e métrica de tempo entre aceite, pagamento e visibilidade. |
| Dono | Ecommerce, operação do tenant e dono do gateway. |

Falha do gateway continua contando na visão do cliente e ganha uma segunda
classificação “fornecedor” para permitir contingência e cobrança do provedor.

### JRN-004 — Emitir documento fiscal

| Item | Definição |
|---|---|
| Resultado bom | Solicitação válida recebe estado definitivo rastreável, sem emissão duplicada. |
| SLI de sucesso | Solicitações válidas com estado definitivo / solicitações aceitas. |
| Meta inicial | >= 99,0% em 30 dias; 95% com estado definitivo em até 15 minutos. |
| Proteção | Documento fiscal duplicado = 0; perda de XML/protocolo confirmado = 0. |
| Fonte atual | Venda, status NF-e/NFC-e, XML, SEFAZ/Bling e monitor de fluxo. |
| Lacuna | Evento comum entre envio, retorno, retry, contingência e reconciliação. |
| Dono | Responsável fiscal do tenant, contador e dono técnico da integração. |

Rejeição correta causada por cadastro fiscal inválido não é erro técnico, mas
continua sendo indicador de negócio e deve ter causa acionável para o tenant.

### JRN-005 — Processar integração e webhook

| Item | Definição |
|---|---|
| Resultado bom | Evento autêntico é aceito, processado uma única vez, reconciliado e rastreável. |
| SLI de sucesso | Eventos aceitos que chegam ao estado terminal correto / eventos autênticos aceitos. |
| Meta inicial | >= 99,0% em 30 dias; 99% concluídos em até 5 minutos. |
| Proteção | Efeito de negócio duplicado = 0; webhook sem autenticação aceito = 0. |
| Fonte atual | Filas, idempotência, monitor Bling, incidentes e catálogo de integrações. |
| Alerta inicial | Item mais antigo > 5 min, crescimento contínuo ou fila >= 50; ajustar após a linha de base. |
| Lacuna | Instrumentação uniforme em todas as integrações e teste de replay/indisponibilidade. |
| Dono | Dono funcional e dono técnico definidos em `docs/CATALOGO_INTEGRACOES.md`. |

### JRN-006 — Ativar uma nova empresa

| Item | Definição |
|---|---|
| Resultado bom | Empresa acessa, possui cadastro mínimo e realiza a primeira operação sem alerta crítico. |
| SLI | Empresas que cumprem cada marco / empresas iniciadas elegíveis. |
| Metas iniciais | Dia 1: acesso confirmado em 100%; dia 3: configuração em >= 90%; dia 7: primeira operação sem erro 5xx/alerta crítico em >= 85%. |
| Fonte atual | Painel Ops por tenant: acesso, registros de setup, vendas/agenda, erros 7d e alertas. |
| Regra de amostra | Com poucos tenants, sempre exibir “2 de 3”, não apenas “66,7%”. |
| Lacuna | Registrar motivo de atraso, responsável, data de desbloqueio e satisfação inicial. |
| Dono | Onboarding/comercial e administrador do tenant. |

Os marcos de dia 1, 3 e 7 já existem no serviço operacional. A porcentagem é uma
meta interna de processo, não obrigação automática do cliente.

### JRN-007 — Atender solicitação de privacidade

| Item | Definição |
|---|---|
| Resultado bom | Pedido validado é registrado, tratado no tenant correto e respondido com evidência, sem dado de terceiros. |
| SLI de registro | Solicitações recebidas e registradas / solicitações conhecidas. |
| Meta inicial | Registro = 100%; solicitações vencidas = 0; vazamento na resposta = 0. |
| Prazo | A aplicação usa meta operacional inicial de 15 dias; depende de validação jurídica por tipo/controlador. |
| Fonte atual | Solicitações LGPD, status, `due_at`, dossiê, anonimização e logs de acesso. |
| Lacuna | Cobrir todos os tipos de titular e medir entrada por canais externos. |
| Dono | Responsável formal por privacidade, ainda a nomear. |

### JRN-008 — Recuperar o sistema e os dados

| Item | Definição |
|---|---|
| Resultado bom | Backup íntegro é restaurado em ambiente isolado e as jornadas críticas voltam sem corrupção. |
| Guardrails atuais | Backup com idade <= 26 h; restore smoke <= 31 dias; SHA-256 obrigatório antes do restore; duração medida; cópia externa verificada quando configurada. |
| Objetivos configurados | RPO 24 h e RTO 4 h. São propostas operacionais, ainda sem aceite/SLA. |
| Fonte atual | Eventos de backup, checksum, duração do restore, cópia externa e painel Ops. |
| Lacuna | Medir a retomada das jornadas, arquivos fora do banco e filas pós-restore; sustentar a evidência recorrente no servidor. |
| Dono | Operação técnica e responsável do negócio pela continuidade. |

## Indicadores de negócio

Indicadores de negócio explicam adoção e valor; eles não substituem SLO técnico.

| ID | Indicador | Fórmula/visão | Frequência | Fonte atual | Cuidado |
|---|---|---|---|---|---|
| KPI-001 | Empresas por estágio | `pending`, `ready`, `active`, `blocked`, com quantidade absoluta | Diário/semanal | Painel Ops de tenants | Não esconder empresa bloqueada na média total. |
| KPI-002 | Tempo até primeiro valor | Dias entre ativação e primeira venda/agenda/consulta | Semanal | Tenant e eventos operacionais | Separar atraso técnico, operacional e do cliente. |
| KPI-003 | Empresas ativas | Tenants com login ou operação nos últimos 7/30 dias | Semanal/mensal | Último login, venda, agenda e consulta | Atividade não mede satisfação sozinha. |
| KPI-004 | Saúde da venda | Finalizadas, canceladas e taxa de cancelamento por tenant | Diário/semanal | Vendas | Exibir contagem; não enviar valor individual para telemetria. |
| KPI-005 | Saúde fiscal | Autorizações, rejeições, pendências e idade da pendência | Diário | Status fiscal/monitor | Separar erro técnico de cadastro rejeitado corretamente. |
| KPI-006 | Saúde de integrações | Sucesso, falha, retry, backlog, idade e reconciliação | Contínuo/diário | Filas e eventos de integração | Comparar por provedor e tenant sem payload. |
| KPI-007 | Incidentes por empresa | P0-P3, MTTD, MTTA, MTTR e recorrência | Mensal | Gestão de incidentes/painel Ops | Poucos incidentes podem indicar subnotificação. |
| KPI-008 | Privacidade | Recebidas, vencidas, concluídas e tempo de resolução | Mensal | Solicitações LGPD | Sem nome/contato no painel agregado. |
| KPI-009 | Continuidade | Idade do backup, restore, cópia externa e sucesso de deploy | Diário/mensal | Painel de continuidade/deploy | Verde exige evidência recente, não mera configuração. |

Indicadores financeiros detalhados continuam dentro de cada tenant. A operação
SaaS deve usar agregados mínimos para confiabilidade e suporte, com acesso
restrito; não deve criar um repositório paralelo de dados comerciais.

## Orçamento de erro e decisão de release

Para cada SLO percentual aprovado:

| Consumo do orçamento em 30 dias | Estado | Ação |
|---:|---|---|
| < 50% | Verde | Evolução normal, mantendo os gates. |
| 50% a < 80% | Amarelo | Analisar tendência, rota/tenant/provedor e corrigir causa recorrente. |
| 80% a < 100% | Laranja | Reduzir mudanças de risco no domínio e priorizar confiabilidade. |
| >= 100% | Vermelho | Bloquear release não essencial que aumente risco; abrir problema estrutural e plano de recuperação. |

Tolerância zero, P0, incidente de segurança, corrupção, cross-tenant ou duplicação
financeira bloqueia release independentemente do orçamento restante.

## Alertas e resposta

| Sinal | Severidade inicial | Resposta |
|---|---|---|
| Health/watchdog falhou repetidamente | P0/P1 conforme alcance | Confirmar alcance, banco/host, acionar recuperação e validar jornada. |
| 2 ou mais 5xx por tenant/rota na janela atual | P1 inicial | Correlacionar request IDs, tenant e deploy; abrir alerta persistido. |
| 4 ou mais requisições >= 3 s por tenant/rota | P2 inicial | Medir p95 real, banco e query; não assumir indisponibilidade. |
| Fila >= 50 ou item mais antigo > 5 min | P1/P2 | Suspender retry agressivo, verificar provedor, reconciliar e evitar duplicidade. |
| Backup > 26 h ou última tentativa falhou | P0/P1 | Proteger banco, corrigir backup e validar restore conforme autorização. |
| Restore > 31 dias ou cópia externa ausente | P2 | Agendar teste controlado e registrar evidência. |
| Empresa `blocked` ou marco atrasado | P1/P2 de onboarding | Registrar causa, responsável e próxima ação, sem alterar dados às cegas. |
| Solicitação LGPD vencida | P1 de processo | Escalar ao responsável por privacidade e registrar decisão. |

Os níveis finais seguem `docs/GESTAO_INCIDENTES_SUSTENTACAO.md` e dependem do
impacto real, não apenas do número bruto.

## Plano de implantação da medição

### P0 — tornar os percentuais calculáveis

1. Criar evento sanitizado por jornada com:
   `journey`, `operation_id`, `tenant_id`, `started_at`, `duration_ms`, `outcome`,
   `reason_code`, `provider` e `request_id`. **Implementado para login, seleção
   de tenant e finalização de venda**, usando o instante terminal `created_at`.
2. Coletar toda tentativa elegível, não apenas erro 5xx ou lentidão.
   **Implementado nas três rotas iniciais; falta ampliar para as outras
   jornadas.**
3. Criar contadores e histogramas por jornada/tenant, com cardinalidade limitada
   e sem nome, e-mail, documento, conteúdo, valor ou segredo.
4. Consolidar probe externa e série histórica para disponibilidade.

### P1 — linha de base e alertas

5. Executar 30 dias de linha de base, validando perda/duplicidade de telemetria.
6. Mostrar numerador, denominador, amostra e “sem medição” no painel Ops.
7. Ativar alertas de burn rate e fila/idade, começando com notificação restrita.
8. Revisar falsos positivos e ajustar meta somente com evidência registrada.

### P2 — aprovação e capacidade

9. Aprovar os SLOs internos com o responsável do negócio.
10. Rodar jornadas autenticadas em homologação e comparar p95/p99, banco e
    integração com a linha de base.
11. Só então definir faixa segura de empresas/carga e avaliar SLA comercial.

## Gate de manutenção

Toda nova jornada crítica precisa entrar neste documento e responder:

1. qual resultado o usuário considera concluído;
2. o que conta como tentativa válida, sucesso, falha e exclusão;
3. qual é a meta, janela e amostra mínima;
4. onde está a fonte e como detectar telemetria ausente;
5. quem responde e qual alerta é acionado;
6. quais dados são proibidos na métrica;
7. como testar em homologação sem usar produção como laboratório.

## Evidências no repositório

- Health e métricas protegidas: `backend/app/health_router.py`.
- Logging HTTP sanitizado: `backend/app/middlewares/request_logging.py`.
- Eventos de erro/lentidão: `backend/app/services/error_event_reporter.py`.
- Painel Ops: `backend/app/services/ops_dashboard_service.py`.
- Alertas por rota/tenant:
  `backend/app/services/ops_dashboard_actionable_alerts.py`.
- Continuidade: `backend/app/services/ops_continuity_service.py`.
- Ativação de empresas: `backend/app/services/ops_tenants_service.py`.
- Capacidade segura: `docs/TESTE_CAPACIDADE_SEGURO.md`.
- Incidentes: `docs/GESTAO_INCIDENTES_SUSTENTACAO.md`.
- Dados/LGPD: `docs/CATALOGO_DADOS_CRITICOS_LGPD.md`.
- Integrações: `docs/CATALOGO_INTEGRACOES.md`.

