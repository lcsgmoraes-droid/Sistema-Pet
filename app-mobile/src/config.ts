// Configuracao central da API.
// Ordem de resolucao:
// 1. EXPO_PUBLIC_API_URL sobrescreve tudo, util para preview/staging.
// 2. Em dev, EXPO_PUBLIC_DEV_API_URL ou localhost.
// 3. Em release, EXPO_PUBLIC_PROD_API_URL ou producao.
const DEFAULT_DEV_API_URL = 'http://localhost:8000/api';
const DEFAULT_PROD_API_URL = 'https://mlprohub.com.br/api';

const ENV_API_URL = process.env.EXPO_PUBLIC_API_URL;
const DEV_API_URL = process.env.EXPO_PUBLIC_DEV_API_URL || DEFAULT_DEV_API_URL;
const PROD_API_URL = process.env.EXPO_PUBLIC_PROD_API_URL || DEFAULT_PROD_API_URL;

function normalizeApiUrl(url: string) {
  return url.trim().replace(/\/+$/, '');
}

export const API_BASE_URL = normalizeApiUrl(
  ENV_API_URL || (__DEV__ ? DEV_API_URL : PROD_API_URL),
);

export const PONTOS = {
  // A cada R$1 gasto = X pontos
  PONTOS_POR_REAL: 1,
  // 100 pontos = R$5 de desconto
  REAIS_POR_100_PONTOS: 5,
  // Bonus de boas-vindas ao cadastrar
  BONUS_CADASTRO: 50,
};
