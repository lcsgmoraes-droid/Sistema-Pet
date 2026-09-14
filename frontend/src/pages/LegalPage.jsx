import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { billingContract } from "../data/billingContract";

const privacyContact = "lcsgmoraes@gmail.com";
const privacyController =
  "WCO COMERCIO E IMPORTACAO LTDA, CNPJ 51.510.640/0001-82, com sede na Rua Alcides Tenorio de Brito Guerra, 51, Parque Sao Matheus, Presidente Prudente/SP, CEP 19025-420";

const legalContent = {
  contrato: billingContract,
  termos: {
    title: "Termos de Uso",
    eyebrow: "Contrato de uso da plataforma",
    version: "Versao 2026-09-14",
    updatedAt: "14/09/2026",
    intro:
      "Estes Termos regulam o acesso e o uso do CorePet, plataforma de gestao, vendas, estoque, financeiro, entregas, atendimento, loja online, aplicativo e integracoes para operacoes de pet shop, clinica, banho e tosa e negocios relacionados.",
    sections: [
      {
        title: "1. Aceite dos Termos",
        body: "Ao criar conta, acessar a plataforma, convidar usuarios, usar a loja online, usar o aplicativo ou continuar navegando apos atualizacoes relevantes, o usuario declara que leu e aceitou estes Termos e que teve acesso e tomou ciencia da Politica de Privacidade.",
        bullets: [
          "O aceite pode ser registrado por checkbox, login, confirmacao de e-mail, uso continuado ou outro mecanismo equivalente.",
          "A versao aceita, data, IP, user-agent e identificadores tecnicos podem ser registrados para fins de auditoria.",
          "Se o usuario nao concordar com estes Termos, deve interromper o uso da plataforma e solicitar orientacao ao administrador da conta.",
        ],
      },
      {
        title: "2. Quem pode usar",
        body: "A plataforma e destinada a empresas, representantes, colaboradores, parceiros operacionais e clientes finais autorizados a acessar os recursos disponibilizados.",
        bullets: [
          "O usuario deve fornecer informacoes verdadeiras, atuais e completas.",
          "O usuario deve ter capacidade para assumir as obrigacoes decorrentes do uso ou autorizacao valida da empresa ou responsavel.",
          "Contas de colaboradores, entregadores, administradores e clientes finais podem ter permissoes diferentes.",
        ],
      },
      {
        title: "3. Conta, tenant e administrador",
        body: "Cada empresa cadastrada possui um ambiente proprio, chamado tenant, com dados, usuarios, permissoes e configuracoes vinculados a essa empresa.",
        bullets: [
          "O administrador inicial e responsavel por configurar usuarios, permissoes, acessos, integracoes, regras fiscais, precos, estoque e operacao.",
          "O administrador deve remover ou bloquear usuarios que nao devem mais acessar a plataforma.",
          "A empresa e responsavel pelos dados inseridos por seus usuarios, colaboradores, clientes, canais e integracoes.",
          "O compartilhamento de senhas, tokens ou acessos pessoais e proibido.",
        ],
      },
      {
        title: "4. Login, senha e confirmacao de e-mail",
        body: "O acesso pode exigir e-mail confirmado, senha, codigo de recuperacao, bloqueio temporario por tentativas falhas e outras medidas de seguranca.",
        bullets: [
          "O usuario deve manter e-mail, telefone e demais dados de recuperacao atualizados.",
          "A plataforma pode bloquear temporariamente acessos suspeitos, tentativas repetidas ou contas com risco operacional.",
          "Links e codigos enviados por e-mail sao pessoais, temporarios e nao devem ser encaminhados a terceiros.",
          "Ao suspeitar de acesso indevido, o usuario deve trocar a senha e avisar o administrador ou suporte.",
        ],
      },
      {
        title: "5. Uso permitido",
        body: "A plataforma deve ser usada para atividades licitas, compativeis com a gestao operacional do negocio e com as funcionalidades contratadas ou liberadas.",
        bullets: [
          "Gerenciar clientes, pets, produtos, estoque, vendas, compras, financeiro, entregas, agendamentos, campanhas e atendimento.",
          "Conectar integracoes autorizadas, como marketplace, ERP, pagamentos, fiscais, e-mail, WhatsApp, rotas e outros provedores.",
          "Gerar relatorios, indicadores, documentos e historicos de operacao.",
          "Atender clientes finais por loja online, app, canais digitais e fluxo presencial.",
        ],
      },
      {
        title: "6. Uso proibido",
        body: "E proibido usar a plataforma de forma abusiva, ilicita, insegura, fraudulenta ou que prejudique outros usuarios, tenants, clientes finais ou terceiros.",
        bullets: [
          "Tentar acessar dados, tenants, contas, APIs ou ambientes sem autorizacao.",
          "Inserir codigo malicioso, explorar vulnerabilidades, automatizar abuso, sobrecarregar servicos ou burlar limites.",
          "Usar dados de clientes, pets, funcionarios ou terceiros fora das finalidades permitidas.",
          "Enviar spam, comunicacoes enganosas, conteudo discriminatorio, ilegal ou sem base adequada.",
          "Falsificar identidade, documentos, vendas, pagamentos, entregas, comprovantes, notas fiscais ou registros.",
          "Revender, copiar, sublicenciar ou disponibilizar a plataforma sem autorizacao.",
        ],
      },
      {
        title: "7. Dados operacionais e qualidade das informacoes",
        body: "Pedidos, vendas, clientes, pets, produtos, estoque, financeiro, comissoes, documentos fiscais, entregas e integracoes dependem de dados corretos e revisao humana quando necessario.",
        bullets: [
          "O usuario deve conferir cadastros, precos, custos, margens, estoque, impostos, notas, pagamentos e relatorios antes de tomar decisoes.",
          "Sugestoes, automacoes, alertas e indicadores apoiam a operacao, mas nao substituem a revisao do responsavel.",
          "Importacoes, sincronizacoes e webhooks podem depender da qualidade dos dados recebidos de terceiros.",
          "Registros historicos podem ser mantidos para auditoria, rastreabilidade, seguranca, obrigacoes legais e defesa de direitos.",
        ],
      },
      {
        title: "8. Loja online, app e clientes finais",
        body: "Quando a empresa habilita loja online, app, area do cliente ou canais digitais, clientes finais podem criar conta, fazer pedidos, consultar dados e interagir com a loja.",
        bullets: [
          "A empresa deve manter informacoes comerciais, politicas de entrega, troca, devolucao, precos e disponibilidade atualizadas.",
          "Pedidos online podem depender de confirmacao de pagamento, estoque, horario de atendimento, raio de entrega e validacao operacional.",
          "A comunicacao com clientes finais deve respeitar autorizacoes, preferencias, descadastro e regras aplicaveis.",
          "O cliente final deve fornecer dados verdadeiros e manter seus dados de contato atualizados.",
        ],
      },
      {
        title: "9. Integracoes e servicos de terceiros",
        body: "A plataforma pode se conectar a provedores externos, como Bling, marketplaces, gateways de pagamento, bancos, emissores fiscais, WhatsApp, e-mail, mapas, IA e outros servicos.",
        bullets: [
          "Cada provedor externo possui suas proprias regras, disponibilidade, limites, politicas e responsabilidades.",
          "Interrupcoes, atrasos, alteracoes de API, instabilidade ou erros de terceiros podem afetar funcionalidades da plataforma.",
          "O usuario deve manter credenciais, tokens, consentimentos e autorizacoes de integracoes validos.",
          "Integracoes podem exigir compartilhamento de dados estritamente necessario para executar a funcionalidade solicitada.",
        ],
      },
      {
        title: "10. Pagamentos, fiscal e financeiro",
        body: "Recursos financeiros, conciliacao, caixa, contas, comissoes, pedidos, notas fiscais e relatorios existem para apoiar a gestao e devem ser conferidos pelo responsavel.",
        bullets: [
          "A empresa e responsavel por validar regras fiscais, tributarias, contabeis, bancarias e comerciais aplicaveis ao seu negocio.",
          "Valores, taxas, parcelas, recebimentos, estornos, creditos e conciliacoes podem depender de dados de terceiros e parametrizacoes internas.",
          "Documentos fiscais, pagamentos e comprovantes devem ser revisados antes de envio, cancelamento ou tomada de decisao.",
        ],
      },
      {
        title: "11. Disponibilidade, manutencao e desempenho",
        body: "A plataforma busca operar com estabilidade, seguranca e melhoria continua, mas pode passar por manutencoes, atualizacoes, incidentes ou indisponibilidades temporarias.",
        bullets: [
          "Podem ocorrer janelas de manutencao, deploys, rotinas de backup, atualizacoes de seguranca e otimizacoes.",
          "A plataforma pode limitar, pausar ou ajustar rotinas para preservar estabilidade, seguranca, integridade de dados ou desempenho.",
          "Falhas de internet, navegador, dispositivo, provedor, gateway, marketplace ou infraestrutura de terceiros podem afetar a experiencia.",
        ],
      },
      {
        title: "12. Auditoria, logs e seguranca operacional",
        body: "Para proteger usuarios, tenants, clientes finais e a propria plataforma, podem ser mantidos logs de acesso, eventos de seguranca, alteracoes relevantes e trilhas de auditoria.",
        bullets: [
          "Logs podem incluir usuario, IP, user-agent, horario, acao executada, tenant, rota, identificadores tecnicos e resultado da operacao.",
          "Eventos sensiveis, como login, troca de senha, recuperacao, alteracao de permissoes, exclusoes e acessos relevantes, podem ser auditados.",
          "A plataforma pode bloquear, suspender ou revisar acessos com sinais de abuso, fraude, risco, vazamento ou violacao destes Termos.",
        ],
      },
      {
        title: "13. Conteudo, propriedade intelectual e marcas",
        body: "A plataforma, telas, codigo, fluxos, componentes, documentacao, layout, marca e recursos pertencem aos respectivos titulares e sao disponibilizados apenas para uso autorizado.",
        bullets: [
          "O usuario conserva responsabilidade sobre dados, imagens, textos, documentos e informacoes que inserir na plataforma.",
          "Nao e permitido copiar, desmontar, revender, sublicenciar, fazer engenharia reversa ou criar derivacoes nao autorizadas.",
          "Marcas, produtos, imagens e dados de terceiros devem ser usados apenas quando o usuario possuir autorizacao ou base adequada.",
        ],
      },
      {
        title: "14. Suporte, comunicacoes e avisos",
        body: "Comunicacoes podem ocorrer por e-mail, sistema, WhatsApp, notificacoes, telefone, area administrativa ou outros canais informados.",
        bullets: [
          "Avisos operacionais, seguranca, confirmacao de e-mail, recuperacao de senha, incidentes e atualizacoes podem ser enviados aos contatos cadastrados.",
          "O usuario deve acompanhar comunicacoes relevantes e manter os canais atualizados.",
          "Solicitacoes de suporte podem exigir dados tecnicos, prints, logs, identificadores de venda, pedido, cliente, produto ou tenant.",
        ],
      },
      {
        title: "15. Suspensao, cancelamento e encerramento",
        body: "Acesso, funcionalidades ou contas podem ser suspensos ou encerrados em caso de risco, inadimplencia, violacao dos Termos, ordem legal, encerramento comercial ou solicitacao do responsavel.",
        bullets: [
          "Antes do encerramento, a empresa deve exportar dados necessarios quando aplicavel e permitido.",
          "Apos o encerramento, dados podem ser mantidos pelo periodo necessario para obrigacoes legais, auditoria, seguranca, cobranca e defesa de direitos.",
          "Clientes finais podem perder acesso a loja online, historico e recursos vinculados quando a empresa desativa o canal.",
        ],
      },
      {
        title: "16. Limitacoes e responsabilidades",
        body: "A plataforma e uma ferramenta de apoio operacional. A execucao diaria do negocio, a revisao das informacoes e as decisoes comerciais, fiscais e financeiras continuam sob responsabilidade dos usuarios autorizados e da empresa.",
        bullets: [
          "A plataforma nao garante resultado comercial, financeiro, fiscal, logistico, veterinario ou publicitario especifico.",
          "A empresa responde pelas informacoes que insere, pelas permissoes que concede e pelas decisoes tomadas a partir dos dados.",
          "Falhas devem ser comunicadas para analise, correcao e mitigacao, sempre que possivel.",
        ],
      },
      {
        title: "17. Atualizacoes destes Termos",
        body: "Estes Termos podem ser atualizados para refletir mudancas de produto, seguranca, operacao, integracoes, requisitos legais ou modelos comerciais.",
        bullets: [
          "Mudancas relevantes podem exigir novo aceite.",
          "A versao vigente fica disponivel nesta pagina.",
          "O uso continuado apos atualizacao pode indicar concordancia com a nova versao, quando permitido.",
        ],
      },
      {
        title: "18. Contato",
        body: "Duvidas operacionais, seguranca, privacidade, conta ou uso da plataforma podem ser encaminhadas pelo suporte do sistema ou pelo e-mail de contato informado nesta pagina.",
        bullets: [
          `Canal principal de contato: ${privacyContact}.`,
          "Clientes finais tambem podem procurar a loja responsavel pelo atendimento, pedido, entrega, troca, devolucao ou dados cadastrados.",
        ],
      },
    ],
  },
  privacidade: {
    title: "Politica de Privacidade",
    eyebrow: "Protecao de dados pessoais",
    version: "Versao 2026-09-14",
    updatedAt: "14/09/2026",
    intro:
      "Esta Politica explica quais dados pessoais podem ser tratados no CorePet, para quais finalidades, com quais justificativas legais, com quem podem ser compartilhados, por quanto tempo podem ser mantidos e como o titular pode exercer seus direitos.",
    sections: [
      {
        title: "1. Abrangencia",
        body: "Esta Politica se aplica a usuarios administradores, colaboradores, entregadores, clientes finais, tutores de pets, fornecedores, contatos comerciais, visitantes de paginas publicas e demais pessoas que interajam com a plataforma.",
        bullets: [
          "Abrange dados tratados no ERP, PDV, loja online, app, paginas publicas, suporte, integracoes, e-mails e canais digitais.",
          "Tambem se aplica a logs, registros tecnicos, auditoria, seguranca, cookies e dados recebidos de integracoes.",
          "Politicas especificas de lojas, marketplaces, meios de pagamento, emissores fiscais e terceiros podem complementar esta Politica.",
        ],
      },
      {
        title: "2. Controlador, operador e responsabilidades",
        body: `${privacyController}, e a fornecedora da plataforma CorePet. O papel de controlador ou operador e definido em cada operacao de tratamento, de acordo com quem toma as decisoes sobre a finalidade e os meios essenciais do uso dos dados.`,
        bullets: [
          "Em regra, a loja ou empresa cadastrada e controladora dos dados que insere sobre clientes, tutores, pets, colaboradores, pedidos, entregas e sua operacao.",
          "Nessas operacoes, o CorePet atua como operador para hospedar, processar, proteger, auditar, dar suporte e disponibilizar as funcionalidades contratadas, seguindo as instrucoes da empresa controladora.",
          "O CorePet atua como controlador dos dados necessarios a cadastro e administracao da conta SaaS, cobranca da assinatura, seguranca da plataforma, prevencao a fraude, suporte, auditoria e defesa de direitos.",
          "Clientes finais podem exercer direitos tanto perante a loja responsavel pelo atendimento quanto pelo canal de privacidade informado nesta Politica, conforme o caso.",
        ],
      },
      {
        title: "3. Dados de conta e autenticacao",
        body: "Para criar e proteger contas, podemos tratar dados de identificacao, contato e seguranca.",
        bullets: [
          "Nome, e-mail, telefone, CPF/CNPJ quando informado, empresa, cargo, perfil, permissoes e tenant.",
          "Senha protegida por hash, tokens temporarios, codigo de confirmacao, codigo de recuperacao e status de e-mail verificado.",
          "Data de aceite dos Termos e da Politica, versoes aceitas, IP, user-agent e registros de consentimento.",
          "Ultimo login, tentativas falhas, bloqueios temporarios, logout, troca de senha e eventos de seguranca.",
        ],
      },
      {
        title: "4. Dados de clientes, tutores e pets",
        body: "Quando a empresa usa a plataforma para atendimento e venda, podem ser tratados dados de clientes, tutores e animais cadastrados.",
        bullets: [
          "Nome, codigo interno, CPF/CNPJ, e-mail, telefone, endereco, preferencias, historico de compras, credito, debitos, agendamentos e comunicacoes.",
          "Dados de pets, como nome, especie, raca, porte, idade, peso, observacoes, historico de banho e tosa, lembretes, vacinas, atendimentos e informacoes operacionais.",
          "Informacoes veterinarias ou de saude podem exigir cuidado adicional e devem ser usadas somente por usuarios autorizados e para finalidades compativeis.",
          "Dados de entrega, como endereco, referencia, rota, status, entregador, comprovantes e ocorrencias.",
          "Durante uma rota ativa, o app do entregador pode coletar localizacao precisa, data e hora e deslocamento para permitir o acompanhamento pela loja e pelo cliente vinculado. A coleta comeca quando o entregador confirma Iniciar Rota, pode continuar com o app minimizado ou a tela bloqueada e para quando a rota e finalizada ou cancelada.",
        ],
      },
      {
        title: "5. Dados comerciais, fiscais e financeiros",
        body: "A plataforma pode tratar dados necessarios a vendas, compras, estoque, financeiro, documentos fiscais, conciliacao, relatorios e auditoria.",
        bullets: [
          "Pedidos, itens, produtos, SKU, codigo de barras, marcas, fornecedores, precos, custos, margens, estoque, notas fiscais e movimentacoes.",
          "Pagamentos, recebimentos, parcelas, formas de pagamento, taxas, contas a pagar, contas a receber, credito de cliente, caixa e conciliacao.",
          "Dados fiscais e documentos podem ser mantidos por prazos relacionados a obrigacoes legais, regulatoria, auditoria e defesa de direitos.",
        ],
      },
      {
        title: "6. Dados de comunicacao e campanhas",
        body: "A plataforma pode viabilizar comunicacoes transacionais, operacionais, relacionamento e campanhas, conforme configuracao da empresa e preferencias aplicaveis.",
        bullets: [
          "E-mails de confirmacao, recuperacao de senha, avisos de pedido, entrega, cobranca, suporte e seguranca.",
          "Mensagens de WhatsApp, SMS, push, e-mail marketing, campanhas, lembretes, retorno de banho e tosa, pos-venda e reativacao.",
          "Registros de envio, abertura, erro, descadastro, preferencia, consentimento e historico de atendimento podem ser mantidos.",
          "Comunicacoes promocionais devem observar preferencias, bases adequadas e possibilidade de oposicao ou descadastro quando aplicavel.",
        ],
      },
      {
        title: "7. Dados tecnicos, logs e cookies",
        body: "Ao acessar a plataforma, podemos coletar dados tecnicos necessarios para funcionamento, seguranca, desempenho, auditoria e melhoria.",
        bullets: [
          "IP, data e hora, user-agent, navegador, dispositivo, sistema operacional, identificadores de sessao, rota acessada e eventos de erro.",
          "Cookies ou tecnologias semelhantes podem ser usados para login, sessao, preferencias, seguranca, medicao de uso e melhoria da experiencia.",
          "Cookies estritamente necessarios podem ser indispensaveis para funcionamento do sistema.",
          "Cookies de medicao, experiencia ou marketing, quando usados, devem respeitar transparencia, finalidade e escolhas disponiveis.",
        ],
      },
      {
        title: "8. Dados, finalidades e bases legais",
        body: "A justificativa legal depende da pessoa, do recurso utilizado e de quem atua como controlador. As relacoes abaixo mostram as combinacoes normalmente aplicaveis, sem transformar o aceite desta Politica em autorizacao generica para qualquer uso.",
        bullets: [
          "Conta e autenticacao — nome, e-mail, telefone, empresa, perfil, permissoes, senha protegida, IP e dados do dispositivo sao usados para criar e administrar a conta, autenticar, recuperar acesso e proteger a sessao. Bases normalmente aplicaveis: procedimentos preliminares e execucao de contrato; legitimo interesse e prevencao a fraude para seguranca, conforme avaliacao do caso.",
          "Assinatura e cobranca do CorePet — dados da empresa, representante, contato de cobranca, plano, faturas e status de pagamento sao usados para contratar, cobrar, prestar suporte financeiro e comprovar a relacao. Bases normalmente aplicaveis: execucao de contrato, obrigacao legal ou regulatoria e exercicio regular de direitos.",
          "Clientes, tutores, pets e operacao da loja — cadastros, pedidos, vendas, agendamentos, atendimentos, entregas e historicos sao usados pela empresa cadastrada para prestar seus servicos. A empresa define a base legal aplicavel; o CorePet realiza o processamento necessario para executar o contrato SaaS e as instrucoes da controladora.",
          "Dados fiscais, financeiros e de credito — documentos, pagamentos, parcelas, debitos, conciliacoes e registros transacionais sao usados para executar operacoes, cumprir deveres fiscais e contabeis, cobrar e defender direitos. Bases normalmente aplicaveis: contrato, obrigacao legal ou regulatoria, protecao do credito e exercicio regular de direitos.",
          "Comunicacoes — e-mail, telefone, WhatsApp, SMS e push podem ser usados para confirmacao de conta, pedido, entrega, cobranca, seguranca e suporte com base no contrato, obrigacao aplicavel ou interesse legitimo avaliado. Comunicacoes promocionais dependem de consentimento ou de outra base previamente documentada pela controladora e sempre devem oferecer oposicao ou descadastro quando aplicavel.",
          "Localizacao de entrega — a posicao do entregador, data, hora e deslocamento sao usados somente durante a rota ativa para executar, acompanhar e comprovar a entrega. A empresa responsavel pela rota deve informar seus colaboradores e definir a base adequada; o CorePet nao usa essa localizacao para publicidade.",
          "Logs, cookies e seguranca — IP, user-agent, sessao, rota acessada e eventos tecnicos sao usados para funcionamento, auditoria, suporte, prevencao a fraude e seguranca. Cookies necessarios acompanham a prestacao do servico; analytics ou marketing nao essenciais dependem da escolha e da base legal aplicavel.",
          "IA e integracoes opcionais — recebem apenas o contexto necessario ao recurso solicitado e seguem a mesma finalidade e base legal do processo de origem. Habilitar uma integracao nao autoriza reutilizacao dos dados para finalidade incompativel.",
          "Solicitacoes de titulares — identificacao, contato, pedido e evidencia da resposta sao usados para verificar identidade, atender direitos e comprovar o atendimento. Bases normalmente aplicaveis: obrigacao legal ou regulatoria e exercicio regular de direitos.",
        ],
      },
      {
        title: "9. Como aplicamos as bases legais",
        body: "A base legal e registrada e avaliada conforme a finalidade concreta. Nem todo tratamento depende de consentimento, e a simples ciencia desta Politica nao substitui o consentimento especifico quando ele for exigido.",
        bullets: [
          "Consentimento e usado somente quando for livre, informado, destacado, vinculado a finalidade determinada e passivel de revogacao por meio facilitado.",
          "Execucao de contrato ou procedimentos preliminares cobre apenas os dados necessarios para contratar, entregar a plataforma ou realizar a operacao solicitada.",
          "Obrigacao legal ou regulatoria pode exigir a coleta ou conservacao de documentos fiscais, contabeis, trabalhistas, de seguranca ou de atendimento, conforme o caso.",
          "Legitimo interesse exige avaliacao de finalidade, necessidade, expectativas do titular, impacto e salvaguardas; nao e uma autorizacao generica para melhorar o servico ou enviar publicidade.",
          "Protecao do credito, prevencao a fraude e exercicio regular de direitos sao usados somente quando a operacao e os requisitos legais correspondentes estiverem presentes.",
          "O registro de aceite desta Politica comprova que o documento foi apresentado ao usuario; ele nao autoriza usos incompativeis com as finalidades informadas.",
        ],
      },
      {
        title: "10. Fornecedores, destinatarios e integracoes",
        body: "Cada fornecedor recebe somente os dados necessarios ao recurso utilizado. Integracoes escolhidas pela empresa cadastrada somente recebem dados quando habilitadas e podem atuar como operadoras, suboperadoras ou controladoras independentes, conforme o servico e o contrato aplicavel.",
        bullets: [
          "Infraestrutura — DigitalOcean pode hospedar a aplicacao e o banco de dados; armazenamento ou backup S3 compativel, inclusive Cloudflare R2 quando configurado, pode receber arquivos e copias protegidas.",
          "Cobranca da assinatura CorePet — Asaas pode receber identificacao da empresa, contato de cobranca, valor, vencimento, identificadores e status da cobranca.",
          "Pagamentos do e-commerce — Mercado Pago e, em fluxos legados ou condicionais, Pagar.me podem receber dados do pedido, pagador, valor, meio e resultado da transacao quando a loja habilitar o recurso.",
          "Operacao, marketplace e fiscal — Bling, iFood, SEFAZ, IntNFe e EcommerceAI podem receber ou devolver produtos, estoque, pedidos, documentos e identificadores fiscais quando a empresa conectar cada integracao.",
          "Comunicacoes — WhatsApp e o ecossistema Meta, 360dialog, WAHA e o provedor SMTP configurado, como Google/Gmail, podem processar contatos, conteudo e metadados das mensagens necessarias ao canal habilitado.",
          "Notificacoes do app — Expo Push e os servicos de entrega da Apple e do Google podem processar token do dispositivo, plataforma e conteudo minimo da notificacao.",
          "Mapas e rotas — Google Maps pode receber enderecos, coordenadas e parametros de rota necessarios a geocodificacao, distancia e acompanhamento da entrega.",
          "Inteligencia artificial — OpenAI pode receber o contexto minimo enviado a recursos opcionais de IA. Usuarios nao devem inserir senhas, segredos, documentos completos ou dados pessoais desnecessarios nos prompts.",
          "A posicao da rota ativa pode ser exibida a usuarios autorizados da loja e ao cliente que possui o acesso de rastreio daquela entrega. A localizacao do entregador nao e usada para publicidade.",
          "Fornecedores, clientes, usuarios autorizados, autoridades publicas ou terceiros quando houver obrigacao, autorizacao ou necessidade legitima.",
          "A lista efetivamente aplicavel varia conforme os recursos contratados e habilitados. Alteracoes materiais serao refletidas nesta Politica, e o titular pode pedir pelo canal de privacidade a relacao de destinatarios aplicavel ao seu caso.",
        ],
      },
      {
        title: "11. Transferencias internacionais",
        body: "Alguns provedores de infraestrutura, e-mail, comunicacao, notificacao, analytics, IA, pagamento ou suporte podem armazenar ou processar dados fora do Brasil.",
        bullets: [
          "A transferencia deve estar vinculada a finalidade informada, limitar-se ao minimo necessario e possuir base legal para o tratamento.",
          "Quando aplicavel, a transferencia sera apoiada por mecanismo valido previsto na LGPD e na regulamentacao da ANPD, como decisao de adequacao, clausulas-padrao contratuais, clausulas especificas aprovadas ou outra hipotese legal cabivel.",
          "O CorePet avalia medidas contratuais, tecnicas e organizacionais do fornecedor conforme o risco e as informacoes disponiveis.",
          "Integracoes contratadas diretamente pela empresa cadastrada podem possuir regras proprias de transferencia internacional, que tambem devem ser avaliadas pela respectiva controladora.",
          "O titular pode solicitar informacoes sobre os paises e mecanismos aplicaveis ao seu tratamento pelo canal de privacidade.",
        ],
      },
      {
        title: "12. Retencao, encerramento e descarte",
        body: "O cancelamento da assinatura, a desativacao de uma integracao e um pedido de exclusao nao produzem o mesmo efeito para todos os registros. Aplicamos o criterio correspondente a cada categoria e preservamos somente o que possuir finalidade e justificativa de conservacao.",
        bullets: [
          "Conta e assinatura — os dados operacionais permanecem disponiveis enquanto a conta estiver ativa. Apos cancelamento ou encerramento, o acesso pode ser limitado e a empresa deve solicitar a exportacao pelo suporte; identificadores minimos podem permanecer para cobranca, auditoria, seguranca e defesa de direitos.",
          "Clientes, pets e historicos — quando nao houver obrigacao de conservar a identificacao, os dados podem ser corrigidos, bloqueados, eliminados ou anonimizados. Vendas, documentos e trilhas que precisem permanecer podem conservar o fato da operacao com os campos pessoais reduzidos ou anonimizados.",
          "Fiscal, financeiro, contabil, trabalhista e veterinario — os registros seguem os prazos legais, regulatorios, profissionais ou de defesa aplicaveis a cada documento e relacao; um pedido de exclusao nao elimina registro cuja conservacao seja obrigatoria.",
          "Marketing e preferencias — o uso promocional termina com o descadastro, oposicao ou revogacao aplicavel. Pode ser preservada evidencia minima da escolha para impedir novo envio indevido e comprovar o atendimento.",
          "Entregas — a coleta de localizacao precisa termina quando a rota e finalizada ou cancelada. Depois disso, apenas a ultima posicao e metricas vinculadas a rota podem permanecer pelo periodo necessario a comprovacao da entrega e defesa de direitos.",
          "Logs e auditoria — como referencia operacional, logs brutos de aplicacao, HTTP e containers sao mantidos normalmente por 30 dias e podem chegar a 90 dias em incidente; eventos detalhados de jornada, por 90 dias; trilhas de auditoria, por ate 24 meses em consulta ativa e, quando justificadas, por ate 7 anos em arquivo protegido ou forma anonimizada.",
          "Backups — o backup local do banco utiliza ciclo padrao de 14 dias. Copias externas, quando configuradas, seguem o ciclo de vida protegido definido para o armazenamento. Dados eliminados ou anonimizados deixam de reaparecer na base ativa e saem das copias conforme a renovacao do ciclo, salvo preservacao obrigatoria ou bloqueio por investigacao.",
          "Exportacoes e arquivos temporarios — sao disponibilizados somente pelo tempo necessario a entrega, importacao, verificacao ou suporte e devem ser eliminados ou ter o acesso revogado depois da finalidade.",
          "Legal hold — prazos podem ser suspensos para incidente, fraude, disputa, auditoria, ordem de autoridade ou exercicio regular de direitos. Encerrado o motivo, o registro volta ao ciclo normal de descarte.",
          "O titular pode solicitar pelo canal de privacidade o criterio e o periodo aplicavel a uma categoria especifica de seus dados.",
        ],
      },
      {
        title: "13. Direitos dos titulares",
        body: "Titulares podem solicitar, conforme aplicavel, informacoes e providencias sobre seus dados pessoais.",
        bullets: [
          "Confirmacao da existencia de tratamento.",
          "Acesso aos dados pessoais tratados.",
          "Correcao de dados incompletos, inexatos ou desatualizados.",
          "Anonimizacao, bloqueio ou eliminacao de dados desnecessarios, excessivos ou tratados em desconformidade.",
          "Portabilidade, quando regulamentada e tecnicamente aplicavel.",
          "Informacao sobre compartilhamento de dados.",
          "Informacao sobre a possibilidade de nao consentir e consequencias da negativa.",
          "Revogacao do consentimento, quando o tratamento depender de consentimento.",
          "Oposicao a tratamento em desconformidade com a legislacao aplicavel.",
          "Revisao de decisoes automatizadas, quando aplicavel.",
        ],
      },
      {
        title: "14. Como exercer direitos",
        body: "Solicitacoes podem ser feitas pelo canal de suporte, pelo canal da loja responsavel ou pelo contato de privacidade abaixo.",
        bullets: [
          `Canal de privacidade: ${privacyContact}.`,
          "Informe apenas os dados suficientes para localizar o cadastro e verificar a identidade, como nome, um contato ja cadastrado, empresa/loja relacionada e tipo de solicitacao. Nao envie senha, codigo de acesso, documento completo ou dado de cartao por e-mail.",
          "Podemos solicitar informacoes adicionais para confirmar identidade, evitar fraude e proteger dados de terceiros.",
          "Quando a loja for controladora dos dados, a solicitacao pode ser direcionada ou compartilhada com a loja responsavel pelo atendimento.",
        ],
      },
      {
        title: "15. Seguranca da informacao",
        body: "Adotamos medidas tecnicas e organizacionais para reduzir riscos de acesso indevido, perda, alteracao, destruicao, vazamento ou uso nao autorizado de dados.",
        bullets: [
          "Controle de acesso por usuario, tenant e permissoes.",
          "Senhas protegidas por hash e recuperacao por tokens/codigos temporarios.",
          "Bloqueio temporario por tentativas falhas e registros de eventos de autenticacao.",
          "Logs, auditoria, monitoramento, health checks, segregacao por tenant e trilhas operacionais.",
          "Backups, deploy seguro, controle de ambiente, atualizacoes e medidas preventivas de estabilidade.",
          "Nenhum sistema e totalmente imune a riscos; incidentes identificados sao tratados com medidas de contencao, analise e comunicacao quando aplicavel.",
        ],
      },
      {
        title: "16. Incidentes de seguranca",
        body: "Em caso de incidente que possa afetar dados pessoais, podem ser adotadas medidas de investigacao, contencao, correcao, registro, comunicacao e prevencao de recorrencia.",
        bullets: [
          "A avaliacao considera natureza dos dados, titulares afetados, impacto, probabilidade de dano, medidas de protecao e acoes corretivas.",
          "Quando exigido, titulares, empresas envolvidas, autoridades ou parceiros podem ser comunicados.",
          "Usuarios devem comunicar suspeitas de vazamento, acesso indevido, dispositivo comprometido ou credencial exposta.",
        ],
      },
      {
        title: "17. Dados de criancas, adolescentes e pets",
        body: "A plataforma pode conter dados de menores quando inseridos por responsaveis, tutores, lojas ou profissionais autorizados, especialmente em cadastros de clientes, dependentes ou atendimentos.",
        bullets: [
          "Dados de menores devem ser inseridos apenas quando necessarios e por responsavel autorizado.",
          "Dados de pets nao sao dados pessoais por si so, mas podem se relacionar ao tutor e devem ser protegidos quando identificarem uma pessoa.",
          "Informacoes sensiveis ou de saude devem receber acesso restrito e finalidade compativel.",
        ],
      },
      {
        title: "18. Decisoes automatizadas, IA e sugestoes",
        body: "A plataforma pode apresentar sugestoes, alertas, classificacoes, filtros, previsoes, automacoes e recursos de IA para apoiar a operacao.",
        bullets: [
          "Esses recursos podem usar dados historicos, estoque, vendas, atendimentos, produtos, movimentacoes, integracoes e parametros configurados.",
          "Sugestoes devem ser revisadas pelo usuario responsavel antes de decisoes comerciais, financeiras, fiscais, veterinarias ou operacionais relevantes.",
          "Quando aplicavel, o titular pode solicitar informacoes ou revisao de decisoes baseadas exclusivamente em tratamento automatizado.",
        ],
      },
      {
        title: "19. Preferencias, consentimento e descadastro",
        body: "Algumas funcionalidades podem depender de consentimento, preferencia ou autorizacao, como comunicacoes promocionais, cookies nao necessarios e determinados canais de contato.",
        bullets: [
          "O titular pode revogar consentimento quando o tratamento se basear nele.",
          "A revogacao pode limitar funcionalidades, comunicacoes, personalizacoes ou acesso a determinados recursos.",
          "Comunicacoes obrigatorias, transacionais, legais, fiscais, seguranca e suporte podem continuar quando necessarias.",
        ],
      },
      {
        title: "20. Atualizacoes desta Politica",
        body: "Esta Politica pode ser atualizada para refletir novas funcionalidades, integracoes, requisitos legais, medidas de seguranca ou mudancas operacionais.",
        bullets: [
          "Mudancas relevantes de finalidade, base legal, compartilhamento ou impacto ao titular podem ser comunicadas por e-mail, aviso no sistema, nova ciencia ou novo consentimento quando este for a base aplicavel.",
          "A versao vigente fica disponivel nesta pagina.",
          "O uso continuado pode registrar ciencia da nova versao, mas nao substitui consentimento especifico quando ele for legalmente necessario.",
        ],
      },
      {
        title: "21. Contato de privacidade",
        body: `O canal de privacidade de ${privacyController} recebe duvidas, solicitacoes de titulares, incidentes, preferencias e comunicacoes relacionadas a protecao de dados.`,
        bullets: [
          `E-mail: ${privacyContact}.`,
          "Informe somente o contexto necessario, como loja relacionada, contato ja cadastrado e, quando indispensavel, numero do pedido ou outro identificador da operacao.",
          "Clientes finais tambem podem procurar diretamente a loja responsavel pelo pedido, entrega, atendimento, cadastro ou relacionamento comercial.",
        ],
      },
    ],
  },
};

