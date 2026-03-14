import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FlaskConical, CalendarDays, Search, FileText, Sparkles } from "lucide-react";
import { vetApi } from "./vetApi";

function hojeIso() {
  return new Date().toISOString().slice(0, 10);
}

function formatarData(iso) {
  if (!iso) return "-";
  const data = new Date(`${iso}T12:00:00`);
  return data.toLocaleDateString("pt-BR");
}

export default function VetExamesAnexados() {
  const navigate = useNavigate();

  const [periodo, setPeriodo] = useState("hoje");
  const [dataInicio, setDataInicio] = useState(hojeIso());
  const [dataFim, setDataFim] = useState(hojeIso());
  const [tutorBusca, setTutorBusca] = useState("");

  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [dados, setDados] = useState({ items: [], total: 0 });

  const itens = useMemo(() => (Array.isArray(dados.items) ? dados.items : []), [dados]);

  async function carregar() {
    try {
      setCarregando(true);
      setErro("");

      const params = {
        periodo,
        tutor: tutorBusca.trim() || undefined,
      };

      if (periodo === "periodo") {
        params.data_inicio = dataInicio;
        params.data_fim = dataFim;
      }

      const res = await vetApi.listarExamesAnexados(params);
      setDados(res.data || { items: [], total: 0 });
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro ao carregar exames anexados.");
      setDados({ items: [], total: 0 });
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-xl">
            <FlaskConical size={20} className="text-orange-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-800">Exames Anexados</h1>
            <p className="text-xs text-gray-500">Lista enxuta por data de upload, com foco no que já tem arquivo.</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => navigate("/pets")}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          Novo exame (via ficha do pet)
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <div className="flex flex-wrap gap-2">
          {[
            { id: "hoje", label: "Hoje" },
            { id: "semana", label: "Semana" },
            { id: "periodo", label: "Período" },
          ].map((op) => (
            <button
              key={op.id}
              type="button"
              onClick={() => setPeriodo(op.id)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                periodo === op.id
                  ? "bg-orange-500 text-white border-orange-500"
                  : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              }`}
            >
              {op.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Tutor (nome)</label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={tutorBusca}
                onChange={(e) => setTutorBusca(e.target.value)}
                placeholder="Digite o nome do tutor..."
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-300"
              />
            </div>
          </div>

          {periodo === "periodo" && (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Data início</label>
                <input
                  type="date"
                  value={dataInicio}
                  onChange={(e) => setDataInicio(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-300"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Data fim</label>
                <input
                  type="date"
                  value={dataFim}
                  onChange={(e) => setDataFim(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-300"
                />
              </div>
            </>
          )}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={carregar}
            disabled={carregando}
            className="px-4 py-2 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-60"
          >
            {carregando ? "Carregando..." : "Aplicar filtros"}
          </button>
          <button
            type="button"
            onClick={() => {
              setPeriodo("hoje");
              setDataInicio(hojeIso());
              setDataFim(hojeIso());
              setTutorBusca("");
            }}
            className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Limpar
          </button>
        </div>
      </div>

      {erro && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          {erro}
        </div>
      )}

      <div className="text-sm text-gray-500">
        Total: <strong>{dados.total || 0}</strong> exame(s) com anexo
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {itens.length === 0 ? (
          <div className="p-10 text-center space-y-2">
            <FileText size={30} className="mx-auto text-gray-300" />
            <p className="text-gray-500">Nenhum exame anexado encontrado para esse filtro.</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {itens.map((item) => (
              <li key={item.exame_id} className="px-4 py-3 hover:bg-orange-50 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-gray-800">{item.nome_exame || "Exame"}</p>
                    <p className="text-xs text-gray-600">
                      Tutor: {item.tutor_nome || "-"} | Pet: {item.pet_nome || "-"}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700">
                      <CalendarDays size={12} /> {formatarData(item.data_upload)}
                    </span>
                    <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700">
                      {item.status || "-"}
                    </span>
                    {item.tem_interpretacao_ia && (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-violet-100 text-violet-700">
                        <Sparkles size={12} /> IA pronta
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => navigate(`/veterinario/consultas/nova?pet_id=${item.pet_id}`)}
                      className="text-xs px-3 py-1.5 border border-orange-200 text-orange-700 rounded-md hover:bg-orange-100"
                    >
                      Abrir consulta
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate(`/pets/${item.pet_id}`)}
                      className="text-xs px-3 py-1.5 border border-gray-200 rounded-md hover:bg-gray-50"
                    >
                      Ver pet
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
