// Perfis de acesso ao app (mobile) que uma Pessoa pode ter — independente do
// login administrativo do ERP. Usado na tela Usuários (criação e edição).
export const PERFIS_APP = [
  { value: "cliente", label: "Cliente", description: "Compras, pedidos e dados do cliente" },
  {
    value: "gestor",
    label: "Gestor",
    description: "Indicadores financeiros e gerenciais, somente para consulta",
  },
  {
    value: "funcionario",
    label: "Funcionário",
    description: "Rotinas internas liberadas para funcionários",
  },
  {
    value: "banho_tosa",
    label: "Banho & Tosa",
    description: "Agenda, check-in e andamento dos pets",
  },
  { value: "entregador", label: "Entregador", description: "Entregas e rotas do app" },
  { value: "taxi_dog", label: "Taxi Dog", description: "Coleta, rota e devolução dos pets" },
  { value: "veterinario", label: "Veterinário", description: "Agenda e recursos veterinários" },
];

export function canManageAppAccessProfiles(user) {
  if (!user) return false;

  const roleName = String(user.role?.name || user.role || "")
    .trim()
    .toLowerCase();
  const permissions = Array.isArray(user.permissions) ? user.permissions : [];

  return (
    user.is_admin === true ||
    ["admin", "administrador", "super admin", "superadmin"].includes(roleName) ||
    permissions.includes("*") ||
    permissions.includes("usuarios.manage")
  );
}
