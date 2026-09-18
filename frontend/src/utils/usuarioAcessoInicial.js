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

export function buildInitialAccessCredentials({
  tenant,
  username,
  loginPhone,
  password,
  personName = "",
}) {
  const normalizedTenant = String(tenant || "").trim();
  const normalizedUsername = String(username || "")
    .trim()
    .toLowerCase();
  const normalizedLoginPhone = String(loginPhone || "").replace(/\D/g, "");
  const normalizedPassword = String(password || "");

  if (
    (!normalizedLoginPhone && (!normalizedTenant || !normalizedUsername)) ||
    !normalizedPassword
  ) {
    return null;
  }

  return {
    tenant: normalizedTenant,
    username: normalizedUsername,
    loginPhone: normalizedLoginPhone,
    password: normalizedPassword,
    personName: String(personName || "").trim(),
  };
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
