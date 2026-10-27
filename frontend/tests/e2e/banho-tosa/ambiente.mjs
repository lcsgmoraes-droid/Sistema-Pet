const hostsLocais = new Set(["127.0.0.1", "localhost", "[::1]"]);

export function urlLocal(valor, nome) {
  let url;
  try {
    url = new URL(valor);
  } catch {
    throw new Error(`${nome} deve ser uma origem HTTP local valida.`);
  }
  if (
    url.protocol !== "http:" ||
    !hostsLocais.has(url.hostname) ||
    !url.port ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  ) {
    throw new Error(
      `${nome} deve ser uma origem HTTP local com porta explicita. Producao e URLs remotas sao proibidas.`,
    );
  }
  return url.origin;
}

export function ambienteBanhoTosa(env = process.env) {
  if (env.E2E_CREATE_TEST_IDENTITY !== "1") return null;
  return {
    baseURL: urlLocal(env.E2E_BASE_URL || "http://127.0.0.1:5173", "E2E_BASE_URL"),
    apiURL: urlLocal(env.E2E_BT_API_URL || "http://127.0.0.1:8000", "E2E_BT_API_URL"),
  };
}
import process from "node:process";
import { URL } from "node:url";
