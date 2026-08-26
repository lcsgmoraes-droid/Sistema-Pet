# Catálogo de dados críticos e inventário LGPD

Atualizado em: 2026-08-26

Status: fonte técnica e operacional oficial para localizar os principais grupos
de dados do Sistema Pet, sua criticidade, controles existentes e decisões ainda
pendentes.

## Limite deste documento

Este catálogo é um inventário técnico, não um parecer jurídico, contábil ou uma
certificação de conformidade. Ele descreve o que foi encontrado no código e na
documentação. A presença de uma funcionalidade no código não comprova que ela
esteja configurada, exercitada ou aprovada para todos os tenants em produção.

As finalidades e hipóteses legais abaixo são propostas para validação. O
responsável pelo negócio deve aprová-las com apoio jurídico e contábil
qualificado, por operação de tratamento, antes que sejam tratadas como decisão
definitiva. Consentimento não deve ser usado como fundamento genérico quando
outra hipótese for a adequada. Legítimo interesse exige avaliação própria e não
é uma autorização automática.

Referências oficiais:

- LGPD compilada no Planalto:
  https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm
- Direitos dos titulares, ANPD:
  https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares
- Guia da ANPD sobre agentes de tratamento e encarregado:
  https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-para-definicoes-dos-agentes-de-tratamento-de-dados-pessoais-e-do-encarregado
- Guia de segurança da ANPD para agentes de pequeno porte:
  https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-publica-guia-de-seguranca-para-agentes-de-tratamento-de-pequeno-porte

## Como ler o catálogo

### Classificação de acesso

| Classe | Uso esperado | Exemplos |
|---|---|---|
| Público | Pode ser publicado de forma intencional. | Nome comercial, catálogo público e política de privacidade. |
| Interno | Uso operacional sem dado pessoal relevante. | Configuração de tela e classificação interna de produto. |
| Confidencial | Dado comercial ou operacional limitado ao tenant e funções autorizadas. | Custos, margem, estoque e relatórios financeiros. |
| Pessoal restrito | Dado de pessoa natural ou conteúdo privado. | CPF, telefone, endereço, IP e mensagens. |
| Segredo restrito | Credencial ou material que permite acesso. | Senha, token, chave de API, certificado e segredo de webhook. |

Senha, token, chave, certificado e segredo nunca devem aparecer em log, captura,
evidência, PR, documento ou repositório. Hash de senha continua sendo dado de
acesso restrito.

### Criticidade operacional

| Nível | Efeito de indisponibilidade, perda ou corrupção |
|---|---|
| C1 — crítico | Interrompe acesso, venda, financeiro, fiscal ou compromete isolamento/segurança. |
| C2 — importante | Prejudica atendimento, operação, integração ou rastreabilidade, mas admite contingência curta. |
| C3 — apoio | Pode ser reconstruído ou adiado sem parar as jornadas essenciais. |

Criticidade não é sinônimo de dado pessoal: um saldo financeiro pode ser C1 e
confidencial; um telefone pode ser pessoal restrito e C2.

### Estado das decisões

- **Implementado:** há código, configuração versionada ou procedimento e
  evidência localizável.
- **Proposto:** direção técnica razoável, ainda dependente de aceite do negócio,
  jurídico, contador ou teste operacional.
- **Pendente:** não há decisão ou evidência suficiente; não deve ser prometido
  como controle concluído.

## Papéis e responsabilidade

Os papéis da LGPD são definidos por operação de tratamento, e não apenas pelo
nome da empresa ou do software. A mesma organização pode ter papéis diferentes
em tratamentos diferentes.

| Escopo | Direção atual | Decisão pendente |
|---|---|---|
| Dados de clientes, pets, vendas e operação da loja | A empresa usuária normalmente determina finalidade e uso; a plataforma executa funcionalidades contratadas. | Contrato e análise por tratamento devem confirmar quando cada parte atua como controlador, operador ou controlador conjunto. |
| Conta SaaS, cobrança da assinatura, segurança e prevenção a fraude da própria plataforma | A operação da plataforma pode determinar finalidades próprias. | Formalizar no contrato e na política a responsabilidade da empresa mantenedora. |
| Integrações escolhidas pelo tenant | O tenant autoriza e configura o serviço; a plataforma transmite o mínimo necessário. | Registrar subprocessadores, contratos, local de tratamento, transferência internacional e retenção de cada fornecedor. |
| Decisão de negócio | Responsável pela empresa/tenant. | Nomear formalmente responsáveis por aprovar finalidade, acesso, retenção e descarte. |
| Execução técnica | IA ou pessoa desenvolvedora seguindo PR, CI, auditoria e autorização de produção. | Uma decisão jurídica não pode ser tomada apenas pela execução técnica. |
| Canal de privacidade | Existe contato público na política do sistema. | Confirmar identidade, atribuições e publicidade do encarregado ou canal responsável aplicável. |

