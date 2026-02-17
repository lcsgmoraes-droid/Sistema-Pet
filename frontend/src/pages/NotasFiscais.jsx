import { useState, useEffect } from 'react';
import { 
  FileText, 
  Download, 
  X, 
  CheckCircle, 
  AlertCircle, 
  Calendar,
  Search,
  Filter,
  Eye,
  Printer,
  XCircle,
  Trash2
} from 'lucide-react';
import api from '../api';

export default function NotasFiscais() {
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroSituacao, setFiltroSituacao] = useState('');
  const [dataInicial, setDataInicial] = useState('');
  const [dataFinal, setDataFinal] = useState('');
  const [busca, setBusca] = useState('');
  const [erro, setErro] = useState('');
  const [notaSelecionada, setNotaSelecionada] = useState(null);
  const [modalCancelar, setModalCancelar] = useState(null);
  const [justificativa, setJustificativa] = useState('');
  const [cancelando, setCancelando] = useState(false);

  const SITUACOES = [
    { value: '', label: 'Todas' },
    { value: 'Autorizada', label: 'Autorizada' },
    { value: 'Emitida DANFE', label: 'Emitida DANFE' },
    { value: 'Cancelada', label: 'Cancelada' },
    { value: 'Pendente', label: 'Pendente' }
  ];

  useEffect(() => {
    carregarNotas();
  }, [filtroSituacao, dataInicial, dataFinal]);

  const carregarNotas = async () => {
    try {
      setLoading(true);
      setErro('');
      
      const params = new URLSearchParams();
      if (filtroSituacao) params.append('situacao', filtroSituacao);
      if (dataInicial) params.append('data_inicial', dataInicial);
      if (dataFinal) params.append('data_final', dataFinal);
      
      const response = await api.get(`/nfe/?${params.toString()}`);
      setNotas(response.data.notas || []);
    } catch (error) {
      console.error('Erro ao carregar notas:', error);
      setErro('Erro ao carregar notas fiscais');
    } finally {
      setLoading(false);
    }
  };

  const baixarDanfe = async (nfeId, numero) => {
    try {
      const response = await api.get(`/nfe/${nfeId}/danfe`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `danfe_${numero}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Erro ao baixar DANFE:', error);
      alert('Erro ao baixar DANFE');
    }
  };

  const baixarXml = async (nfeId, numero) => {
    try {
      const response = await api.get(`/nfe/${nfeId}/xml`);
      
      const blob = new Blob([response.data.xml], { type: 'application/xml' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `nfe_${numero}.xml`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Erro ao baixar XML:', error);
      alert('Erro ao baixar XML');
    }
  };

  const cancelarNota = async () => {
    if (!justificativa || justificativa.length < 15) {
      alert('A justificativa deve ter no mínimo 15 caracteres');
      return;
    }

    try {
      setCancelando(true);
      await api.post(`/nfe/${modalCancelar.id}/cancelar`, {
        justificativa
      });
      
      alert('Nota fiscal cancelada com sucesso!');
      setModalCancelar(null);
      setJustificativa('');
      carregarNotas();
    } catch (error) {
      console.error('Erro ao cancelar nota:', error);
      alert(error.response?.data?.detail || 'Erro ao cancelar nota fiscal');
    } finally {
      setCancelando(false);
    }
  };

  const excluirNota = async (venda_id, numero) => {
    if (!confirm(`Deseja realmente excluir a nota ${numero}?\n\nIsso apenas remove os dados da nota do sistema, não cancela no Bling/SEFAZ.`)) {
      return;
    }

    try {
      await api.delete(`/nfe/${venda_id}`);
      alert('Nota fiscal excluída com sucesso!');
      carregarNotas();
    } catch (error) {
      console.error('Erro ao excluir nota:', error);
      alert(error.response?.data?.detail || 'Erro ao excluir nota fiscal');
    }
  };

  const getSituacaoCor = (status) => {
    switch (status?.toLowerCase()) {
      case 'autorizada':
      case 'emitida danfe':
        return 'bg-green-100 text-green-800';
      case 'cancelada':
        return 'bg-red-100 text-red-800';
      case 'pendente':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSituacaoIcone = (status) => {
    switch (status?.toLowerCase()) {
      case 'autorizada':
      case 'emitida danfe':
        return <CheckCircle className="w-4 h-4" />;
      case 'cancelada':
        return <X className="w-4 h-4" />;
      case 'pendente':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const notasFiltradas = notas.filter(nota => {
    if (!busca) return true;
    
    const buscaLower = busca.toLowerCase();
    return (
      nota.numero?.toLowerCase().includes(buscaLower) ||
      nota.serie?.toLowerCase().includes(buscaLower) ||
      nota.cliente?.nome?.toLowerCase().includes(buscaLower) ||
      nota.cliente?.cpf_cnpj?.toLowerCase().includes(buscaLower)
    );
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <FileText className="w-8 h-8 text-blue-600" />
          Notas Fiscais de Saída
        </h1>
        <p className="text-gray-600 mt-1">Gerencie suas NF-e e NFC-e emitidas</p>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-5 h-5 text-gray-600" />
          <h2 className="font-semibold text-gray-800">Filtros</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Busca */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por número, cliente..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Data Inicial */}
            <div>
              <input
                type="date"
                value={dataInicial}
                onChange={(e) => setDataInicial(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Data Final */}
            <div>
              <input
                type="date"
                value={dataFinal}
                onChange={(e) => setDataFinal(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Situação */}
            <select
              value={filtroSituacao}
              onChange={(e) => setFiltroSituacao(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
          {SITUACOES.map(sit => (
            <option key={sit.value} value={sit.value}>{sit.label}</option>
          ))}
        </select>
      </div>
    </div>

    {/* Erro */}
    {erro && (
      <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4 mb-6 flex items-center gap-2">
        <AlertCircle className="w-5 h-5" />
        {erro}
      </div>
    )}

    {/* Loading */}
    {loading ? (
      <div className="bg-white rounded-lg shadow-sm p-12 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="text-gray-600 mt-4">Carregando notas fiscais...</p>
      </div>
    ) : notasFiltradas.length === 0 ? (
      <div className="bg-white rounded-lg shadow-sm p-12 text-center">
        <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-800 mb-2">
          Nenhuma nota encontrada
        </h3>
        <p className="text-gray-600">
          {busca || filtroSituacao || dataInicial || dataFinal
            ? 'Tente ajustar os filtros'
            : 'Emita sua primeira nota fiscal em uma venda'}
        </p>
      </div>
    ) : (
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Número
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Data Emissão
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Cliente
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Situação
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Valor
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {notasFiltradas.map((nota) => (
                  <tr key={nota.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {nota.numero}
                      </div>
                      <div className="text-sm text-gray-500">
                        Série {nota.serie}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {nota.data_emissao
                          ? new Date(nota.data_emissao).toLocaleDateString('pt-BR')
                          : '-'}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">
                        {nota.cliente?.nome || 'Cliente não informado'}
                      </div>
                      <div className="text-sm text-gray-500">
                        {nota.cliente?.cpf_cnpj || ''}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getSituacaoCor(nota.status)}`}>
                        {getSituacaoIcone(nota.status)}
                        {nota.status || 'Pendente'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      R$ {nota.valor.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        {/* Botão Cancelar - só para notas autorizadas */}
                        {(nota.status?.toLowerCase() === 'autorizada' || nota.status?.toLowerCase() === 'emitida danfe') && (
                          <button
                            onClick={() => setModalCancelar(nota)}
                            className="text-red-600 hover:text-red-900 p-1 hover:bg-red-50 rounded"
                            title="Cancelar NF-e"
                          >
                            <XCircle className="w-5 h-5" />
                          </button>
                        )}
                        
                        {/* Botão Excluir */}
                        <button
                          onClick={() => excluirNota(nota.venda_id, nota.numero)}
                          className="text-gray-600 hover:text-gray-900 p-1 hover:bg-gray-50 rounded"
                          title="Excluir nota do sistema"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                        
                        <button
                          onClick={() => baixarDanfe(nota.id, nota.numero)}
                          className="text-blue-600 hover:text-blue-900 p-1 hover:bg-blue-50 rounded"
                          title="Baixar DANFE"
                        >
                          <Printer className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => baixarXml(nota.id, nota.numero)}
                          className="text-green-600 hover:text-green-900 p-1 hover:bg-green-50 rounded"
                          title="Baixar XML"
                        >
                          <Download className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => setNotaSelecionada(nota)}
                          className="text-gray-600 hover:text-gray-900 p-1 hover:bg-gray-50 rounded"
                          title="Ver Detalhes"
                        >
                          <Eye className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
      </div>
    )}

    {/* Total de registros */}
    {!loading && notasFiltradas.length > 0 && (
      <div className="mt-4 text-sm text-gray-600 text-center">
        {notasFiltradas.length} {notasFiltradas.length === 1 ? 'nota encontrada' : 'notas encontradas'}
      </div>
    )}

    {/* Modal de Detalhes */}
    {notaSelecionada && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
          <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
            <h3 className="text-xl font-bold text-gray-800">
              Detalhes da Nota Fiscal #{notaSelecionada.numero}
            </h3>
            <button
              onClick={() => setNotaSelecionada(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-600">Número</label>
                <p className="text-gray-900">{notaSelecionada.numero}</p>
              </div>
              <div>
                    <label className="text-sm font-medium text-gray-600">Série</label>
                    <p className="text-gray-900">{notaSelecionada.serie}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Modelo</label>
                    <p className="text-gray-900">{notaSelecionada.modelo}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Tipo</label>
                    <p className="text-gray-900">{notaSelecionada.tipo === 'nfe' ? 'NF-e' : 'NFC-e'}</p>
                  </div>
                  <div className="col-span-2">
                    <label className="text-sm font-medium text-gray-600">Chave de Acesso</label>
                    <p className="text-gray-900 text-xs break-all">{notaSelecionada.chave || '-'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Cliente</label>
                    <p className="text-gray-900">{notaSelecionada.cliente?.nome}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">CPF/CNPJ</label>
                    <p className="text-gray-900">{notaSelecionada.cliente?.cpf_cnpj}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Valor Total</label>
                    <p className="text-gray-900 text-lg font-bold">R$ {notaSelecionada.valor.toFixed(2)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Situação</label>
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getSituacaoCor(notaSelecionada.status)}`}>
                      {getSituacaoIcone(notaSelecionada.status)}
                      {notaSelecionada.status}
                    </span>
                  </div>
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  onClick={() => baixarDanfe(notaSelecionada.id, notaSelecionada.numero)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  <Printer className="w-5 h-5" />
                  Baixar DANFE
                </button>
                <button
                  onClick={() => baixarXml(notaSelecionada.id, notaSelecionada.numero)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                >
                  <Download className="w-5 h-5" />
                  Baixar XML
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Cancelamento */}
      {modalCancelar && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4">
            <div className="bg-red-50 border-b px-6 py-4 flex items-center gap-3">
              <XCircle className="w-6 h-6 text-red-600" />
              <h3 className="text-xl font-bold text-gray-800">
                Cancelar Nota Fiscal
              </h3>
            </div>

            <div className="p-6 space-y-4">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <p className="text-sm text-yellow-800">
                  <strong>Atenção:</strong> O cancelamento de uma nota fiscal é irreversível e será enviado para a SEFAZ.
                </p>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-2">
                  <strong>Nota:</strong> #{modalCancelar.numero} - Série {modalCancelar.serie}
                </p>
                <p className="text-sm text-gray-600">
                  <strong>Cliente:</strong> {modalCancelar.cliente?.nome}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Justificativa do Cancelamento *
                </label>
                <textarea
                  value={justificativa}
                  onChange={(e) => setJustificativa(e.target.value)}
                  placeholder="Digite o motivo do cancelamento (mínimo 15 caracteres)"
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  {justificativa.length}/15 caracteres
                </p>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setModalCancelar(null);
                    setJustificativa('');
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  disabled={cancelando}
                >
                  Voltar
                </button>
                <button
                  onClick={cancelarNota}
                  disabled={cancelando || justificativa.length < 15}
                  className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {cancelando ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Cancelando...
                    </>
                  ) : (
                    <>
                      <XCircle className="w-5 h-5" />
                      Confirmar Cancelamento
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
