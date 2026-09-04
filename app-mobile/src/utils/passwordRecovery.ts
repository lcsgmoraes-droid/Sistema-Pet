export type PasswordResetRequestResponse = {
  expires_in_minutes?: number;
};

export function passwordResetEmailWasSent(
  response: PasswordResetRequestResponse | null | undefined,
): boolean {
  const expiresInMinutes = Number(response?.expires_in_minutes);
  return Number.isFinite(expiresInMinutes) && expiresInMinutes > 0;
}