Nenhuma pessoa de suporte ou desenvolvimento recebe acesso amplo por padrão.
Todo acesso extraordinário deve ter necessidade, menor escopo possível,
autorização e evidência auditável.

## Inventário executivo

| ID | Domínio | Titulares ou partes relacionadas | Classificação / criticidade | Fonte principal | Responsável funcional proposto |
|---|---|---|---|---|---|
| DAD-001 | Tenant, empresa e contrato SaaS | Representante, administrador e contatos da empresa | Pessoal restrito + confidencial / C1 | Banco principal e configuração do tenant | Administração SaaS e responsável da empresa |
| DAD-002 | Usuários, autenticação, sessões e permissões | Usuários internos e administradores | Pessoal restrito; credenciais como segredo restrito / C1 | `users`, sessões, dispositivos e autorização | Administração SaaS e administrador do tenant |
| DAD-003 | Clientes, tutores e contatos | Clientes finais, responsáveis e parceiros pessoa física | Pessoal restrito / C1 | `clientes` | Empresa usuária |
| DAD-004 | Pets, agenda e prontuário veterinário | Tutor vinculado; profissionais responsáveis pelo registro | Pessoal restrito por vínculo e confidencial clínico / C1 | `pets`, agenda e módulos veterinários | Empresa usuária e responsável técnico veterinário |
| DAD-005 | Vendas, pedidos, pagamentos e entregas | Cliente, vendedor, entregador e recebedor | Pessoal restrito + confidencial / C1 | Vendas, pedidos, pagamentos e rotas | Empresa usuária |
| DAD-006 | Financeiro, caixa, conciliação, DRE e comissões | Usuários, funcionários, parceiros e fornecedores vinculados | Confidencial; pessoal quando vinculado / C1 | Módulos financeiro, caixa e conciliação | Responsável financeiro do tenant |
| DAD-007 | Produtos, estoque, compras e fornecedores | Contatos de fornecedor quando pessoa natural | Interno/confidencial; eventualmente pessoal / C1 | Catálogo, estoque, compras e importações | Operação/compras do tenant |
| DAD-008 | Funcionários, parceiros e remuneração | Funcionários, prestadores, vendedores e entregadores | Pessoal restrito + confidencial / C1 | Cadastros, cargos, comissões e acertos | Responsável administrativo/RH do tenant |
| DAD-009 | Ecommerce, app, notificações e dispositivos | Cliente do ecommerce e usuário do app | Pessoal restrito / C1 | Pedidos, conta ecommerce, dispositivos e push | Empresa usuária |
| DAD-010 | WhatsApp, campanhas e atendimento | Cliente, contato e atendente | Pessoal restrito e conteúdo privado / C2 | Banco, provedor de mensagens e filas | Empresa usuária |
| DAD-011 | Fiscal, XML e SEFAZ | Emitente, destinatário, fornecedor e responsáveis | Pessoal restrito + confidencial fiscal / C1 | Banco, XML, SEFAZ e Bling quando configurado | Responsável fiscal/contador do tenant |
| DAD-012 | Integrações, webhooks e identificadores externos | Depende do payload transmitido | Herdada do dado; credenciais como segredo restrito / C1 | Banco, ambiente e fornecedores externos | Dono funcional da integração |
| DAD-013 | Auditoria, segurança e observabilidade | Usuários, clientes e agentes associados ao evento | Pessoal restrito + confidencial / C1 | Banco, JSONL, containers, proxy e host | Administração SaaS/operação técnica |
| DAD-014 | IA, sugestões e evidências clínicas externas | Usuário, cliente/tutor e profissional conforme o conteúdo enviado | Pessoal restrito se houver conteúdo identificável / C2 | Banco e provedor externo quando habilitado | Dono funcional do módulo e responsável técnico |
| DAD-015 | Preferências, consentimentos e solicitações LGPD | Titular e pessoa solicitante | Pessoal restrito / C1 | Tabelas LGPD e trilha de acesso | Responsável por privacidade do tenant/plataforma |
| DAD-016 | Backups, exports, imports e arquivos temporários | Todos os titulares presentes na origem | Maior classificação contida no conjunto / C1 | Backup privado, exportação autorizada e arquivos controlados | Operação técnica e dono do dado |

