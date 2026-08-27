export const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "active", label: "Ativos" },
  { value: "inactive", label: "Inativos" },
  { value: "trial", label: "Trial" },
  { value: "suspended", label: "Suspensos" },
];

export const TENANT_STATUS_EDIT_OPTIONS = [
  { value: "active", label: "Ativo" },
  { value: "trial", label: "Trial" },
  { value: "inactive", label: "Inativo" },
  { value: "suspended", label: "Suspenso" },
];

export const PLAN_EDIT_OPTIONS = [
  { value: "pet-start", label: "Pet Start" },
  { value: "pet-basico", label: "Pet Basico" },
  { value: "pet-gestao", label: "Pet Gestao" },
  { value: "pet-venda-ativa", label: "Pet Venda Ativa" },
  { value: "vet-start", label: "Vet Start" },
  { value: "vet-gestao", label: "Vet Gestao" },
  { value: "vet-completo", label: "Vet Completo" },
  { value: "grooming-start", label: "B&T Start" },
  { value: "grooming-gestao", label: "B&T Gestao" },
  { value: "grooming-completo", label: "B&T Completo" },
  { value: "basico", label: "Basico" },
  { value: "premium", label: "Premium" },
  { value: "enterprise", label: "Enterprise" },
  { value: "free", label: "Free legado" },
  { value: "legacy", label: "Legacy" },
  { value: "completo", label: "Completo" },
];

export const BILLING_OFFER_PLAN_OPTIONS = PLAN_EDIT_OPTIONS.slice(0, 10);

export const BILLING_TYPE_OPTIONS = [
  { value: "UNDEFINED", label: "Cliente escolhe no Asaas" },
  { value: "CREDIT_CARD", label: "Cartão de crédito recorrente" },
  { value: "PIX", label: "PIX mensal" },
  { value: "BOLETO", label: "Boleto mensal" },
];

export const BILLING_EDIT_OPTIONS = [
  { value: "trial", label: "Trial" },
  { value: "active", label: "Ativo / em dia" },
  { value: "past_due", label: "Pendente" },
  { value: "overdue", label: "Atrasado" },
  { value: "blocked", label: "Bloqueado" },
  { value: "canceled", label: "Cancelado" },
  { value: "expired", label: "Expirado" },
];

export const SOURCE_EDIT_OPTIONS = [
  { value: "manual", label: "Manual" },
  { value: "admin", label: "Admin" },
  { value: "trial", label: "Trial" },
  { value: "asaas", label: "Asaas" },
  { value: "stripe", label: "Stripe" },
  { value: "mercado_pago", label: "Mercado Pago" },
  { value: "external", label: "Externo" },
];

export const ONBOARDING_SATISFACTION_OPTIONS = [
  { value: "not_collected", label: "Ainda nao perguntamos" },
  { value: "satisfied", label: "Satisfeito" },
  { value: "neutral", label: "Neutro / precisa de retorno" },
  { value: "dissatisfied", label: "Insatisfeito" },
];
