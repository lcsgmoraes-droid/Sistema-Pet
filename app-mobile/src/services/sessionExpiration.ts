type SessionExpiredHandler = () => void | Promise<void>;

let sessionExpiredHandler: SessionExpiredHandler | null = null;
let expirationReported = false;

export function registerSessionExpiredHandler(handler: SessionExpiredHandler): () => void {
  sessionExpiredHandler = handler;

  return () => {
    if (sessionExpiredHandler === handler) {
      sessionExpiredHandler = null;
    }
  };
}

export function markSessionActive(): void {
  expirationReported = false;
}

export async function notifySessionExpired(): Promise<void> {
  if (!sessionExpiredHandler || expirationReported) return;

  expirationReported = true;
  await sessionExpiredHandler();
}
