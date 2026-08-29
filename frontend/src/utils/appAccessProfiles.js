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
