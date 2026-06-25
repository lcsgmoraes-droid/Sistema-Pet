export const REQUEST_TYPES = [
  ["access", "Acesso aos dados"],
  ["export", "Exportacao"],
  ["correction", "Correcao"],
  ["deletion", "Exclusao"],
  ["revocation", "Revogacao"],
  ["information", "Informacao"],
];

export const REQUEST_STATUS = [
  ["pending", "Pendente"],
  ["in_review", "Em analise"],
  ["waiting_customer", "Aguardando cliente"],
  ["completed", "Concluida"],
  ["rejected", "Rejeitada"],
  ["cancelled", "Cancelada"],
];

export const STATUS_INTENT = {
  pending: "warning",
  in_review: "info",
  waiting_customer: "purple",
  completed: "success",
  rejected: "danger",
  cancelled: "neutral",
};

export const PREFERENCES = [
  ["marketing_email", "Email marketing", "Ofertas, cupons e campanhas por email."],
  ["marketing_whatsapp", "WhatsApp marketing", "Mensagens promocionais e lembretes comerciais."],
  ["marketing_sms", "SMS marketing", "Comunicacoes curtas por SMS."],
  ["marketing_push", "Push no app", "Avisos e campanhas no aplicativo."],
  [
    "analytics",
    "Analise e personalizacao",
    "Uso de dados para segmentacao e melhoria da experiencia.",
  ],
];

export const REQUEST_TYPE_LABEL = Object.fromEntries(REQUEST_TYPES);
export const REQUEST_STATUS_LABEL = Object.fromEntries(REQUEST_STATUS);

export const DEFAULT_PROCESS_FORM = {
  status: "in_review",
  resolution_notes: "",
};

export const DEFAULT_ANONYMIZE_FORM = {
  confirmacao: "",
  resolution_notes: "",
};

export const DEFAULT_NEW_REQUEST = {
  request_type: "access",
  details: "",
  requester_name: "",
  requester_email: "",
  requester_phone: "",
};