## Detalhamento por domínio

### DAD-001 — Tenant, empresa e contrato SaaS

- **Dados:** razão/nome comercial, CNPJ, endereço, contatos, plano, módulos,
  configurações gerais e fiscais, aceite de contrato e cobrança da assinatura.
- **Finalidade proposta:** criar e operar a conta empresarial, habilitar módulos,
  prestar suporte, cobrar o serviço e cumprir obrigações contratuais/fiscais.
- **Hipótese a validar:** execução de contrato e obrigação legal; contatos de
  representantes exigem definição contratual e aviso de privacidade.
- **Controles existentes:** segregação por `tenant_id`, permissões, migrations,
  contrato/versionamento e trilha Git.
- **Retenção:** conta ativa e período posterior justificado por obrigação,
  cobrança e defesa de direitos; prazo definitivo pendente.
- **Lacunas:** formalizar proprietário do cadastro, encerramento do tenant,
  exportação, bloqueio, descarte e retenção pós-contrato.

### DAD-002 — Usuários, autenticação, sessões e permissões

- **Dados:** nome, e-mail, telefone, CPF/CNPJ quando informado, hash de senha,
  OAuth, MFA, códigos de recuperação, tokens temporários, IP, user-agent,
  tentativas de login, sessões, permissões e tokens de dispositivo.
- **Finalidade proposta:** autenticar, autorizar, recuperar acesso, proteger a
  conta, auditar e enviar notificações operacionais.
- **Hipótese a validar:** contrato, legítimo interesse após avaliação para
  segurança/prevenção a fraude e, quando aplicável, obrigação legal.
- **Controles existentes:** senha por hash, expiração/revogação de sessão,
  verificação de e-mail, MFA, bloqueio por tentativas, RBAC e auditoria.
- **Retenção:** sessão até expiração/revogação; demais prazos precisam de matriz
  aprovada. Tokens e segredos revogados não devem permanecer indefinidamente.
- **Direitos:** o fluxo de solicitação possui modelo genérico, mas a automação de
  dossiê/anonimização atual cobre diretamente clientes, não todos os usuários.
- **Lacunas:** revisar proteção dos segredos MFA/códigos de backup e completar
  acesso, correção e descarte para usuários internos.

### DAD-003 — Clientes, tutores e contatos

- **Dados:** nome, CPF/CNPJ, e-mail, telefones, nascimento, endereços, crédito,
  observações, alertas de PDV, histórico, preferências e vínculos com pets.
- **Finalidade proposta:** cadastro, atendimento, venda, entrega, crédito,
  relacionamento e execução dos serviços solicitados.
- **Hipótese a validar:** contrato/procedimentos preliminares, obrigação legal,
  proteção do crédito quando cabível e consentimento para marketing opcional.
- **Controles existentes:** escopo por tenant/RLS, permissões, preferências,
  histórico de consentimento, dossiê/exportação, solicitações e anonimização.
- **Retenção:** cadastro ativo enquanto necessário à relação; históricos fiscais
  e transacionais podem exigir conservação com anonimização do cadastro.
- **Lacunas:** aprovar prazo por campo/finalidade e garantir que observações livres
  não recebam dados excessivos.

### DAD-004 — Pets, agenda e prontuário veterinário

- **Dados:** identificação do pet, foto, microchip, tutor, nascimento, peso,
  alergias, condições, medicamentos, histórico, exames e atendimentos.
- **Enquadramento:** dados do animal não são automaticamente dados pessoais
  sensíveis de uma pessoa natural. O vínculo com tutor, profissional, atendimento
  e conteúdo livre pode conter dado pessoal; por prudência recebe acesso restrito
  e confidencialidade clínica.
- **Finalidade proposta:** identificação do animal, agendamento, prestação e
  continuidade do atendimento veterinário.
