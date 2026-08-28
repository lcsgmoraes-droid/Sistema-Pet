export function resolveTenantLoginReference(user, selectedTenantRaw = null) {
  const sessionTenant = String(user?.tenant?.name || "").trim();
  if (sessionTenant) return sessionTenant;

  try {
    const selectedTenant =
      typeof selectedTenantRaw === "string" ? JSON.parse(selectedTenantRaw) : selectedTenantRaw;

    return String(selectedTenant?.name || selectedTenant?.nome || selectedTenant?.id || "").trim();
  } catch {
    return "";
  }
}

export function buildInitialAccessCredentials({ tenant, username, password, personName = "" }) {
  const normalizedTenant = String(tenant || "").trim();
  const normalizedUsername = String(username || "")
    .trim()
    .toLowerCase();
  const normalizedPassword = String(password || "");

  if (!normalizedTenant || !normalizedUsername || !normalizedPassword) return null;

  return {
    tenant: normalizedTenant,
    username: normalizedUsername,
    password: normalizedPassword,
    personName: String(personName || "").trim(),
  };
}

export function formatInitialAccessCredentials(credentials) {
  if (!credentials) return "";

  return [
    "Acesso ao CorePet",
    `Loja: ${credentials.tenant}`,
    `Nome de usuario: ${credentials.username}`,
    `Senha inicial: ${credentials.password}`,
    "Login: https://corepet.com.br/login",
  ].join("\n");
}
