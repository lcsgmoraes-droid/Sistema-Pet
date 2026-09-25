export function resolveTenantLoginReference(user, selectedTenantRaw = null) {
  const sessionTenant = String(
    user?.tenant?.login_name || user?.tenant?.nome_acesso || user?.tenant?.name || "",
  ).trim();
  if (sessionTenant) return sessionTenant;

  try {
    const selectedTenant =
      typeof selectedTenantRaw === "string" ? JSON.parse(selectedTenantRaw) : selectedTenantRaw;

    return String(
      selectedTenant?.login_name ||
        selectedTenant?.nome_acesso ||
        selectedTenant?.name ||
        selectedTenant?.nome ||
        selectedTenant?.id ||
        "",
    ).trim();
  } catch {
    return "";
  }
}

export function formatInitialAccessCredentials(credentials) {
  if (!credentials) return "";

  const lines = ["Acesso ao CorePet"];
  if (credentials.loginPhone) {
    lines.push(`Celular: ${credentials.loginPhone}`);
  } else {
    lines.push(`Loja: ${credentials.tenant}`);
    lines.push(`Nome de usuario: ${credentials.username}`);
  }
  lines.push(`Senha inicial: ${credentials.password}`);
  lines.push("Login: https://corepet.com.br/login");
  return lines.join("\n");
}