- **Hipótese a validar:** relação contratual com o tutor e obrigações profissionais
  e regulatórias aplicáveis. Não presumir “tutela da saúde” humana sem análise.
- **Controles existentes:** vínculo ao tenant/tutor; anonimização do cliente
  também anonimiza pets e remove foto local vinculada.
- **Retenção:** prazo clínico/profissional pendente de validação com responsável
  técnico e jurídico; legal hold prevalece quando aplicável.
- **Lacunas:** inventariar arquivos de exames, storage externo, downloads e
  obrigação de prontuário por tipo de atendimento.

### DAD-005 — Vendas, pedidos, pagamentos e entregas

- **Dados:** cliente, itens, pet atendido, valores, descontos, vendedor, forma de
  pagamento, identificadores da transação, endereço/rota, recebedor e ocorrências.
- **Finalidade proposta:** concluir pedido/venda, receber, entregar, reconciliar,
  atender suporte e preservar histórico obrigatório.
- **Hipótese a validar:** contrato, obrigação fiscal/contábil, proteção do crédito
  e exercício regular de direitos conforme cada campo.
- **Controles existentes:** transações no banco, tenant, idempotência em fluxos
  integrados, conciliação e histórico preservado após anonimização do cliente.
- **Retenção:** prazos fiscais, contábeis, cobrança e chargeback pendentes de
  aprovação; o cadastro pessoal pode ser anonimizado sem apagar a venda exigível.
- **Lacunas:** confirmar que nenhum fluxo armazena número completo ou código de
  segurança de cartão; documentar retenção dos identificadores de gateway.

### DAD-006 — Financeiro, caixa, conciliação, DRE e comissões

- **Dados:** recebimentos, despesas, saldos, margens, taxas, contas, extratos,
  comissões, repasses, remuneração e referências a pessoas/empresas.
- **Finalidade proposta:** gestão financeira, pagamento, conciliação, análise de
  resultado, auditoria e cumprimento contábil/fiscal.
- **Hipótese a validar:** contrato e obrigações legais; dados de trabalhadores e
  prestadores exigem análise trabalhista/contratual.
- **Controles existentes:** tenant, permissões, trilha de negócio, importação
  controlada e reconciliação.
- **Retenção:** pendente de tabela aprovada pelo responsável financeiro, contador
  e jurídico.
- **Lacunas:** proprietário formal, segregação de funções e revisão periódica de
  acessos aos relatórios mais sensíveis.

### DAD-007 — Produtos, estoque, compras e fornecedores

- **Dados:** produtos, imagens, preços, custos, lotes, validade, movimentações,
  notas de entrada e contatos de fornecedor.
- **Finalidade proposta:** compra, venda, reposição, rastreabilidade de estoque e
  análise de margem.
- **Hipótese a validar:** execução de contrato/obrigação legal para dados pessoais
  de contatos; grande parte do domínio é dado empresarial, não pessoal.
- **Controles existentes:** tenant, estoque transacional, trilhas, importações e
  storage S3 compatível opcional.
- **Retenção:** histórico de movimentação e nota conforme regras fiscais/contábeis;
  arquivos temporários devem ser eliminados depois da importação validada.
- **Lacunas:** política de ciclo de vida para imagens/arquivos órfãos e contatos de
  fornecedor inativos.

### DAD-008 — Funcionários, parceiros e remuneração

- **Dados:** nome, contato, documento quando cadastrado, cargo, vínculo, salário,
  comissão, desempenho, acerto e dados de entregadores/prestadores.
- **Finalidade proposta:** controle de acesso, operação, remuneração, comissão e
  cumprimento de obrigações contratuais/trabalhistas.
- **Hipótese a validar:** contrato e obrigação legal, conforme o tipo de vínculo.
- **Controles existentes:** tenant, cargos/permissões e módulos de comissão/acerto.
- **Retenção:** pendente de validação trabalhista, fiscal e contábil; dados não
  necessários à operação não devem ser mantidos por conveniência.
- **Lacunas:** fluxo de direitos/anonimização específico, perfil formal de acesso
  de RH e separação mais clara entre cliente, parceiro e funcionário no cadastro.

### DAD-009 — Ecommerce, app, notificações e dispositivos

- **Dados:** conta do cliente, pedidos, endereço, preferências, notificações,
  token push, plataforma, modelo do dispositivo, versão do app e erros de envio.
