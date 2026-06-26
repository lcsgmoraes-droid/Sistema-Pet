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
  { value: "basico", label: "Basico" },
  { value: "premium", label: "Premium" },
  { value: "enterprise", label: "Enterprise" },
  { value: "free", label: "Free legado" },
  { value: "legacy", label: "Legacy" },
  { value: "completo", label: "Completo" },
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
