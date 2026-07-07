type EmailVerificationParams = {
  emailVerified?: boolean | string | number | null;
  email?: string | null;
};

export function isEmailVerificationSuccess(params?: EmailVerificationParams | null) {
  const value = params?.emailVerified;
  return value === true || value === "1" || value === 1 || value === "true";
}

export function normalizeVerifiedEmailParam(email?: string | null) {
  return typeof email === "string" ? email.trim().toLowerCase() : "";
}