- **Finalidade proposta:** oferecer compra e acompanhamento, autenticar, entregar
  notificações solicitadas e diagnosticar falhas.
- **Hipótese a validar:** contrato e consentimento/preferência para comunicações
  promocionais; notificações estritamente transacionais devem ser distinguidas.
- **Controles existentes:** tenant, autenticação do ecommerce, preferências,
  revogação/estado de dispositivo e exportação de pedidos no dossiê do cliente.
- **Retenção:** tokens de dispositivos inativos e erros antigos precisam de purge
  definido; pedidos seguem retenção transacional.
- **Lacunas:** documentar descarte ao logout/desativação e validar disclosures das
  lojas a cada mudança de coleta ou SDK.

### DAD-010 — WhatsApp, campanhas e atendimento

- **Dados:** telefone, nome, identificadores de mensagem, conteúdo, anexos,
  sessões, status de entrega, preferências, consentimento e histórico de suporte.
- **Finalidade proposta:** atendimento solicitado, mensagens transacionais e,
  quando permitido, campanhas segmentadas.
- **Hipótese a validar:** contrato/procedimento solicitado para atendimento;
  consentimento ou outra base validada para marketing. Descadastro deve ser
  efetivo independentemente do canal de entrada.
- **Controles existentes:** tenant, preferências, consentimentos, bloqueio de
  campanhas por preferência e autenticação fail-closed dos webhooks prioritários.
- **Retenção:** conteúdo e anexos ainda precisam de prazo próprio; metadados podem
  permanecer pelo prazo mínimo de reconciliação/segurança aprovado.
- **Lacunas:** deduplicação persistente de mensagens, minimização de conteúdo em
  logs, política de anexos e contrato/retenção de cada provedor.

### DAD-011 — Fiscal, XML e SEFAZ

- **Dados:** CNPJ/CPF, emitente, destinatário, endereço, itens, tributos, chave,
  XML, protocolo, rejeição e identificadores do provedor fiscal.
- **Finalidade proposta:** emitir, receber, consultar e conservar documentos
  fiscais, reconciliar vendas/compras e cumprir obrigação legal.
- **Hipótese a validar:** cumprimento de obrigação legal/regulatória e exercício
  regular de direitos.
- **Controles existentes:** tenant, integração autenticada, trilha da venda,
  importação XML e tratamento de status.
- **Retenção:** contador/jurídico deve aprovar prazo por documento e evento; não
  usar uma regra genérica de logs para XML fiscal.
- **Lacunas:** política formal de certificados, rotação, acesso a XML, exportação
  no encerramento do contrato e descarte depois do prazo obrigatório.

### DAD-012 — Integrações, webhooks e identificadores externos

- **Dados:** IDs externos, estado de sincronização, payload mínimo, timestamps,
  erros, correlation IDs, tokens e segredos.
- **Finalidade proposta:** integrar funções escolhidas, reconciliar resultados,
  evitar duplicidade e diagnosticar falhas.
- **Hipótese a validar:** acompanha a finalidade do dado de origem; compartilhamento
  exige transparência, necessidade, contrato e avaliação do fornecedor.
- **Controles existentes:** catálogo de integrações, timeouts/retries em parte dos
  clientes, idempotência em fluxos críticos, webhooks prioritários fail-closed e
  segredos fora do Git.
- **Retenção:** payloads brutos devem ser mínimos e temporários; IDs técnicos podem
  durar enquanto necessários à reconciliação e auditoria.
- **Lacunas:** registro de operadores/suboperadores, transferência internacional,
  DPA/termos, local de tratamento e política de retenção por fornecedor.

Ver `docs/CATALOGO_INTEGRACOES.md` para o contrato técnico de cada integração.

### DAD-013 — Auditoria, segurança e observabilidade

- **Dados:** usuário/tenant, ação, entidade, IP, user-agent, request/correlation
  ID, erro sanitizado, alerta, deploy e recuperação.
- **Finalidade proposta:** segurança, rastreabilidade, suporte, prevenção a fraude,
  disponibilidade, investigação e defesa de direitos.
- **Hipótese a validar:** legítimo interesse após avaliação, obrigação legal e
  exercício regular de direitos conforme a fonte.
- **Controles existentes:** auditoria no banco, logs JSONL, painel Ops, alertas,
  mascaramento e lista explícita de dados proibidos em log.
