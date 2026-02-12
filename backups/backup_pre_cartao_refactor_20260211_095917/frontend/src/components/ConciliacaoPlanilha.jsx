import React, { useState } from 'react';
import axios from 'axios';

const ConciliacaoPlanilha = () => {
  const [step, setStep] = useState(1); // 1=upload, 2=mapeamento, 3=resultado
  const [file, setFile] = useState(null);
  const [uploadData, setUploadData] = useState(null);
  const [mapeamento, setMapeamento] = useState({
    coluna_identificador: '',
    coluna_valor: '',
    coluna_data: '',
    coluna_status: '',
    coluna_adquirente: '',
    formato_data: 'DD/MM/YYYY'
  });
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(false);

  // Step 1: Upload do arquivo
  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('/api/conciliacao/upload-planilha', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setUploadData(response.data);
      setStep(2);
    } catch (error) {
      alert('Erro ao carregar planilha: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Processar com mapeamento
  const handleProcessar = async (e) => {
    e.preventDefault();
    
    if (!mapeamento.coluna_identificador || !mapeamento.coluna_valor || !mapeamento.coluna_data) {
      alert('Preencha os campos obrigatórios: Identificador, Valor e Data');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('coluna_identificador', mapeamento.coluna_identificador);
    formData.append('coluna_valor', mapeamento.coluna_valor);
    formData.append('coluna_data', mapeamento.coluna_data);
    formData.append('formato_data', mapeamento.formato_data);
    
    if (mapeamento.coluna_status) {
      formData.append('coluna_status', mapeamento.coluna_status);
    }
    if (mapeamento.coluna_adquirente) {
      formData.append('coluna_adquirente', mapeamento.coluna_adquirente);
    }

    try {
      const response = await axios.post('/api/conciliacao/mapear-colunas', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setResultado(response.data);
      setStep(3);
    } catch (error) {
      alert('Erro ao processar conciliação: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const resetar = () => {
    setStep(1);
    setFile(null);
    setUploadData(null);
    setMapeamento({
      coluna_identificador: '',
      coluna_valor: '',
      coluna_data: '',
      coluna_status: '',
      coluna_adquirente: '',
      formato_data: 'DD/MM/YYYY'
    });
    setResultado(null);
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">📊 Conciliação de Pagamentos via Planilha</h1>

      {/* Step 1: Upload */}
      {step === 1 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">1️⃣ Upload da Planilha</h2>
          <p className="text-gray-600 mb-4">
            Faça upload de uma planilha Excel (.xlsx) ou CSV com os dados das transações da adquirente 
            (Stone, Cielo, Rede, PagSeguro, etc).
          </p>

          <form onSubmit={handleFileUpload}>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">
                Selecione o arquivo:
              </label>
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={(e) => setFile(e.target.files[0])}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>

            <button
              type="submit"
              disabled={!file || loading}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading ? 'Carregando...' : '📤 Fazer Upload'}
            </button>
          </form>
        </div>
      )}

      {/* Step 2: Mapeamento de Colunas */}
      {step === 2 && uploadData && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">2️⃣ Configuração de Mapeamento</h2>
          
          <div className="bg-blue-50 p-4 rounded mb-4">
            <p className="font-medium">📄 {uploadData.filename}</p>
            <p className="text-sm text-gray-600">{uploadData.total_rows} linhas carregadas</p>
          </div>

          <form onSubmit={handleProcessar}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {/* Identificador */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  * Coluna do Identificador:
                  <span className="text-xs text-gray-500 ml-2">(NSU, STONEID, RRN, etc)</span>
                </label>
                <select
                  value={mapeamento.coluna_identificador}
                  onChange={(e) => setMapeamento({...mapeamento, coluna_identificador: e.target.value})}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  required
                >
                  <option value="">Selecione...</option>
                  {uploadData.columns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              {/* Valor */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  * Coluna do Valor:
                </label>
                <select
                  value={mapeamento.coluna_valor}
                  onChange={(e) => setMapeamento({...mapeamento, coluna_valor: e.target.value})}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  required
                >
                  <option value="">Selecione...</option>
                  {uploadData.columns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              {/* Data */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  * Coluna da Data:
                </label>
                <select
                  value={mapeamento.coluna_data}
                  onChange={(e) => setMapeamento({...mapeamento, coluna_data: e.target.value})}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  required
                >
                  <option value="">Selecione...</option>
                  {uploadData.columns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              {/* Formato Data */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  * Formato da Data:
                </label>
                <select
                  value={mapeamento.formato_data}
                  onChange={(e) => setMapeamento({...mapeamento, formato_data: e.target.value})}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                >
                  <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                  <option value="DD/MM/YYYY HH:MM">DD/MM/YYYY HH:MM</option>
                  <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                </select>
              </div>

              {/* Status (opcional) */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Coluna do Status (opcional):
                </label>
                <select
                  value={mapeamento.coluna_status}
                  onChange={(e) => setMapeamento({...mapeamento, coluna_status: e.target.value})}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                >
                  <option value="">Não usar</option>
                  {uploadData.columns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              {/* Adquirente (opcional) */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Coluna da Adquirente (opcional):
                </label>
                <select
                  value={mapeamento.coluna_adquirente}
                  onChange={(e) => setMapeamento({...mapeamento, coluna_adquirente: e.target.value})}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                >
                  <option value="">Não usar</option>
                  {uploadData.columns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Preview */}
            <div className="mb-6">
              <h3 className="font-medium mb-2">📋 Preview dos Dados:</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm border">
                  <thead className="bg-gray-100">
                    <tr>
                      {uploadData.columns.map(col => (
                        <th key={col} className="px-4 py-2 border">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {uploadData.preview.slice(0, 5).map((row, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        {uploadData.columns.map(col => (
                          <td key={col} className="px-4 py-2 border">{row[col]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                type="button"
                onClick={resetar}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                ← Voltar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
              >
                {loading ? 'Processando...' : '✅ Processar Conciliação'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Step 3: Resultado */}
      {step === 3 && resultado && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">3️⃣ Resultado da Conciliação</h2>

          {/* Resumo */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded">
              <p className="text-2xl font-bold text-blue-600">{resultado.resumo.total}</p>
              <p className="text-sm text-gray-600">Total Processado</p>
            </div>
            <div className="bg-green-50 p-4 rounded">
              <p className="text-2xl font-bold text-green-600">{resultado.resumo.conciliados_automatico}</p>
              <p className="text-sm text-gray-600">Match Automático (NSU)</p>
            </div>
            <div className="bg-yellow-50 p-4 rounded">
              <p className="text-2xl font-bold text-yellow-600">{resultado.resumo.conciliados_manual}</p>
              <p className="text-sm text-gray-600">Match Manual (Valor+Data)</p>
            </div>
            <div className="bg-red-50 p-4 rounded">
              <p className="text-2xl font-bold text-red-600">{resultado.resumo.pendentes}</p>
              <p className="text-sm text-gray-600">Sem Match</p>
            </div>
          </div>

          {/* Detalhes */}
          <div className="overflow-x-auto mb-6">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Linha</th>
                  <th className="px-4 py-2 text-left">Identificador</th>
                  <th className="px-4 py-2 text-left">Valor</th>
                  <th className="px-4 py-2 text-left">Data</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Venda</th>
                </tr>
              </thead>
              <tbody>
                {resultado.detalhes.map((item, idx) => (
                  <tr key={idx} className={item.match ? 'bg-green-50' : 'bg-red-50'}>
                    <td className="px-4 py-2">{item.linha}</td>
                    <td className="px-4 py-2 font-mono text-xs">{item.identificador}</td>
                    <td className="px-4 py-2">R$ {item.valor?.toFixed(2)}</td>
                    <td className="px-4 py-2">{item.data}</td>
                    <td className="px-4 py-2">
                      {item.match ? (
                        <span className="px-2 py-1 bg-green-200 text-green-800 rounded text-xs">
                          ✅ {item.match_type === 'nsu' ? 'NSU' : 'Valor+Data'}
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-red-200 text-red-800 rounded text-xs">
                          ❌ Sem match
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {item.venda_numero || item.motivo || item.erro}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            onClick={resetar}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            🔄 Nova Conciliação
          </button>
        </div>
      )}
    </div>
  );
};

export default ConciliacaoPlanilha;
