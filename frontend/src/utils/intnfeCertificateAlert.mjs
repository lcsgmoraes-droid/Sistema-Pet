function localDateKey(now) {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function intnfeCertificateAlertKey(tenantId, now = new Date()) {
  const normalizedTenant = String(tenantId || "").trim();
  if (!normalizedTenant) return null;
  return `intnfe_certificate_alert:${normalizedTenant}:${localDateKey(now)}`;
}

export function shouldNotifyIntNFeCertificate(status, tenantId, storage, now = new Date()) {
  const key = intnfeCertificateAlertKey(tenantId, now);
  return Boolean(status?.certificado_alerta && key && storage?.getItem(key) !== "shown");
}

export function markIntNFeCertificateAlert(tenantId, storage, now = new Date()) {
  const key = intnfeCertificateAlertKey(tenantId, now);
  if (key) storage?.setItem(key, "shown");
  return key;
}
