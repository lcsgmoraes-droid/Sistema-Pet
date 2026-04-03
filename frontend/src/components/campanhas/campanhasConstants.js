export const TIPO_LABELS = {
  loyalty_stamp: {
    label: "Cartão Fidelidade",
    color: "bg-purple-100 text-purple-800",
    emoji: "🏷️",
  },
  cashback: {
    label: "Cashback",
    color: "bg-green-100 text-green-800",
    emoji: "💰",
  },
  birthday: {
    label: "Aniversário",
    color: "bg-pink-100 text-pink-800",
    emoji: "🎂",
  },
  birthday_customer: {
    label: "Aniversário Cliente",
    color: "bg-pink-100 text-pink-800",
    emoji: "🎂",
  },
  birthday_pet: {
    label: "Aniversário Pet",
    color: "bg-orange-100 text-orange-800",
    emoji: "🐾",
  },
  welcome: {
    label: "Boas-vindas",
    color: "bg-blue-100 text-blue-800",
    emoji: "👋",
  },
  welcome_app: {
    label: "Boas-vindas App",
    color: "bg-blue-100 text-blue-800",
    emoji: "👋",
  },
  inactivity: {
    label: "Clientes Inativos",
    color: "bg-red-100 text-red-800",
    emoji: "😴",
  },
  ranking_monthly: {
    label: "Ranking Mensal",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "🏆",
  },
  quick_repurchase: {
    label: "Recompra Rápida",
    color: "bg-teal-100 text-teal-800",
    emoji: "🔁",
  },
  monthly_highlight: {
    label: "Destaque Mensal",
    color: "bg-amber-100 text-amber-800",
    emoji: "🌟",
  },
  win_back: {
    label: "Reativação",
    color: "bg-red-100 text-red-800",
    emoji: "🔄",
  },
  raffle: {
    label: "Sorteio",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "🎲",
  },
};

export const USER_CREATABLE_TYPES = new Set([
  "inactivity",
  "quick_repurchase",
  "bulk_segment",
]);

export const CUPOM_STATUS = {
  active: { label: "Ativo", color: "bg-green-100 text-green-700" },
  used: { label: "Usado", color: "bg-gray-100 text-gray-600" },
  expired: { label: "Expirado", color: "bg-red-100 text-red-600" },
  voided: { label: "Cancelado", color: "bg-red-100 text-red-600" },
};

export const RANK_LABELS = {
  bronze: {
    label: "Bronze",
    color: "bg-amber-100 text-amber-800",
    border: "border-amber-300",
    emoji: "🥉",
  },
  silver: {
    label: "Prata",
    color: "bg-gray-100 text-gray-700",
    border: "border-gray-400",
    emoji: "🥈",
  },
  gold: {
    label: "Ouro",
    color: "bg-yellow-100 text-yellow-800",
    border: "border-yellow-400",
    emoji: "🥇",
  },
  diamond: {
    label: "Platina",
    color: "bg-purple-100 text-purple-800",
    border: "border-purple-400",
    emoji: "👑",
  },
  platinum: {
    label: "Diamante",
    color: "bg-cyan-100 text-cyan-800",
    border: "border-cyan-400",
    emoji: "💎",
  },
};

export const FRASES_ANIVERSARIO = {
  birthday_customer: {
    brinde:
      "🎂 Feliz aniversário, {nome}! Seu carinho merece uma celebração especial! Apareça na nossa loja para retirar seu presente surpresa. Será um prazer ver você! 🎁",
    cupom:
      "🎉 Feliz aniversário, {nome}! Neste dia tão especial preparamos um cupom de {desconto} de desconto pra você celebrar com muito mimo pro seu pet! Use o código {code}. 🐾",
  },
  birthday_pet: {
    brinde:
      "🐾🎂 Que dia mais fofo! {nome_pet} está fazendo aniversário e a gente não podia deixar passar em branco! Venha buscar o mimo especial que separamos pro seu melhor amigo — tem muito carinho esperando por vocês! Um beijo nas patinhas! 🥳",
    cupom:
      "🎈 O {nome_pet} tá de parabéns hoje, {nome}! Para comemorar esse dia tão especial, preparamos um cupom de {desconto} de desconto pra mimar o(a) aniversariante! Use o código {code} e vai fundo nos mimos! 🐕🎁",
  },
};

export const hoje = new Date().toISOString().slice(0, 10);
export const primeiroDiaMes = `${hoje.slice(0, 7)}-01`;

export function createDefaultPremio() {
  return {
    tipo_premio: "cupom",
    coupon_value: 50,
    coupon_valid_days: 10,
    mensagem:
      "Parabéns! Você foi um dos nossos melhores clientes do mês! 🏆",
    mensagem_brinde:
      "Parabéns! Você foi um dos nossos melhores clientes do mês. Passe em nossa loja e retire seu brinde especial — será um prazer recebê-lo! 🎁",
    retirar_de: "",
    retirar_ate: "",
  };
}
