import { formatBrazilianLoginPhone } from "../../utils/loginPhone.js";

function cleanText(value) {
  return typeof value === "string" ? value.trim() : "";
}

export function resolveLayoutSessionIdentity(user) {
  const tenantLabel =
    cleanText(user?.tenant?.login_name) ||
    cleanText(user?.tenant?.name) ||
    cleanText(user?.tenant?.nome) ||
    "Loja atual";

  const loginPhone = cleanText(user?.login_phone);
  const userLabel =
    (loginPhone ? formatBrazilianLoginPhone(loginPhone) : "") ||
    cleanText(user?.username) ||
    cleanText(user?.email) ||
    cleanText(user?.name) ||
    cleanText(user?.nome) ||
    "Usuário";

  const avatarSource = cleanText(user?.name) || cleanText(user?.nome) || userLabel || tenantLabel;

  return {
    tenantLabel,
    userLabel,
    avatarInitial: avatarSource.charAt(0).toUpperCase() || "U",
  };
}
