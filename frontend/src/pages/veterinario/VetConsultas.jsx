import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Stethoscope, Plus, Search, Filter, FileText, AlertCircle } from "lucide-react";
import { vetApi } from "./vetApi";

const STATUS_LABEL = {
  aberta: "Aberta",
  finalizada: "Finalizada",
  cancelada: "Cancelada",
};

const STATUS_COLOR = {
  aberta: "bg-blue-100 text-blue-800",
  finalizada: "bg-green-100 text-green-800",
  cancelada: "bg-gray-100 text-gray-500",
};

function formatData(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function formatHora(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export default function VetConsultas() {
  const navigate = useNavigate();
  const [consultas, setConsultas] = useState([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const POR_PAGINA = 20;
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      setErro(null);
      const res = await vetApi.listarConsultas({
        skip: (pagina - 1) * POR_PAGINA,
        limit: POR_PAGINA,
        status: filtroStatus || undefined,
      });
      const data = res.data;
      // aceita {items, total} ou array direto
      if (Array.isArray(data)) {
        setConsultas(data);
        setTotal(data.length);
      } else {
        setConsultas(data.items ?? []);
        setTotal(data.total ?? 0);
      }
    } catch {
      setErro("Não foi possível carregar as consultas.");
    } finally {
      setCarregando(false);
    }
  }, [pagina, filtroStatus]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  // Filtro local por busca (nome do pet)
  const consultasFiltradas = consultas.filter((c) => {
    if (!busca) return true;
    const texto = busca.toLowerCase();
    return (
      (c.pet_nome ?? "").toLowerCase().includes(texto) ||
      (c.veterinario_nome ?? "").toLowerCase().includes(texto) ||
      (c.diagnostico ?? "").toLowerCase().includes(texto)
    );
  });

  const totalPaginas = Math.ceil(total / POR_PAGINA);

  return (
    <div className="p-6 space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-xl">
            <Stethoscope size={22} className="text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Consultas / Prontuários</h1>
            <p className="text-sm text-gray-500">{total} registro{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <button
          onClick={() => navigate("/veterinario/consultas/nova")}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          Nova consulta
        </button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por pet, veterinário ou diagnóstico…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <div className="relative">
          <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <select
            value={filtroStatus}
            onChange={(e) => { setFiltroStatus(e.target.value); setPagina(1); }}
            className="pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white appearance-none"
          >
            <option value="">Todos os status</option>
            <option value="aberta">Aberta</option>
            <option value="finalizada">Finalizada</option>
            <option value="cancelada">Cancelada</option>
          </select>
        </div>
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {carregando ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          </div>
        ) : erro ? (
          <div className="flex items-center gap-2 text-red-600 p-6">
            <AlertCircle size={18} />
            <span className="text-sm">{erro}</span>
          </div>
        ) : consultasFiltradas.length === 0 ? (
          <div className="p-12 text-center">
            <FileText size={32} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-400 text-sm">Nenhuma consulta encontrada.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Data</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Pet</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Veterinário</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Motivo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Diagnóstico</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {consultasFiltradas.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-blue-50 transition-colors cursor-pointer"
                  onClick={() => navigate(`/veterinario/consultas/${c.id}`)}
                >
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {formatData(c.data_hora)}
                    <span className="text-xs ml-1 text-gray-400">{formatHora(c.data_hora)}</span>
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-800">{c.pet_nome ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{c.veterinario_nome ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{c.motivo_consulta ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{c.diagnostico ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[c.status] ?? "bg-gray-100"}`}>
                      {STATUS_LABEL[c.status] ?? c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/veterinario/consultas/${c.id}`); }}
                      className="text-blue-500 hover:text-blue-700 text-xs underline"
                    >
                      Abrir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Paginação */}
      {totalPaginas > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-400">
            Mostrando página {pagina} de {totalPaginas}
          </p>
          <div className="flex gap-2">
            <button
              disabled={pagina <= 1}
              onClick={() => setPagina((p) => p - 1)}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
            >
              ← Anterior
            </button>
            <button
              disabled={pagina >= totalPaginas}
              onClick={() => setPagina((p) => p + 1)}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
            >
              Próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
