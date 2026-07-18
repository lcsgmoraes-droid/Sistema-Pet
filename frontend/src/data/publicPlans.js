export const salesContactBaseUrl = "https://wa.me/5518997401641";

export function buildSalesContactUrl(message) {
  return `${salesContactBaseUrl}?text=${encodeURIComponent(message)}`;
}

export const segmentOptions = [
  { id: "all", label: "Quero conhecer tudo", shortLabel: "Visão completa" },
  { id: "pet", label: "Loja Pet", shortLabel: "Loja Pet" },
  { id: "vet", label: "Veterinário", shortLabel: "Veterinário" },
  { id: "grooming", label: "Banho & Tosa", shortLabel: "Banho & Tosa" },
];

export const segmentSummaries = {
  all: {
    eyebrow: "Ecossistema CorePet",
    title: "Loja, clínica e serviços trabalhando na mesma operação.",
    description:
      "Conheça os três módulos separadamente ou combine Loja Pet, Veterinário e Banho & Tosa conforme o seu negócio cresce.",
    highlights: [
      "Clientes e pets em uma única base",
      "PDV, agenda, estoque e financeiro conectados",
      "App para aproximar a empresa dos clientes",
      "Planos que começam pequenos e crescem com a operação",
    ],
    startingPrice: null,
  },
  pet: {
    eyebrow: "Para lojas e pet shops",
    title: "Seu ERP registra o que você vendeu. O CorePet trabalha para vender de novo.",
    description:
      "PDV, estoque, compras, gestão, app, e-commerce, campanhas, recorrência e entregas em uma operação integrada.",
    highlights: [
      "Venda e estoque em tempo real",
      "Entrada de NF por XML e compras inteligentes",
      "Resultado, margem e DRE para decidir melhor",
      "App, e-commerce e venda ativa no plano completo",
    ],
    startingPrice: "R$ 49,90",
  },
  vet: {
    eyebrow: "Para veterinários e clínicas",
    title: "Comece pela agenda e evolua até a gestão clínica completa.",
    description:
      "Atenda em domicílio, em consultório, em clínica ou hospital com planos adequados para cada momento da operação.",
    highlights: [
      "Agenda profissional e lembretes pelo app",
      "Prontuário, consultas, exames e vacinas",
      "Financeiro, documentos e histórico do pet",
      "Internação, protocolos e inteligência no plano completo",
    ],
    startingPrice: "R$ 79,90",
  },
  grooming: {
    eyebrow: "Para Banho & Tosa",
    title: "Da agenda de quem trabalha sozinho à gestão completa da equipe.",
    description:
      "Organize horários, avise clientes, acompanhe atendimentos e evolua para pacotes, comissões, custos e automações.",
    highlights: [
      "Agenda, clientes, pets e lembretes",
      "Fila do dia, equipe, pacotes e recorrência",
      "Financeiro, comissões e indicadores",
      "Custos, campanhas e taxi dog no plano completo",
    ],
    startingPrice: "R$ 59,90",
  },
};

export const publicPlans = {
  pet: [
    {
      id: "pet-start",
      name: "Pet Start",
      price: "49,90",
      description: "Para começar a organizar e vender com um investimento popular.",
      features: [
        "PDV, clientes, pets e produtos",
        "Estoque e histórico essenciais",
        "Até 500 vendas por mês",
        "Um acesso simultâneo",
      ],
    },
    {
      id: "pet-basico",
      name: "Pet Básico",
      price: "197,00",
      description: "Para uma loja em crescimento que precisa operar sem limite de vendas.",
      features: [
        "Vendas ilimitadas e múltiplos PDVs",
        "Até três acessos simultâneos",
        "Entrada de nota por XML",
        "Estoque, permissões e controles avançados",
      ],
    },
    {
      id: "pet-gestao",
      name: "Pet Gestão",
      price: "397,00",
      description: "Para comprar melhor e acompanhar o resultado real da empresa.",
      features: [
        "Tudo do Pet Básico",
        "Pedidos e sugestão inteligente de compras",
        "Financeiro, DRE e ponto de equilíbrio",
        "Fornecedores e indicadores gerenciais",
      ],
      featured: true,
    },
    {
      id: "pet-venda-ativa",
      name: "Pet Venda Ativa",
      price: "697,00",
      description:
        "A operação completa para vender em todos os canais e trazer o cliente de volta.",
      features: [
        "Tudo do Pet Gestão",
        "App e e-commerce integrados",
        "Campanhas, recorrência e recompra",
        "Entregas, rotas e emissão fiscal integrada",
      ],
    },
  ],
  vet: [
    {
      id: "vet-start",
      name: "Vet Start",
      price: "79,90",
      description: "Para veterinários autônomos, atendimento domiciliar e quem está começando.",
      features: [
        "Agenda profissional no celular",
        "Tutores, pets, serviços e preços",
        "PDV e recebimentos simples",
        "Lembretes e próximos agendamentos pelo app",
      ],
    },
    {
      id: "vet-gestao",
      name: "Vet Gestão",
      price: "247,00",
      description: "Para consultórios e clínicas que precisam unir atendimento clínico e gestão.",
      features: [
        "Tudo do Vet Start",
        "Consultas, prontuário e prescrições",
        "Exames, vacinas e carteirinha digital",
        "Financeiro, documentos e relatórios",
      ],
      featured: true,
    },
    {
      id: "vet-completo",
      name: "Vet Completo",
      price: "497,00",
      description: "Para clínicas estruturadas e hospitais veterinários.",
      features: [
        "Tudo do Vet Gestão",
        "Internações, leitos e medicações",
        "Protocolos, repasses e calculadora de doses",
        "Assistente de IA e indicadores avançados",
      ],
    },
  ],
  grooming: [
    {
      id: "grooming-start",
      name: "B&T Start",
      price: "59,90",
      description: "Para quem trabalha sozinho, em domicílio ou em uma estrutura pequena.",
      features: [
        "Agenda para um profissional",
        "Clientes, pets, serviços e preços",
        "PDV e recebimentos simples",
        "Lembretes e status pelo app",
      ],
    },
    {
      id: "grooming-gestao",
      name: "B&T Gestão",
      price: "117,00",
      description: "Para operações com equipe, pacotes e maior volume de atendimentos.",
      features: [
        "Tudo do B&T Start",
        "Vários profissionais e fila do dia",
        "Pacotes, créditos e recorrência",
        "Comissões, financeiro e relatórios",
      ],
      featured: true,
    },
    {
      id: "grooming-completo",
      name: "B&T Completo",
      price: "157,00",
      description: "Para automatizar retornos e acompanhar custos e rentabilidade.",
      features: [
        "Tudo do B&T Gestão",
        "Custos e margem por serviço",
        "Campanhas, retornos e indicadores",
        "Fidelidade, taxi dog e rotas",
      ],
    },
  ],
};

export const serviceInvoiceAddon = {
  name: "Emissão de NFS-e integrada",
  price: "59,90",
  description:
    "Adicional opcional para Veterinário e Banho & Tosa, operado por emissor fiscal parceiro e conectado ao CorePet.",
  features: [
    "Contratação separada do plano principal",
    "Emissão de nota de serviço dentro do fluxo do CorePet",
    "Configuração assistida dos dados da empresa e dos serviços",
    "Disponibilidade sujeita à homologação do município e do emissor parceiro",
  ],
};
