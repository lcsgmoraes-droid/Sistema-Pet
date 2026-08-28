export function normalizePessoaAppLogin(appLogin) {
  if (!appLogin) return appLogin;

  const email = String(appLogin.email || "")
    .trim()
    .toLowerCase();

  return {
    ...appLogin,
    email: email || null,
  };
}
