// Configuração central da API
// Em produção, aponta para mlprohub.com.br; em dev, para o IP local da máquina

// ⚠️ Se mudar de rede Wi-Fi, verifique o IP rodando no terminal:
//    Get-NetIPAddress -AddressFamily IPv4
const DEV_API_URL = 'https://postdiscoidal-grouty-chandra.ngrok-free.dev'; // ngrok tunnel (temporário para teste)
const PROD_API_URL = 'https://mlprohub.com.br/api';

// Durante desenvolvimento via Expo Go: use o IP local
// Em produção (build de release): use a URL de produção
const IS_DEV = __DEV__;

export const API_BASE_URL = IS_DEV ? DEV_API_URL : PROD_API_URL;

export const PONTOS = {
  // A cada R$1 gasto = X pontos
  PONTOS_POR_REAL: 1,
  // 100 pontos = R$5 de desconto
  REAIS_POR_100_PONTOS: 5,
  // Bônus de boas-vindas ao cadastrar
  BONUS_CADASTRO: 50,
};
