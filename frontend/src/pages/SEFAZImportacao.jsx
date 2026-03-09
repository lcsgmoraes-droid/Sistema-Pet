import { useState } from 'react';
import api from '../api';

export default function SEFAZImportacao() {
  const [chave, setChave] = useState('');
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState('');
  const [loading, setLoading] = useState(false);

  function formatarChave(valor) {
    // Remove tudo que não for dígito e limita a 44
    return valor.replace(/\D/g, '').slice(0, 44);
  }

  async function consultar(e) {
    e.preventDefault();
    setErro('');
    setResultado(null);

    if (chave.length !== 44) {
      setErro('A chave de acesso deve ter exatamente 44 dígitos.');
      return;
    }

    try {
      setLoading(true);
      const resp = await api.post('/sefaz/consultar', { chave_acesso: chave });
      setResultado(resp.data);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao consultar a SEFAZ.';
      setErro(msg);
    } finally {
      setLoading(false);
    }
  }

  function formatarMoeda(valor) {
    return valor?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) ?? '—';
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">📄 Consulta NF-e — SEFAZ</h1>
        <p className="text-gray-500 text-sm mt-1">
          Cole a chave de acesso da nota fiscal (44 dígitos) para consultar os dados diretamente na SEFAZ.
        </p>
      </div>

      {/* Aviso modo desenvolvimento */}
      <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4 mb-6 text-sm text-yellow-800">
        <strong>⚠️ Modo desenvolvimento:</strong> Os dados exibidos são simulados. Para consultas reais é necessário configurar o certificado digital A1 da empresa.
      </div>

      {/* Formulário de consulta */}
      <form onSubmit={consultar} className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Chave de Acesso (44 dígitos)
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={chave}
            onChange={e => setChave(formatarChave(e.target.value))}
            placeholder="Ex: 35250112345678000195550010000001231234567890"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            maxLength={44}
          />
          <button
            type="submit"
            disabled={loading || chave.length !== 44}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Consultando...' : 'Consultar'}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">{chave.length}/44 dígitos preenchidos</p>

        {erro && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {erro}
          </div>
        )}
      </form>

      {/* Resultado */}
      {resultado && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {/* Aviso da API */}
          {resultado.aviso && (
            <div className="bg-yellow-50 px-6 py-3 text-xs text-yellow-700 border-b border-yellow-200">
              {resultado.aviso}
            </div>
          )}

          {/* Cabeçalho da NF-e */}
          <div className="p-6 border-b border-gray-100">
            <h2 className="text-lg font-bold text-gray-800 mb-4">Dados da Nota Fiscal</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Número / Série:</span>
                <span className="ml-2 font-semibold">{resultado.numero_nf} / {resultado.serie}</span>
              </div>
              <div>
                <span className="text-gray-500">Emissão:</span>
                <span className="ml-2 font-semibold">{resultado.data_emissao}</span>
              </div>
              <div>
                <span className="text-gray-500">Emitente:</span>
                <span className="ml-2 font-semibold">{resultado.emitente_nome}</span>
              </div>
              <div>
                <span className="text-gray-500">CNPJ Emitente:</span>
                <span className="ml-2 font-semibold">{resultado.emitente_cnpj}</span>
              </div>
              <div>
                <span className="text-gray-500">Destinatário:</span>
                <span className="ml-2 font-semibold">{resultado.destinatario_nome || '—'}</span>
              </div>
              <div>
                <span className="text-gray-500">Valor Total:</span>
                <span className="ml-2 font-bold text-green-700 text-base">{formatarMoeda(resultado.valor_total_nf)}</span>
              </div>
            </div>
          </div>

          {/* Itens */}
          <div className="p-6">
            <h3 className="text-sm font-bold text-gray-700 mb-3">Itens da Nota ({resultado.itens?.length})</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-gray-600 text-xs uppercase">
                    <th className="text-left px-3 py-2">#</th>
                    <th className="text-left px-3 py-2">Código</th>
                    <th className="text-left px-3 py-2">Descrição</th>
                    <th className="text-left px-3 py-2">NCM</th>
                    <th className="text-right px-3 py-2">Qtd</th>
                    <th className="text-left px-3 py-2">UN</th>
                    <th className="text-right px-3 py-2">Unit.</th>
                    <th className="text-right px-3 py-2">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {resultado.itens?.map(item => (
                    <tr key={item.numero_item} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-gray-500">{item.numero_item}</td>
                      <td className="px-3 py-2 font-mono text-xs">{item.codigo_produto}</td>
                      <td className="px-3 py-2">{item.descricao}</td>
                      <td className="px-3 py-2 font-mono text-xs text-gray-500">{item.ncm || '—'}</td>
                      <td className="px-3 py-2 text-right">{item.quantidade}</td>
                      <td className="px-3 py-2 text-gray-500">{item.unidade}</td>
                      <td className="px-3 py-2 text-right">{formatarMoeda(item.valor_unitario)}</td>
                      <td className="px-3 py-2 text-right font-semibold">{formatarMoeda(item.valor_total)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-gray-300 bg-gray-50">
                    <td colSpan={7} className="px-3 py-2 text-right font-bold text-gray-700">Total da NF-e</td>
                    <td className="px-3 py-2 text-right font-bold text-green-700">{formatarMoeda(resultado.valor_total_nf)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