const LegalPage = ({ type = "termos" }) => {
  const content = legalContent[type] || legalContent.termos;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <main className="mx-auto max-w-5xl px-5 py-8 sm:px-6 lg:px-8">
        <Link
          to="/login"
          className="inline-flex items-center gap-2 text-sm font-semibold text-blue-700 hover:text-blue-800"
        >
          <img src="/brand/corepet/corepet-icon-64.png" alt="" className="h-4 w-4 rounded" />
          CorePet
        </Link>

        <section className="mt-8 rounded-lg border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-6 border-b border-slate-200 pb-8 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-blue-700">
                <ShieldCheck className="h-3.5 w-3.5" />
                {content.eyebrow}
              </div>
              <h1 className="mt-4 text-3xl font-bold tracking-normal text-slate-950">
                {content.title}
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{content.intro}</p>
            </div>
            <div className="min-w-44 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              <div className="font-semibold text-slate-900">{content.version}</div>
              <div className="mt-1">Atualizado em {content.updatedAt}</div>
            </div>
          </div>

          <div className="mt-8 grid gap-8 lg:grid-cols-[240px_minmax(0,1fr)]">
            <aside className="hidden lg:block">
              <div className="sticky top-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
                  Nesta pagina
                </div>
                <nav className="mt-3 space-y-2">
                  {content.sections.map((section) => (
                    <a
                      key={section.title}
                      href={`#${section.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                      className="block text-xs leading-5 text-slate-600 hover:text-blue-700"
                    >
                      {section.title}
                    </a>
                  ))}
                </nav>
              </div>
            </aside>

            <div className="space-y-8">
              {content.sections.map((section) => (
                <section
                  key={section.title}
                  id={section.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}
                  className="scroll-mt-8 border-b border-slate-100 pb-8 last:border-b-0 last:pb-0"
                >
                  <h2 className="text-lg font-bold text-slate-950">{section.title}</h2>
                  <p className="mt-2 text-sm leading-7 text-slate-700">{section.body}</p>
                  {section.bullets?.length > 0 && (
                    <ul className="mt-4 space-y-2 text-sm leading-6 text-slate-600">
                      {section.bullets.map((bullet) => (
                        <li key={bullet} className="flex gap-3">
                          <span className="mt-2 h-1.5 w-1.5 flex-none rounded-full bg-blue-600" />
                          <span>{bullet}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default LegalPage;
