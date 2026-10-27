// Conteúdo da página de apoio "Conectar o WhatsApp oficial" (API oficial da Meta).
// Texto e regras de apresentação ficam aqui, fora do React, para testar e ajustar fácil.
// Os nomes de telas da Meta mudam com o tempo: confira os links antes de publicar mudanças.

export const LINKS_META = {
  negocios: "https://business.facebook.com/",
  verificacao: "https://www.facebook.com/business/help/2058515294227817",
  desenvolvedores: "https://developers.facebook.com/apps/",
  precos: "https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing",
  documentacao: "https://developers.facebook.com/docs/whatsapp/cloud-api/get-started",
};

// Passos feitos fora do sistema (na Meta). O usuário marca "Já fiz" para acompanhar.
export const PASSOS_NA_META = [
  {
    id: "preparar",
    titulo: "Separe o que você vai precisar",
    resumo: "Leva 5 minutos e evita travar no meio do caminho.",
    itens: [
      "Dados da empresa: razão social, CNPJ, endereço e site ou rede social da loja.",
      "Um login do Facebook de quem é dono ou administrador da empresa.",
      "Um número de telefone só para o atendimento da loja, que receba SMS ou ligação. Ele não pode estar ativo em um WhatsApp comum: se estiver, apague a conta do WhatsApp nesse número antes.",
      "Um cartão para a Meta cobrar as mensagens pagas (a cobrança é feita pela Meta, direto na conta da loja).",
    ],
    links: [{ rotulo: "Tabela de preços da Meta", href: "precos" }],
  },
  {
    id: "empresa",
    titulo: "Crie e verifique a empresa na Meta",
    resumo: "É a conta onde ficam o seu WhatsApp, o app e as cobranças.",
    itens: [
      "Entre em business.facebook.com com o login do administrador e crie o portfólio empresarial (o nome da loja).",
      "Preencha os dados da empresa exatamente como estão no CNPJ.",
      "Abra Configurações do negócio > Central de segurança e inicie a Verificação da empresa. A Meta pede documentos e pode levar alguns dias. Sem verificar, os limites de envio são menores.",
    ],
    links: [
      { rotulo: "Abrir a Meta Business", href: "negocios" },
      { rotulo: "Como verificar a empresa", href: "verificacao" },
    ],
  },
  {
    id: "app",
    titulo: "Crie o app e adicione o WhatsApp",
    resumo: "O app é o “aplicativo” que conecta o seu WhatsApp ao CorePet.",
    itens: [
      "Abra developers.facebook.com/apps e clique em Criar app.",
      "Quando perguntar o que o app vai fazer, escolha o caso de uso de conectar com clientes pelo WhatsApp (ou o tipo Empresa).",
      "Vincule o app ao portfólio empresarial que você criou no passo anterior.",
      "No painel do app, confirme que o produto WhatsApp está adicionado.",
    ],
    links: [{ rotulo: "Abrir os apps da Meta", href: "desenvolvedores" }],
  },
  {
    id: "numero",
    titulo: "Adicione o número e copie os dois IDs",
    resumo: "Os IDs identificam o seu número e a sua conta do WhatsApp.",
    itens: [
      "No app, abra WhatsApp > Configuração da API (API Setup).",
      "Adicione o número de telefone da loja e confirme com o código recebido por SMS ou ligação. Informe o nome de exibição que os tutores verão (a Meta analisa esse nome).",
      "Na mesma tela, copie o ID do número de telefone e o ID da conta do WhatsApp Business. Você vai colar os dois no passo 6.",
      "Em Configurações do negócio > Contas do WhatsApp, cadastre a forma de pagamento da conta.",
    ],
    links: [],
  },
  {
    id: "token",
    titulo: "Gere o token permanente e copie o segredo do app",
    resumo: "O token é a “chave” que deixa o CorePet enviar mensagens pela sua conta.",
    itens: [
      "Em Configurações do negócio > Usuários > Usuários do sistema, crie um usuário do sistema com a função de Administrador (use o nome “CorePet”).",
      "Clique em Atribuir ativos: dê controle total sobre o app e sobre a conta do WhatsApp.",
      "Clique em Gerar token: escolha o app, deixe a validade como Nunca e marque as permissões whatsapp_business_messaging e whatsapp_business_management.",
      "Copie o token e guarde: a Meta mostra uma vez só. Não envie por e-mail nem mensagem.",
      "No app, abra Configurações do app > Básico e copie a Chave secreta do app (App Secret).",
    ],
    links: [{ rotulo: "Abrir a Meta Business", href: "negocios" }],
  },
];

