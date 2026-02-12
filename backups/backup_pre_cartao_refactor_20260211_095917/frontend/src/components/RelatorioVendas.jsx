import { useState, useEffect } from 'react';
import api from '../api';
import { Calendar, DollarSign, TrendingUp, Package, Users, CreditCard, Filter } from 'lucide-react';

export default function RelatorioVendas() {
  const [loading, setLoading] = useState(true);
  const [abaAtiva, setAbaAtiva] = useState('resumo');
  const [dataInicio, setDataInicio] = useState(new Date().toISOString().split('T')[0]);
  const [dataFim, setDataFim] = useState(new Date().toISOString().split('T')[0]);
  
  // Estados dos dados
  const [resumo, setResumo] = useState({
    venda_bruta: 0,
    taxa_entrega: 0,
    desconto: 0,
    venda_liquida: 0,
    em_aberto: 0,
    quantidade_vendas: 0
  });
  
  const [vendasPorData, setVendasPorData] = useState([]);
  const [formasRecebimento, setFormasRecebimento] = useState([]);
  const [vendasPorFuncionario, setVendasPorFuncionario] = useState([]);
  const [vendasPorTipo, setVendasPorTipo] = useState([]);
  const [vendasPorGrupo, setVendasPorGrupo] = useState([]);
  const [produtosDetalhados, setProdutosDetalhados] = useState([]);
  const [listaVendas, setListaVendas] = useState([]);

  const getToken = () => localStorage.getItem('access_token');

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0);
  };

  const formatarData = (dataStr) => {
    const data = new Date(dataStr);
    return data.toLocaleDateString('pt-BR');
  };

  const carregarDados = async () => {
    setLoading(true);
    const token = getToken();
    const config = {
      headers: { Authorization: `Bearer ${token}` },
      params: { data_inicio: dataInicio, data_fim: dataFim }
    };

    try {
      const response = await api.get(`/vendas/relatorio`, config);
      const data = response.data;

      setResumo(data.resumo || {});
      setVendasPorData(data.vendas_por_data || []);
      setFormasRecebimento(data.formas_recebimento || []);
      setVendasPorFuncionario(data.vendas_por_funcionario || []);
      setVendasPorTipo(data.vendas_por_tipo || []);
      setVendasPorGrupo(data.vendas_por_grupo || []);
      setProdutosDetalhados(data.produtos_detalhados || []);
      setListaVendas(data.lista_vendas || []);
      
      console.log('✅ Dados carregados:', {
        vendasPorData: data.vendas_por_data?.length || 0,
        formasRecebimento: data.formas_recebimento?.length || 0
      });
    } catch (error) {
      console.error('Erro ao carregar relatório:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarDados();
  }, [dataInicio, dataFim]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div style={{backgroundColor: 'red', color: 'white', padding: '20px', fontSize: '24px', fontWeight: 'bold'}}>
        🔴 TESTE: ARQUIVO ESTÁ SENDO CARREGADO CORRETAMENTE
      </div>
      {/* Cabeçalho com Filtros */}
      <div className="mb-6 bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold text-gray-800">Consulta de Vendas</h1>
          <div className="flex gap-2">
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="border rounded px-3 py-2"
            />
            <span className="self-center">até</span>
            <input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="border rounded px-3 py-2"
            />
          </div>
        </div>

        {/* Abas */}
        <div className="flex gap-2 border-b">
          <button
            onClick={() => setAbaAtiva('resumo')}
            className={`px-4 py-2 font-medium ${
              abaAtiva === 'resumo'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Resumo
          </button>
          <button
            onClick={() => setAbaAtiva('produtos')}
            className={`px-4 py-2 font-medium ${
              abaAtiva === 'produtos'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Totais por produto/serviço
          </button>
          <button
            onClick={() => setAbaAtiva('lista')}
            className={`px-4 py-2 font-medium ${
              abaAtiva === 'lista'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Lista de Vendas
          </button>
        </div>
      </div>

      {/* Conteúdo das Abas */}
      {abaAtiva === 'resumo' && (
        <div>
          {/* Cards de Resumo */}
          <div className="grid grid-cols-5 gap-4 mb-6">
            <div className="bg-green-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">{formatarMoeda(resumo.venda_bruta)}</div>
              <div className="text-sm">Venda bruta</div>
            </div>
            <div className="bg-gray-400 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">{formatarMoeda(resumo.taxa_entrega)}</div>
              <div className="text-sm">Taxa de entrega</div>
            </div>
            <div className="bg-yellow-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">{formatarMoeda(resumo.desconto)}</div>
              <div className="text-sm">{resumo.percentual_desconto}% de desconto</div>
            </div>
            <div className="bg-blue-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">{formatarMoeda(resumo.venda_liquida)}</div>
              <div className="text-sm">Venda Líquida</div>
            </div>
            <div className="bg-red-500 text-white p-4 rounded-lg shadow">
              <div className="text-3xl font-bold">{formatarMoeda(resumo.em_aberto)}</div>
              <div className="text-sm">Em aberto</div>
            </div>
          </div>

          {/* Vendas por Data */}
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
              Vendas por data
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Data</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Tkt. Médio</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Taxa entrega</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">(%)</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                    <th className="px-4 py-2 text-right">Vl. recebido</th>
                    <th className="px-4 py-2 text-right">Saldo aberto</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorData.map((item, idx) => (
                    <tr key={idx} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2">{formatarData(item.data)}</td>
                      <td className="px-4 py-2 text-right">{item.quantidade}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.ticket_medio)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.taxa_entrega)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.desconto)}</td>
                      <td className="px-4 py-2 text-right">{item.percentual_desconto}%</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_liquido)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_recebido)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.saldo_aberto)}</td>
                    </tr>
                  ))}
                  {/* Linha de Total */}
                  {vendasPorData.length > 0 && (
                    <tr style={{backgroundColor: '#374151', color: 'white', fontWeight: 'bold'}}>
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">{vendasPorData.reduce((sum, item) => sum + item.quantidade, 0)}</td>
                      <td className="px-4 py-3 text-right">-</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.valor_bruto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.taxa_entrega, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.desconto, 0))}</td>
                      <td className="px-4 py-3 text-right">-</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.valor_liquido, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.valor_recebido, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorData.reduce((sum, item) => sum + item.saldo_aberto, 0))}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Grid com outras tabelas */}
          <div className="grid grid-cols-2 gap-6">
            {/* Formas de Recebimento */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Formas de recebimento
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Forma</th>
                    <th className="px-4 py-2 text-right">Valor pago</th>
                  </tr>
                </thead>
                <tbody>
                  {formasRecebimento.map((item, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="px-4 py-2">{item.forma_pagamento}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_total)}</td>
                    </tr>
                  ))}
                  {formasRecebimento.length > 0 && (
                    <tr style={{backgroundColor: '#374151', color: 'white', fontWeight: 'bold'}}>
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(formasRecebimento.reduce((sum, item) => sum + item.valor_total, 0))}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Funcionário */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Funcionário
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Nome</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorFuncionario.map((item, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="px-4 py-2">{item.funcionario}</td>
                      <td className="px-4 py-2 text-right">{item.quantidade}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.desconto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_liquido)}</td>
                    </tr>
                  ))}
                  {vendasPorFuncionario.length > 0 && (
                    <tr style={{backgroundColor: '#374151', color: 'white', fontWeight: 'bold'}}>
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">{vendasPorFuncionario.reduce((sum, item) => sum + item.quantidade, 0)}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorFuncionario.reduce((sum, item) => sum + item.valor_bruto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorFuncionario.reduce((sum, item) => sum + item.desconto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorFuncionario.reduce((sum, item) => sum + item.valor_liquido, 0))}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Tipo */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Tipo
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Tipo</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorTipo.map((item, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="px-4 py-2">{item.tipo}</td>
                      <td className="px-4 py-2 text-right">{item.quantidade}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.desconto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_liquido)}</td>
                    </tr>
                  ))}
                  {vendasPorTipo.length > 0 && (
                    <tr style={{backgroundColor: '#374151', color: 'white', fontWeight: 'bold'}}>
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">{vendasPorTipo.reduce((sum, item) => sum + item.quantidade, 0)}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorTipo.reduce((sum, item) => sum + item.valor_bruto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorTipo.reduce((sum, item) => sum + item.desconto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorTipo.reduce((sum, item) => sum + item.valor_liquido, 0))}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Grupo de Produto */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Grupo de produto
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Nome</th>
                    <th className="px-4 py-2 text-right">Percentual</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorGrupo.map((item, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="px-4 py-2">{item.grupo}</td>
                      <td className="px-4 py-2 text-right">{item.percentual}%</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.desconto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(item.valor_liquido)}</td>
                    </tr>
                  ))}
                  {vendasPorGrupo.length > 0 && (
                    <tr style={{backgroundColor: '#374151', color: 'white', fontWeight: 'bold'}}>
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">-</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorGrupo.reduce((sum, item) => sum + item.valor_bruto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorGrupo.reduce((sum, item) => sum + item.desconto, 0))}</td>
                      <td className="px-4 py-3 text-right">{formatarMoeda(vendasPorGrupo.reduce((sum, item) => sum + item.valor_liquido, 0))}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Aba Produtos Detalhados */}
      {abaAtiva === 'produtos' && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
            Produtos/Serviços
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Produtos/Serviços</th>
                  <th className="px-4 py-2 text-right">Itens</th>
                  <th className="px-4 py-2 text-right">Bruto</th>
                  <th className="px-4 py-2 text-right">Desconto</th>
                  <th className="px-4 py-2 text-right">Líquido</th>
                </tr>
              </thead>
              <tbody>
                {produtosDetalhados.map((categoria, catIdx) => (
                  <>
                    {/* Linha da Categoria */}
                    <tr key={`cat-${catIdx}`} className="bg-blue-50 font-semibold border-b-2 border-blue-300">
                      <td className="px-4 py-2">{categoria.categoria}</td>
                      <td className="px-4 py-2 text-right">{categoria.total_quantidade}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(categoria.total_bruto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(categoria.total_desconto)}</td>
                      <td className="px-4 py-2 text-right">{formatarMoeda(categoria.total_liquido)}</td>
                    </tr>
                    
                    {/* Subcategorias */}
                    {categoria.subcategorias && categoria.subcategorias.map((subcategoria, subIdx) => (
                      <>
                        <tr key={`subcat-${catIdx}-${subIdx}`} className="bg-gray-50 font-medium border-b">
                          <td className="px-4 py-2 pl-8">📁 {subcategoria.subcategoria}</td>
                          <td className="px-4 py-2 text-right">{subcategoria.total_quantidade}</td>
                          <td className="px-4 py-2 text-right">{formatarMoeda(subcategoria.total_bruto)}</td>
                          <td className="px-4 py-2 text-right">{formatarMoeda(subcategoria.total_desconto)}</td>
                          <td className="px-4 py-2 text-right">{formatarMoeda(subcategoria.total_liquido)}</td>
                        </tr>
                        
                        {/* Produtos da Subcategoria */}
                        {subcategoria.produtos.map((produto, prodIdx) => (
                          <tr key={`prod-${catIdx}-${subIdx}-${prodIdx}`} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-2 pl-12 text-gray-700">{produto.produto}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{produto.quantidade}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.valor_bruto)}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.desconto)}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.valor_liquido)}</td>
                          </tr>
                        ))}
                      </>
                    ))}
                    
                    {/* Produtos diretos da Categoria (sem subcategoria) */}
                    {categoria.produtos && categoria.produtos.map((produto, prodIdx) => (
                      <tr key={`prod-${catIdx}-${prodIdx}`} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-2 pl-8 text-gray-700">{produto.produto}</td>
                        <td className="px-4 py-2 text-right text-gray-700">{produto.quantidade}</td>
                        <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.valor_bruto)}</td>
                        <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.desconto)}</td>
                        <td className="px-4 py-2 text-right text-gray-700">{formatarMoeda(produto.valor_liquido)}</td>
                      </tr>
                    ))}
                  </>
                ))}
                
                {/* Linha de Total */}
                {produtosDetalhados.length > 0 && (
                  <tr style={{backgroundColor: '#374151', color: 'white', fontWeight: 'bold'}}>
                    <td className="px-4 py-3">TOTAL GERAL</td>
                    <td className="px-4 py-3 text-right">
                      {produtosDetalhados.reduce((sum, cat) => sum + cat.total_quantidade, 0)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(produtosDetalhados.reduce((sum, cat) => sum + cat.total_bruto, 0))}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(produtosDetalhados.reduce((sum, cat) => sum + cat.total_desconto, 0))}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(produtosDetalhados.reduce((sum, cat) => sum + cat.total_liquido, 0))}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Aba Lista de Vendas */}
      {abaAtiva === 'lista' && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
            Lista de Vendas
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Cód.</th>
                  <th className="px-4 py-2 text-left">Data e hora</th>
                  <th className="px-4 py-2 text-left">Cliente</th>
                  <th className="px-4 py-2 text-left">Animal</th>
                  <th className="px-4 py-2 text-right">Valor</th>
                  <th className="px-4 py-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {listaVendas.map((venda) => (
                  <tr key={venda.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-2">{venda.numero_venda || venda.id}</td>
                    <td className="px-4 py-2">{formatarData(venda.data_venda)}</td>
                    <td className="px-4 py-2">{venda.cliente_nome}</td>
                    <td className="px-4 py-2">{venda.pet_nome || '-'}</td>
                    <td className="px-4 py-2 text-right">{formatarMoeda(venda.total)}</td>
                    <td className="px-4 py-2 text-center">
                      <span className={`px-2 py-1 rounded text-xs ${
                        venda.status === 'finalizada' ? 'bg-green-100 text-green-800' :
                        venda.status === 'baixa_parcial' ? 'bg-blue-100 text-blue-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {venda.status === 'finalizada' ? 'Baixada' : 
                         venda.status === 'baixa_parcial' ? 'Parcial' : 
                         'Em aberto'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
