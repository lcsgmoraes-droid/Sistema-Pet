/**
 * Ecommerce API Client
 * Instância axios para o módulo de e-commerce (loja pública).
 * Headers de autenticação são adicionados por chamada, não na instância.
 */
import axios from 'axios';

// baseURL vazio: as chamadas já incluem /api/ no path (ex: /api/ecommerce/...)
// Não usar VITE_API_URL aqui para não duplicar o prefixo /api
const ecommerceApi = axios.create({
  baseURL: '',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default ecommerceApi;
