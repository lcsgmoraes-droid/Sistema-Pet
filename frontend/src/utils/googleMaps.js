/**
 * Google Maps Loader - Etapa 9.1
 * 
 * Carrega o Google Maps API dinamicamente quando necessário.
 * Evita carregar a API na inicialização do app.
 * 
 * Uso:
 * ```javascript
 * import { loadGoogleMaps, isGoogleMapsLoaded } from '@/utils/googleMaps';
 * 
 * // Carregar antes de usar
 * await loadGoogleMaps();
 * 
 * // Verificar se já está carregado
 * if (isGoogleMapsLoaded()) {
 *   // Usar google.maps...
 * }
 * ```
 */

// Estado de carregamento
let isLoading = false;
let isLoaded = false;
let loadPromise = null;

/**
 * Verifica se o Google Maps já está carregado
 */
export function isGoogleMapsLoaded() {
  return isLoaded && typeof window.google !== 'undefined' && window.google.maps;
}

/**
 * Carrega o Google Maps API dinamicamente
 * 
 * @returns {Promise<void>} Promise que resolve quando o Maps estiver carregado
 * @throws {Error} Se a API Key não estiver configurada
 */
export async function loadGoogleMaps() {
  // Se já está carregado, retorna imediatamente
  if (isGoogleMapsLoaded()) {
    return Promise.resolve();
  }

  // Se já está carregando, retorna a promise existente
  if (isLoading && loadPromise) {
    return loadPromise;
  }

  // Pega a API Key do ambiente
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  
  if (!apiKey || apiKey === 'your_google_maps_api_key_here') {
    console.warn('[Google Maps] API Key não configurada. Configure VITE_GOOGLE_MAPS_API_KEY no arquivo .env');
    throw new Error('Google Maps API Key não configurada');
  }

  // Inicia o carregamento
  isLoading = true;
  
  loadPromise = new Promise((resolve, reject) => {
    try {
      // Cria o elemento script
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
      script.async = true;
      script.defer = true;

      // Callback de sucesso
      script.onload = () => {
        isLoaded = true;
        isLoading = false;
        console.log('[Google Maps] API carregada com sucesso');
        resolve();
      };

      // Callback de erro
      script.onerror = (error) => {
        isLoading = false;
        console.error('[Google Maps] Erro ao carregar API:', error);
        reject(new Error('Falha ao carregar Google Maps API'));
      };

      // Adiciona o script ao head
      document.head.appendChild(script);
    } catch (error) {
      isLoading = false;
      console.error('[Google Maps] Erro ao criar script:', error);
      reject(error);
    }
  });

  return loadPromise;
}

/**
 * Hook React para carregar Google Maps
 * 
 * @returns {Object} { isLoaded, isLoading, error, load }
 */
export function useGoogleMaps() {
  const [state, setState] = React.useState({
    isLoaded: isGoogleMapsLoaded(),
    isLoading: false,
    error: null
  });

  const load = React.useCallback(async () => {
    if (state.isLoaded) return;
    
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      await loadGoogleMaps();
      setState({ isLoaded: true, isLoading: false, error: null });
    } catch (error) {
      setState({ isLoaded: false, isLoading: false, error: error.message });
    }
  }, [state.isLoaded]);

  return { ...state, load };
}

/**
 * Reseta o estado do loader (útil para testes)
 */
export function resetGoogleMapsLoader() {
  isLoading = false;
  isLoaded = false;
  loadPromise = null;
}

export default {
  loadGoogleMaps,
  isGoogleMapsLoaded,
  useGoogleMaps,
  resetGoogleMapsLoader
};
