export function isVeterinarioProfile(user) {
  const roleName = String(user?.role?.name || "").toLowerCase();
  if (roleName.includes("veter")) {
    return true;
  }

  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  return permissions.some((permission) => {
    const normalized = String(permission || "").toLowerCase();
    return normalized.includes("veterin") || normalized.startsWith("vet.");
  });
}

export function isMobileViewport() {
  return typeof window !== "undefined" && window.innerWidth < 768;
}
