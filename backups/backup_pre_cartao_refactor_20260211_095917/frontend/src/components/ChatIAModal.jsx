import React, { useState, useEffect, useRef } from 'react';
import { X, Send, Sparkles, MessageCircle, Loader } from 'lucide-react';
import api from '../api';

const ChatIAModal = ({ isOpen, onClose, contexto }) => {
  const [mensagens, setMensagens] = useState([]);
  const [inputMensagem, setInputMensagem] = useState('');
  const [enviando, setEnviando] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (isOpen && mensagens.length === 0) {
      // Mensagem de boas-vindas
      setMensagens([{
        tipo: 'ia',
        conteudo: `Olá! Sou seu especialista financeiro com IA. Analisando seu ${contexto?.tipo || 'relatório'}...\n\nPosso ajudar com:\n• Análise de resultados\n• Sugestões de melhoria\n• Comparações de períodos\n• Projeções financeiras\n\nO que deseja saber?`,
        timestamp: new Date()
      }]);
    }
  }, [isOpen, mensagens.length, contexto]);

  useEffect(() => {
    scrollToBottom();
  }, [mensagens]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const enviarMensagem = async () => {
    if (!inputMensagem.trim()) return;

    const novaMensagem = {
      tipo: 'usuario',
      conteudo: inputMensagem,
      timestamp: new Date()
    };

    setMensagens(prev => [...prev, novaMensagem]);
    setInputMensagem('');
    setEnviando(true);

    try {
      const response = await api.post('/api/ia/chat', {
        mensagem: inputMensagem,
        contexto: contexto
      });

      const respostaIA = {
        tipo: 'ia',
        conteudo: response.data.resposta,
        timestamp: new Date()
      };

      setMensagens(prev => [...prev, respostaIA]);
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      const erroMsg = {
        tipo: 'ia',
        conteudo: 'Desculpe, houve um erro ao processar sua mensagem. Tente novamente.',
        timestamp: new Date()
      };
      setMensagens(prev => [...prev, erroMsg]);
    } finally {
      setEnviando(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      enviarMensagem();
    }
  };

  const sugestoesPergunta = [
    'Como melhorar minha margem de lucro?',
    'Quais são os principais gastos?',
    'Compare com o mês anterior',
    'Há despesas atípicas?'
  ];

  const usarSugestao = (sugestao) => {
    setInputMensagem(sugestao);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl h-[600px] flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-4 rounded-t-2xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-white bg-opacity-20 p-2 rounded-lg">
              <Sparkles size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold">Especialista Financeiro IA</h2>
              <p className="text-sm text-purple-100">Análise inteligente dos seus dados</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Contexto */}
        {contexto && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-indigo-200 p-3">
            <div className="text-sm text-indigo-800">
              📊 Analisando: <span className="font-semibold">{contexto.tipo}</span>
              {contexto.periodo && (
                <span className="ml-2">• {contexto.periodo}</span>
              )}
              {contexto.valor && (
                <span className="ml-2">• Valor: R$ {contexto.valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
              )}
            </div>
          </div>
        )}

        {/* Mensagens */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {mensagens.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.tipo === 'usuario' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl p-4 ${
                  msg.tipo === 'usuario'
                    ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {msg.tipo === 'ia' && (
                  <div className="flex items-center gap-2 mb-2">
                    <MessageCircle size={16} className="text-purple-600" />
                    <span className="text-xs font-semibold text-purple-600">IA Especialista</span>
                  </div>
                )}
                <p className="whitespace-pre-wrap">{msg.conteudo}</p>
                <span className="text-xs opacity-70 mt-2 block">
                  {msg.timestamp.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))}
          {enviando && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl p-4">
                <div className="flex items-center gap-2">
                  <Loader className="animate-spin text-purple-600" size={20} />
                  <span className="text-gray-600">Analisando...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Sugestões */}
        {mensagens.length <= 1 && (
          <div className="border-t border-gray-200 p-3 bg-gray-50">
            <p className="text-xs text-gray-600 mb-2 font-medium">💡 Sugestões de perguntas:</p>
            <div className="flex flex-wrap gap-2">
              {sugestoesPergunta.map((sugestao, idx) => (
                <button
                  key={idx}
                  onClick={() => usarSugestao(sugestao)}
                  className="text-xs px-3 py-1.5 bg-white border border-purple-200 text-purple-700 rounded-full hover:bg-purple-50 transition-colors"
                >
                  {sugestao}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="border-t border-gray-200 p-4 bg-white rounded-b-2xl">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputMensagem}
              onChange={(e) => setInputMensagem(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Digite sua pergunta..."
              disabled={enviando}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100"
            />
            <button
              onClick={enviarMensagem}
              disabled={!inputMensagem.trim() || enviando}
              className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatIAModal;
