import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  FlaskConical,
  CalendarDays,
  Search,
  FileText,
  Sparkles,
  Plus,
  X,
  AlertCircle,
  Bot,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import TutorAutocomplete from "../../components/TutorAutocomplete";
import NovoPetButton from "../../components/veterinario/NovoPetButton";
import { buildReturnTo } from "../../utils/petReturnFlow";
import ExameAnexadoPainelIA from "./components/ExameAnexadoPainelIA";

function hojeIso() {
  return new Date().toISOString().slice(0, 10);
}

function formatarData(iso) {
  if (!iso) return "-";
  const data = new Date(`${iso}T12:00:00`);
  return data.toLocaleDateString("pt-BR");
}

const FORM_INICIAL = {
  pet_id: "",
  tipo: "laboratorial",
  nome: "",
  data_solicitacao: hojeIso(),
  laboratorio: "",
  observacoes: "",
};

export default function VetExamesAnexados() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const [periodo, setPeriodo] = useState("hoje");
  const [dataInicio, setDataInicio] = useState(hojeIso());
  const [dataFim, setDataFim] = useState(hojeIso());
  const [tutorBusca, setTutorBusca] = useState("");

  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [dados, setDados] = useState({ items: [], total: 0 });
  const [exameExpandidoId, setExameExpandidoId] = useState("");

  const [pets, setPets] = useState([]);
  const [novaAberta, setNovaAberta] = useState(false);
  const [salvandoNovo, setSalvandoNovo] = useState(false);
  const [erroNovo, setErroNovo] = useState("");
  const [tutorFormSelecionado, setTutorFormSelecionado] = useState(null);
  const [form, setForm] = useState(FORM_INICIAL);
  const [arquivoNovo, setArquivoNovo] = useState(null);

  const itens = useMemo(() => (Array.isArray(dados.items) ? dados.items : []), [dados]);

  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const acaoQuery = searchParams.get("acao") || "";
  const agendamentoIdQuery = searchParams.get("agendamento_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";

  const petsDoTutor = useMemo(() => {
    if (!tutorFormSelecionado?.id) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(tutorFormSelecionado.id) && pet.ativo !== false
    );
  }, [pets, tutorFormSelecionado]);

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
    api
      .get("/vet/pets", { params: { limit: 500 } })
      .then((r) => setPets(r.data?.items ?? r.data ?? []))
      .catch(() => setPets([]));
  }, []);

  useEffect(() => {
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;

    const petEncontrado = pets.find((pet) => String(pet.id) === String(petIdAlvo));
    if (!petEncontrado) return;

    const tutor = petEncontrado?.cliente_id
      ? {
          id: String(petEncontrado.cliente_id),
          nome: petEncontrado.cliente_nome ?? `Tutor #${petEncontrado.cliente_id}`,
          telefone: petEncontrado.cliente_telefone ?? "",
          celular: petEncontrado.cliente_celular ?? "",
        }
      : null;

    setTutorFormSelecionado(tutor);
    setForm((prev) => ({
      ...prev,
      pet_id: String(petEncontrado.id),
    }));

    if (acaoQuery === "novo" || novoPetIdQuery) {
      setNovaAberta(true);
    }
  }, [petIdQuery, novoPetIdQuery, acaoQuery, pets]);

  useEffect(() => {
    if (!tutorIdQuery || tutorFormSelecionado?.id) return;
    setTutorFormSelecionado({
      id: String(tutorIdQuery),
      nome: tutorNomeQuery || `Tutor #${tutorIdQuery}`,
    });
  }, [tutorIdQuery, tutorNomeQuery, tutorFormSelecionado]);

  function abrirNovoExame() {
    setErroNovo("");
    setArquivoNovo(null);
    setNovaAberta(true);
  }

  function fecharNovoExame() {
    setNovaAberta(false);
    setErroNovo("");
    setTutorFormSelecionado(null);
    setForm(FORM_INICIAL);
    setArquivoNovo(null);

    if (acaoQuery === "novo" || petIdQuery || novoPetIdQuery || agendamentoIdQuery || consultaIdQuery) {
      navigate("/veterinario/exames", { replace: true });
    }
  }

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search, { acao: "novo" }),
    [location.pathname, location.search]
  );

  async function salvarExame() {
    if (!form.pet_id || !form.nome) return;
    setSalvandoNovo(true);
    setErroNovo("");

    try {
      const res = await vetApi.criarExame({
        pet_id: Number(form.pet_id),
        consulta_id: consultaIdQuery ? Number(consultaIdQuery) : undefined,
        agendamento_id: agendamentoIdQuery ? Number(agendamentoIdQuery) : undefined,
        tipo: form.tipo,
        nome: form.nome,
        data_solicitacao: form.data_solicitacao || undefined,
        laboratorio: form.laboratorio || undefined,
        observacoes: form.observacoes || undefined,
      });
      if (arquivoNovo) {
        await vetApi.uploadArquivoExame(res.data.id, arquivoNovo);
        try {
          await vetApi.processarArquivoExameIA(res.data.id);
        } catch (erroProcessamento) {
          console.warn("Nao foi possivel processar o arquivo do exame com IA automaticamente.", erroProcessamento);
        }
      }
      fecharNovoExame();
      await carregar();
    } catch (e) {
      setErroNovo(e?.response?.data?.detail || "Erro ao registrar exame.");
    } finally {
      setSalvandoNovo(false);
    }
  }

  function atualizarResumoExame(exameAtualizado) {
    if (!exameAtualizado?.id) return;
    setDados((atual) => ({
      ...atual,
      items: (Array.isArray(atual.items) ? atual.items : []).map((item) =>
        String(item.exame_id) === String(exameAtualizado.id)
          ? {
              ...item,
              status: exameAtualizado.status || item.status,
              arquivo_nome: exameAtualizado.arquivo_nome || item.arquivo_nome,
              arquivo_url: exameAtualizado.arquivo_url || item.arquivo_url,
              tem_interpretacao_ia: Boolean(
                exameAtualizado.interpretacao_ia ||
                  exameAtualizado.interpretacao_ia_resumo ||
                  exameAtualizado.interpretacao_ia_payload
              ),
            }
          : item
      ),
    }));
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-xl">
            <FlaskConical size={20} className="text-orange-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-800">Exames Anexados</h1>
            <p className="text-xs text-gray-500">
              Lista enxuta por data de upload, com foco no que ja tem arquivo.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={abrirNovoExame}
            className="inline-flex items-center gap-2 rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600"
          >
            <Plus size={15} />
            Novo exame
          </button>
          <button
            type="button"
            onClick={() => navigate("/pets")}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Ver pets
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <div className="flex flex-wrap gap-2">
          {[
            { id: "hoje", label: "Hoje" },
            { id: "semana", label: "Semana" },
            { id: "periodo", label: "Periodo" },
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
                <label className="block text-xs font-medium text-gray-600 mb-1">Data inicio</label>
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
              <li key={item.exame_id} className="px-4 py-3 transition-colors hover:bg-orange-50">
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
                      onClick={() =>
                        item.consulta_id
                          ? navigate(`/veterinario/consultas/${item.consulta_id}`)
                          : navigate(`/veterinario/consultas/nova?pet_id=${item.pet_id}`)
                      }
                      className="text-xs px-3 py-1.5 border border-orange-200 text-orange-700 rounded-md hover:bg-orange-100"
                    >
                      {item.consulta_id ? `Abrir consulta #${item.consulta_id}` : "Abrir consulta"}
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate(`/pets/${item.pet_id}`)}
                      className="text-xs px-3 py-1.5 border border-gray-200 rounded-md hover:bg-gray-50"
                    >
                      Ver pet
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setExameExpandidoId((atual) =>
                          String(atual) === String(item.exame_id) ? "" : String(item.exame_id)
                        )
                      }
                      className="inline-flex items-center gap-1 text-xs px-3 py-1.5 border border-indigo-200 text-indigo-700 rounded-md hover:bg-indigo-50"
                    >
                      <Bot size={13} />
                      {String(exameExpandidoId) === String(item.exame_id) ? "Fechar IA" : "Abrir IA"}
                      {String(exameExpandidoId) === String(item.exame_id) ? (
                        <ChevronUp size={13} />
                      ) : (
                        <ChevronDown size={13} />
                      )}
                    </button>
                  </div>
                </div>

                {String(exameExpandidoId) === String(item.exame_id) && (
                  <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
                    <ExameAnexadoPainelIA
                      resumo={item}
                      onAtualizado={atualizarResumoExame}
                      onNovoExame={abrirNovoExame}
                      onAbrirConsulta={() =>
                        item.consulta_id
                          ? navigate(`/veterinario/consultas/${item.consulta_id}`)
                          : navigate(`/veterinario/consultas/nova?pet_id=${item.pet_id}`)
                      }
                    />
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {novaAberta && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={fecharNovoExame}
        >
          <div
            className="w-full max-w-3xl rounded-2xl bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-bold text-gray-800">Novo exame</h2>
                <p className="mt-1 text-sm text-gray-500">
                  Registre a solicitacao do exame com tutor e pet ja vinculados.
                </p>
              </div>
              <button
                type="button"
                onClick={fecharNovoExame}
                className="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                aria-label="Fechar modal"
              >
                <X size={18} />
              </button>
            </div>

            {erroNovo && (
              <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                <AlertCircle size={16} />
                <span>{erroNovo}</span>
              </div>
            )}

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              {consultaIdQuery && (
                <div className="sm:col-span-2 rounded-lg border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-800">
                  Este exame ficara vinculado a consulta <strong>#{consultaIdQuery}</strong>.
                </div>
              )}

              <div className="sm:col-span-2">
                <TutorAutocomplete
                  label="Tutor"
                  inputId="exame-tutor"
                  selectedTutor={tutorFormSelecionado}
                  onSelect={(tutor) => {
                    setTutorFormSelecionado(tutor);
                    setForm((prev) => ({ ...prev, pet_id: "" }));
                  }}
                  placeholder="Digite o nome, CPF ou telefone do tutor..."
                />
              </div>

              <div className="sm:col-span-2">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <label className="block text-xs font-medium text-gray-600">Pet*</label>
                  <NovoPetButton
                    tutorId={tutorFormSelecionado?.id}
                    tutorNome={tutorFormSelecionado?.nome}
                    returnTo={retornoNovoPet}
                    onBeforeNavigate={fecharNovoExame}
                  />
                </div>
                <select
                  value={form.pet_id}
                  onChange={(e) => setForm((prev) => ({ ...prev, pet_id: e.target.value }))}
                  disabled={!tutorFormSelecionado?.id}
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
                >
                  <option value="">
                    {!tutorFormSelecionado?.id
                      ? "Selecione o tutor primeiro..."
                      : petsDoTutor.length > 0
                      ? "Selecione o pet..."
                      : "Nenhum pet vinculado a este tutor"}
                  </option>
                  {petsDoTutor.map((pet) => (
                    <option key={pet.id} value={pet.id}>
                      {pet.nome}
                      {pet.especie ? ` (${pet.especie})` : ""}
                    </option>
                  ))}
                </select>
                {tutorFormSelecionado?.id && petsDoTutor.length === 0 && (
                  <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para este tutor.</p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Tipo*</label>
                <select
                  value={form.tipo}
                  onChange={(e) => setForm((prev) => ({ ...prev, tipo: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
                >
                  <option value="laboratorial">Laboratorial</option>
                  <option value="imagem">Imagem</option>
                  <option value="clinico">Clinico</option>
                  <option value="outro">Outro</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Data da solicitacao</label>
                <input
                  type="date"
                  value={form.data_solicitacao}
                  onChange={(e) => setForm((prev) => ({ ...prev, data_solicitacao: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-gray-600">Nome do exame*</label>
                <input
                  type="text"
                  value={form.nome}
                  onChange={(e) => setForm((prev) => ({ ...prev, nome: e.target.value }))}
                  placeholder="Ex: Hemograma completo"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-gray-600">Laboratorio</label>
                <input
                  type="text"
                  value={form.laboratorio}
                  onChange={(e) => setForm((prev) => ({ ...prev, laboratorio: e.target.value }))}
                  placeholder="Opcional"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-gray-600">Observacoes</label>
                <textarea
                  value={form.observacoes}
                  onChange={(e) => setForm((prev) => ({ ...prev, observacoes: e.target.value }))}
                  rows={4}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="Informacoes adicionais do exame agendado..."
                />
              </div>

              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-gray-600">Arquivo do exame</label>
                <input
                  type="file"
                  onChange={(e) => setArquivoNovo(e.target.files?.[0] ?? null)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-orange-100 file:px-3 file:py-1.5 file:text-orange-700"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Se anexar agora, o exame ja aparece nesta tela e fica pronto para consulta pela IA.
                </p>
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={fecharNovoExame}
                className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={salvarExame}
                disabled={salvandoNovo || !form.pet_id || !form.nome}
                className="flex-1 rounded-lg bg-orange-500 px-4 py-2 text-sm text-white hover:bg-orange-600 disabled:opacity-60"
              >
                {salvandoNovo ? "Salvando..." : "Registrar exame"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
