import React, { useState, useEffect } from 'react';
import api from '../api';

const Comissoes = () => {
  const [funcionarios, setFuncionarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [funcionarioSelecionado, setFuncionarioSelecionado] = useState(null);
  const [configuracoes, setConfiguracoes] = useState([]);
  const [arvoreProdutos, setArvoreProdutos] = useState([]);
  const [loadingArvore, setLoadingArvore] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    carregarFuncionarios();
  }, []);

  const carregarFuncionarios = async () => {
    try {
      setLoading(true);
      const response = await api.get('/comissoes/configuracoes/funcionarios');
      if (response.data.success) {
        setFuncionarios(response.data.data);
      }
    } catch (error) {
      console.error('Erro ao carregar funcionários:', error);
      setError('Erro ao carregar funcionários com comissões');
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = async (funcionarioId = null) => {
    setFuncionarioSelecionado(funcionarioId);
    setShowModal(true);
    setLoadingArvore(true);
    
    try {
      // Carregar árvore de produtos
      const arvoreResponse = await api.get('/comissoes/arvore-produtos');
      if (arvoreResponse.data.success) {
        setArvoreProdutos(arvoreResponse.data.data);
      }

      // Se está editando, carregar configurações existentes
      if (funcionarioId) {
        const configResponse = await api.get(`/comissoes/configuracoes/funcionario/${funcionarioId}`);
        if (configResponse.data.success) {
          setConfiguracoes(configResponse.data.data);
        }
      }
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      setError('Erro ao carregar dados de configuração');
    } finally {
      setLoadingArvore(false);
    }
  };

  const fecharModal = () => {
    setShowModal(false);
    setFuncionarioSelecionado(null);
    setConfiguracoes([]);
    setArvoreProdutos([]);
    carregarFuncionarios(); // ✅ Atualiza a lista ao fechar
  };

  const duplicarConfiguracao = async (funcionarioOrigemId) => {
    const funcionarioDestinoId = prompt('Digite o ID do funcionário de destino:');
    if (!funcionarioDestinoId) return;

    try {
      const response = await api.post('/comissoes/configuracoes/duplicar', {
        funcionario_origem_id: parseInt(funcionarioOrigemId),
        funcionario_destino_id: parseInt(funcionarioDestinoId)
      });

      if (response.data.success) {
        alert(response.data.message);
        carregarFuncionarios();
      }
    } catch (error) {
      console.error('Erro ao duplicar configuração:', error);
      alert('Erro ao duplicar configuração');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Cadastro de Comissões</h1>
            <p className="text-gray-600 mt-1">Gerencie as comissões dos funcionários</p>
          </div>
          <button
            onClick={() => abrirModal()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <span>+</span>
            Nova Comissão
          </button>
        </div>
      </div>

      {/* Erro */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Lista de Funcionários */}
      <div className="bg-white rounded-lg shadow">
        {funcionarios.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <p className="text-lg mb-2">Nenhuma comissão configurada</p>
            <p className="text-sm">Clique em "Nova Comissão" para começar</p>
          </div>
        ) : (
          <div className="divide-y">
            {funcionarios.map((funcionario) => (
              <div
                key={funcionario.id}
                className="p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                onClick={() => abrirModal(funcionario.id)}
              >
                <div className="flex justify-between items-center">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-600 font-semibold">
                          {funcionario.nome.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-800">{funcionario.nome}</h3>
                        <p className="text-sm text-gray-500">{funcionario.cargo}</p>
                      </div>
                    </div>
                    <div className="mt-2 flex gap-4 text-sm text-gray-600">
                      <span>
                        <strong>{funcionario.categorias}</strong> categorias
                      </span>
                      <span>
                        <strong>{funcionario.subcategorias}</strong> subcategorias
                      </span>
                      <span>
                        <strong>{funcionario.produtos}</strong> produtos específicos
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        abrirModal(funcionario.id);
                      }}
                      className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded"
                    >
                      Editar
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        duplicarConfiguracao(funcionario.id);
                      }}
                      className="px-3 py-1 text-gray-600 hover:bg-gray-100 rounded"
                      title="Duplicar configuração para outro funcionário"
                    >
                      Duplicar
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal de Configuração */}
      {showModal && (
        <ModalConfiguracao
          funcionarioId={funcionarioSelecionado}
          configuracoes={configuracoes}
          arvoreProdutos={arvoreProdutos}
          loading={loadingArvore}
          onClose={fecharModal}
          onSave={() => {
            carregarFuncionarios();
            fecharModal(); // ✅ Fecha o modal após salvar
          }}
        />
      )}
    </div>
  );
};

// Modal de Configuração
const ModalConfiguracao = ({ funcionarioId, configuracoes, arvoreProdutos, loading, onClose, onSave }) => {
  const [funcionarios, setFuncionarios] = useState([]);
  const [funcionarioSel, setFuncionarioSel] = useState(funcionarioId || '');
  const [dataFechamento, setDataFechamento] = useState('');
  const [regras, setRegras] = useState({
    desconta_taxa_cartao: true,
    desconta_impostos: true,
    desconta_taxa_entrega: false,
    comissao_venda_parcial: true, // Nova opção
  });
  const [categoriasExpanded, setCategoriasExpanded] = useState({});
  const [configuracao, setConfiguracao] = useState({});
  const [itemSelecionado, setItemSelecionado] = useState(null);
  const [configuracoesParaSalvar, setConfiguracoesParaSalvar] = useState([]);
  const [salvando, setSalvando] = useState(false);
  const [progressoSalvamento, setProgressoSalvamento] = useState({ atual: 0, total: 0 });
  const [regrasOriginais, setRegrasOriginais] = useState(null);

  useEffect(() => {
    carregarFuncionarios();
  }, []);

  useEffect(() => {
    // Processar configurações existentes
    const configMap = {};
    configuracoes.forEach(config => {
      const key = `${config.tipo}-${config.referencia_id}`;
      configMap[key] = config;
    });
    setConfiguracao(configMap);
    
    // CARREGAR REGRAS da primeira configuração (todas compartilham as mesmas regras)
    if (configuracoes.length > 0) {
      const primeiraConfig = configuracoes[0];
      const regrasCarregadas = {
        desconta_taxa_cartao: primeiraConfig.desconta_taxa_cartao ?? true,
        desconta_impostos: primeiraConfig.desconta_impostos ?? true,
        desconta_taxa_entrega: primeiraConfig.desconta_custo_entrega ?? false,
        comissao_venda_parcial: primeiraConfig.comissao_venda_parcial ?? true,
      };
      setRegras(regrasCarregadas);
      setRegrasOriginais(regrasCarregadas); // Salvar estado original
    }
  }, [configuracoes]);

  const carregarFuncionarios = async () => {
    try {
      const response = await api.get('/comissoes/funcionarios');
      if (response.data.success) {
        setFuncionarios(response.data.data);
        
        // Se estiver editando, carregar data de fechamento do funcionário
        if (funcionarioId) {
          const funcionario = response.data.data.find(f => f.id === parseInt(funcionarioId));
          if (funcionario && funcionario.data_fechamento_comissao) {
            setDataFechamento(String(funcionario.data_fechamento_comissao));
          }
        }
      }
    } catch (error) {
      console.error('Erro ao carregar funcionários:', error);
    }
  };

  const toggleCategoria = (catId) => {
    setCategoriasExpanded(prev => ({
      ...prev,
      [catId]: !prev[catId]
    }));
  };

  const selecionarItem = (tipo, id, nome) => {
    const key = `${tipo}-${id}`;
    const configExistente = configuracao[key];

    setItemSelecionado({
      tipo,
      id,
      nome,
      tipo_calculo: configExistente?.tipo_calculo || 'percentual',
      percentual: configExistente?.percentual || 10,
      percentual_loja: configExistente?.percentual_loja || 50,
      permite_edicao_venda: configExistente?.permite_edicao_venda || false,
      observacoes: configExistente?.observacoes || '',
    });
  };

  const adicionarConfiguracao = () => {
    if (!funcionarioSel) {
      alert('Selecione um funcionário');
      return;
    }

    if (!itemSelecionado) {
      alert('Selecione um item para configurar');
      return;
    }

    // Verificar se já existe na lista
    const jaDuplicado = configuracoesParaSalvar.some(
      c => c.tipo === itemSelecionado.tipo && c.referencia_id === itemSelecionado.id
    );
    
    if (jaDuplicado) {
      alert('Este item já foi adicionado à lista!');
      return;
    }

    // Verificar conflitos de hierarquia
    if (itemSelecionado.tipo === 'categoria') {
      const temProdutosOuSubs = configuracoesParaSalvar.some(
        c => (c.tipo === 'subcategoria' || c.tipo === 'produto') && c.nome.includes(itemSelecionado.nome)
      );
      if (temProdutosOuSubs) {
        const confirma = confirm(
          `⚠️ ATENÇÃO: Você já configurou produtos/subcategorias desta categoria.\n\n` +
          `HIERARQUIA: Produto > Subcategoria > Categoria\n\n` +
          `A configuração mais específica tem prioridade.\n\nDeseja adicionar mesmo assim?`
        );
        if (!confirma) return;
      }
    }

    const novaConfig = {
      tipo: itemSelecionado.tipo,
      referencia_id: itemSelecionado.id,
      nome: itemSelecionado.nome,
      tipo_calculo: itemSelecionado.tipo_calculo,
      percentual: parseFloat(itemSelecionado.percentual) || 0,
      percentual_loja: itemSelecionado.tipo_calculo === 'lucro' ? (parseFloat(itemSelecionado.percentual_loja) || 0) : null,
      permite_edicao_venda: itemSelecionado.permite_edicao_venda || false,
      observacoes: itemSelecionado.observacoes || '',
    };

    setConfiguracoesParaSalvar([...configuracoesParaSalvar, novaConfig]);
    setItemSelecionado(null);
    alert('Configuração adicionada! Configure mais itens ou clique em "Salvar Todas"');
  };

  const removerConfiguracao = (index) => {
    setConfiguracoesParaSalvar(configuracoesParaSalvar.filter((_, i) => i !== index));
  };

  const salvarTodasConfiguracoes = async () => {
    if (!funcionarioSel) {
      alert('Selecione um funcionário');
      return;
    }

    if (configuracoesParaSalvar.length === 0) {
      alert('Adicione pelo menos uma configuração');
      return;
    }

    setSalvando(true);

    try {
      // 1️⃣ Atualizar data de fechamento do funcionário (se fornecida)
      if (dataFechamento) {
        await api.put(`/funcionarios/${funcionarioSel}`, {
          data_fechamento_comissao: parseInt(dataFechamento)
        });
      }

      // 2️⃣ Preparar TODAS as configurações
      const configuracoes = configuracoesParaSalvar.map(config => ({
        funcionario_id: parseInt(funcionarioSel),
        tipo: config.tipo,
        referencia_id: config.referencia_id,
        tipo_calculo: config.tipo_calculo,
        percentual: parseFloat(config.percentual) || 0,
        percentual_loja: config.percentual_loja ? parseFloat(config.percentual_loja) : null,
        permite_edicao_venda: config.permite_edicao_venda || false,
        observacoes: config.observacoes || '',
        desconta_taxa_cartao: regras.desconta_taxa_cartao,
        desconta_impostos: regras.desconta_impostos,
        desconta_taxa_entrega: regras.desconta_taxa_entrega,
        comissao_venda_parcial: regras.comissao_venda_parcial,
      }));

      console.log('Enviando configurações em batch:', configuracoes);

      // 3️⃣ SALVAR TUDO DE UMA VEZ em uma única transação
      const response = await api.post('/comissoes/configuracoes/batch', {
        configuracoes: configuracoes
      });

      console.log('Resposta do servidor:', response.data);

      if (response.data.success) {
        alert(`✅ ${response.data.total} configurações salvas com sucesso!`);
        setConfiguracoesParaSalvar([]);
        
        // 🔥 RECARREGAR configurações após salvar
        if (funcionarioSel) {
          try {
            const configResponse = await api.get(`/comissoes/configuracoes/funcionario/${funcionarioSel}`);
            if (configResponse.data.success) {
              // Atualizar mapa de configurações
              const configMap = {};
              configResponse.data.data.forEach(config => {
                const key = `${config.tipo}-${config.referencia_id}`;
                configMap[key] = config;
              });
              setConfiguracao(configMap);
            }
          } catch (error) {
            console.error('Erro ao recarregar configurações:', error);
          }
        }
        
        onSave(); // Fecha modal e recarrega lista de funcionários
      }
    } catch (error) {
      console.error('Erro ao salvar configurações:', error);
      console.error('Resposta do servidor:', error.response?.data);
      
      const mensagemErro = error.response?.data?.detail || error.message || 'Erro desconhecido';
      alert(`❌ Erro ao salvar configurações:\n\n${mensagemErro}`);
    } finally {
      setSalvando(false);
      setProgressoSalvamento({ atual: 0, total: 0 });
    }
  };

  const salvarItem = async () => {
    if (!funcionarioSel) {
      alert('Selecione um funcionário');
      return;
    }

    // Se não há item selecionado, salvar apenas as regras em TODAS as configurações existentes
    if (!itemSelecionado) {
      if (Object.keys(configuracao).length === 0) {
        alert('Nenhuma configuração encontrada para atualizar as regras.');
        return;
      }

      const regrasAlteradas = regrasOriginais && (
        regras.desconta_taxa_cartao !== regrasOriginais.desconta_taxa_cartao ||
        regras.desconta_impostos !== regrasOriginais.desconta_impostos ||
        regras.desconta_taxa_entrega !== regrasOriginais.desconta_taxa_entrega ||
        regras.comissao_venda_parcial !== regrasOriginais.comissao_venda_parcial
      );

      if (!regrasAlteradas) {
        alert('Nenhuma alteração detectada nas regras.');
        return;
      }

      if (!confirm('Deseja atualizar as regras de cálculo em TODAS as configurações deste funcionário?')) {
        return;
      }

      try {
        console.log('💾 SALVANDO REGRAS - Estado atual:', regras);
        // Atualizar cada configuração existente com as novas regras
        for (const [key, config] of Object.entries(configuracao)) {
          const dados = {
            funcionario_id: parseInt(funcionarioSel),
            tipo: config.tipo,
            referencia_id: config.referencia_id,
            tipo_calculo: config.tipo_calculo,
            percentual: parseFloat(config.percentual),
            percentual_loja: config.percentual_loja ? parseFloat(config.percentual_loja) : null,
            desconta_taxa_cartao: regras.desconta_taxa_cartao,
            desconta_impostos: regras.desconta_impostos,
            desconta_custo_entrega: regras.desconta_taxa_entrega,
            comissao_venda_parcial: regras.comissao_venda_parcial,
            permite_edicao_venda: config.permite_edicao_venda,
            observacoes: config.observacoes || '',
          };
          console.log('💾 Dados sendo enviados ao backend:', dados);

          await api.post('/comissoes/configuracoes', dados);
        }

        alert('✅ Regras atualizadas com sucesso em todas as configurações!');
        setRegrasOriginais(regras); // Atualizar regras originais
        // ✅ Não recarrega mais - mantém o modal aberto
      } catch (error) {
        console.error('Erro ao atualizar regras:', error);
        alert('Erro ao atualizar regras');
      }
      return;
    }

    // Fluxo normal: salvar item selecionado
    if (!itemSelecionado) {
      alert('Selecione um item para configurar');
      return;
    }

    try {
      const dados = {
        funcionario_id: parseInt(funcionarioSel),
        tipo: itemSelecionado.tipo,
        referencia_id: itemSelecionado.id,
        tipo_calculo: itemSelecionado.tipo_calculo,
        percentual: parseFloat(itemSelecionado.percentual),
        percentual_loja: itemSelecionado.tipo_calculo === 'lucro' ? parseFloat(itemSelecionado.percentual_loja) : null,
        desconta_taxa_cartao: regras.desconta_taxa_cartao,
        desconta_impostos: regras.desconta_impostos,
        desconta_custo_entrega: regras.desconta_taxa_entrega,
        comissao_venda_parcial: regras.comissao_venda_parcial,
        permite_edicao_venda: itemSelecionado.permite_edicao_venda,
        observacoes: itemSelecionado.observacoes,
      };

      const response = await api.post('/comissoes/configuracoes', dados);

      if (response.data.success) {
        alert('Configuração salva com sucesso!');
        
        // Atualizar configuração local
        const key = `${itemSelecionado.tipo}-${itemSelecionado.id}`;
        setConfiguracao(prev => ({
          ...prev,
          [key]: { ...dados, id: response.data.config_id, nome_item: itemSelecionado.nome }
        }));
        
        setItemSelecionado(null);
        // ✅ Não recarrega mais - mantém o modal aberto
      }
    } catch (error) {
      console.error('Erro ao salvar configuração:', error);
      alert('Erro ao salvar configuração');
    }
  };

  const getConfiguracao = (tipo, id) => {
    const key = `${tipo}-${id}`;
    return configuracao[key];
  };

  const temConfiguracao = (tipo, id) => {
    return !!getConfiguracao(tipo, id);
  };

  const itemJaAdicionado = (tipo, id) => {
    return configuracoesParaSalvar.some(c => c.tipo === tipo && c.referencia_id === id);
  };

  // Função recursiva para renderizar categorias em qualquer nível
  const renderCategoria = (categoria, nivel = 0) => {
    const indentacao = '  '.repeat(nivel);
    const icone = nivel === 0 ? '📦' : '→';
    const temFilhas = categoria.filhas && categoria.filhas.length > 0;
    const temProdutos = categoria.produtos && categoria.produtos.length > 0;
    
    // 🔥 OCULTAR categoria se já estiver configurada
    const jaConfigurado = temConfiguracao('categoria', categoria.id);
    if (jaConfigurado) {
      // Ainda renderizar filhas e produtos se existirem (dentro de um fragment)
      if (!categoriasExpanded[categoria.id]) return null;
      
      return (
        <React.Fragment key={`cat-${categoria.id}`}>
          {temFilhas && categoria.filhas.map(filha => renderCategoria(filha, nivel + 1))}
          
          {temProdutos && (
            <div className="pl-6" style={{ paddingLeft: `${24 + nivel * 20}px` }}>
              {categoria.produtos.map(prod => {
                const prodConfigurado = temConfiguracao('produto', prod.id);
                const prodAdicionado = itemJaAdicionado('produto', prod.id);
                
                // 🔥 OCULTAR produto se já estiver configurado
                if (prodConfigurado) return null;
                
                return (
                  <div
                    key={`prod-${prod.id}`}
                    className={`p-2 flex items-center justify-between cursor-pointer hover:bg-gray-50 ${
                      prodAdicionado ? 'bg-yellow-50' : ''
                    }`}
                    onClick={() => selecionarItem('produto', prod.id, prod.nome)}
                  >
                    <span className="text-sm">📌 {prod.nome}</span>
                    {prodAdicionado && (
                      <span className="text-xs text-yellow-600">⏳ Na lista</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </React.Fragment>
      );
    }

    return (
      <div key={`cat-${categoria.id}`} className="border-b last:border-b-0">
        {/* Categoria */}
        <div
          className={`p-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 ${
            itemJaAdicionado('categoria', categoria.id) ? 'bg-yellow-50' : ''
          }`}
          style={{ paddingLeft: `${12 + nivel * 20}px` }}
          onClick={() => selecionarItem('categoria', categoria.id, `${indentacao}${categoria.nome}`)}
        >
          <div className="flex items-center gap-2">
            {(temFilhas || temProdutos) && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleCategoria(categoria.id);
                }}
                className="text-gray-500"
              >
                {categoriasExpanded[categoria.id] ? '▼' : '▶'}
              </button>
            )}
            <span className={nivel === 0 ? 'font-medium' : 'text-sm'}>
              {icone} {categoria.nome}
              {nivel > 0 && <span className="text-xs text-gray-500 ml-1">(Nível {nivel + 1})</span>}
            </span>
          </div>
          {itemJaAdicionado('categoria', categoria.id) && (
            <span className="text-xs text-yellow-600">⏳ Na lista</span>
          )}
        </div>

        {/* Filhas e Produtos (quando expandido) */}
        {categoriasExpanded[categoria.id] && (
          <div>
            {/* Categorias Filhas (recursivo) */}
            {temFilhas && (
              <div>
                {categoria.filhas.map(filha => renderCategoria(filha, nivel + 1))}
              </div>
            )}

            {/* Produtos desta categoria */}
            {temProdutos && (
              <div className="pl-6" style={{ paddingLeft: `${24 + nivel * 20}px` }}>
                {categoria.produtos.map(prod => {
                  const prodConfigurado = temConfiguracao('produto', prod.id);
                  const prodAdicionado = itemJaAdicionado('produto', prod.id);
                  
                  // 🔥 OCULTAR produto se já estiver configurado
                  if (prodConfigurado) return null;
                  
                  return (
                    <div
                      key={`prod-${prod.id}`}
                      className={`p-2 flex items-center justify-between cursor-pointer hover:bg-gray-50 ${
                        prodAdicionado ? 'bg-yellow-50' : ''
                      }`}
                      onClick={() => selecionarItem('produto', prod.id, prod.nome)}
                    >
                      <span className="text-sm">📌 {prod.nome}</span>
                      {prodAdicionado && (
                        <span className="text-xs text-yellow-600">⏳ Na lista</span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b flex justify-between items-center">
          <h2 className="text-2xl font-bold">Configuração de Comissão</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Selecionar Funcionário */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Funcionário
            </label>
            <select
              value={funcionarioSel}
              onChange={(e) => setFuncionarioSel(e.target.value)}
              className="w-full border rounded-lg px-3 py-2"
              disabled={!!funcionarioId}
            >
              <option value="">Selecione um funcionário</option>
              {funcionarios.map(func => (
                <option key={func.id} value={func.id}>
                  {func.nome} - {func.cargo}
                </option>
              ))}
            </select>
            
            {/* Aviso sobre Parceiro */}
            <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded text-xs">
              <div className="flex items-start gap-2">
                <span className="text-blue-600">ℹ️</span>
                <div className="text-blue-700">
                  <strong>Apenas parceiros podem receber comissões.</strong><br />
                  Se a pessoa não aparecer na lista, marque-a como "Parceiro" no cadastro de pessoas primeiro.
                </div>
              </div>
            </div>
          </div>

          {/* Data de Fechamento de Comissão */}
          {funcionarioSel && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📅 Dia do mês para fechamento de comissão
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="1"
                  max="31"
                  value={dataFechamento}
                  onChange={(e) => setDataFechamento(e.target.value)}
                  placeholder="Ex: 5 (paga dia 5 de cada mês)"
                  className="flex-1 border rounded-lg px-3 py-2"
                />
                <button
                  onClick={async () => {
                    try {
                      await api.put(`/clientes/${funcionarioSel}`, {
                        data_fechamento_comissao: dataFechamento ? parseInt(dataFechamento) : null
                      });
                      alert('✅ Data de fechamento salva com sucesso!');
                    } catch (error) {
                      console.error('Erro ao salvar data:', error);
                      alert('❌ Erro ao salvar data de fechamento');
                    }
                  }}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 whitespace-nowrap"
                >
                  💾 Salvar Data
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Deixe em branco para pagamento 30 dias após a venda (padrão)
              </p>
            </div>
          )}

          {/* Regras de Cálculo */}
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-semibold mb-3">Regras de Cálculo</h3>
            
            {/* Aviso sobre Hierarquia */}
            <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded text-sm">
              <div className="font-semibold text-blue-800 mb-1">📋 Hierarquia de Configurações</div>
              <div className="text-blue-700 text-xs">
                <strong>Produto</strong> (prioridade máxima) → <strong>Subcategoria</strong> → <strong>Categoria</strong> (prioridade mínima)
                <br />
                <span className="text-blue-600">Ao vender um produto, o sistema busca a configuração mais específica.</span>
              </div>
            </div>

            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={regras.desconta_taxa_cartao}
                  onChange={(e) => {
                    console.log('✅ Checkbox TAXA CARTÃO alterado para:', e.target.checked);
                    setRegras({...regras, desconta_taxa_cartao: e.target.checked});
                  }}
                  className="rounded"
                />
                <span className="text-sm">Desconta taxa de cartão</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={regras.desconta_impostos}
                  onChange={(e) => {
                    console.log('✅ Checkbox IMPOSTOS alterado para:', e.target.checked);
                    setRegras({...regras, desconta_impostos: e.target.checked});
                  }}
                  className="rounded"
                />
                <span className="text-sm">Desconta impostos</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={regras.desconta_taxa_entrega}
                  onChange={(e) => {
                    console.log('✅ Checkbox TAXA ENTREGA alterado para:', e.target.checked);
                    setRegras({...regras, desconta_taxa_entrega: e.target.checked});
                  }}
                  className="rounded"
                />
                <span className="text-sm">Desconta taxa de entrega</span>
              </label>
              <div className="border-t pt-2 mt-3">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={regras.comissao_venda_parcial}
                    onChange={(e) => {
                      console.log('✅ Checkbox VENDA PARCIAL alterado para:', e.target.checked);
                      setRegras({...regras, comissao_venda_parcial: e.target.checked});
                    }}
                    className="rounded"
                  />
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">Gerar comissão em vendas parciais</span>
                    <span className="text-xs text-gray-500">
                      {regras.comissao_venda_parcial 
                        ? 'Comissão gerada proporcionalmente a cada pagamento recebido'
                        : 'Comissão gerada somente quando a venda estiver 100% paga'}
                    </span>
                  </div>
                </label>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Árvore de Produtos */}
            <div>
              <h3 className="font-semibold mb-3">Seleção de Produtos</h3>
              
              {/* Lista de Itens Já Configurados */}
              {Object.keys(configuracao).length > 0 && (
                <div className="mb-4 border rounded-lg p-3 bg-green-50">
                  <h4 className="text-sm font-semibold text-green-800 mb-2">
                    ✅ Itens Já Configurados ({Object.keys(configuracao).length})
                  </h4>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {Object.entries(configuracao).map(([key, config]) => (
                      <div
                        key={key}
                        className="w-full flex items-center justify-between text-xs bg-white p-2 rounded hover:bg-gray-50 transition-colors group"
                      >
                        <button
                          onClick={() => selecionarItem(config.tipo, config.referencia_id, config.nome_item || 'Item')}
                          className="flex-1 flex items-center gap-2 text-left"
                        >
                          {config.tipo === 'categoria' && '📦'}
                          {config.tipo === 'subcategoria' && '📂'}
                          {config.tipo === 'produto' && '📌'}
                          <span className="text-gray-700">{config.nome_item || 'Item'}</span>
                          <span className="text-green-600 font-medium ml-auto">
                            {config.tipo_calculo === 'percentual' ? `${config.percentual}%` : `Lucro ${config.percentual}%`}
                          </span>
                        </button>
                        <button
                          onClick={async () => {
                            if (confirm(`Deseja remover a configuração de "${config.nome_item || 'Item'}"?`)) {
                              try {
                                await api.delete(`/comissoes/configuracoes/${config.id}`);
                                alert('Configuração removida com sucesso!');
                                // Atualizar estado local
                                const novoConfig = { ...configuracao };
                                delete novoConfig[key];
                                setConfiguracao(novoConfig);
                                // ✅ Não recarrega mais - mantém o modal aberto
                              } catch (error) {
                                console.error('Erro ao remover:', error);
                                alert('Erro ao remover configuração');
                              }
                            }
                          }}
                          className="ml-2 text-red-600 hover:text-red-800 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          🗑️
                        </button>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-green-700 mt-2 italic">
                    💡 Clique em um item para editar
                  </p>
                </div>
              )}
              
              {loading ? (
                <div className="text-center py-8">Carregando...</div>
              ) : (
                <div key={Object.keys(configuracao).length} className="border rounded-lg max-h-96 overflow-y-auto">
                  {arvoreProdutos.map(categoria => renderCategoria(categoria, 0))}
                </div>
              )}
            </div>

            {/* Configuração do Item Selecionado */}
            <div>
              <h3 className="font-semibold mb-3">Configuração</h3>
              {itemSelecionado ? (
                <div className="border rounded-lg p-4 space-y-4">
                  <div>
                    <h4 className="font-medium text-gray-700">
                      {itemSelecionado.tipo === 'categoria' && '📦 '}
                      {itemSelecionado.tipo === 'subcategoria' && '📂 '}
                      {itemSelecionado.tipo === 'produto' && '📌 '}
                      {itemSelecionado.nome}
                    </h4>
                    <p className="text-xs text-gray-500 mt-1">
                      Tipo: {itemSelecionado.tipo}
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Tipo de Comissão
                    </label>
                    <div className="space-y-2">
                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          value="percentual"
                          checked={itemSelecionado.tipo_calculo === 'percentual'}
                          onChange={(e) => setItemSelecionado({...itemSelecionado, tipo_calculo: e.target.value})}
                        />
                        <span className="text-sm">Percentual fixo sobre venda</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          value="lucro"
                          checked={itemSelecionado.tipo_calculo === 'lucro'}
                          onChange={(e) => setItemSelecionado({...itemSelecionado, tipo_calculo: e.target.value})}
                        />
                        <span className="text-sm">Divisão de lucro</span>
                      </label>
                    </div>
                  </div>

                  {itemSelecionado.tipo_calculo === 'percentual' ? (
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Percentual
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="0.1"
                          value={itemSelecionado.percentual}
                          onChange={(e) => setItemSelecionado({...itemSelecionado, percentual: e.target.value})}
                          className="border rounded px-3 py-2 w-24"
                        />
                        <span>%</span>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Divisão do Lucro
                      </label>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs text-gray-600">Funcionário</label>
                          <div className="flex items-center gap-2 mt-1">
                            <input
                              type="number"
                              min="0"
                              max="100"
                              value={itemSelecionado.percentual}
                              onChange={(e) => {
                                const val = parseFloat(e.target.value);
                                setItemSelecionado({
                                  ...itemSelecionado,
                                  percentual: val,
                                  percentual_loja: 100 - val
                                });
                              }}
                              className="border rounded px-2 py-1 w-20"
                            />
                            <span className="text-sm">%</span>
                          </div>
                        </div>
                        <div>
                          <label className="text-xs text-gray-600">Loja</label>
                          <div className="flex items-center gap-2 mt-1">
                            <input
                              type="number"
                              value={itemSelecionado.percentual_loja}
                              readOnly
                              className="border rounded px-2 py-1 w-20 bg-gray-100"
                            />
                            <span className="text-sm">%</span>
                          </div>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        Cálculo: Preço Venda - Desconto - Taxas - Impostos - Custo = Lucro
                      </p>
                    </div>
                  )}

                  <div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={itemSelecionado.permite_edicao_venda}
                        onChange={(e) => setItemSelecionado({...itemSelecionado, permite_edicao_venda: e.target.checked})}
                        className="rounded"
                      />
                      <span className="text-sm">Permite editar percentual na venda</span>
                    </label>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Observações
                    </label>
                    <textarea
                      value={itemSelecionado.observacoes}
                      onChange={(e) => setItemSelecionado({...itemSelecionado, observacoes: e.target.value})}
                      className="border rounded px-3 py-2 w-full"
                      rows="3"
                    />
                  </div>

                  <button
                    onClick={adicionarConfiguracao}
                    className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded mb-2"
                  >
                    ➕ Adicionar à Lista
                  </button>

                  <button
                    onClick={salvarItem}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded"
                  >
                    💾 Salvar Agora
                  </button>
                </div>
              ) : (
                <div className="border rounded-lg p-8 text-center text-gray-500">
                  <p>Selecione uma categoria, subcategoria ou produto ao lado para configurar</p>
                </div>
              )}

              {/* Lista de Configurações Adicionadas */}
              {configuracoesParaSalvar.length > 0 && (
                <div className="mt-6 border rounded-lg p-4">
                  <h4 className="font-semibold mb-3">Configurações a Salvar ({configuracoesParaSalvar.length})</h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {configuracoesParaSalvar.map((config, index) => (
                      <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded text-sm">
                        <div>
                          <span className="font-medium">{config.nome}</span>
                          <span className="text-gray-500 ml-2">
                            ({config.tipo_calculo === 'percentual' ? `${config.percentual}%` : `Lucro ${config.percentual}%`})
                          </span>
                        </div>
                        <button
                          onClick={() => removerConfiguracao(index)}
                          className="text-red-600 hover:text-red-800"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                  <button
                    onClick={salvarTodasConfiguracoes}
                    disabled={salvando}
                    className={`w-full py-2 rounded mt-4 text-white ${
                      salvando 
                        ? 'bg-gray-400 cursor-not-allowed' 
                        : 'bg-blue-600 hover:bg-blue-700'
                    }`}
                  >
                    {salvando ? (
                      <span>
                        ⏳ Salvando {progressoSalvamento.atual}/{progressoSalvamento.total}...
                      </span>
                    ) : (
                      '💾 Salvar Todas as Configurações'
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t bg-gray-50">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              <p className="text-sm text-gray-600">
                ℹ️ As configurações se aplicam <strong>apenas às comissões futuras</strong>. Comissões já geradas não são alteradas.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={onClose}
                className="px-4 py-2 border rounded hover:bg-gray-50 bg-white"
              >
                Fechar
              </button>
              <button
                onClick={salvarItem}
                disabled={!itemSelecionado && (!regrasOriginais || (
                  regras.desconta_taxa_cartao === regrasOriginais.desconta_taxa_cartao &&
                  regras.desconta_impostos === regrasOriginais.desconta_impostos &&
                  regras.desconta_taxa_entrega === regrasOriginais.desconta_taxa_entrega &&
                  regras.comissao_venda_parcial === regrasOriginais.comissao_venda_parcial
                ))}
                className={`px-6 py-2 rounded font-medium ${
                  itemSelecionado || (regrasOriginais && (
                    regras.desconta_taxa_cartao !== regrasOriginais.desconta_taxa_cartao ||
                    regras.desconta_impostos !== regrasOriginais.desconta_impostos ||
                    regras.desconta_taxa_entrega !== regrasOriginais.desconta_taxa_entrega ||
                    regras.comissao_venda_parcial !== regrasOriginais.comissao_venda_parcial
                  ))
                    ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                💾 {itemSelecionado ? 'Salvar Alterações' : 'Atualizar Regras'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Comissoes;
