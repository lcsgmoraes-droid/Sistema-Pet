import React, { useState } from 'react';
import type { HandoffItem } from '../../../stores/whatsappStore';
import { whatsappService } from '../../../services/whatsappService';

interface BotAssistProps {
  handoff: HandoffItem | null;
}

export const BotAssist: React.FC<BotAssistProps> = ({ handoff }) => {
  const [testText, setTestText] = useState('');
  const [sentimentResult, setSentimentResult] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  const handleAnalyze = async () => {
    if (!testText.trim()) return;
    
    setIsAnalyzing(true);
    try {
      const result = await whatsappService.testSentiment(testText);
      setSentimentResult(result);
    } catch (error) {
      console.error('Error analyzing sentiment:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };
  
  const suggestedResponses = [
    'Entendo sua frustração. Vou verificar isso imediatamente.',
    'Obrigado por aguardar. Estou analisando sua solicitação.',
    'Vou encaminhar para o setor responsável e retorno em breve.',
    'Consegui resolver! Precisa de mais alguma coisa?',
  ];
  
  if (!handoff) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <p className="text-sm text-gray-400 text-center">
          Selecione uma conversa para ver sugestões
        </p>
      </div>
    );
  }
  
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Bot Assist 🤖</h3>
        <p className="text-xs text-gray-500 mt-1">
          Análise de sentimento e sugestões
        </p>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Sentiment Analyzer */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Analisar Sentimento
          </h4>
          <textarea
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="Cole uma mensagem do cliente..."
            rows={4}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleAnalyze}
            disabled={!testText.trim() || isAnalyzing}
            className="mt-2 w-full px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isAnalyzing ? 'Analisando...' : 'Analisar'}
          </button>
          
          {sentimentResult && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-600">Score:</span>
                <span className={`text-sm font-bold ${
                  sentimentResult.score > 0 ? 'text-green-600' : 
                  sentimentResult.score < 0 ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {sentimentResult.score.toFixed(2)}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-600">Label:</span>
                <span className="text-sm font-bold text-gray-900">
                  {sentimentResult.label}
                </span>
              </div>
              
              {sentimentResult.emotions.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-gray-600">Emoções:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {sentimentResult.emotions.map((emotion: string, i: number) => (
                      <span key={i} className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                        {emotion}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {sentimentResult.triggers.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-gray-600">Gatilhos:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {sentimentResult.triggers.map((trigger: string, i: number) => (
                      <span key={i} className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">
                        {trigger}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {sentimentResult.should_handoff && (
                <div className="pt-2 border-t border-gray-200">
                  <span className="text-xs font-medium text-red-600">
                    ⚠️ Recomenda handoff humano
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Suggested Responses */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Respostas Sugeridas
          </h4>
          <div className="space-y-2">
            {suggestedResponses.map((response, i) => (
              <button
                key={i}
                onClick={() => {
                  navigator.clipboard.writeText(response);
                }}
                className="w-full text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 text-sm text-gray-700 transition-colors"
              >
                {response}
              </button>
            ))}
          </div>
        </div>
        
        {/* Quick Actions */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Ações Rápidas
          </h4>
          <div className="space-y-2">
            <button className="w-full px-4 py-2 bg-orange-50 text-orange-700 border border-orange-200 rounded-lg text-sm font-medium hover:bg-orange-100 transition-colors">
              📋 Ver histórico completo
            </button>
            <button className="w-full px-4 py-2 bg-purple-50 text-purple-700 border border-purple-200 rounded-lg text-sm font-medium hover:bg-purple-100 transition-colors">
              📊 Análise de perfil
            </button>
            <button className="w-full px-4 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors">
              🔗 Criar ticket
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