- **Retenção implementada/proposta:** matriz operacional em
  `docs/RETENCAO_LOGS_AUDITORIA.md`: por exemplo, `audit_logs` por 24 meses quente
  e 7 anos arquivado; logs HTTP/container por 30 dias e até 90 dias em incidente.
  Esses prazos ainda dependem de validação jurídica e automação completa.
- **Lacunas:** job de purge/anonimização, rotação no host, agregação antes do
  descarte e medição da idade/volume dos registros.

### DAD-014 — IA, sugestões e evidências clínicas externas

- **Dados:** prompt, contexto selecionado, resposta, decisão/feedback e consulta a
  fontes externas. O conteúdo pode se tornar pessoal se o usuário inserir nome,
  documento, contato ou histórico identificável.
- **Finalidade proposta:** apoio à análise, sugestão e busca de evidência; a
  decisão final continua humana quando houver impacto clínico ou financeiro.
- **Hipótese a validar:** acompanha a jornada principal; dado pessoal não deve ser
  enviado por simples conveniência e dado excessivo deve ser removido.
- **Controles existentes:** integração opcional e modelos de logs/decisão em
  módulos de IA.
- **Retenção:** pendente por tipo de uso, provedor e contrato.
- **Lacunas:** política de minimização/anonimização de prompts, revisão dos termos
  do provedor, transferência internacional, retenção externa e proibição clara de
  segredos nos prompts.

### DAD-015 — Preferências, consentimentos e solicitações LGPD

- **Dados:** titular, preferência, texto/versão aceita, data, IP, user-agent,
  contato do solicitante, tipo, status, prazo, resposta e executor.
- **Finalidade proposta:** provar preferências, atender direitos, auditar acesso e
  registrar a resolução.
- **Hipótese a validar:** cumprimento de obrigação legal, exercício regular de
  direitos e consentimento somente para as finalidades que realmente dependem
  dele.
- **Controles existentes:** preferências de e-mail, WhatsApp, SMS, push e
  analytics; histórico/revogação; solicitação com prazo operacional inicial de
  15 dias; acesso, exportação, correção, exclusão, revogação e informação; dossiê
  e anonimização de clientes; log da operação.
- **Retenção:** a própria solicitação deve manter prova mínima da execução, com
  dados do solicitante reduzidos após conclusão quando possível.
- **Lacunas:** validar prazo e procedimento jurídico, ampliar automação para
  usuário/funcionário/fornecedor, medir atendimento e consolidar o serviço legado
  de exclusão que ainda contém caminho incompleto.

### DAD-016 — Backups, exports, imports e arquivos temporários

- **Dados:** cópias agregadas do banco ou subconjuntos exportados/importados;
  herdam a maior classificação presente na origem.
- **Finalidade proposta:** continuidade, restauração, portabilidade, migração e
  atendimento autorizado a titular/tenant.
- **Hipótese a validar:** continuidade contratual, segurança, obrigação legal e
  exercício regular de direitos conforme o artefato.
- **Controles existentes:** dump local privado com retenção padrão de 14 dias,
  restore smoke isolado e cópia externa S3 compatível opcional com checksum e
  ciclo de vida configurável. Último restore real documentado: 2026-05-17.
- **Retenção:** 14 dias é o padrão técnico atual do dump local, não uma definição
  jurídica para os dados de origem. Exportações e temporários devem ter descarte
  explícito após uso.
- **Lacunas:** confirmar ativação/evidência da cópia externa, aprovar ciclo de vida,
  criptografia e acesso, registrar como solicitações de exclusão alcançam backups
  futuros e testar restauração periodicamente.

Ver `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md`.

## Finalidade e hipótese legal: matriz para aprovação

Esta tabela é uma fila de decisão. “Proposta” não significa aprovação.

