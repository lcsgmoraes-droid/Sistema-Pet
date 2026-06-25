import { Filter, RefreshCw, Search } from "lucide-react";

import { SITUACOES_NF_SAIDA } from "./centralNFSaidaUtils";

export default function NFSaidaFilters({
  busca,
  setBusca,
  dataInicial,
  setDataInicial,
  dataFinal,
  setDataFinal,
  filtroSituacao,
  setFiltroSituacao,
  carregarNotas,
  loading,
}) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-600" />
          <h2 className="font-semibold text-gray-800">Notas Fiscais Emitidas</h2>
        </div>
        <button
          type="button"
          onClick={() => carregarNotas(true)}
          disabled={loading}
          className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Atualizar
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por número, cliente..."
            value={busca}
            onChange={(event) => setBusca(event.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <input
          type="date"
          value={dataInicial}
          onChange={(event) => setDataInicial(event.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        />
        <input
          type="date"
          value={dataFinal}
          onChange={(event) => setDataFinal(event.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={filtroSituacao}
          onChange={(event) => setFiltroSituacao(event.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          {SITUACOES_NF_SAIDA.map((situacao) => (
            <option key={situacao.value} value={situacao.value}>
              {situacao.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
