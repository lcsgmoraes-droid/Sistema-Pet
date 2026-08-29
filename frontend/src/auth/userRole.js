const normalizeRoleName = (user) =>
  String(user?.role?.name || "")
    .trim()
    .toLowerCase();

export const isAdminRole = (user) => ["admin", "administrador"].includes(normalizeRoleName(user));

export const getDefaultAuthenticatedRoute = (user) => {
  const roleName = normalizeRoleName(user);

  if (roleName === "caixa") {
    return "/pdv";
  }

  if (isAdminRole(user) || roleName === "gerente") {
    return "/dashboard";
  }

  return "/lembretes";
};
