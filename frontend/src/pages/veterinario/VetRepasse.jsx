import { useState, useEffect, useCallback } from "react";
import { DollarSign, CheckCircle, AlertCircle, Clock, RefreshCw, Download } from "lucide-react";
import { vetApi } from "./vetApi";
import { formatMoneyBRL } from "../../utils/formatters";

function formatData(iso) {
  if (!iso) return "—";
  return new Date(`${iso}T12:00:00`).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function badgeStatus(status) {
  switch (status) {
    case "recebido":
      return { label: "Recebido", cls: "bg-green-100 text-green-700" };
    case "pendente":
      return { label: "Pendente", cls: "bg-yellow-100 text-yellow-700" };
    case "vencido":
      return { label: "Vencido", cls: "bg-red-100 text-red-700" };
    default:
      return { label: status, cls: "bg-gray-100 text-gray-600" };
  }
}

function badgeTipo(tipo) {
  if (tipo === "repasse_empresa") {
    return { label: "Repasse empresa", cls: "bg-sky-100 text-sky-700" };
  }
  return { label: "Líquido veterinário", cls: "bg-violet-100 text-violet-700" };
}

export default function VetRepasse() {
  const hoje = new Date().toISOString().slice(0, 10);
  const primeiroDiaMes = hoje.slice(0, 8) + "01";

  const [dataInicio, setDataInicio] = useState(primeiroDiaMes);
  const [dataFim, setDataFim] = useState(hoje);
  const [filtroStatus, setFiltroStatus] = useState("");
  const [filtroTipo, setFiltroTipo] = useState("");
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [baixando, setBaixando] = useState(null); // id da conta em processamento

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      if (filtroStatus) params.status = filtroStatus;
      const res = await vetApi.relatorioRepasse(params);
      setDados(res.data);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao carregar relatório de repasse.");
    } finally {
      setCarregando(false);
    }
  }, [dataInicio, dataFim, filtroStatus]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function darBaixa(contaId) {
    setBaixando(contaId);
    try {
      await vetApi.baixarRepasse(contaId);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao dar baixa no lançamento.");
    } finally {
      setBaixando(null);
    }
  }

  const itensFiltrados =
    (dados?.items ?? []).filter((item) => {
      if (filtroTipo && item.tipo !== filtroTipo) return false;
      return true;
    });

  const totalFiltrado = itensFiltrados.reduce((s, i) => s + (i.valor || 0), 0);
  const totalRecebidoFiltrado = itensFiltrados
    .filter((i) => i.status === "recebido")
    .reduce((s, i) => s + (i.valor || 0), 0);
  const totalPendenteFiltrado = totalFiltrado - totalRecebidoFiltrado;

  return (
    <div className="p-6 space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sky-100 rounded-xl">
            <DollarSign size={22} className="text-sky-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Fechamento de Repasse</h1>
            <p className="text-sm text-gray-500">Controle de recebimento dos lançamentos veterinários</p>
          </div>
        </div>
        <button
          onClick={carregar}
          disabled={carregando}
          className="flex items-center gap-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-600 px-3 py-2 rounded-lg text-sm transition-colors disabled:opacity-60"
        >
          <RefreshCw size={14} className={carregando ? "animate-spin" : ""} />
          Atualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Data início</label>
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Data fim</label>
            <input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
            <select
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-300"
            >
              <option value="">Todos</option>
              <option value="pendente">Pendente</option>
              <option value="recebido">Recebido</option>
              <option value="vencido">Vencido</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Tipo de lançamento</label>
            <select
              value={filtroTipo}
              onChange={(e) => setFiltroTipo(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-300"
            >
              <option value="">Todos</option>
              <option value="repasse_empresa">Repasse empresa</option>
              <option value="liquido_vet">Líquido veterinário</option>
            </select>
          </div>
        </div>
      </div>

      {/* Erro */}
      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      {/* Cards de resumo */}
      {dados && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign size={16} className="text-sky-500" />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total no período</span>
            </div>
            <p className="text-2xl font-bold text-gray-800">{formatMoneyBRL(totalFiltrado)}</p>
            <p className="text-xs text-gray-400 mt-1">{itensFiltrados.length} lançamento(s)</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle size={16} className="text-green-500" />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Recebido</span>
            </div>
            <p className="text-2xl font-bold text-green-700">{formatMoneyBRL(totalRecebidoFiltrado)}</p>
            <p className="text-xs text-gray-400 mt-1">
              {itensFiltrados.filter((i) => i.status === "recebido").length} lançamento(s) baixado(s)
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <Clock size={16} className="text-yellow-500" />
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Pendente</span>
            </div>
            <p className="text-2xl font-bold text-yellow-700">{formatMoneyBRL(totalPendenteFiltrado)}</p>
            <p className="text-xs text-gray-400 mt-1">
              {itensFiltrados.filter((i) => i.status !== "recebido").length} aguardando baixa
            </p>
          </div>
        </div>
      )}

      {/* Tabela */}
      {carregando ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500" />
        </div>
      ) : itensFiltrados.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
          <Download size={36} className="mx-auto text-gray-200 mb-3" />
          <p className="text-gray-400 text-sm">Nenhum lançamento encontrado para o filtro selecionado.</p>
          <p className="text-xs text-gray-300 mt-1">Os lançamentos são gerados automaticamente ao finalizar consultas com procedimentos.</p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Descrição</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tipo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Valor</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Emissão</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Recebimento</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {itensFiltrados.map((item) => {
                const badge = badgeStatus(item.status);
                const tipoBadge = badgeTipo(item.tipo);
                return (
                  <tr key={item.id} className="hover:bg-sky-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800 text-sm">{item.descricao}</p>
                      {item.observacoes && (
                        <p className="text-xs text-gray-400 mt-0.5">{item.observacoes}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${tipoBadge.cls}`}>
                        {tipoBadge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold text-gray-800">
                      {formatMoneyBRL(item.valor)}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{formatData(item.data_emissao)}</td>
                    <td className="px-4 py-3 text-gray-500">{formatData(item.data_recebimento)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {item.status !== "recebido" ? (
                        <button
                          onClick={() => darBaixa(item.id)}
                          disabled={baixando === item.id}
                          className="flex items-center gap-1.5 text-xs bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg transition-colors disabled:opacity-60"
                        >
                          <CheckCircle size={12} />
                          {baixando === item.id ? "Baixando…" : "Dar baixa"}
                        </button>
                      ) : (
                        <span className="flex items-center gap-1 text-xs text-green-600">
                          <CheckCircle size={12} />
                          Baixado
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-gray-400 text-right">
        Os lançamentos são gerados ao finalizar uma consulta com procedimentos vinculados a um veterinário parceiro.
      </p>
    </div>
  );
}
