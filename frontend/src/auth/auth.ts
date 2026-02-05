export type UserPermission = string;

export function getUserPermissions(): UserPermission[] {
  const raw = localStorage.getItem("permissions");
  return raw ? JSON.parse(raw) : [];
}

export function hasPermission(permission: string): boolean {
  const permissions = getUserPermissions();
  return permissions.includes("*") || permissions.includes(permission);
}
