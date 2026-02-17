/**
 * ABA 6: Chat IA - Página Principal
 * Chat com assistente financeiro inteligente
 */

import React, { useState, useEffect, useRef } from 'react';
import api from '../../api';
import { toast } from 'react-hot-toast';
import { Send, Loader, MessageSquare, Plus, Trash2, Bot, User } from 'lucide-react';

export default function ChatIA() {
  const [conversas, setConversas] = useState([]);
  const [conversaAtiva, setConversaAtiva] = useState(null);
  const [mensagens, setMensagens] = useState([]);
  const [mensagemInput, setMensagemInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    carregarConversas();
  }, []);

  useEffect(() => {
    if (conversaAtiva) {
      carregarMensagens(conversaAtiva);
    }
  }, [conversaAtiva]);

  useEffect(() => {
    scrollToBottom();
  }, [mensagens]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const carregarConversas = async () => {
    try {
      const response = await api.get('/chat/conversas');
      setConversas(response.data);
    } catch (error) {
      console.error('Erro ao carregar conversas:', error);
    }
  };

  const carregarMensagens = async (conversaId) => {
    setLoading(true);
    try {
      const response = await api.get(`/chat/conversa/${conversaId}/mensagens`);
      setMensagens(response.data);
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error);
      toast.error('Erro ao carregar mensagens');
    } finally {
      setLoading(false);
    }
  };

  const novaConversa = async () => {
    try {
      const response = await api.post('/chat/nova-conversa', {});
      
      setConversas([response.data, ...conversas]);
      setConversaAtiva(response.data.id);
      setMensagens([]);
      toast.success('Nova conversa criada!');
    } catch (error) {
      console.error('Erro ao criar conversa:', error);
      toast.error('Erro ao criar conversa');
    }
  };

  const enviarMensagem = async (e) => {
    e.preventDefault();
    
    if (!mensagemInput.trim() || !conversaAtiva) return;

    setEnviando(true);
    const mensagemTexto = mensagemInput;
    setMensagemInput('');

    try {
      const response = await api.post('/chat/enviar', {
        conversa_id: conversaAtiva,
        mensagem: mensagemTexto
      });

      // Adicionar ambas mensagens ao estado
      setMensagens([
        ...mensagens,
        {
          id: response.data.mensagem_usuario.id,
          tipo: 'usuario',
          conteudo: response.data.mensagem_usuario.conteudo,
          criado_em: response.data.mensagem_usuario.criado_em
        },
        {
          id: response.data.mensagem_ia.id,
          tipo: 'assistente',
          conteudo: response.data.mensagem_ia.conteudo,
          criado_em: response.data.mensagem_ia.criado_em
        }
      ]);

      // Atualizar lista de conversas
      carregarConversas();
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      toast.error('Erro ao enviar mensagem');
      setMensagemInput(mensagemTexto); // Restaurar mensagem
    } finally {
      setEnviando(false);
    }
  };

  const deletarConversa = async (conversaId) => {
    if (!confirm('Deseja deletar esta conversa?')) return;

    try {
      await api.delete(`/chat/conversa/${conversaId}`);

      setConversas(conversas.filter(c => c.id !== conversaId));
      if (conversaAtiva === conversaId) {
        setConversaAtiva(null);
        setMensagens([]);
      }
      toast.success('Conversa deletada');
    } catch (error) {
      console.error('Erro ao deletar conversa:', error);
      toast.error('Erro ao deletar conversa');
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Bot className="w-8 h-8 text-blue-600" />
              Chat IA Financeiro
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              Pergunte sobre seu fluxo de caixa, projeções e saúde financeira
            </p>
          </div>
          <button
            onClick={novaConversa}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-5 h-5" />
            Nova Conversa
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Lista de conversas */}
        <div className="w-80 bg-white border-r border-gray-200 overflow-y-auto">
          <div className="p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">
              Conversas Recentes
            </h2>
            
            {conversas.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Nenhuma conversa ainda</p>
                <button
                  onClick={novaConversa}
                  className="mt-3 text-blue-600 text-sm hover:underline"
                >
                  Criar primeira conversa
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {conversas.map((conversa) => (
                  <div
                    key={conversa.id}
                    onClick={() => setConversaAtiva(conversa.id)}
                    className={`p-3 rounded-lg cursor-pointer transition-colors group ${
                      conversaAtiva === conversa.id
                        ? 'bg-blue-50 border-2 border-blue-200'
                        : 'bg-gray-50 hover:bg-gray-100'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {conversa.titulo || 'Nova conversa'}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {conversa.total_mensagens} mensagens
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deletarConversa(conversa.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-700 transition-opacity"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Área de chat */}
        <div className="flex-1 flex flex-col bg-gray-50">
          {!conversaAtiva ? (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <Bot className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">Selecione ou crie uma conversa</p>
                <p className="text-sm mt-2">
                  Faça perguntas sobre seu fluxo de caixa e receba análises inteligentes
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Mensagens */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {loading ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader className="w-8 h-8 animate-spin text-blue-600" />
                  </div>
                ) : mensagens.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    <div className="text-center">
                      <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>Inicie a conversa fazendo uma pergunta</p>
                      <div className="mt-4 text-sm space-y-1">
                        <p className="text-gray-400">Exemplos:</p>
                        <p className="text-blue-600">"Qual é meu saldo atual?"</p>
                        <p className="text-blue-600">"Como está minha situação financeira?"</p>
                        <p className="text-blue-600">"Há algum alerta?"</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  mensagens.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.tipo === 'usuario' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`flex gap-3 max-w-3xl ${
                          msg.tipo === 'usuario' ? 'flex-row-reverse' : 'flex-row'
                        }`}
                      >
                        <div
                          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                            msg.tipo === 'usuario'
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-200 text-gray-700'
                          }`}
                        >
                          {msg.tipo === 'usuario' ? (
                            <User className="w-5 h-5" />
                          ) : (
                            <Bot className="w-5 h-5" />
                          )}
                        </div>
                        <div
                          className={`px-4 py-3 rounded-lg ${
                            msg.tipo === 'usuario'
                              ? 'bg-blue-600 text-white'
                              : 'bg-white text-gray-900 border border-gray-200'
                          }`}
                        >
                          <p className="text-sm whitespace-pre-wrap">{msg.conteudo}</p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="border-t border-gray-200 bg-white p-4">
                <form onSubmit={enviarMensagem} className="flex gap-2">
                  <input
                    type="text"
                    value={mensagemInput}
                    onChange={(e) => setMensagemInput(e.target.value)}
                    placeholder="Digite sua pergunta..."
                    disabled={enviando}
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                  />
                  <button
                    type="submit"
                    disabled={enviando || !mensagemInput.trim()}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                  >
                    {enviando ? (
                      <Loader className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </form>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