// Passos feitos aqui no sistema, na ordem em que aparecem depois dos da Meta.
export const PASSOS_NO_SISTEMA = [
  { id: "credenciais", numero: 6, titulo: "Cole os dados aqui" },
  { id: "webhook", numero: 7, titulo: "Aponte o webhook da Meta para o CorePet" },
  { id: "testar", numero: 8, titulo: "Teste a conexão" },
  { id: "ativar", numero: 9, titulo: "Ative o WhatsApp oficial" },
];

export const PASSOS_DO_WEBHOOK = [
  "No app, abra WhatsApp > Configuração (Configuration) e, em Webhook, clique em Editar.",
  "Cole o endereço de retorno (Callback URL) e o token de verificação mostrados abaixo e clique em Verificar e salvar.",
  "Na lista de campos do webhook, assine o campo messages.",
  "Volte aqui e clique em “Inscrever o app na conta” para a Meta começar a enviar as respostas dos tutores.",
];

const ROTULOS_DE_STATUS = {
  conectado: { texto: "Conectado", detalhe: "Tudo certo. Falta só ativar, se ainda não ativou." },
  aguardando_teste: { texto: "Falta testar", detalhe: "Os dados foram salvos. Teste a conexão." },
  erro: { texto: "Com problema", detalhe: "O último teste falhou. Veja o que corrigir abaixo." },
};

/** Resumo para o topo da página: { texto, detalhe, tom } (tom: neutro | ok | atencao | erro). */
export function resumoDoVinculo(estado) {
  if (estado?.ativo && estado?.status?.codigo === "conectado") {
    return {
      texto: "WhatsApp oficial ativo",
      detalhe: "As mensagens saem e chegam pela API oficial da Meta.",
      tom: "ok",
    };
  }
  const codigo = estado?.status?.codigo;
  if (!codigo) {
    return {
      texto: "Não configurado",
      detalhe: "Siga os passos abaixo para conectar o número da loja.",
      tom: "neutro",
    };
  }
  const rotulo = ROTULOS_DE_STATUS[codigo] || { texto: codigo, detalhe: "" };
  return {
    ...rotulo,
    tom: codigo === "conectado" ? "ok" : codigo === "erro" ? "erro" : "atencao",
  };
}

/** Em qual passo do guia o usuário deve olhar, dado o código devolvido pelo teste. */
export function passoDoErro(passoDoGuia) {
  if (passoDoGuia === "token") return "token";
  if (passoDoGuia === "ids") return "numero";
  return null;
}

/** Passos técnicos concluídos, vistos a partir do estado do servidor. */
export function passosConcluidos(estado) {
  const credenciais = estado?.credenciais || {};
  const salvo = Boolean(
    credenciais.waba_id &&
    credenciais.phone_number_id &&
    credenciais.tem_token &&
    credenciais.tem_app_secret,
  );
  const conectado = estado?.status?.codigo === "conectado";
  return {
    credenciais: salvo,
    webhook: Boolean(estado?.status?.ultimo_webhook_em),
    testar: conectado,
    ativar: Boolean(estado?.ativo),
  };
}

export const ROTULO_DA_QUALIDADE = {
  GREEN: "Alta",
  YELLOW: "Média",
  RED: "Baixa",
  UNKNOWN: "Ainda não avaliada",
};
