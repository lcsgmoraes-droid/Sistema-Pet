/**
 * Ecommerce API Client
 * Instância axios para o módulo de e-commerce (loja pública).
 * Headers de autenticação são adicionados por chamada, não na instância.
 */
import axios from 'axios';

const BASE_URL = import.meta.env.DEV
  ? '/api'
  : (import.meta.env.VITE_API_URL || '/api');

const ecommerceApi = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default ecommerceApi;
