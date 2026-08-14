export const BILLING_CONTRACT_VERSION = "2026-08-14-01";
export const BILLING_CONTRACT_DOCUMENT_SHA256 =
  "827819d29b30bf7b6a14a6c5f659cf5b0da475311dba6845c846570fb15e70a8";

export const BILLING_ACCEPTANCE_TEXT =
  "Li e aceito o Resumo da Contratação, o Contrato de Assinatura CorePet, os Termos de Uso e a Política de Privacidade. Confirmo o plano, o valor, o ciclo e o primeiro vencimento exibidos e autorizo a cobrança correspondente. Declaro que tenho poderes para representar a empresa cadastrada.";

export const billingContract = {
  title: "Contrato de Assinatura CorePet",
  eyebrow: "Licença de uso de software e serviços SaaS",
  version: `Versão ${BILLING_CONTRACT_VERSION}`,
  updatedAt: "14/08/2026",
  intro:
    "Este Contrato regula a assinatura paga da plataforma CorePet. Ele deve ser lido em conjunto com o resumo comercial exibido antes da contratação, os Termos de Uso e a Política de Privacidade.",
  sections: [
    {
      title: "1. Partes e documentos da contratação",
      body: "A contratada é WCO COMERCIO E IMPORTACAO LTDA, CNPJ 51.510.640/0001-82, com sede na Rua Alcides Tenorio de Brito Guerra, 51, Parque São Matheus, Presidente Prudente/SP, CEP 19025-420, fornecedora da plataforma CorePet. A contratante é a empresa identificada no resumo da contratação e representada pelo administrador que realiza o aceite eletrônico.",
      bullets: [
        "O resumo da contratação define plano, preço, ciclo, primeiro vencimento, limites e adicionais escolhidos.",
        "Este Contrato define as regras gerais da assinatura; os Termos de Uso regulam o uso da plataforma; e a Política de Privacidade descreve o tratamento de dados pessoais.",
        "Em caso de divergência comercial, prevalece o resumo específico que foi exibido e aceito pelo administrador.",
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
        "Revisar preços, estoque, impostos, documentos fiscais, pagamentos, relatórios, prontuários, prescrições e demais dados antes de decisões relevantes.",
        "Manter profissionais habilitados para decisões veterinárias, fiscais, contábeis, trabalhistas, financeiras e jurídicas.",
      ],
    },
    {
      title: "9. Integrações, disponibilidade e suporte",
      body: "A plataforma pode depender de provedores de pagamento, bancos, emissores fiscais, marketplaces, ERPs, WhatsApp, e-mail, mapas, inteligência artificial e outros serviços de terceiros.",
      bullets: [
        "A CorePet não controla indisponibilidades ou alterações de terceiros, mas prestará suporte razoável para diagnosticar ocorrências na integração.",
        "Poderão ocorrer manutenções programadas, correções emergenciais e interrupções decorrentes de infraestrutura ou terceiros.",
        "SLA, créditos por indisponibilidade ou suporte prioritário somente existem quando descritos no plano ou em anexo específico.",
        "Backups de continuidade não substituem os arquivos e exportações que a contratante deva conservar.",
      ],
    },
    {
      title: "10. Dados, privacidade e confidencialidade",
      body: "A contratante mantém seus direitos sobre os dados operacionais inseridos na plataforma. A CorePet poderá tratá-los na medida necessária para executar, proteger e dar suporte ao serviço.",
      bullets: [
        "Em regra, a contratante atua como controladora dos dados de seus clientes, colaboradores e parceiros, e a CorePet atua como operadora para prestar o serviço.",
        "A CorePet poderá atuar como controladora dos dados necessários a cadastro, cobrança, segurança, suporte, prevenção a fraude e defesa de direitos.",
        "As partes protegerão informações confidenciais e observarão a Política de Privacidade e a legislação aplicável.",
      ],
    },
    {
      title: "11. Propriedade intelectual e decisões profissionais",
      body: "O software, a marca, o código, as interfaces, os modelos e a documentação pertencem à CorePet ou aos respectivos licenciantes. O contrato concede apenas o direito de uso durante a assinatura.",
      bullets: [
        "É proibido copiar, revender, sublicenciar, desmontar, realizar engenharia reversa ou contornar controles sem autorização legal ou contratual.",
        "Alertas, automações, cálculos, relatórios e recursos de inteligência artificial são apoio operacional e devem ser revisados por pessoa autorizada.",
        "A CorePet não garante resultado econômico, clínico, tributário, logístico ou comercial específico.",
      ],
    },
    {
      title: "12. Suspensão, cancelamento e encerramento",
      body: "A CorePet poderá suspender o acesso em caso de inadimplência, risco de segurança, fraude, ordem legal, violação grave ou ameaça à estabilidade, com aviso e oportunidade razoável de regularização sempre que a urgência permitir.",
      bullets: [
        "Nos planos mensais sem fidelidade expressa, o cancelamento pode ser solicitado a qualquer momento e produz efeito ao final do ciclo já pago.",
        "Fidelidade, multa ou prazo mínimo somente valerão se destacados no resumo da contratação e aceitos pelo administrador.",
        "Valores do ciclo em andamento não serão devolvidos proporcionalmente, salvo condição comercial mais favorável ou direito legal aplicável.",
        "Após o encerramento, aplicam-se os prazos de exportação, retenção e eliminação informados nos documentos vigentes.",
      ],
    },
    {
      title: "13. Responsabilidades e força maior",
      body: "Cada parte responde pelos danos diretos que causar por descumprimento de suas obrigações, conforme prova, nexo causal e legislação aplicável. Nenhuma disposição afasta responsabilidade que não possa ser limitada por lei.",
      bullets: [
        "A CorePet não responde por dano causado exclusivamente por dado incorreto, uso indevido, permissão concedida pela contratante ou ambiente local inseguro.",
        "Falha de terceiro não exclui a responsabilidade própria da parte que tiver contribuído para o dano ou deixado de adotar medida razoável de prevenção.",
        "Não haverá inadimplemento por evento inevitável e fora do controle razoável da parte afetada enquanto perdurarem seus efeitos, desde que haja comunicação e mitigação.",
      ],
    },
    {
      title: "14. Alterações, comunicações e solução de conflitos",
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
