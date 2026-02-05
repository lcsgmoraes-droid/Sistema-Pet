import { useState, useEffect } from 'react';
import { X, Search, RotateCcw, AlertCircle, Check, Filter, Package, Layers } from 'lucide-react';
import api from '../api';

export default function ModalDevolucao({ caixaId, onClose, onSucesso }) {
  const [passo, setPasso] = useState(1); // 1: listar vendas, 2: selecionar itens
  const [vendas, setVendas] = useState([]);
  const [vendaSelecionada, setVendaSelecionada] = useState(null);
  const [itensSelecionados, setItensSelecionados] = useState({});
  const [quantidades, setQuantidades] = useState({});
  const [motivo, setMotivo] = useState('');
  const [gerarCredito, setGerarCredito] = useState(false);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');
  
  // 🆕 Estados para devolução de KIT
  const [modoDevolucaoKit, setModoDevolucaoKit] = useState({}); // {itemId: 'kit_inteiro' | 'componentes'}
  const [componentesSelecionados, setComponentesSelecionados] = useState({}); // {itemId: {componenteId: true/false}}
  const [quantidadesComponentes, setQuantidadesComponentes] = useState({}); // {itemId: {componenteIndex: quantidade}}
  
  // Filtros
  const [filtros, setFiltros] = useState({
    busca: '',
    data_inicio: '',
    data_fim: '',
    status: 'finalizada'
  });

  useEffect(() => {
    buscarVendas();
  }, [filtros]);

  const buscarVendas = async () => {
    setLoading(true);
    setErro('');

    try {
      const params = {
        per_page: 50,
        ...filtros
      };
      
      const response = await api.get('/vendas', { params });
      setVendas(response.data.vendas || []);
    } catch (error) {
      console.error('Erro ao buscar vendas:', error);
      setErro('Erro ao carregar vendas');
    } finally {
      setLoading(false);
    }
  };

  const selecionarVenda = async (venda) => {
    setLoading(true);
    setErro('');

    try {
      // Buscar detalhes completos da venda
      const response = await api.get(`/vendas/${venda.id}`);
      setVendaSelecionada(response.data);
      
      // Inicializar quantidades com o máximo disponível
      const qtds = {};
      response.data.itens.forEach(item => {
        qtds[item.id] = item.quantidade;
      });
      setQuantidades(qtds);
      
      setPasso(2);
    } catch (error) {
      console.error('Erro ao buscar venda:', error);
      setErro(error.response?.data?.detail || 'Erro ao carregar detalhes da venda');
    } finally {
      setLoading(false);
    }
  };

  const toggleItem = (itemId) => {
    const wasSelected = itensSelecionados[itemId];
    
    setItensSelecionados(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
    
    // 🆕 Se está desmarcando, limpar estados do KIT
    if (wasSelected) {
      setModoDevolucaoKit(prev => {
        const novo = { ...prev };
        delete novo[itemId];
        return novo;
      });
      setComponentesSelecionados(prev => {
        const novo = { ...prev };
        delete novo[itemId];
        return novo;
      });
      setQuantidadesComponentes(prev => {
        const novo = { ...prev };
        delete novo[itemId];
        return novo;
      });
    }
  };

  const handleQuantidadeChange = (itemId, valor) => {
    const item = vendaSelecionada.itens.find(i => i.id === itemId);
    const qtdMaxima = item.quantidade;
    const qtdNova = Math.min(Math.max(0, parseFloat(valor) || 0), qtdMaxima);
    
    setQuantidades(prev => ({
      ...prev,
      [itemId]: qtdNova
    }));
  };

  // 🆕 Funções para gerenciar devolução de KIT
  const isItemKit = (item) => {
    return item.tipo_produto === 'KIT' && item.composicao_kit && item.composicao_kit.length > 0;
  };

  const handleEscolhaModoKit = (itemId, modo) => {
    setModoDevolucaoKit(prev => ({
      ...prev,
      [itemId]: modo
    }));

    // Se escolheu componentes, inicializar estados
    if (modo === 'componentes') {
      const item = vendaSelecionada.itens.find(i => i.id === itemId);
      if (item && item.composicao_kit) {
        // Inicializar todos componentes como NÃO selecionados
        const compSel = {};
        const compQtd = {};
        item.composicao_kit.forEach((comp, index) => {
          compSel[index] = false;
          // Quantidade máxima = quantidade do componente no KIT * quantidade do KIT vendido
          compQtd[index] = comp.quantidade * item.quantidade;
        });
        
        setComponentesSelecionados(prev => ({
          ...prev,
          [itemId]: compSel
        }));
        
        setQuantidadesComponentes(prev => ({
          ...prev,
          [itemId]: compQtd
        }));
      }
    }
  };

  const toggleComponente = (itemId, componenteIndex) => {
    setComponentesSelecionados(prev => ({
      ...prev,
      [itemId]: {
        ...(prev[itemId] || {}),
        [componenteIndex]: !prev[itemId]?.[componenteIndex]
      }
    }));
  };

  const handleQuantidadeComponenteChange = (itemId, componenteIndex, valor) => {
    const item = vendaSelecionada.itens.find(i => i.id === itemId);
    const componente = item.composicao_kit[componenteIndex];
    const qtdMaxima = componente.quantidade * item.quantidade;
    const qtdNova = Math.min(Math.max(0, parseFloat(valor) || 0), qtdMaxima);
    
    setQuantidadesComponentes(prev => ({
      ...prev,
      [itemId]: {
        ...(prev[itemId] || {}),
        [componenteIndex]: qtdNova
      }
    }));
  };

  const handleConfirmar = async () => {
    // 🆕 Validar KITs: se selecionou KIT, precisa escolher modo
    const itensKitSemEscolha = Object.keys(itensSelecionados)
      .filter(id => itensSelecionados[id])
      .filter(id => {
        const item = vendaSelecionada.itens.find(i => i.id === parseInt(id));
        return isItemKit(item) && !modoDevolucaoKit[id];
      });

    if (itensKitSemEscolha.length > 0) {
      setErro('Para itens KIT, você deve escolher entre devolver o KIT inteiro ou selecionar componentes');
      return;
    }

    // 🆕 Construir lista de itens para devolução
    const itensDevolucao = [];

    Object.keys(itensSelecionados)
      .filter(id => itensSelecionados[id])
      .forEach(id => {
        const itemId = parseInt(id);
        const item = vendaSelecionada.itens.find(i => i.id === itemId);

        if (isItemKit(item)) {
          const modo = modoDevolucaoKit[id];

          if (modo === 'kit_inteiro') {
            // Devolver KIT inteiro
            itensDevolucao.push({
              item_id: itemId,
              quantidade: quantidades[id]
            });
          } else if (modo === 'componentes') {
            // Devolver apenas componentes selecionados
            const compSel = componentesSelecionados[id] || {};
            const compQtd = quantidadesComponentes[id] || {};

            const componentesParaDevolver = Object.keys(compSel)
              .filter(index => compSel[index])
              .map(index => parseInt(index));

            if (componentesParaDevolver.length === 0) {
              setErro(`Você deve selecionar pelo menos um componente do KIT "${item.produto_nome}"`);
              return;
            }

            // Para cada componente selecionado, criar entrada de devolução
            componentesParaDevolver.forEach(index => {
              const componente = item.composicao_kit[index];
              const qtd = compQtd[index] || 0;

              if (qtd <= 0) {
                setErro(`Quantidade do componente "${componente.produto_nome}" deve ser maior que zero`);
                return;
              }

              // 🔥 IMPORTANTE: Enviar como devolução de componente
              // O backend precisa entender que é um componente de KIT
              itensDevolucao.push({
                produto_id: componente.produto_id,
                quantidade: qtd,
                preco_unitario: (item.preco_unitario / item.composicao_kit.reduce((sum, c) => sum + c.quantidade, 0)) * componente.quantidade,
                is_componente_kit: true,
                kit_item_id: itemId
              });
            });
          }
        } else {
          // Item normal (não KIT)
          itensDevolucao.push({
            item_id: itemId,
            quantidade: quantidades[id]
          });
        }
      });

    if (itensDevolucao.length === 0) {
      setErro('Selecione pelo menos um item para devolução');
      return;
    }

    // Validar quantidades
    const temQuantidadeInvalida = itensDevolucao.some(item => item.quantidade <= 0);
    if (temQuantidadeInvalida) {
      setErro('Todas as quantidades devem ser maiores que zero');
      return;
    }

    if (!motivo.trim()) {
      setErro('Informe o motivo da devolução');
      return;
    }

    setLoading(true);
    setErro('');

    try {
      await api.post(`/vendas/${vendaSelecionada.id}/devolucao`, {
        caixa_id: caixaId,
        itens: itensDevolucao,
        motivo: motivo,
        gerar_credito: gerarCredito
      });

      alert('Devolução registrada com sucesso!');
      onSucesso();
    } catch (error) {
      console.error('Erro ao registrar devolução:', error);
      setErro(error.response?.data?.detail || 'Erro ao registrar devolução');
    } finally {
      setLoading(false);
    }
  };

  const calcularTotalDevolucao = () => {
    if (!vendaSelecionada) return 0;
    
    let total = 0;

    Object.keys(itensSelecionados)
      .filter(id => itensSelecionados[id])
      .forEach(id => {
        const item = vendaSelecionada.itens.find(i => i.id === parseInt(id));
        
        if (isItemKit(item)) {
          const modo = modoDevolucaoKit[id];

          if (modo === 'kit_inteiro') {
            // Valor do KIT inteiro
            const qtd = quantidades[id] || 0;
            total += item.preco_unitario * qtd;
          } else if (modo === 'componentes') {
            // Valor proporcional dos componentes
            const compSel = componentesSelecionados[id] || {};
            const compQtd = quantidadesComponentes[id] || {};
            
            // Calcular valor proporcional baseado na composição
            const totalQuantidadeComposicao = item.composicao_kit.reduce((sum, c) => sum + c.quantidade, 0);
            
            Object.keys(compSel)
              .filter(index => compSel[index])
              .forEach(index => {
                const componente = item.composicao_kit[index];
                const qtd = compQtd[index] || 0;
                
                // Valor proporcional do componente
                const valorProporcional = (item.preco_unitario / totalQuantidadeComposicao) * componente.quantidade;
                const qtdKits = qtd / componente.quantidade;
                total += valorProporcional * qtdKits;
              });
          }
        } else {
          // Item normal
          const qtd = quantidades[id] || 0;
          total += item.preco_unitario * qtd;
        }
      });

    return total;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
              <RotateCcw className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Devolução</h2>
              <p className="text-sm text-gray-500">
                {passo === 1 ? 'Selecione a venda' : 'Selecionar itens para devolução'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Passo 1: Lista de Vendas */}
          {passo === 1 && (
            <div className="space-y-4">
              {/* Filtros */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Buscar
                    </label>
                    <input
                      type="text"
                      value={filtros.busca}
                      onChange={(e) => setFiltros({ ...filtros, busca: e.target.value })}
                      placeholder="Número da venda, cliente..."
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Data Início
                    </label>
                    <input
                      type="date"
                      value={filtros.data_inicio}
                      onChange={(e) => setFiltros({ ...filtros, data_inicio: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Data Fim
                    </label>
                    <input
                      type="date"
                      value={filtros.data_fim}
                      onChange={(e) => setFiltros({ ...filtros, data_fim: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>

              {/* Lista de Vendas */}
              {loading ? (
                <div className="text-center py-12">
                  <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
                  <p className="mt-4 text-gray-600">Carregando vendas...</p>
                </div>
              ) : vendas.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 rounded-lg">
                  <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">Nenhuma venda encontrada</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {vendas.map((venda) => (
                    <button
                      key={venda.id}
                      onClick={() => selecionarVenda(venda)}
                      className="w-full text-left p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-semibold text-gray-900">
                            Venda #{venda.numero_venda || venda.id}
                          </div>
                          <div className="text-sm text-gray-600 mt-1">
                            Cliente: {venda.cliente?.nome || 'Consumidor Final'}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {venda.data_criacao ? new Date(venda.data_criacao).toLocaleString('pt-BR', {
                              day: '2-digit',
                              month: '2-digit',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            }) : 'Data não disponível'}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-green-600">
                            R$ {venda.total.toFixed(2)}
                          </div>
                          <div className={`text-xs mt-1 px-2 py-1 rounded ${
                            venda.status === 'finalizada' ? 'bg-green-100 text-green-800' :
                            venda.status === 'baixa_parcial' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {venda.status === 'finalizada' ? 'Finalizada' :
                             venda.status === 'baixa_parcial' ? 'Parcial' : 'Aberta'}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {erro && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                  <AlertCircle className="w-5 h-5" />
                  <span>{erro}</span>
                </div>
              )}
            </div>
          )}

          {/* Passo 2: Selecionar Itens */}
          {passo === 2 && vendaSelecionada && (
            <div className="space-y-6">
              {/* Informações da Venda */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-2">Venda #{vendaSelecionada.numero_venda || vendaSelecionada.id}</h3>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Data:</span>
                    <span className="ml-2 font-medium">
                      {vendaSelecionada.data_criacao ? new Date(vendaSelecionada.data_criacao).toLocaleString('pt-BR', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      }) : 'Data não disponível'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Cliente:</span>
                    <span className="ml-2 font-medium">{vendaSelecionada.cliente?.nome || 'Consumidor Final'}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Total:</span>
                    <span className="ml-2 font-medium text-green-600">R$ {vendaSelecionada.total.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Lista de Itens */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">Itens da Venda</h3>
                <div className="space-y-2">
                  {vendaSelecionada.itens.map((item) => {
                    const isKit = isItemKit(item);
                    const modoKit = modoDevolucaoKit[item.id];

                    return (
                      <div
                        key={item.id}
                        className={`border rounded-lg p-4 transition-colors ${
                          itensSelecionados[item.id] ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                        }`}
                      >
                        <div className="flex items-start gap-4">
                          <input
                            type="checkbox"
                            checked={itensSelecionados[item.id] || false}
                            onChange={() => toggleItem(item.id)}
                            className="mt-1 w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                          />
                          
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <div className="font-medium text-gray-900">{item.produto_nome}</div>
                              {isKit && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded">
                                  <Layers className="w-3 h-3" />
                                  KIT
                                </span>
                              )}
                            </div>
                            <div className="text-sm text-gray-600">
                              Preço unitário: R$ {item.preco_unitario.toFixed(2)} | 
                              Qtd vendida: {item.quantidade}
                            </div>
                            
                            {/* 🆕 ESCOLHA: KIT INTEIRO OU COMPONENTES */}
                            {itensSelecionados[item.id] && isKit && (
                              <div className="mt-4 bg-white border-2 border-purple-300 rounded-lg p-4">
                                <div className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                  <Package className="w-5 h-5 text-purple-600" />
                                  Como deseja devolver este KIT?
                                </div>
                                
                                <div className="space-y-3">
                                  <label className="flex items-start gap-3 cursor-pointer group">
                                    <input
                                      type="radio"
                                      name={`modo-kit-${item.id}`}
                                      checked={modoKit === 'kit_inteiro'}
                                      onChange={() => handleEscolhaModoKit(item.id, 'kit_inteiro')}
                                      className="mt-1 w-4 h-4 text-blue-600 focus:ring-2 focus:ring-blue-500"
                                    />
                                    <div className="flex-1">
                                      <div className="font-medium text-gray-800 group-hover:text-blue-700 transition-colors">
                                        📦 Devolver KIT Inteiro
                                      </div>
                                      <p className="text-xs text-gray-600 mt-1">
                                        Devolve o KIT completo como uma unidade
                                      </p>
                                    </div>
                                  </label>

                                  <label className="flex items-start gap-3 cursor-pointer group">
                                    <input
                                      type="radio"
                                      name={`modo-kit-${item.id}`}
                                      checked={modoKit === 'componentes'}
                                      onChange={() => handleEscolhaModoKit(item.id, 'componentes')}
                                      className="mt-1 w-4 h-4 text-purple-600 focus:ring-2 focus:ring-purple-500"
                                    />
                                    <div className="flex-1">
                                      <div className="font-medium text-gray-800 group-hover:text-purple-700 transition-colors">
                                        🧩 Selecionar Componentes
                                      </div>
                                      <p className="text-xs text-gray-600 mt-1">
                                        Escolha quais componentes do KIT devolver
                                      </p>
                                    </div>
                                  </label>
                                </div>
                              </div>
                            )}

                            {/* QUANTIDADE - KIT INTEIRO */}
                            {itensSelecionados[item.id] && !isKit && (
                              <div className="mt-3 flex items-center gap-4">
                                <label className="text-sm font-medium text-gray-700">
                                  Quantidade a devolver:
                                </label>
                                <input
                                  type="number"
                                  step="0.01"
                                  min="0"
                                  max={item.quantidade}
                                  value={quantidades[item.id]}
                                  onChange={(e) => handleQuantidadeChange(item.id, e.target.value)}
                                  className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-600">
                                  Subtotal: R$ {(item.preco_unitario * (quantidades[item.id] || 0)).toFixed(2)}
                                </span>
                              </div>
                            )}

                            {/* QUANTIDADE - KIT INTEIRO (quando escolheu devolver inteiro) */}
                            {itensSelecionados[item.id] && isKit && modoKit === 'kit_inteiro' && (
                              <div className="mt-3 flex items-center gap-4">
                                <label className="text-sm font-medium text-gray-700">
                                  Quantidade de KITs a devolver:
                                </label>
                                <input
                                  type="number"
                                  step="0.01"
                                  min="0"
                                  max={item.quantidade}
                                  value={quantidades[item.id]}
                                  onChange={(e) => handleQuantidadeChange(item.id, e.target.value)}
                                  className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-600">
                                  Subtotal: R$ {(item.preco_unitario * (quantidades[item.id] || 0)).toFixed(2)}
                                </span>
                              </div>
                            )}

                            {/* LISTA DE COMPONENTES (quando escolheu devolver por componentes) */}
                            {itensSelecionados[item.id] && isKit && modoKit === 'componentes' && (
                              <div className="mt-4 bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4">
                                <div className="font-semibold text-gray-800 mb-3">
                                  Selecione os componentes a devolver:
                                </div>
                                <div className="space-y-3">
                                  {item.composicao_kit.map((componente, compIndex) => {
                                    const compSelecionado = componentesSelecionados[item.id]?.[compIndex];
                                    const qtdMaxima = componente.quantidade * item.quantidade;

                                    return (
                                      <div
                                        key={compIndex}
                                        className={`border rounded-lg p-3 transition-colors ${
                                          compSelecionado ? 'border-purple-500 bg-white' : 'border-gray-200 bg-gray-50'
                                        }`}
                                      >
                                        <div className="flex items-start gap-3">
                                          <input
                                            type="checkbox"
                                            checked={compSelecionado || false}
                                            onChange={() => toggleComponente(item.id, compIndex)}
                                            className="mt-1 w-4 h-4 text-purple-600 rounded focus:ring-2 focus:ring-purple-500"
                                          />
                                          <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                              <Package className="w-4 h-4 text-gray-500" />
                                              <span className="font-medium text-gray-800">
                                                {componente.produto_nome}
                                              </span>
                                            </div>
                                            <div className="text-xs text-gray-600 mt-1">
                                              Qtd no KIT: {componente.quantidade} | Qtd total disponível: {qtdMaxima}
                                            </div>
                                            
                                            {compSelecionado && (
                                              <div className="mt-2 flex items-center gap-3">
                                                <label className="text-xs font-medium text-gray-700">
                                                  Quantidade:
                                                </label>
                                                <input
                                                  type="number"
                                                  step="0.01"
                                                  min="0"
                                                  max={qtdMaxima}
                                                  value={quantidadesComponentes[item.id]?.[compIndex] || 0}
                                                  onChange={(e) => handleQuantidadeComponenteChange(item.id, compIndex, e.target.value)}
                                                  className="w-24 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-purple-500"
                                                />
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Motivo */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Motivo da Devolução *
                </label>
                <textarea
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  placeholder="Descreva o motivo da devolução..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={3}
                />
              </div>

              {/* Opção de Crédito ou Dinheiro */}
              <div className="bg-gradient-to-br from-purple-50 to-blue-50 border-2 border-purple-200 rounded-lg p-5">
                <label className="block text-sm font-bold text-gray-800 mb-3">
                  💳 Tipo de Devolução
                </label>
                <div className="space-y-3">
                  <label className="flex items-start gap-3 cursor-pointer group">
                    <input
                      type="radio"
                      checked={!gerarCredito}
                      onChange={() => setGerarCredito(false)}
                      className="mt-1 w-5 h-5 text-green-600 focus:ring-2 focus:ring-green-500"
                    />
                    <div className="flex-1">
                      <div className="font-semibold text-gray-800 group-hover:text-green-700 transition-colors">
                        💵 Devolver em Dinheiro
                      </div>
                      <p className="text-xs text-gray-600 mt-1">
                        O valor será devolvido em dinheiro e registrado como saída de caixa
                      </p>
                    </div>
                  </label>

                  <label className="flex items-start gap-3 cursor-pointer group">
                    <input
                      type="radio"
                      checked={gerarCredito}
                      onChange={() => setGerarCredito(true)}
                      className="mt-1 w-5 h-5 text-purple-600 focus:ring-2 focus:ring-purple-500"
                    />
                    <div className="flex-1">
                      <div className="font-semibold text-gray-800 group-hover:text-purple-700 transition-colors">
                        🎁 Gerar Crédito para o Cliente
                      </div>
                      <p className="text-xs text-gray-600 mt-1">
                        O valor será convertido em crédito para uso em futuras compras (sem movimentação de caixa)
                      </p>
                    </div>
                  </label>
                </div>

                {gerarCredito && !vendaSelecionada?.cliente_id && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-300 rounded-lg">
                    <p className="text-xs text-yellow-800 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      <span><strong>Atenção:</strong> Esta venda não possui cliente vinculado. Para gerar crédito, é necessário ter um cliente cadastrado.</span>
                    </p>
                  </div>
                )}
              </div>

              {/* Total */}
              <div className={`border-2 rounded-lg p-4 ${gerarCredito ? 'bg-purple-50 border-purple-300' : 'bg-orange-50 border-orange-200'}`}>
                <div className="flex justify-between items-center">
                  <div>
                    <span className="text-lg font-semibold text-gray-900">
                      {gerarCredito ? 'Crédito a Gerar:' : 'Total da Devolução:'}
                    </span>
                    {gerarCredito && vendaSelecionada?.cliente && (
                      <p className="text-xs text-gray-600 mt-1">
                        Cliente: <strong>{vendaSelecionada.cliente.nome}</strong>
                      </p>
                    )}
                  </div>
                  <span className={`text-2xl font-bold ${gerarCredito ? 'text-purple-600' : 'text-orange-600'}`}>
                    R$ {calcularTotalDevolucao().toFixed(2)}
                  </span>
                </div>
              </div>

              {erro && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                  <AlertCircle className="w-5 h-5" />
                  <span>{erro}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-6 bg-gray-50">
          <div className="flex justify-between">
            <button
              onClick={passo === 1 ? onClose : () => {
                setPasso(1);
                setVendaSelecionada(null);
                setItensSelecionados({});
                setQuantidades({});
                setMotivo('');
                setErro('');
              }}
              disabled={loading}
              className="px-6 py-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {passo === 1 ? 'Cancelar' : 'Voltar'}
            </button>

            {passo === 2 && (
              <button
                onClick={handleConfirmar}
                disabled={loading || Object.values(itensSelecionados).filter(Boolean).length === 0}
                className="flex items-center gap-2 px-8 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Processando...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-5 h-5" />
                    <span>Confirmar Devolução</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
