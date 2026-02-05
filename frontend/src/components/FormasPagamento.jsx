import React, { useState, useEffect } from 'react';
import api from '../api';
import { toast } from 'react-hot-toast';

const FormasPagamento = () => {
  const [formas, setFormas] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mostrarModal, setMostrarModal] = useState(false);
  const [editando, setEditando] = useState(null);
  
  const [formData, setFormData] = useState({
    nome: '',
    tipo: 'dinheiro',
    taxa_percentual: 0,
    taxa_fixa: 0,
    prazo_dias: 0,
    operadora: '',
    gera_contas_receber: false,
    split_parcelas: false,
    conta_bancaria_destino_id: null,
    requer_nsu: false,
    tipo_cartao: '',
    bandeira: '',
    ativo: true,
    permite_parcelamento: false,
    parcelas_maximas: 1,
    taxas_por_parcela: {},
    permite_antecipacao: false,
    dias_recebimento_antecipado: null,
    taxa_antecipacao_percentual: null,
    icone: '💳',
    cor: '#3B82F6'
  });

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = async () => {
    try {
      const [formasRes, bancariasRes] = await Promise.all([
        api.get(`/financeiro/formas-pagamento?apenas_ativas=false`),
        api.get(`/api/contas-bancarias?apenas_ativas=true`)
      ]);
      
      setFormas(formasRes.data);
      setContasBancarias(bancariasRes.data);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar formas de pagamento');
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = (forma = null) => {
    if (forma) {
      setEditando(forma.id);
      
      // Parse taxas_por_parcela se for string JSON
      let taxasPorParcela = {};
      if (forma.taxas_por_parcela) {
        try {
          taxasPorParcela = typeof forma.taxas_por_parcela === 'string' 
            ? JSON.parse(forma.taxas_por_parcela) 
            : forma.taxas_por_parcela;
        } catch (e) {
          console.error('Erro ao parsear taxas_por_parcela:', e);
        }
      }
      
      setFormData({
        nome: forma.nome,
        tipo: forma.tipo,
        taxa_percentual: forma.taxa_percentual,
        taxa_fixa: forma.taxa_fixa,
        prazo_dias: forma.prazo_dias,
        operadora: forma.operadora || '',
        gera_contas_receber: forma.gera_contas_receber,
        split_parcelas: forma.split_parcelas,
        conta_bancaria_destino_id: forma.conta_bancaria_destino_id,
        requer_nsu: forma.requer_nsu,
        tipo_cartao: forma.tipo_cartao || '',
        bandeira: forma.bandeira || '',
        ativo: forma.ativo,
        permite_parcelamento: forma.permite_parcelamento,
        parcelas_maximas: forma.parcelas_maximas,
        taxas_por_parcela: taxasPorParcela,
        permite_antecipacao: forma.permite_antecipacao || false,
        dias_recebimento_antecipado: forma.dias_recebimento_antecipado || null,
        taxa_antecipacao_percentual: forma.taxa_antecipacao_percentual || null,
        icone: forma.icone || '💳',
        cor: forma.cor || '#3B82F6'
      });
    } else {
      setEditando(null);
      setFormData({
        nome: '',
        tipo: 'dinheiro',
        taxa_percentual: 0,
        taxa_fixa: 0,
        prazo_dias: 0,
        operadora: '',
        gera_contas_receber: false,
        split_parcelas: false,
        conta_bancaria_destino_id: null,
        requer_nsu: false,
        tipo_cartao: '',
        bandeira: '',
        ativo: true,
        permite_parcelamento: false,
        parcelas_maximas: 1,
        taxas_por_parcela: {},
        permite_antecipacao: false,
        dias_recebimento_antecipado: null,
        taxa_antecipacao_percentual: null,
        icone: '💳',
        cor: '#3B82F6'
      });
    }
    setMostrarModal(true);
  };

  const salvar = async () => {
    try {
      // Preparar dados para envio - converter taxas_por_parcela para JSON string
      const dadosParaEnviar = {
        ...formData,
        taxas_por_parcela: Object.keys(formData.taxas_por_parcela).length > 0 
          ? JSON.stringify(formData.taxas_por_parcela)
          : null
      };

      if (editando) {
        await api.put(`/financeiro/formas-pagamento/${editando}`, dadosParaEnviar);
        toast.success('Forma de pagamento atualizada!');
      } else {
        await api.post(`/financeiro/formas-pagamento`, dadosParaEnviar);
        toast.success('Forma de pagamento criada!');
      }

      setMostrarModal(false);
      carregarDados();
    } catch (error) {
      console.error('Erro ao salvar:', error);
      toast.error('Erro ao salvar forma de pagamento');
    }
  };

  const excluir = async (id) => {
    if (!confirm('Deseja realmente excluir esta forma de pagamento?')) return;

    try {
            await api.delete(`/financeiro/formas-pagamento/${id}`);
      toast.success('Forma de pagamento excluída!');
      carregarDados();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      toast.error('Erro ao excluir forma de pagamento');
    }
  };

  const tiposDisponiveis = [
    { value: 'dinheiro', label: 'Dinheiro', icone: '💵' },
    { value: 'cartao_credito', label: 'Cartão de Crédito', icone: '💳' },
    { value: 'cartao_debito', label: 'Cartão de Débito', icone: '💳' },
    { value: 'pix', label: 'PIX', icone: '📱' },
    { value: 'boleto', label: 'Boleto', icone: '📄' },
    { value: 'transferencia', label: 'Transferência', icone: '🏦' }
  ];

  if (loading) {
    return <div className="flex justify-center items-center h-64">Carregando...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Formas de Pagamento/Recebimento</h2>
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          onClick={() => abrirModal()}
        >
          + Nova Forma
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Taxa %</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Taxa Fixa</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prazo</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Conta Destino</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {formas.length === 0 ? (
              <tr>
                <td colSpan="8" className="px-6 py-4 text-center text-gray-500">
                  Nenhuma forma de pagamento cadastrada
                </td>
              </tr>
            ) : (
              formas.map(forma => (
                <tr key={forma.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{forma.icone}</span>
                      <div>
                        <div className="font-medium">{forma.nome}</div>
                        {forma.operadora && (
                          <div className="text-xs text-gray-500">{forma.operadora}</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {tiposDisponiveis.find(t => t.value === forma.tipo)?.label || forma.tipo}
                  </td>
                  <td className="px-6 py-4 text-sm">{forma.taxa_percentual}%</td>
                  <td className="px-6 py-4 text-sm">
                    R$ {forma.taxa_fixa?.toFixed(2) || '0.00'}
                  </td>
                  <td className="px-6 py-4 text-sm">{forma.prazo_dias} dias</td>
                  <td className="px-6 py-4 text-sm">
                    {forma.conta_bancaria_destino_id ? (
                      contasBancarias.find(c => c.id === forma.conta_bancaria_destino_id)?.nome || 'N/A'
                    ) : (
                      <span className="text-gray-400">Nenhuma</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs ${
                      forma.ativo ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {forma.ativo ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button
                        className="text-blue-600 hover:text-blue-800"
                        onClick={() => abrirModal(forma)}
                      >
                        ✏️
                      </button>
                      <button
                        className="text-red-600 hover:text-red-800"
                        onClick={() => excluir(forma.id)}
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {mostrarModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center sticky top-0">
              <h3 className="text-xl font-semibold">
                {editando ? 'Editar' : 'Nova'} Forma de Pagamento
              </h3>
              <button
                onClick={() => setMostrarModal(false)}
                className="text-white hover:bg-blue-700 px-3 py-1 rounded"
              >
                ✕
              </button>
            </div>
            
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4">
                {/* Nome */}
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Nome *</label>
                  <input
                    type="text"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={formData.nome}
                    onChange={(e) => setFormData({...formData, nome: e.target.value})}
                    placeholder="Ex: Dinheiro, PIX, Stone Crédito..."
                  />
                </div>

                {/* Tipo */}
                <div>
                  <label className="block text-sm font-medium mb-1">Tipo *</label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={formData.tipo}
                    onChange={(e) => setFormData({...formData, tipo: e.target.value})}
                  >
                    {tiposDisponiveis.map(t => (
                      <option key={t.value} value={t.value}>
                        {t.icone} {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Ícone */}
                <div>
                  <label className="block text-sm font-medium mb-1">Ícone</label>
                  <input
                    type="text"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={formData.icone}
                    onChange={(e) => setFormData({...formData, icone: e.target.value})}
                    placeholder="💵"
                    maxLength={2}
                  />
                </div>

                {/* Taxa Percentual */}
                <div>
                  <label className="block text-sm font-medium mb-1">Taxa % (Ex: 2.5%)</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={formData.taxa_percentual}
                    onChange={(e) => setFormData({...formData, taxa_percentual: parseFloat(e.target.value) || 0})}
                  />
                </div>

                {/* Taxa Fixa */}
                <div>
                  <label className="block text-sm font-medium mb-1">Taxa Fixa (R$)</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    step="0.01"
                    value={formData.taxa_fixa}
                    onChange={(e) => setFormData({...formData, taxa_fixa: parseFloat(e.target.value) || 0})}
                  />
                </div>

                {/* Prazo */}
                <div>
                  <label className="block text-sm font-medium mb-1">Prazo (dias)</label>
                  <input
                    type="number"
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={formData.prazo_dias}
                    onChange={(e) => setFormData({...formData, prazo_dias: parseInt(e.target.value) || 0})}
                  />
                </div>

                {/* Conta Bancária Destino */}
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Conta Bancária Destino</label>
                  <select
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    value={formData.conta_bancaria_destino_id || ''}
                    onChange={(e) => setFormData({...formData, conta_bancaria_destino_id: parseInt(e.target.value) || null})}
                  >
                    <option value="">Selecione...</option>
                    {contasBancarias.map(c => (
                      <option key={c.id} value={c.id}>{c.nome}</option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Esta conta será usada automaticamente quando esta forma for selecionada em pagamentos/recebimentos
                  </p>
                </div>

                {/* Operadora (para cartões) */}
                {(formData.tipo === 'cartao_credito' || formData.tipo === 'cartao_debito') && (
                  <>
                    <div>
                      <label className="block text-sm font-medium mb-1">Operadora</label>
                      <input
                        type="text"
                        className="w-full border border-gray-300 rounded px-3 py-2"
                        value={formData.operadora}
                        onChange={(e) => setFormData({...formData, operadora: e.target.value})}
                        placeholder="Stone, Cielo, Rede..."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Bandeira</label>
                      <select
                        className="w-full border border-gray-300 rounded px-3 py-2"
                        value={formData.bandeira}
                        onChange={(e) => setFormData({...formData, bandeira: e.target.value})}
                      >
                        <option value="">Selecione...</option>
                        <option value="visa">Visa</option>
                        <option value="master">Mastercard</option>
                        <option value="elo">Elo</option>
                        <option value="amex">American Express</option>
                        <option value="hipercard">Hipercard</option>
                      </select>
                    </div>
                  </>
                )}

                {/* Checkboxes */}
                <div className="col-span-2 space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.ativo}
                      onChange={(e) => setFormData({...formData, ativo: e.target.checked})}
                    />
                    <span className="text-sm">Ativo</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.gera_contas_receber}
                      onChange={(e) => setFormData({...formData, gera_contas_receber: e.target.checked})}
                    />
                    <span className="text-sm">Gera Contas a Receber (para cartões com prazo)</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.requer_nsu}
                      onChange={(e) => setFormData({...formData, requer_nsu: e.target.checked})}
                    />
                    <span className="text-sm">Requer NSU (número de transação)</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.permite_parcelamento}
                      onChange={(e) => setFormData({...formData, permite_parcelamento: e.target.checked})}
                    />
                    <span className="text-sm">Permite Parcelamento</span>
                  </label>

                  {formData.permite_parcelamento && (
                    <div className="ml-6 space-y-3">
                      <div>
                        <label className="block text-sm font-medium mb-1">Máximo de Parcelas</label>
                        <input
                          type="number"
                          className="w-full border border-gray-300 rounded px-3 py-2"
                          min="1"
                          max="24"
                          value={formData.parcelas_maximas}
                          onChange={(e) => setFormData({...formData, parcelas_maximas: parseInt(e.target.value) || 1})}
                        />
                      </div>

                      {/* Configuração de taxas por parcela */}
                      <div className="bg-blue-50 border border-blue-200 rounded p-3">
                        <h4 className="text-sm font-semibold text-blue-900 mb-2">📊 Taxas Específicas por Número de Parcelas</h4>
                        <p className="text-xs text-blue-700 mb-3">Configure taxas diferentes para cada quantidade de parcelas. Se não informado, usa a taxa base ({formData.taxa_percentual}%).</p>
                        
                        <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                          {Array.from({length: formData.parcelas_maximas}, (_, i) => i + 1).map(numParcelas => (
                            <div key={numParcelas} className="flex items-center gap-2">
                              <label className="text-xs font-medium text-gray-700 w-10">{numParcelas}x:</label>
                              <input
                                type="number"
                                step="0.01"
                                className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
                                placeholder={formData.taxa_percentual}
                                value={formData.taxas_por_parcela[numParcelas] || ''}
                                onChange={(e) => {
                                  const novasTaxas = {...formData.taxas_por_parcela};
                                  if (e.target.value) {
                                    novasTaxas[numParcelas] = parseFloat(e.target.value);
                                  } else {
                                    delete novasTaxas[numParcelas];
                                  }
                                  setFormData({...formData, taxas_por_parcela: novasTaxas});
                                }}
                              />
                              <span className="text-xs text-gray-500">%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.permite_antecipacao}
                      onChange={(e) => setFormData({...formData, permite_antecipacao: e.target.checked})}
                    />
                    <span className="text-sm">Permite Antecipação de Recebíveis</span>
                  </label>

                  {formData.permite_antecipacao && (
                    <div className="ml-6 space-y-3">
                      <div>
                        <label className="block text-sm font-medium mb-1">Dias para Recebimento Antecipado</label>
                        <input
                          type="number"
                          className="w-full border border-gray-300 rounded px-3 py-2"
                          min="0"
                          max="30"
                          value={formData.dias_recebimento_antecipado || ''}
                          onChange={(e) => setFormData({...formData, dias_recebimento_antecipado: parseInt(e.target.value) || null})}
                          placeholder="Ex: 1 (cai em D+1)"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Quantos dias após a venda o dinheiro cai na conta com antecipação (geralmente D+1)
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-1">Taxa de Antecipação (%) - OPCIONAL</label>
                        <input
                          type="number"
                          step="0.01"
                          className="w-full border border-gray-300 rounded px-3 py-2"
                          value={formData.taxa_antecipacao_percentual || ''}
                          onChange={(e) => setFormData({...formData, taxa_antecipacao_percentual: parseFloat(e.target.value) || null})}
                          placeholder="Ex: 0.50"
                        />
                        <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded">
                          <p className="text-xs text-amber-800 font-semibold mb-1">💡 Duas formas de configurar:</p>
                          <p className="text-xs text-amber-700 mb-1">
                            <strong>1. Com taxa de antecipação:</strong> Preencha este campo e a taxa será somada automaticamente às taxas por parcela configuradas acima
                          </p>
                          <p className="text-xs text-amber-700">
                            <strong>2. Sem taxa de antecipação:</strong> Deixe vazio e configure nos campos 1x a 12x acima já com o valor final (taxa normal + antecipação somadas)
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 border-t p-4">
              <button
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                onClick={() => setMostrarModal(false)}
              >
                Cancelar
              </button>
              <button
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                onClick={salvar}
              >
                ✓ Salvar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FormasPagamento;
