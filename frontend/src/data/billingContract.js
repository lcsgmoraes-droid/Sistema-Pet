export const BILLING_CONTRACT_VERSION = "2026-09-14-02";
export const BILLING_CONTRACT_DOCUMENT_SHA256 =
  "591557963e446eca1a55e46dba0337ddf95373aa2f0660c6d88cb2142e5aa44e";

export const BILLING_ACCEPTANCE_TEXT =
  "Li e aceito o Resumo da Contratação, o Contrato de Assinatura CorePet e os Termos de Uso. Declaro que tive acesso e estou ciente da Política de Privacidade. Confirmo o plano, o valor, o ciclo e o primeiro vencimento exibidos. Quando houver proposta específica, confirmo também seu escopo, exclusões, implantação, suporte e a informação sobre ausência ou existência de SLA. Autorizo a cobrança correspondente e declaro que tenho poderes para representar a empresa cadastrada.";

export const billingContract = {
  title: "Contrato de Assinatura CorePet",
  eyebrow: "Licença de uso de software e serviços SaaS",
  version: `Versão ${BILLING_CONTRACT_VERSION}`,
  updatedAt: "14/09/2026",
  intro:
    "Este Contrato regula a assinatura paga da plataforma CorePet. Ele deve ser lido em conjunto com o resumo comercial exibido antes da contratação, os Termos de Uso e a Política de Privacidade.",
  sections: [
    {
      title: "1. Partes e documentos da contratação",
      body: "A contratada é WCO COMERCIO E IMPORTACAO LTDA, CNPJ 51.510.640/0001-82, com sede na Rua Alcides Tenorio de Brito Guerra, 51, Parque São Matheus, Presidente Prudente/SP, CEP 19025-420, fornecedora da plataforma CorePet. A contratante é a empresa identificada no resumo da contratação e representada pelo administrador que realiza o aceite eletrônico.",
      bullets: [
        "O resumo da contratação define plano, preço, ciclo, primeiro vencimento, limites e adicionais escolhidos.",
        "As condições específicas da proposta definem escopo, implantação, migração, exclusões, suporte, personalizações e regras de encerramento aplicáveis à contratação.",
        "Este Contrato define as regras gerais da assinatura; os Termos de Uso regulam o uso da plataforma; e a Política de Privacidade descreve o tratamento de dados pessoais.",
        "Em caso de divergência sobre condição específica, prevalecem a proposta aceita e os anexos assinados; depois, este Contrato e os Termos de Uso, cada qual em seu tema.",
      ],
    },
    {
      title: "2. Objeto e licença de uso",
      body: "A CorePet disponibiliza acesso remoto à plataforma em modelo de software como serviço (SaaS), conforme os módulos e limites do plano contratado.",
      bullets: [
        "A licença é limitada, não exclusiva, intransferível e válida enquanto a assinatura estiver vigente.",
        "Somente os módulos, usuários, limites, adicionais e integrações indicados na oferta integram a assinatura paga.",
        "Recursos de teste, demonstração, piloto ou beta podem mudar e não integram automaticamente o plano contratado.",
      ],
    },
    {
      title: "3. Aceite eletrônico e representação",
      body: "O contrato é celebrado quando o administrador visualiza o resumo da contratação, acessa estes documentos, marca o campo de concordância e confirma a assinatura.",
      bullets: [
        "O aceitante declara que possui capacidade e poderes para contratar em nome da empresa cadastrada.",
        "O aceite poderá ser comprovado por registros de versão, hash, data e hora, usuário, empresa, plano, preço, IP, navegador e identificador do evento.",
        "Cada novo aceite gera um registro histórico, sem substituir os aceites anteriores.",
      ],
    },
    {
      title: "4. Período gratuito e início da cobrança",
      body: "Quando oferecido, o período gratuito terá a duração e o escopo informados na plataforma. O teste não se converte automaticamente em plano pago e não autoriza cobrança sem o aceite expresso do administrador.",
      bullets: [
        "Módulos liberados para experiência podem não integrar o plano escolhido ao final do teste.",
        "O primeiro vencimento será mostrado no resumo da contratação antes da confirmação.",
        "Sem contratação, o acesso poderá ser limitado ao final do teste, respeitadas as regras de exportação e guarda aplicáveis.",
      ],
    },
    {
      title: "5. Plano, preço e cobrança",
      body: "A mensalidade, o ciclo, a forma de pagamento e o primeiro vencimento são os exibidos no resumo aceito. A cobrança poderá ser processada pelo Asaas ou por outro provedor informado.",
      bullets: [
        "A mensalidade é devida enquanto a assinatura permanecer ativa, mesmo que a contratante utilize apenas parte dos recursos disponíveis.",
        "Mudança de plano, adicional ou aumento de limite dependerá de solicitação ou aceite do administrador e poderá gerar ajuste proporcional previamente informado.",
        "Encargos por atraso somente serão aplicados quando informados e dentro dos limites legais.",
      ],
    },
    {
      title: "6. Reajuste anual",
      body: "Os valores da assinatura serão reajustados a cada 12 meses, contados do início da assinatura paga ou do último reajuste, pela variação acumulada do IPCA divulgado pelo IBGE. A periodicidade de reajuste nunca será inferior a 12 meses.",
      bullets: [
        "Se o IPCA for extinto ou não puder ser utilizado, será adotado índice oficial que melhor reflita a inflação do período.",
        "O novo valor e a data de vigência serão informados com antecedência mínima de 30 dias pelos canais cadastrados e dentro da plataforma.",
        "Aumento extraordinário fora dessa regra exigirá nova proposta ou aceite, com possibilidade de cancelamento antes da vigência e sem multa, ressalvados valores vencidos.",
        "Mudança de plano, adicional solicitado e alteração tributária determinada por lei não se confundem com o reajuste anual, mas serão informados com transparência.",
      ],
    },
    {
      title: "7. Obrigações da CorePet",
      body: "A CorePet prestará o serviço com diligência técnica, segurança proporcional ao risco e respeito aos recursos contratados.",
      bullets: [
        "Disponibilizar os recursos do plano e manter medidas de controle de acesso, monitoramento, logs e continuidade operacional.",
        "Corrigir falhas sob seu controle em prazo compatível com gravidade, impacto e complexidade e comunicar incidentes relevantes quando aplicável.",
        "Preservar a confidencialidade dos dados, cumprir a legislação de proteção de dados e limitar acessos ao necessário.",
        "Manter canal de suporte e meios razoáveis de consulta e exportação dos dados conforme o plano e as condições de encerramento.",
      ],
    },
    {
      title: "8. Obrigações da contratante",
      body: "A contratante é responsável pela administração da conta, pela qualidade das informações inseridas e pelo uso lícito da plataforma por seus usuários.",
      bullets: [
        "Fornecer dados corretos e atualizados, pagar os valores contratados e manter os dados de cobrança válidos.",
        "Administrar usuários e permissões, remover acessos indevidos e impedir o compartilhamento de senhas e tokens.",
        "Proteger dispositivos, redes, e-mails, credenciais e integrações sob seu controle, seguir recomendações de segurança comunicadas e avisar imediatamente qualquer suspeita de comprometimento.",
        "Revisar preços, estoque, impostos, documentos fiscais, pagamentos, relatórios, prontuários, prescrições e demais dados antes de decisões relevantes.",
        "Manter profissionais habilitados para decisões veterinárias, fiscais, contábeis, trabalhistas, financeiras e jurídicas.",
      ],
    },
    {
      title: "9. Suporte, disponibilidade, manutenção e terceiros",
      body: "A CorePet busca manter a plataforma disponível e corrigir falhas sob seu controle, mas a assinatura padrão não contém garantia numérica de disponibilidade nem prazo garantido de resolução, salvo quando houver SLA específico aceito pelas partes.",
      bullets: [
        "O canal, o horário e as metas de primeira resposta constam das condições específicas da proposta; primeira resposta não significa resolução garantida.",
        "Um SLA somente existe em anexo específico que defina indicador, janela de medição, meta, exclusões, manutenção, forma de apuração e eventual crédito.",
        "Sem esse anexo, não há percentual contratual de disponibilidade, crédito automático ou suporte prioritário presumido.",
        "Manutenções programadas serão comunicadas com antecedência razoável quando causarem impacto relevante; correções urgentes de segurança ou estabilidade podem ocorrer sem aviso prévio.",
        "A plataforma pode depender de pagamentos, bancos, emissores fiscais, marketplaces, ERPs, WhatsApp, e-mail, mapas, inteligência artificial e outros terceiros. A CorePet não controla esses serviços, mas responde por suas próprias escolhas, integrações e medidas razoáveis de prevenção e mitigação.",
        "Backups de continuidade não substituem os arquivos e exportações que a contratante deva conservar.",
      ],
    },
    {
      title: "10. Dados, segurança, incidentes e confidencialidade",
      body: "A contratante mantém seus direitos sobre os dados e conteúdos inseridos na plataforma. A CorePet poderá tratá-los na medida necessária para executar, proteger e dar suporte ao serviço, respeitando os papéis definidos na legislação e na Política de Privacidade.",
      bullets: [
        "Em regra, a contratante atua como controladora dos dados de seus clientes, colaboradores e parceiros, e a CorePet atua como operadora para prestar o serviço.",
        "A CorePet poderá atuar como controladora dos dados necessários a cadastro, cobrança, segurança, suporte, prevenção a fraude e defesa de direitos.",
        "Cada parte deve proteger os ambientes, credenciais e acessos sob seu controle, limitar permissões ao necessário e preservar evidências sem divulgar dados ou segredos indevidamente.",
        "Ao confirmar incidente que afete dados pessoais da contratante, a CorePet a avisará sem atraso indevido e, sempre que razoavelmente possível, em até 1 dia útil, com as informações disponíveis e atualizações relevantes.",
        "A contratante decide e realiza comunicações à ANPD e aos titulares quando atuar como controladora; a CorePet prestará cooperação razoável. Quando a CorePet for controladora, cumprirá diretamente suas obrigações legais.",
        "A distribuição de custos e responsabilidades por incidente observará a participação comprovada de cada parte, suas obrigações próprias e a legislação; o uso de terceiros não elimina responsabilidade que a lei atribua à parte.",
        "As obrigações de confidencialidade continuam após o encerramento enquanto a informação permanecer confidencial ou protegida por lei.",
      ],
    },
    {
      title: "11. Propriedade intelectual, personalizações e sugestões",
      body: "O software, a marca, o código, as interfaces, os modelos e a documentação pertencem à CorePet ou aos respectivos licenciantes. O contrato concede apenas o direito de uso durante a assinatura.",
      bullets: [
        "É proibido copiar, revender, sublicenciar, desmontar, realizar engenharia reversa ou contornar controles sem autorização legal ou contratual.",
        "Dados, marcas, imagens, textos e documentos fornecidos pela contratante continuam pertencendo aos respectivos titulares; a contratante autoriza seu uso apenas para executar o serviço.",
        "Desenvolvimento sob medida somente integra a contratação quando descrito nas condições específicas ou em Ordem de Serviço com escopo, preço, prazo, aceite, manutenção e entregáveis.",
        "Salvo cessão expressa em documento assinado, o código, componentes reutilizáveis, arquitetura, métodos, melhorias e funcionalidades desenvolvidos permanecem da CorePet e podem ser reutilizados sem expor informações confidenciais da contratante.",
        "Exclusividade, cessão de direitos ou entrega de código-fonte exigem previsão expressa, preço próprio e definição dos componentes preexistentes, de terceiros e de código aberto que ficam excluídos da cessão.",
        "Sugestões e feedback podem ser usados para melhorar o produto sem exclusividade ou pagamento, desde que não revelem informação confidencial ou dado pessoal fora da finalidade.",
        "Alertas, automações, cálculos, relatórios e recursos de inteligência artificial são apoio operacional e devem ser revisados por pessoa autorizada.",
        "A CorePet não garante resultado econômico, clínico, tributário, logístico ou comercial específico.",
      ],
    },
    {
      title: "12. Escopo, implantação e controle de mudanças",
      body: "A CorePet deve entregar o escopo registrado na proposta aceita. Necessidades não descritas, mudanças posteriores e novas integrações não entram automaticamente na mensalidade ou no prazo original.",
      bullets: [
        "Correção é a adequação de comportamento que contrarie o escopo aceito; melhoria ou personalização é capacidade nova, ampliação ou preferência não prevista.",
        "Pedidos em reunião, suporte, mensagem ou WhatsApp iniciam uma avaliação, mas só alteram a contratação após proposta ou Ordem de Serviço aceita.",
        "A mudança deve registrar responsável, descrição, dependências, preço, prazo, critérios de aceite, propriedade intelectual e impacto na manutenção.",
        "Atraso da contratante no envio de dados, acessos, validações ou decisões pode deslocar o cronograma na medida do impacto comprovado.",
        "Migrações, importações e integrações dependem da qualidade, formato, autorização e disponibilidade dos dados e sistemas de origem.",
      ],
    },
    {
      title: "13. Suspensão, cancelamento, exportação e encerramento",
      body: "A CorePet poderá suspender o acesso em caso de inadimplência, risco de segurança, fraude, ordem legal, violação grave ou ameaça à estabilidade, com aviso e oportunidade razoável de regularização sempre que a urgência permitir.",
      bullets: [
        "Nos planos mensais sem fidelidade expressa, o cancelamento pode ser solicitado a qualquer momento e produz efeito ao final do ciclo já pago.",
        "Fidelidade, multa ou prazo mínimo somente valerão se destacados no resumo da contratação e aceitos pelo administrador.",
        "Valores do ciclo em andamento não serão devolvidos proporcionalmente, salvo condição comercial mais favorável ou direito legal aplicável.",
        "Salvo prazo diferente destacado na proposta, a contratante pode solicitar exportação assistida disponível por até 30 dias após o encerramento; recomenda-se exportar os dados essenciais antes do término do acesso.",
        "Exportação extraordinária, transformação de formato, migração assistida ou trabalho técnico fora do recurso padrão pode depender de orçamento prévio.",
        "Após o encerramento, aplicam-se os prazos de retenção e eliminação da Política de Privacidade, obrigações legais e eventual preservação necessária para auditoria, cobrança ou defesa de direitos.",
      ],
    },
    {
      title: "14. Responsabilidades, limite e força maior",
      body: "Cada parte responde pelos danos diretos que causar por descumprimento de suas obrigações, conforme prova, nexo causal e legislação aplicável. Nenhuma disposição afasta responsabilidade que não possa ser limitada por lei.",
      bullets: [
        "Em relação estritamente empresarial e na extensão permitida por lei, a responsabilidade total da CorePet ligada à assinatura fica limitada ao valor pago ou devido pela contratante nos 12 meses anteriores ao fato que originou a reclamação, salvo limite diferente em anexo assinado.",
        "O limite não se aplica a dolo, fraude, violação deliberada de confidencialidade ou propriedade intelectual, valores devidos pela contratante nem a obrigação que a lei não permita limitar, inclusive perante titulares de dados e consumidores quando aplicável.",
        "Na extensão permitida por lei, nenhuma parte responde por dano indireto, perda de oportunidade, economia esperada ou lucro meramente estimado sem relação direta e comprovada com o descumprimento.",
        "A CorePet não responde por dano causado exclusivamente por dado incorreto, uso indevido, permissão concedida pela contratante ou ambiente local inseguro.",
        "Falha de terceiro não exclui a responsabilidade própria da parte que tiver contribuído para o dano ou deixado de adotar medida razoável de prevenção.",
        "Não haverá inadimplemento por evento inevitável e fora do controle razoável da parte afetada enquanto perdurarem seus efeitos, desde que haja comunicação e mitigação.",
      ],
    },
    {
      title: "15. Alterações, comunicações e solução de conflitos",
      body: "Alterações materiais serão comunicadas com antecedência razoável. Mudança extraordinária de preço, inclusão de fidelidade, redução relevante de direitos ou ampliação material de responsabilidade exigirá novo aceite ou proposta específica.",
      bullets: [
        "Avisos poderão ser enviados pelo sistema, e-mail, aplicativo, WhatsApp ou outro canal cadastrado; a contratante deve manter os contatos atualizados.",
        "Aplica-se a legislação brasileira. As partes buscarão primeiro resolver divergências pelos canais de suporte e negociação.",
        "Para relações empresariais, fica eleito o foro de Presidente Prudente/SP, ressalvado foro obrigatório ou regra legal mais favorável aplicável.",
        "Contato contratual: lcsgmoraes@gmail.com e telefone/WhatsApp (18) 99740-1641.",
      ],
    },
  ],
};