| Tratamento | Finalidade | Hipótese proposta para validação | Aprovação |
|---|---|---|---|
| Conta e acesso de usuário | Autenticar, autorizar e prestar o SaaS | Execução de contrato; segurança sob avaliação própria | Pendente negócio/jurídico |
| Cadastro e atendimento do cliente | Vender, agendar, entregar e prestar serviço | Contrato/procedimentos preliminares; obrigação legal conforme o evento | Pendente negócio/jurídico |
| Marketing por e-mail/WhatsApp/SMS/push | Comunicação promocional opcional | Consentimento ou outra hipótese formalmente validada, com oposição/descadastro | Pendente negócio/jurídico |
| Fiscal, contábil e financeiro | Emitir, conciliar e conservar registros | Obrigação legal/regulatória e exercício regular de direitos | Pendente contador/jurídico |
| Segurança e auditoria | Detectar abuso, investigar e comprovar ações | Legítimo interesse após avaliação; obrigação legal/exercício de direitos quando aplicável | Pendente negócio/jurídico |
| Veterinário | Prestar e documentar atendimento do animal | Contrato e obrigações profissionais aplicáveis | Pendente responsável técnico/jurídico |
| Funcionários/prestadores | Operar acesso, remuneração e obrigações do vínculo | Contrato e obrigação legal | Pendente administrativo/jurídico |
| IA e provedores externos | Apoiar funcionalidades escolhidas | Hipótese da jornada principal, com necessidade/minimização e contrato do operador | Pendente negócio/jurídico |
| Solicitação do titular | Receber, verificar, executar e provar resposta | Cumprimento de obrigação legal e exercício de direitos | Pendente validação do procedimento |

## Ciclo de vida obrigatório

```text
coletar o mínimo
      ↓
classificar e vincular ao tenant
      ↓
usar somente na finalidade autorizada
      ↓
compartilhar apenas com integração necessária
      ↓
auditar sem copiar conteúdo/segredo em log
      ↓
reter pelo prazo aprovado ou legal hold
      ↓
exportar, corrigir, anonimizar ou eliminar com evidência
```

Regras transversais:

1. Campo livre não autoriza coletar qualquer informação.
2. Toda tabela de negócio multiempresa deve usar o contrato de tenant e RLS
   aplicável.
3. Exportação deve exigir autenticação, permissão, tenant e justificativa.
4. Integração recebe somente os campos necessários à operação.
5. Backup não pode virar arquivo de consulta ou compartilhamento.
6. Exclusão deve considerar obrigação de retenção, legal hold, integrações,
   arquivos e cópias de segurança; quando o histórico precisar permanecer,
   preferir anonimização consistente.
7. Novo domínio de dados deve entrar neste catálogo no mesmo PR.

## Fluxo operacional de direitos do titular

O sistema já oferece estrutura para acesso, exportação, correção, exclusão,
revogação e informação. O fluxo seguro é:

1. receber a solicitação no canal publicado e registrar tenant, tipo e escopo;
2. verificar a identidade sem pedir mais dados do que o necessário;
3. localizar o titular somente dentro do tenant correto;
4. classificar obrigação de conservação e eventual legal hold;
5. gerar dossiê ou executar correção/revogação/anonimização autorizada;
6. revisar a resposta para não incluir dados de terceiros ou de outro tenant;
7. registrar executor, data, decisão e evidência, reduzindo os dados do pedido
   encerrado quando possível;
8. comunicar o resultado pelo canal validado.

O prazo de 15 dias encontrado no serviço é uma meta operacional inicial, não
uma interpretação jurídica universal. O procedimento e os prazos devem ser
revisados quando a identidade do controlador e o tipo do pedido forem
confirmados.

## Continuidade: backup, RPO e RTO

| Grupo | Evidência atual | RPO aprovado | RTO aprovado | Próxima ação |
|---|---|---|---|---|
| Banco principal C1 | Backup diário documentado, dump local por 14 dias e restore smoke real registrado | Pendente | Pendente | Medir duração e perda possível; negócio aprova os objetivos antes de publicar SLA. |
| Arquivos de pet/exames/imagens | Há armazenamento local e S3 opcional em partes do sistema | Pendente | Pendente | Mapear cobertura real do backup e testar restauração de arquivo. |
| Segredos/configuração de produção | Fora do Git por regra; alguns arquivos são root-owned | Não se aplica como dado transacional | Pendente | Documentar recuperação/rotação sem copiar segredo para evidência. |
| Logs/auditoria | Matriz de retenção existe; rotação/purge ainda incompletos | Pendente | Pendente | Definir quais trilhas são necessárias durante recuperação e incidente. |

Não há SLA numérico aprovado de RPO/RTO neste momento. O catálogo registra essa
ausência em vez de inventar uma promessa. O responsável pelo negócio deve
aprovar objetivos somente após teste mensurável da infraestrutura real.

## Controles já existentes

