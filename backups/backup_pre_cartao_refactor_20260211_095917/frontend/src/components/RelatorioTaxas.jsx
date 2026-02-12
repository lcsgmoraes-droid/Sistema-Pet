import React, { useState, useEffect } from 'react';
import api from '../api';
import { toast } from 'react-hot-toast';

const RelatorioTaxas = () => {
  const [loading, setLoading] = useState(true);
  const [dados, setDados] = useState([]);
  const [filtros, setFiltros] = useState({
    data_inicio: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    data_fim: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = async () => {
    try {
      setLoading(true);
      
      // Buscar todas as vendas do período
      const response = await api.get('/vendas', {
        params: {
          data_inicio: filtros.data_inicio,
          data_fim: filtros.data_fim,
          per_page: 1000  // Buscar todas as vendas do período
        }
      });
      
      // Verificar se response.data.vendas existe
      const vendas = response.data.vendas || [];
      
      // Agrupar por forma de pagamento E número de parcelas
      const vendasPorForma = {};
      
      vendas.forEach(venda => {
        if (!venda.forma_pagamento_nome) return;
        
        // Criar chave única: forma + parcelas
        const numParcelas = venda.numero_parcelas || 1;
        const chave = venda.numero_parcelas > 1 
          ? `${venda.forma_pagamento_nome} (${numParcelas}x)`
          : venda.forma_pagamento_nome;
        
        if (!vendasPorForma[chave]) {
          vendasPorForma[chave] = {
            nome: chave,
            forma_base: venda.forma_pagamento_nome,
            parcelas: numParcelas,
            quantidade: 0,
            valor_bruto: 0,
            total_descontos: 0,
            taxa_entrega: 0,
            valor_liquido_antes_taxas: 0,
            valor_total: 0,
            taxa_total: 0,
            taxa_percentual: venda.taxa_percentual || 0,
            taxa_fixa: venda.taxa_fixa || 0,
            vendas: []
          };
        }
        
        const taxa = (venda.valor_total * (venda.taxa_percentual || 0) / 100) + (venda.taxa_fixa || 0);
        
        vendasPorForma[chave].quantidade++;
        vendasPorForma[chave].valor_bruto += (venda.valor_bruto || venda.valor_total);
        vendasPorForma[chave].total_descontos += (venda.desconto || 0);
        vendasPorForma[chave].taxa_entrega += (venda.taxa_entrega || 0);
        vendasPorForma[chave].valor_total += venda.valor_total;
        vendasPorForma[chave].taxa_total += taxa;
        vendasPorForma[chave].valor_liquido_antes_taxas += (venda.valor_total - taxa);
        vendasPorForma[chave].vendas.push(venda);
      });
      
      const dadosArray = Object.values(vendasPorForma).sort((a, b) => b.taxa_total - a.taxa_total);
      setDados(dadosArray);
      
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar relatório');
    } finally {
      setLoading(false);
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', { 
      style: 'currency', 
      currency: 'BRL' 
    }).format(valor / 100);
  };

  const totalGeral = dados.reduce((acc, d) => acc + d.valor_total, 0);
  const taxasTotais = dados.reduce((acc, d) => acc + d.taxa_total, 0);

  if (loading) {
    return <div className="flex justify-center items-center h-64">Carregando...</div>;
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-4">Relatório de Taxas por Forma de Pagamento</h2>
        
        {/* Filtros */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Data Início</label>
              <input
                type="date"
                className="w-full border border-gray-300 rounded px-3 py-2"
                value={filtros.data_inicio}
                onChange={(e) => setFiltros({...filtros, data_inicio: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Data Fim</label>
              <input
                type="date"
                className="w-full border border-gray-300 rounded px-3 py-2"
                value={filtros.data_fim}
                onChange={(e) => setFiltros({...filtros, data_fim: e.target.value})}
              />
            </div>
            <div className="flex items-end">
              <button
                className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                onClick={carregarDados}
              >
                🔍 Buscar
              </button>
            </div>
          </div>
        </div>

        {/* Resumo Geral */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="text-sm text-blue-600 font-medium">Total Vendido</div>
            <div className="text-2xl font-bold text-blue-900">{formatarMoeda(totalGeral)}</div>
          </div>
          <div className="bg-red-50 rounded-lg p-4">
            <div className="text-sm text-red-600 font-medium">Total em Taxas</div>
            <div className="text-2xl font-bold text-red-900">{formatarMoeda(taxasTotais)}</div>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <div className="text-sm text-green-600 font-medium">Líquido Recebido</div>
            <div className="text-2xl font-bold text-green-900">{formatarMoeda(totalGeral - taxasTotais)}</div>
          </div>
        </div>
      </div>

      {/* Tabela Detalhada */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Forma de Pagamento</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Qtd Vendas</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Valor Bruto</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descontos</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Taxa Entrega</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Valor Líquido</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Taxa Config.</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Taxa Paga</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Valor Final</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">% do Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {dados.length === 0 ? (
              <tr>
                <td colSpan="10" className="px-6 py-4 text-center text-gray-500">
                  Nenhuma venda no período selecionado
                </td>
              </tr>
            ) : (
              dados.map((item, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-6 py-4 font-medium">{item.nome}</td>
                  <td className="px-6 py-4">{item.quantidade}</td>
                  <td className="px-6 py-4">{formatarMoeda(item.valor_bruto)}</td>
                  <td className="px-6 py-4 text-orange-600">{formatarMoeda(item.total_descontos)}</td>
                  <td className="px-6 py-4 text-blue-600">{formatarMoeda(item.taxa_entrega)}</td>
                  <td className="px-6 py-4 font-semibold">{formatarMoeda(item.valor_total)}</td>
                  <td className="px-6 py-4 text-sm">
                    {item.taxa_percentual > 0 && `${item.taxa_percentual}%`}
                    {item.taxa_percentual > 0 && item.taxa_fixa > 0 && ' + '}
                    {item.taxa_fixa > 0 && formatarMoeda(item.taxa_fixa)}
                    {item.taxa_percentual === 0 && item.taxa_fixa === 0 && 'Sem taxa'}
                  </td>
                  <td className="px-6 py-4 text-red-600 font-semibold">{formatarMoeda(item.taxa_total)}</td>
                  <td className="px-6 py-4 text-green-600 font-semibold">
                    {formatarMoeda(item.valor_liquido_antes_taxas)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{width: `${(item.valor_total / totalGeral * 100)}%`}}
                        />
                      </div>
                      <span className="text-sm font-medium">{((item.valor_total / totalGeral) * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
          <tfoot className="bg-gray-50 font-bold">
            <tr>
              <td className="px-6 py-4">TOTAL</td>
              <td className="px-6 py-4">{dados.reduce((acc, d) => acc + d.quantidade, 0)}</td>
              <td className="px-6 py-4">{formatarMoeda(dados.reduce((acc, d) => acc + d.valor_bruto, 0))}</td>
              <td className="px-6 py-4 text-orange-900">{formatarMoeda(dados.reduce((acc, d) => acc + d.total_descontos, 0))}</td>
              <td className="px-6 py-4 text-blue-900">{formatarMoeda(dados.reduce((acc, d) => acc + d.taxa_entrega, 0))}</td>
              <td className="px-6 py-4 text-blue-900">{formatarMoeda(totalGeral)}</td>
              <td className="px-6 py-4">-</td>
              <td className="px-6 py-4 text-red-900">{formatarMoeda(taxasTotais)}</td>
              <td className="px-6 py-4 text-green-900">{formatarMoeda(totalGeral - taxasTotais)}</td>
              <td className="px-6 py-4">100%</td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Dica */}
      <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <span className="text-2xl">💡</span>
          <div>
            <h4 className="font-semibold text-yellow-900 mb-1">Dica</h4>
            <p className="text-sm text-yellow-800">
              Este relatório agrupa vendas por forma de pagamento E número de parcelas (ex: Crédito 1x, Crédito 2x, Crédito 3x...).
              Mostra o fluxo completo: Valor Bruto → Descontos → Taxa Entrega → Valor Líquido → Taxas Financeiras → Valor Final Recebido.
              Para análises precisas, certifique-se de que as taxas estejam sempre atualizadas nas formas de pagamento antes de registrar vendas.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RelatorioTaxas;
