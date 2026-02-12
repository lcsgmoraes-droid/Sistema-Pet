import React, { useState, useEffect, useRef } from 'react';
import { 
  FiUser, FiDollarSign, FiShoppingCart, FiAlertCircle, 
  FiTrendingUp, FiClock, FiPhone, FiMail, FiMapPin,
  FiChevronDown, FiChevronUp, FiPackage, FiMessageCircle,
  FiSend, FiBarChart2, FiLink
} from 'react-icons/fi';
import api from '../api';

/**
 * Widget de informações do cliente para PDV
 * Exibe: resumo financeiro, pets, histórico de compras, oportunidades e sugestões
 */
export default function ClienteInfoWidget({ clienteId }) {
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);
  
  // Chat IA
  const [mensagemChat, setMensagemChat] = useState('');
  const [conversaChat, setConversaChat] = useState([]);
  const [loadingChat, setLoadingChat] = useState(false);
  const chatEndRef = useRef(null);
  
  // Estados de expansão das seções
  const [expandido, setExpandido] = useState({
    resumo: false,
    pets: false,
    compras: false,
    oportunidades: false,
    sugestoes: false,
    relacionados: false,
    sazonalidade: false,
    chat: false
  });

  useEffect(() => {
    if (clienteId) {
      carregarInfoCliente();
    }
  }, [clienteId]);

  const carregarInfoCliente = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get(`/clientes/${clienteId}/info-pdv`);
      setInfo(response.data);
    } catch (err) {
      console.error('Erro ao carregar informações do cliente:', err);
      setError(err.response?.data?.detail || 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const toggleSecao = (secao) => {
    setExpandido(prev => ({
      ...prev,
      [secao]: !prev[secao]
    }));
  };

  const enviarMensagemChat = async () => {
    if (!mensagemChat.trim()) return;
    
    const novaMensagem = mensagemChat;
    setMensagemChat('');
    
    // Adicionar mensagem do usuário
    setConversaChat(prev => [...prev, { tipo: 'user', texto: novaMensagem }]);
    
    try {
      setLoadingChat(true);
      const response = await api.post(`/clientes/${clienteId}/chat-pdv`, {
        mensagem: novaMensagem
      });
      
      // Adicionar resposta da IA
      setConversaChat(prev => [...prev, { 
        tipo: 'ia', 
        texto: response.data.resposta,
        ia_disponivel: response.data.ia_disponivel
      }]);
      
      // Scroll para o fim
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
      
    } catch (err) {
      console.error('Erro no chat:', err);
      setConversaChat(prev => [...prev, { 
        tipo: 'erro', 
        texto: 'Erro ao processar mensagem. Tente novamente.' 
      }]);
    } finally {
      setLoadingChat(false);
    }
  };

  const handleKeyPressChat = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      enviarMensagemChat();
    }
  };

  if (!clienteId) {
    return (
      <div className="bg-white rounded-lg shadow-md p-4 text-center text-gray-500">
        <FiUser className="mx-auto text-4xl mb-2" />
        <p>Selecione um cliente para ver informações</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        <FiAlertCircle className="inline mr-2" />
        {error}
      </div>
    );
  }

  if (!info) return null;

  const { 
    cliente, 
    resumo_financeiro, 
    pets, 
    ultimas_compras, 
    oportunidades, 
    sugestoes,
    produtos_relacionados,
    padroes_sazonais
  } = info;

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden max-h-[85vh] overflow-y-auto">
      {/* CABEÇALHO DO CLIENTE */}
      <div className="bg-gradient-to-r from-indigo-100 to-purple-100 p-4 border-b">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-bold text-lg text-gray-800 mb-1">{cliente.nome}</h3>
            <div className="text-sm text-gray-600 space-y-1">
              {cliente.cpf_cnpj && (
                <p className="flex items-center gap-1">
                  <FiUser className="text-xs" />
                  {cliente.cpf_cnpj}
                </p>
              )}
              {cliente.telefone && (
                <p className="flex items-center gap-1">
                  <FiPhone className="text-xs" />
                  {cliente.telefone}
                </p>
              )}
              {cliente.email && (
                <p className="flex items-center gap-1 truncate">
                  <FiMail className="text-xs" />
                  {cliente.email}
                </p>
              )}
              {cliente.endereco && (
                <p className="flex items-center gap-1 text-xs">
                  <FiMapPin className="text-xs" />
                  {cliente.endereco}, {cliente.bairro} - {cliente.cidade}/{cliente.estado}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* RESUMO FINANCEIRO */}
      <SecaoCollapsible
        titulo="Resumo Financeiro"
        icone={<FiDollarSign />}
        expandido={expandido.resumo}
        onToggle={() => toggleSecao('resumo')}
        badge={resumo_financeiro.numero_compras}
      >
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-green-50 rounded-lg p-3">
            <p className="text-xs text-green-600 font-medium mb-1">Total Gasto</p>
            <p className="text-lg font-bold text-green-700">
              R$ {resumo_financeiro.total_gasto.toFixed(2)}
            </p>
          </div>
          
          <div className="bg-blue-50 rounded-lg p-3">
            <p className="text-xs text-blue-600 font-medium mb-1">Ticket Médio</p>
            <p className="text-lg font-bold text-blue-700">
              R$ {resumo_financeiro.ticket_medio.toFixed(2)}
            </p>
          </div>
          
          <div className="bg-purple-50 rounded-lg p-3">
            <p className="text-xs text-purple-600 font-medium mb-1">Nº Compras</p>
            <p className="text-lg font-bold text-purple-700">
              {resumo_financeiro.numero_compras}
            </p>
          </div>
          
          <div className="bg-orange-50 rounded-lg p-3">
            <p className="text-xs text-orange-600 font-medium mb-1">Maior Compra</p>
            <p className="text-lg font-bold text-orange-700">
              R$ {resumo_financeiro.maior_compra.valor.toFixed(2)}
            </p>
            {resumo_financeiro.maior_compra.data && (
              <p className="text-xs text-gray-500 mt-1">
                {resumo_financeiro.maior_compra.data}
              </p>
            )}
          </div>
        </div>

        {resumo_financeiro.ultima_compra.data && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-500 flex items-center gap-1">
              <FiClock className="text-xs" />
              Última compra: {resumo_financeiro.ultima_compra.data} - R$ {resumo_financeiro.ultima_compra.valor.toFixed(2)}
            </p>
          </div>
        )}
      </SecaoCollapsible>

      {/* PETS REGISTRADOS */}
      {pets && pets.length > 0 && (
        <SecaoCollapsible
          titulo="Pets Registrados"
          icone={<FiUser />}
          expandido={expandido.pets}
          onToggle={() => toggleSecao('pets')}
          badge={pets.length}
        >
          <div className="space-y-2">
            {pets.map(pet => (
              <div key={pet.id} className="flex items-center gap-3 p-2 bg-gray-50 rounded-lg">
                <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-bold">
                  {pet.nome[0].toUpperCase()}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{pet.nome}</p>
                  <p className="text-xs text-gray-500">
                    {pet.especie} {pet.raca && `• ${pet.raca}`}
                    {pet.peso && ` • ${pet.peso}kg`}
                    {pet.idade_anos !== null && ` • ${pet.idade_anos} anos`}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </SecaoCollapsible>
      )}

      {/* OPORTUNIDADES */}
      {oportunidades && oportunidades.length > 0 && (
        <SecaoCollapsible
          titulo="Oportunidades de Venda"
          icone={<FiAlertCircle />}
          expandido={expandido.oportunidades}
          onToggle={() => toggleSecao('oportunidades')}
          badge={oportunidades.length}
          badgeColor="bg-orange-500"
        >
          <div className="space-y-2">
            {oportunidades.map((op, idx) => (
              <div 
                key={idx} 
                className={`p-3 rounded-lg border-l-4 ${
                  op.urgencia === 'alta' 
                    ? 'bg-red-50 border-red-400' 
                    : 'bg-yellow-50 border-yellow-400'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-gray-800 text-sm">{op.produto_nome}</p>
                    <p className="text-xs text-gray-600 mt-1">{op.mensagem}</p>
                  </div>
                  {op.urgencia === 'alta' && (
                    <span className="ml-2 px-2 py-1 bg-red-500 text-white text-xs rounded-full">
                      Urgente
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Atrasado {op.dias_atraso} dias
                </p>
              </div>
            ))}
          </div>
        </SecaoCollapsible>
      )}

      {/* SUGESTÕES */}
      {sugestoes && sugestoes.length > 0 && (
        <SecaoCollapsible
          titulo="Produtos Favoritos"
          icone={<FiTrendingUp />}
          expandido={expandido.sugestoes}
          onToggle={() => toggleSecao('sugestoes')}
          badge={sugestoes.length}
        >
          <div className="space-y-2">
            {sugestoes.map((sug, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
                <div className="flex-1">
                  <p className="font-medium text-gray-800 text-sm">{sug.nome}</p>
                  <p className="text-xs text-gray-500">
                    Comprado {sug.vezes_comprado}x
                    {sug.ultima_compra && ` • Última: ${sug.ultima_compra}`}
                  </p>
                </div>
                <p className="font-bold text-indigo-600 ml-2">
                  R$ {sug.preco.toFixed(2)}
                </p>
              </div>
            ))}
          </div>
        </SecaoCollapsible>
      )}

      {/* ÚLTIMAS COMPRAS */}
      {ultimas_compras && ultimas_compras.length > 0 && (
        <SecaoCollapsible
          titulo="Últimas Compras"
          icone={<FiShoppingCart />}
          expandido={expandido.compras}
          onToggle={() => toggleSecao('compras')}
          badge={ultimas_compras.length}
        >
          <div className="space-y-3">
            {ultimas_compras.map((compra, idx) => (
              <div key={idx} className="border-l-4 border-indigo-300 pl-3 py-2 bg-gray-50 rounded-r-lg">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="text-xs text-gray-500">
                      {compra.data} • Venda #{compra.numero_venda}
                    </p>
                    <p className="font-bold text-indigo-600">
                      R$ {compra.valor_total.toFixed(2)}
                    </p>
                  </div>
                </div>
                
                {compra.produtos && compra.produtos.length > 0 && (
                  <div className="space-y-1 mt-2">
                    {compra.produtos.map((prod, pidx) => (
                      <p key={pidx} className="text-xs text-gray-600 flex items-center gap-1">
                        <FiPackage className="text-xs" />
                        {prod.quantidade}x {prod.nome} - R$ {prod.valor.toFixed(2)}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </SecaoCollapsible>
      )}

      {/* PRODUTOS RELACIONADOS */}
      {produtos_relacionados && produtos_relacionados.length > 0 && (
        <SecaoCollapsible
          titulo="Produtos Comprados Juntos"
          icone={<FiLink />}
          expandido={expandido.relacionados}
          onToggle={() => toggleSecao('relacionados')}
          badge={produtos_relacionados.length}
          badgeColor="bg-purple-500"
        >
          <div className="space-y-2">
            {produtos_relacionados.map((rel, idx) => (
              <div key={idx} className="p-3 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-purple-600">
                    {rel.vezes_juntos}x comprados juntos
                  </span>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-800">{rel.produto1.nome}</span>
                    <span className="text-purple-600 font-bold">R$ {rel.produto1.preco.toFixed(2)}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-800">{rel.produto2.nome}</span>
                    <span className="text-purple-600 font-bold">R$ {rel.produto2.preco.toFixed(2)}</span>
                  </div>
                </div>
                <p className="text-xs text-purple-600 mt-2 italic">
                  💡 Sugestão: Oferecer combo!
                </p>
              </div>
            ))}
          </div>
        </SecaoCollapsible>
      )}

      {/* PADRÕES SAZONAIS */}
      {padroes_sazonais && padroes_sazonais.length > 0 && (
        <SecaoCollapsible
          titulo="Padrões de Compra"
          icone={<FiBarChart2 />}
          expandido={expandido.sazonalidade}
          onToggle={() => toggleSecao('sazonalidade')}
          badge={padroes_sazonais.length}
          badgeColor="bg-green-500"
        >
          <div className="space-y-2">
            {padroes_sazonais.map((padrao, idx) => (
              <div key={idx} className="p-3 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-green-700">{padrao.mes_ano}</span>
                  <span className="text-sm text-green-600">{padrao.numero_compras} compras</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-600">Total:</span>
                    <span className="font-bold text-green-700 ml-1">R$ {padrao.total_gasto.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Ticket médio:</span>
                    <span className="font-bold text-green-700 ml-1">R$ {padrao.ticket_medio.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SecaoCollapsible>
      )}

      {/* CHAT IA */}
      <SecaoCollapsible
        titulo="Chat IA - Assistente de Vendas"
        icone={<FiMessageCircle />}
        expandido={expandido.chat}
        onToggle={() => toggleSecao('chat')}
        badgeColor="bg-blue-500"
      >
        <div className="space-y-3">
          {/* Mensagens sugeridas */}
          {conversaChat.length === 0 && (
            <div className="space-y-2">
              <p className="text-xs text-gray-500 mb-2">Perguntas sugeridas:</p>
              {[
                "Quais os produtos favoritos?",
                "Quando foi a última compra?",
                "Quais pets ele tem?",
                "Quanto já gastou total?"
              ].map((sugestao, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setMensagemChat(sugestao);
                    setTimeout(() => enviarMensagemChat(), 100);
                  }}
                  className="w-full text-left px-3 py-2 text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg transition-colors"
                >
                  {sugestao}
                </button>
              ))}
            </div>
          )}

          {/* Histórico de conversa */}
          <div className="max-h-64 overflow-y-auto space-y-2">
            {conversaChat.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.tipo === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${
                  msg.tipo === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : msg.tipo === 'erro'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {msg.texto}
                  {msg.tipo === 'ia' && !msg.ia_disponivel && (
                    <p className="text-xs mt-1 opacity-70">💡 Modo básico (IA não configurada)</p>
                  )}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Input de mensagem */}
          <div className="flex gap-2">
            <input
              type="text"
              value={mensagemChat}
              onChange={(e) => setMensagemChat(e.target.value)}
              onKeyPress={handleKeyPressChat}
              placeholder="Digite sua pergunta..."
              disabled={loadingChat}
              className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            />
            <button
              onClick={enviarMensagemChat}
              disabled={loadingChat || !mensagemChat.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loadingChat ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <FiSend className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </SecaoCollapsible>
    </div>
  );
}

/**
 * Componente de seção colapsável
 */
function SecaoCollapsible({ 
  titulo, 
  icone, 
  expandido, 
  onToggle, 
  badge, 
  badgeColor = "bg-indigo-500",
  children 
}) {
  return (
    <div className="border-b border-gray-200">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-indigo-600">{icone}</span>
          <h4 className="font-semibold text-gray-800">{titulo}</h4>
          {badge !== undefined && (
            <span className={`${badgeColor} text-white text-xs px-2 py-1 rounded-full`}>
              {badge}
            </span>
          )}
        </div>
        {expandido ? (
          <FiChevronUp className="text-gray-400" />
        ) : (
          <FiChevronDown className="text-gray-400" />
        )}
      </button>
      
      {expandido && (
        <div className="px-4 pb-4">
          {children}
        </div>
      )}
    </div>
  );
}
