export function buildCorePetLoginUrl(email = "") {
  const params = new URLSearchParams({ emailVerified: "1" });
  const normalizedEmail = String(email || "")
    .trim()
    .toLowerCase();

  if (normalizedEmail) {
    params.set("email", normalizedEmail);
  }

  return `corepet://app/login?${params.toString()}`;
}
