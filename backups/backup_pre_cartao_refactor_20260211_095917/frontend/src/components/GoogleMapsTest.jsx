/**
 * Componente de Teste - Google Maps API (Etapa 9.1)
 * 
 * Este é um componente de exemplo para testar se o Google Maps
 * está configurado corretamente no frontend.
 * 
 * NÃO É NECESSÁRIO adicionar este arquivo ao sistema.
 * É apenas para teste e demonstração.
 * 
 * Uso:
 * 1. Importe este componente em alguma página
 * 2. Clique no botão "Testar Google Maps"
 * 3. Veja o resultado no console e na tela
 */

import React, { useState } from 'react';
import { loadGoogleMaps, isGoogleMapsLoaded } from '@/utils/googleMaps';

export default function GoogleMapsTest() {
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleTest = async () => {
    setStatus('loading');
    setMessage('Carregando Google Maps API...');
    setError('');

    try {
      // Tentar carregar Google Maps
      await loadGoogleMaps();
      
      // Verificar se carregou
      if (isGoogleMapsLoaded()) {
        setStatus('success');
        setMessage('✅ Google Maps carregado com sucesso!');
        
        // Teste adicional: criar geocoder
        try {
          const geocoder = new google.maps.Geocoder();
          const testAddress = 'Av. Paulista, São Paulo, SP';
          
          setMessage(`✅ Google Maps funcionando!\n🔍 Testando geocoding de: ${testAddress}...`);
          
          geocoder.geocode({ address: testAddress }, (results, geocodeStatus) => {
            if (geocodeStatus === 'OK' && results[0]) {
              const location = results[0].geometry.location;
              setMessage(
                `✅ TUDO FUNCIONANDO!\n\n` +
                `📍 Endereço testado: ${testAddress}\n` +
                `🗺️ Coordenadas: ${location.lat()}, ${location.lng()}\n` +
                `📋 Endereço formatado: ${results[0].formatted_address}\n\n` +
                `🎯 Sistema pronto para Etapa 9.2!`
              );
              console.log('✅ Teste Google Maps:', {
                address: testAddress,
                lat: location.lat(),
                lng: location.lng(),
                formatted: results[0].formatted_address
              });
            } else {
              setMessage(
                `⚠️ Maps carregado, mas geocoding falhou.\n` +
                `Status: ${geocodeStatus}\n` +
                `Isso pode ser um problema de quota ou restrições.`
              );
            }
          });
        } catch (err) {
          setMessage(
            `✅ Google Maps carregado\n` +
            `⚠️ Mas houve erro no teste: ${err.message}`
          );
        }
      } else {
        setStatus('error');
        setError('Google Maps não disponível após carregamento');
      }
    } catch (err) {
      setStatus('error');
      setError(err.message);
      
      if (err.message.includes('não configurada')) {
        setMessage(
          `❌ Configuração faltando!\n\n` +
          `📝 Passos para corrigir:\n` +
          `1. Obtenha chave em: https://console.cloud.google.com/\n` +
          `2. Edite frontend/.env\n` +
          `3. Adicione: VITE_GOOGLE_MAPS_API_KEY=sua_chave\n` +
          `4. Reinicie o servidor (npm run dev)`
        );
      }
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          🗺️ Teste Google Maps API
          <span className="text-sm font-normal text-gray-500">(Etapa 9.1)</span>
        </h2>
        
        <p className="text-gray-600 mb-6">
          Clique no botão abaixo para verificar se o Google Maps está configurado corretamente.
        </p>

        <button
          onClick={handleTest}
          disabled={status === 'loading'}
          className={`
            px-6 py-3 rounded-lg font-medium transition-colors
            ${status === 'loading' 
              ? 'bg-gray-300 cursor-not-allowed' 
              : 'bg-blue-600 hover:bg-blue-700 text-white'
            }
          `}
        >
          {status === 'loading' ? '⏳ Testando...' : '🧪 Testar Google Maps'}
        </button>

        {message && (
          <div className={`
            mt-6 p-4 rounded-lg whitespace-pre-line
            ${status === 'success' ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}
          `}>
            <p className={`font-mono text-sm ${status === 'success' ? 'text-green-800' : 'text-gray-800'}`}>
              {message}
            </p>
          </div>
        )}

        {error && (
          <div className="mt-6 p-4 rounded-lg bg-red-50 border border-red-200">
            <p className="font-medium text-red-800 mb-2">❌ Erro:</p>
            <p className="font-mono text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="mt-8 pt-6 border-t border-gray-200">
          <h3 className="font-semibold mb-3">📋 Checklist de Configuração:</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li>✅ Chave obtida no Google Cloud Console</li>
            <li>✅ APIs ativadas (Maps JS, Directions, Distance Matrix)</li>
            <li>✅ Restrições configuradas (domínio/IP)</li>
            <li>✅ Conta de cobrança ativa ($200 grátis/mês)</li>
            <li>✅ VITE_GOOGLE_MAPS_API_KEY no frontend/.env</li>
            <li>✅ GOOGLE_MAPS_API_KEY no backend/.env</li>
            <li>✅ Servidor reiniciado após configuração</li>
          </ul>
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>💡 Dica:</strong> Abra o Console do navegador (F12) para ver logs detalhados do teste.
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * COMO USAR ESTE COMPONENTE:
 * 
 * 1. Adicione em uma rota de teste (ex: /teste-maps):
 * 
 * import GoogleMapsTest from '@/components/GoogleMapsTest';
 * 
 * function TestPage() {
 *   return <GoogleMapsTest />;
 * }
 * 
 * 2. Ou adicione temporariamente em alguma página existente
 * 
 * 3. Acesse a página e clique em "Testar Google Maps"
 * 
 * 4. Remova o componente após confirmar que funciona
 */