- Código-fonte versionado, branch por tarefa, PR, CI e histórico auditável.
- PostgreSQL, migrations Alembic, transações e contrato multiempresa/RLS.
- Autenticação, sessões, permissões, MFA e trilhas de acesso/segurança.
- Política de segredo fora do Git e proibição de dado sensível em log.
- Catálogo de integrações, falhas, retry, idempotência e responsáveis.
- Preferências, consentimentos, revogação e bloqueio de campanhas.
- Dossiê/exportação, solicitações e anonimização automatizada de clientes/pets.
- Backups, checksum, restore smoke isolado e opção de cópia externa privada.
- Política de retenção de logs, legal hold, incidentes e evidências.
- Política de privacidade pública e materiais de disclosure do app.

## Lacunas priorizadas

### P0 — decisão e risco

1. Aprovar, por tratamento, finalidade, hipótese legal e papéis de
   controlador/operador; ajustar contrato e política quando necessário.
2. Nomear responsáveis por privacidade, dados, segurança, financeiro/fiscal e
   cada domínio crítico; confirmar canal/encarregado aplicável.
3. Aprovar retenção por domínio com jurídico, contador e responsável técnico,
   incluindo fiscal, trabalhista, veterinário, mensagens, arquivos e encerramento
   do tenant.
4. Registrar operadores/suboperadores, localização, transferência internacional,
   contrato/DPA e retenção dos fornecedores externos.

### P1 — implementação e prova

5. Automatizar purge/anonimização de logs conforme a política aprovada.
6. Cobrir direitos de usuários, funcionários, fornecedores e contatos, além do
   cliente já suportado; consolidar o caminho legado de exclusão.
7. Mapear e testar backup/restore de arquivos, cópia externa e propagação de
   exclusões para o ciclo de backups.
8. Revisar armazenamento/rotação dos segredos mais sensíveis, incluindo MFA,
   integrações, certificados e credenciais por tenant.
9. Aprovar RPO/RTO depois de medi-los em restauração real e repetir o teste na
   periodicidade definida.

### P2 — manutenção contínua

10. Medir solicitações, prazo, incidentes de privacidade, acessos extraordinários,
    idade dos dados e execução de descarte sem expor titulares.
11. Revisar este catálogo trimestralmente e no mesmo PR que criar novo domínio,
    fornecedor, coleta, finalidade ou tipo de arquivo.
12. Treinar quem atende solicitações para validar identidade, tenant, terceiros,
    legal hold e resposta segura.

## Gate para qualquer novo dado

Uma entrega que cria ou amplia coleta só está pronta quando responder:

1. Qual dado, titular e finalidade?
2. O dado é necessário e minimizado?
3. Quem é dono e quem pode acessar?
4. Qual hipótese legal foi aprovada por quem tem competência?
5. Onde fica, com quem é compartilhado e há transferência internacional?
6. Como é protegido, auditado e recuperado?
7. Por quanto tempo fica e como é eliminado/anonimizado?
8. Como o titular acessa, corrige, revoga ou solicita eliminação?
9. Quais testes, evidências, comunicação e mudança de política são necessários?

Se uma resposta material estiver pendente, a ficha de entrega deve registrar a
pendência, o responsável e impedir publicação quando houver risco não aceito.

## Evidências no repositório

- Modelos de clientes, pets e usuários: `backend/app/models_cadastros.py` e
  `backend/app/models.py`.
- Vendas e pagamentos: `backend/app/vendas_models.py`.
- Solicitações: `backend/app/lgpd_models.py` e
  `backend/app/services/lgpd_requests.py`.
- Preferências/consentimentos: `backend/app/services/lgpd_consents.py`.
- Dossiê e anonimização: `backend/app/services/lgpd_customer_data.py`.
- Rotas operacionais: `backend/app/lgpd_routes.py` e
  `backend/app/routes/app_privacy_routes.py`.
- Política pública: `frontend/src/pages/LegalPage.jsx`.
- Retenção/auditoria: `docs/RETENCAO_LOGS_AUDITORIA.md`.
- Backup/restore: `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md`.
- Integrações: `docs/CATALOGO_INTEGRACOES.md`.
- Incidentes: `docs/GESTAO_INCIDENTES_SUSTENTACAO.md`.
- Multiempresa: `docs/CONTRATO_MULTITENANT_E_ONBOARDING.md`.

