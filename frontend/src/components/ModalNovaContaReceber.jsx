import React, { useState, useEffect } from 'react';
import api from '../api';
import { toast } from 'react-hot-toast';
import { X, Calendar, DollarSign, FileText, User, Tag, Repeat, Plus } from 'lucide-react';

const ModalNovaContaReceber = ({ isOpen, onClose, onSave }) => {
  const [loading, setLoading] = useState(false);
  const [clientes, setClientes] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [subcategoriasDRE, setSubcategoriasDRE] = useState([]);
  const [previewParcelas, setPreviewParcelas] = useState([]);
  const [intervaloParcelas, setIntervaloParcelas] = useState(30);
  const [showModalCategoria, setShowModalCategoria] = useState(false);
  const [formCategoria, setFormCategoria] = useState({
    nome: '',
    tipo: 'receita',
    cor: '#10b981',
    icone: '\ud83d\udcb0',
    descricao: '',
    ativo: true,
    novasSubcategorias: []
  });
  
  const [dados, setDados] = useState({
    descricao: '',
    cliente_id: null,
    categoria_id: null,
    dre_subcategoria_id: null,
    valor_original: '',
    data_emissao: new Date().toISOString().split('T')[0],
    data_vencimento: new Date().toISOString().split('T')[0],
    documento: '',
    observacoes: '',
    
    // Parcelamento
    eh_parcelado: false,
    total_parcelas: 1,
    
    // Recorrência
    eh_recorrente: false,
    tipo_recorrencia: 'mensal',
    intervalo_dias: null,
    data_inicio_recorrencia: null,
    data_fim_recorrencia: null,
    numero_repeticoes: null
  });

  useEffect(() => {
    if (isOpen) {
      carregarDados();
    }
  }, [isOpen]);

  const carregarDados = async () => {
    try {
      const [clientesRes, categoriasRes, subcategoriasDRERes] = await Promise.all([
        api.get('/clientes/?tipo_cadastro=cliente'),
        api.get('/categorias-financeiras/'),
        api.get('/dre/subcategorias')
      ]);
      
      console.log('📦 Categorias recebidas:', categoriasRes.data);
      
      setClientes(clientesRes.data);
      
      // Filtrar categorias: Mostrar APENAS receitas/entradas
      const categoriasReceita = categoriasRes.data.filter(c => {
        const tipo = c.tipo ? c.tipo.toLowerCase() : '';
        const nome = c.nome ? c.nome.toLowerCase() : '';
        
        // ACEITAR se for receita ou entrada
        const ehReceita = tipo === 'receita' || tipo === 'entrada';
        const temReceitaNoNome = nome.includes('receita') || nome.includes('venda');
        
        // BLOQUEAR despesas explícitas
        const ehDespesa = tipo === 'despesa' || tipo === 'saida' || tipo === 'saída';
        
        return (ehReceita || temReceitaNoNome) && !ehDespesa;
      });
      
      setCategorias(categoriasReceita);
      setSubcategoriasDRE(subcategoriasDRERes.data || []);
      
      console.log('✅ Categorias de RECEITA setadas:', categoriasReceita.length);
      console.log('📋 Lista completa:', categoriasReceita);
      console.log('📊 Subcategorias DRE carregadas:', subcategoriasDRERes.data?.length);
    } catch (error) {
      console.error('❌ Erro ao carregar dados:', error);
      toast.error('Erro ao carregar formulário');
    }
  };

  const gerarPreviewParcelas = () => {
    if (!dados.eh_parcelado || !dados.total_parcelas || !dados.data_vencimento || !dados.valor_original) {
      setPreviewParcelas([]);
      return;
    }

    const numParcelas = parseInt(dados.total_parcelas);
    const valorTotal = parseFloat(dados.valor_original);
    const valorParcela = (valorTotal / numParcelas).toFixed(2);
    const dataBase = new Date(dados.data_vencimento);
    
    const parcelas = [];
    for (let i = 0; i < numParcelas; i++) {
      const dataVencimento = new Date(dataBase);
      dataVencimento.setDate(dataBase.getDate() + (i * intervaloParcelas));
      
      parcelas.push({
        numero: i + 1,
        valor: parseFloat(valorParcela),
        data_vencimento: dataVencimento.toISOString().split('T')[0]
      });
    }
    
    // Ajustar última parcela
    const somaCalculada = parcelas.reduce((sum, p) => sum + p.valor, 0);
    const diferenca = valorTotal - somaCalculada;
    if (Math.abs(diferenca) > 0.01) {
      parcelas[parcelas.length - 1].valor += diferenca;
    }
    
    setPreviewParcelas(parcelas);
  };

  const adicionarSubcategoriaNova = () => {
    setFormCategoria({
      ...formCategoria,
      novasSubcategorias: [...formCategoria.novasSubcategorias, { nome: '', descricao: '', ativo: true }]
    });
  };

  const atualizarSubcategoriaNova = (index, field, value) => {
    const novasSubs = [...formCategoria.novasSubcategorias];
    novasSubs[index][field] = value;
    setFormCategoria({ ...formCategoria, novasSubcategorias: novasSubs });
  };

  const removerSubcategoriaNova = (index) => {
    const novasSubs = formCategoria.novasSubcategorias.filter((_, i) => i !== index);
    setFormCategoria({ ...formCategoria, novasSubcategorias: novasSubs });
  };

  const handleKeyDownSubcategoria = (e, index) => {
    if (e.key === 'Tab' && !e.shiftKey && index === formCategoria.novasSubcategorias.length - 1) {
      e.preventDefault();
      adicionarSubcategoriaNova();
    }
  };

  const handleSubmitCategoria = async (e) => {
    e.preventDefault();
    
    if (!formCategoria.nome) {
      toast.error('Preencha o nome da categoria');
      return;
    }

    try {
      const response = await api.post('/categorias-financeiras/', {
        nome: formCategoria.nome,
        tipo: formCategoria.tipo,
        cor: formCategoria.cor,
        icone: formCategoria.icone,
        descricao: formCategoria.descricao,
        ativo: formCategoria.ativo
      });
      
      const categoriaId = response.data.id;
      toast.success('Categoria criada com sucesso!');

      // Criar subcategorias se houver
      if (formCategoria.novasSubcategorias.length > 0) {
        const subsValidas = formCategoria.novasSubcategorias.filter(sub => sub.nome.trim());
        for (const sub of subsValidas) {
          try {
            await api.post('/subcategorias/', {
              categoria_id: categoriaId,
              nome: sub.nome,
              descricao: sub.descricao,
              ativo: sub.ativo
            });
          } catch (subError) {
            console.error('Erro ao criar subcategoria:', subError);
          }
        }
        if (subsValidas.length > 0) {
          toast.success(`${subsValidas.length} subcategoria(s) criada(s)!`);
        }
      }
      
      // Atualizar lista de categorias e selecionar a nova
      await carregarDados();
      setDados({...dados, categoria_id: categoriaId});
      setShowModalCategoria(false);
      setFormCategoria({
        nome: '',
        tipo: 'receita',
        cor: '#10b981',
        icone: '\ud83d\udcb0',
        descricao: '',
        ativo: true,
        novasSubcategorias: []
      });
    } catch (error) {
      console.error('Erro ao salvar categoria:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar categoria');
    }
  };
      const dataVencimento = new Date(dataBase);
      dataVencimento.setDate(dataBase.getDate() + (i * intervaloParcelas));
      
      parcelas.push({
        numero: i + 1,
        valor: parseFloat(valorParcela),
        data_vencimento: dataVencimento.toISOString().split('T')[0]
      });
    }
    
    const somaCalculada = parcelas.reduce((sum, p) => sum + p.valor, 0);
    const diferenca = valorTotal - somaCalculada;
    if (Math.abs(diferenca) > 0.01) {
      parcelas[parcelas.length - 1].valor += diferenca;
    }
    
    setPreviewParcelas(parcelas);
  };

  const atualizarDataParcela = (index, novaData) => {
    const novasParcelas = [...previewParcelas];
    novasParcelas[index].data_vencimento = novaData;
    setPreviewParcelas(novasParcelas);
  };

  const atualizarValorParcela = (index, novoValor) => {
    const novasParcelas = [...previewParcelas];
    novasParcelas[index].valor = parseFloat(novoValor) || 0;
    setPreviewParcelas(novasParcelas);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!dados.descricao || !dados.valor_original || !dados.data_vencimento) {
      toast.error('Preencha todos os campos obrigatórios');
      return;
    }
    
    setLoading(true);
    
    try {
      await api.post('/contas-receber/', {
        ...dados,
        valor_original: parseFloat(dados.valor_original),
        total_parcelas: dados.eh_parcelado ? parseInt(dados.total_parcelas) : 1,
        intervalo_dias: dados.tipo_recorrencia === 'personalizado' ? parseInt(dados.intervalo_dias) : null,
        numero_repeticoes: dados.numero_repeticoes ? parseInt(dados.numero_repeticoes) : null
      });
      
      toast.success(dados.eh_recorrente ? 'Conta recorrente criada com sucesso!' : 'Conta criada com sucesso!');
      onSave();
      onClose();
      resetForm();
    } catch (error) {
      console.error('Erro ao criar conta:', error);
      toast.error(error.response?.data?.detail || 'Erro ao criar conta a receber');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setDados({
      descricao: '',
      cliente_id: null,
      categoria_id: null,
      valor_original: '',
      data_emissao: new Date().toISOString().split('T')[0],
      data_vencimento: new Date().toISOString().split('T')[0],
      documento: '',
      observacoes: '',
      eh_parcelado: false,
      total_parcelas: 1,
      eh_recorrente: false,
      tipo_recorrencia: 'mensal',
      intervalo_dias: null,
      data_inicio_recorrencia: null,
      data_fim_recorrencia: null,
      numero_repeticoes: null
    });
    setPreviewParcelas([]);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full m-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-6 border-b sticky top-0 bg-white">
          <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <Plus className="text-green-600" />
            Nova Conta a Receber
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-700 flex items-center gap-2">
              <FileText size={20} className="text-blue-600" />
              Informações Básicas
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrição *
                </label>
                <input
                  type="text"
                  value={dados.descricao}
                  onChange={(e) => setDados({...dados, descricao: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: Venda #123, Serviço prestado..."
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <User size={16} className="inline mr-1" />
                  Cliente
                </label>
                <select
                  value={dados.cliente_id || ''}
                  onChange={(e) => setDados({...dados, cliente_id: e.target.value ? parseInt(e.target.value) : null})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Selecione...</option>
                  {clientes.map(c => (
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Tag size={16} className="inline mr-1" />
                  Categoria
                </label>
                <div className="flex gap-2">
                  <select
                    value={dados.categoria_id || ''}
                    onChange={(e) => setDados({...dados, categoria_id: e.target.value ? parseInt(e.target.value) : null})}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Selecione...</option>
                    {categorias.map(c => (
                      <option key={c.id} value={c.id}>{c.nome}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setShowModalCategoria(true)}
                    className="px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center gap-1 whitespace-nowrap"
                    title="Adicionar nova categoria"
                  >
                    <Plus size={16} /> Adicionar
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  🏷️ Subcategoria DRE (Demonstrativo de Resultado)
                </label>
                <select
                  value={dados.dre_subcategoria_id || ''}
                  onChange={(e) => setDados({...dados, dre_subcategoria_id: e.target.value ? parseInt(e.target.value) : null})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Sem classificação DRE</option>
                  {subcategoriasDRE.map(sub => (
                    <option key={sub.id} value={sub.id}>{sub.nome}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">Classifique para melhor análise gerencial</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <DollarSign size={16} className="inline mr-1" />
                  Valor *
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={dados.valor_original}
                  onChange={(e) => setDados({...dados, valor_original: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Calendar size={16} className="inline mr-1" />
                  Data Vencimento *
                </label>
                <input
                  type="date"
                  value={dados.data_vencimento}
                  onChange={(e) => setDados({...dados, data_vencimento: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Documento/NF
                </label>
                <input
                  type="text"
                  value={dados.documento}
                  onChange={(e) => setDados({...dados, documento: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  placeholder="Número do documento"
                />
              </div>
            </div>
          </div>

          {/* Recorrência */}
          <div className="space-y-4 border-t pt-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="eh_recorrente"
                checked={dados.eh_recorrente}
                onChange={(e) => setDados({...dados, eh_recorrente: e.target.checked})}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <label htmlFor="eh_recorrente" className="text-lg font-semibold text-gray-700 flex items-center gap-2 cursor-pointer">
                <Repeat size={20} className="text-purple-600" />
                Receita Recorrente
              </label>
            </div>

            {dados.eh_recorrente && (
              <div className="ml-6 space-y-4 p-4 bg-purple-50 rounded-lg">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Tipo de Recorrência *
                    </label>
                    <select
                      value={dados.tipo_recorrencia}
                      onChange={(e) => setDados({...dados, tipo_recorrencia: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="semanal">📅 Semanal (7 em 7 dias)</option>
                      <option value="quinzenal">📆 Quinzenal (15 em 15 dias)</option>
                      <option value="mensal">🗓️ Mensal</option>
                      <option value="personalizado">⚙️ Personalizado</option>
                    </select>
                  </div>

                  {dados.tipo_recorrencia === 'personalizado' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Intervalo (em dias) *
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={dados.intervalo_dias || ''}
                        onChange={(e) => setDados({...dados, intervalo_dias: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
                        placeholder="Ex: 10, 20, 45..."
                        required
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Número de Repetições
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={dados.numero_repeticoes || ''}
                      onChange={(e) => setDados({...dados, numero_repeticoes: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
                      placeholder="Ex: 12 (deixe vazio para infinito)"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Data de Término
                    </label>
                    <input
                      type="date"
                      value={dados.data_fim_recorrencia || ''}
                      onChange={(e) => setDados({...dados, data_fim_recorrencia: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Parcelamento */}
          <div className="space-y-4 border-t pt-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="eh_parcelado_receber"
                checked={dados.eh_parcelado}
                onChange={(e) => {
                  setDados({...dados, eh_parcelado: e.target.checked});
                  if (!e.target.checked) setPreviewParcelas([]);
                }}
                disabled={dados.eh_recorrente}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <label htmlFor="eh_parcelado_receber" className="text-lg font-semibold text-gray-700 cursor-pointer">
                💳 Parcelar esta conta
              </label>
            </div>

            {dados.eh_parcelado && !dados.eh_recorrente && (
              <div className="ml-6 space-y-4 p-4 bg-blue-50 rounded-lg">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Número de Parcelas *
                    </label>
                    <input
                      type="number"
                      min="2"
                      max="120"
                      value={dados.total_parcelas}
                      onChange={(e) => setDados({...dados, total_parcelas: e.target.value})}
                      onBlur={gerarPreviewParcelas}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Intervalo (dias)
                    </label>
                    <select
                      value={intervaloParcelas}
                      onChange={(e) => {
                        setIntervaloParcelas(parseInt(e.target.value));
                        setTimeout(gerarPreviewParcelas, 100);
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="7">7 dias</option>
                      <option value="14">14 dias</option>
                      <option value="15">15 dias</option>
                      <option value="21">21 dias</option>
                      <option value="30">30 dias</option>
                      <option value="60">60 dias</option>
                      <option value="90">90 dias</option>
                    </select>
                  </div>

                  <div>
                    <button
                      type="button"
                      onClick={gerarPreviewParcelas}
                      className="mt-6 w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    >
                      📋 Gerar Preview
                    </button>
                  </div>
                </div>

                {previewParcelas.length > 0 && (
                  <div className="mt-4">
                    <h4 className="font-semibold text-gray-700 mb-3">📅 Preview das Parcelas</h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {previewParcelas.map((parcela, index) => (
                        <div key={index} className="flex items-center gap-3 p-2 bg-white rounded border">
                          <span className="font-semibold text-gray-600 min-w-[80px]">
                            Parcela {parcela.numero}/{previewParcelas.length}
                          </span>
                          <input
                            type="number"
                            step="0.01"
                            value={parcela.valor}
                            onChange={(e) => atualizarValorParcela(index, e.target.value)}
                            className="w-32 px-2 py-1 border border-gray-300 rounded text-sm"
                          />
                          <input
                            type="date"
                            value={parcela.data_vencimento}
                            onChange={(e) => atualizarDataParcela(index, e.target.value)}
                            className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                          />
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 p-2 bg-gray-100 rounded">
                      <strong>Total: R$ {previewParcelas.reduce((sum, p) => sum + p.valor, 0).toFixed(2)}</strong>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Observações
            </label>
            <textarea
              value={dados.observacoes}
              onChange={(e) => setDados({...dados, observacoes: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              rows="3"
            />
          </div>

          <div className="flex justify-end gap-3 border-t pt-4">
            <button
              type="button"
              onClick={() => { onClose(); resetForm(); }}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {loading ? 'Salvando...' : 'Salvar Conta'}
            </button>
          </div>
        </form>
      </div>

      {/* Modal Adicionar Categoria */}
      {showModalCategoria && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-800">Nova Categoria Financeira</h3>
              <button
                type="button"
                onClick={() => setShowModalCategoria(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={24} />
              </button>
            </div>

            <form onSubmit={handleSubmitCategoria} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome da Categoria *
                </label>
                <input
                  type="text"
                  value={formCategoria.nome}
                  onChange={(e) => setFormCategoria({...formCategoria, nome: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  required
                  placeholder="Ex: Vendas, Serviços, Mensalidades..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ícone
                  </label>
                  <select
                    value={formCategoria.icone}
                    onChange={(e) => setFormCategoria({...formCategoria, icone: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    {['💰', '📋', '✨', '🐕', '🩺', '🏨', '🎓', '💼', '🛍️', '🎁', '💵', '📈'].map(i => (
                      <option key={i} value={i}>{i}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cor
                  </label>
                  <input
                    type="color"
                    value={formCategoria.cor}
                    onChange={(e) => setFormCategoria({...formCategoria, cor: e.target.value})}
                    className="w-full h-10 border border-gray-300 rounded-md"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrição
                </label>
                <textarea
                  value={formCategoria.descricao}
                  onChange={(e) => setFormCategoria({...formCategoria, descricao: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows="2"
                />
              </div>

              {/* Subcategorias DRE */}
              <div className="border-t pt-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Subcategorias DRE (opcional)
                  </label>
                  <button
                    type="button"
                    onClick={adicionarSubcategoriaNova}
                    className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  >
                    <Plus size={14} /> Adicionar
                  </button>
                </div>

                {formCategoria.novasSubcategorias.length > 0 && (
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {formCategoria.novasSubcategorias.map((sub, index) => (
                      <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded-md">
                        <input
                          type="text"
                          value={sub.nome}
                          onChange={(e) => atualizarSubcategoriaNova(index, 'nome', e.target.value)}
                          onKeyDown={(e) => handleKeyDownSubcategoria(e, index)}
                          placeholder="Nome (Tab para adicionar mais)"
                          className="flex-1 px-2 py-1 border border-gray-300 rounded-md text-sm"
                        />
                        <button
                          type="button"
                          onClick={() => removerSubcategoriaNova(index)}
                          className="text-red-600 hover:text-red-800 p-1"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {formCategoria.novasSubcategorias.length === 0 && (
                  <p className="text-xs text-gray-500 italic">
                    Aperte Tab no último campo para adicionar mais subcategorias
                  </p>
                )}
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowModalCategoria(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Criar Categoria
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModalNovaContaReceber;
