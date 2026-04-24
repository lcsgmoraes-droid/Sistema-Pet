import { useState, useEffect, useCallback, useMemo } from "react";
import { BedDouble, Plus, Activity, ArrowUpCircle, AlertCircle, Clock, Map as MapIcon, List, LayoutGrid, BellRing, Trash2, Check } from "lucide-react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import TutorAutocomplete from "../../components/TutorAutocomplete";
import NovoPetButton from "../../components/veterinario/NovoPetButton";
import ProdutoEstoqueAutocomplete from "../../components/veterinario/ProdutoEstoqueAutocomplete";
import { useAuth } from "../../contexts/AuthContext";
import { buildReturnTo } from "../../utils/petReturnFlow";

const STORAGE_AGENDA = "vet_internacao_agenda_v1";
const STORAGE_TOTAL_BAIAS = "vet_internacao_total_baias_v1";

function formatData(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}
function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function parseQuantity(value) {
  if (value == null || value === "") return null;
  const parsed = Number(String(value).replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function formatQuantity(value, unidade = "") {
  if (value == null || value === "" || Number.isNaN(Number(value))) return "—";
  const numero = Number(value);
  const texto = Number.isInteger(numero)
    ? numero.toLocaleString("pt-BR")
    : numero.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  return unidade ? `${texto} ${unidade}` : texto;
}

function montarSerieEvolucao(registros = []) {
  return registros
    .filter((item) => item?.data_hora)
    .map((item) => ({
      horario: new Date(item.data_hora).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }),
      temperatura: item.temperatura ?? null,
      fc: item.freq_cardiaca ?? null,
      fr: item.freq_respiratoria ?? null,
      peso: item.peso ?? null,
    }));
}

const STATUS_CORES = {
  internado: "bg-blue-100 text-blue-700",
  ativa: "bg-blue-100 text-blue-700",
  alta: "bg-green-100 text-green-700",
  transferida: "bg-yellow-100 text-yellow-700",
  obito: "bg-red-100 text-red-700",
};

export default function VetInternacoes() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const abrirNovaQuery = searchParams.get("abrir_nova") === "1";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";
  const [aba, setAba] = useState("ativas"); // "ativas" | "historico"
  const [centroAba, setCentroAba] = useState("widget"); // "mapa" | "lista" | "widget" | "agenda"
  const [internacoes, setInternacoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [expandida, setExpandida] = useState(null); // id da internação aberta
  const [evolucoes, setEvolucoes] = useState({}); // { [internacaoId]: [...] }
  const [procedimentosInternacao, setProcedimentosInternacao] = useState({}); // { [internacaoId]: [...] }
  const [modalNova, setModalNova] = useState(false);
  const [modalAlta, setModalAlta] = useState(null); // id
  const [modalEvolucao, setModalEvolucao] = useState(null); // id
  const [modalHistoricoPet, setModalHistoricoPet] = useState(null); // { petId, petNome }
  const [historicoPet, setHistoricoPet] = useState([]);
  const [carregandoHistoricoPet, setCarregandoHistoricoPet] = useState(false);
  const [pets, setPets] = useState([]);
  const [veterinarios, setVeterinarios] = useState([]);
  const [formNova, setFormNova] = useState({ pessoa_id: "", pet_id: "", motivo: "", box: "", responsavel: "" });
  const [tutorNovaSelecionado, setTutorNovaSelecionado] = useState(null);
  const [formAlta, setFormAlta] = useState("");
  const [formEvolucao, setFormEvolucao] = useState({ temperatura: "", fc: "", fr: "", observacoes: "" });
  const [filtroDataAltaInicio, setFiltroDataAltaInicio] = useState("");
  const [filtroDataAltaFim, setFiltroDataAltaFim] = useState("");
  const [filtroPessoaHistorico, setFiltroPessoaHistorico] = useState("");
  const [filtroPetHistorico, setFiltroPetHistorico] = useState("");
  const [agendaProcedimentos, setAgendaProcedimentos] = useState([]);
  const [totalBaias, setTotalBaias] = useState(12);
  const [agendaStorageCarregado, setAgendaStorageCarregado] = useState(false);
  const [baiasStorageCarregado, setBaiasStorageCarregado] = useState(false);
  const [agendaForm, setAgendaForm] = useState({
    internacao_id: "",
    horario: "",
    medicamento: "",
    dose: "",
    quantidade_prevista: "",
    unidade_quantidade: "",
    via: "",
    lembrete_min: "30",
    observacoes: "",
  });
  const [modalFeito, setModalFeito] = useState(null); // item completo da agenda
  const [formFeito, setFormFeito] = useState({
    feito_por: "",
    horario_execucao: "",
    observacao_execucao: "",
    quantidade_prevista: "",
    quantidade_executada: "",
    quantidade_desperdicio: "",
    unidade_quantidade: "",
  });
  const [modalInsumoRapido, setModalInsumoRapido] = useState(false);
  const [insumoRapidoSelecionado, setInsumoRapidoSelecionado] = useState(null);
  const [formInsumoRapido, setFormInsumoRapido] = useState({
    internacao_id: "",
    responsavel: "",
    horario_execucao: "",
    quantidade_utilizada: "1",
    quantidade_desperdicio: "",
    observacoes: "",
  });
  const [salvando, setSalvando] = useState(false);
  const storageScope = useMemo(() => {
    const tenantId = user?.tenant_id || user?.tenant?.id || "tenant";
    const userId = user?.id || "usuario";
    return `${tenantId}_${userId}`;
  }, [user?.tenant_id, user?.tenant?.id, user?.id]);
  const agendaStorageKey = `${STORAGE_AGENDA}_${storageScope}`;
  const totalBaiasStorageKey = `${STORAGE_TOTAL_BAIAS}_${storageScope}`;

  useEffect(() => {
    api.get("/pets", { params: { limit: 500 } }).then((r) => setPets(r.data?.items ?? r.data ?? [])).catch(() => {});
    vetApi.listarVeterinarios().then((r) => setVeterinarios(Array.isArray(r.data) ? r.data : [])).catch(() => setVeterinarios([]));
  }, []);

  useEffect(() => {
    if (abrirNovaQuery) {
      setModalNova(true);
    }
  }, [abrirNovaQuery]);

  useEffect(() => {
    if (!tutorIdQuery) return;
    setFormNova((prev) => ({
      ...prev,
      pessoa_id: prev.pessoa_id || String(tutorIdQuery),
    }));
    setTutorNovaSelecionado((prev) => prev || {
      id: String(tutorIdQuery),
      nome: tutorNomeQuery || `Pessoa #${tutorIdQuery}`,
    });
  }, [tutorIdQuery, tutorNomeQuery]);

  useEffect(() => {
    if (!novoPetIdQuery) return;
    setModalNova(true);
    setFormNova((prev) => ({
      ...prev,
      pet_id: String(novoPetIdQuery),
    }));
  }, [novoPetIdQuery]);

  useEffect(() => {
    setAgendaStorageCarregado(false);
    try {
      const salvo = localStorage.getItem(agendaStorageKey);
      if (!salvo) {
        setAgendaProcedimentos([]);
        return;
      }
      const parsed = JSON.parse(salvo);
      if (Array.isArray(parsed)) setAgendaProcedimentos(parsed);
    } catch {
      setAgendaProcedimentos([]);
    } finally {
      setAgendaStorageCarregado(true);
    }
  }, [agendaStorageKey]);

  useEffect(() => {
    if (!agendaStorageCarregado) return;
    localStorage.setItem(agendaStorageKey, JSON.stringify(agendaProcedimentos));
  }, [agendaProcedimentos, agendaStorageCarregado, agendaStorageKey]);

  useEffect(() => {
    setBaiasStorageCarregado(false);
    try {
      const salvo = localStorage.getItem(totalBaiasStorageKey);
      if (!salvo) {
        setTotalBaias(12);
        return;
      }
      const parsed = Number.parseInt(salvo, 10);
      if (Number.isFinite(parsed) && parsed > 0) {
        setTotalBaias(parsed);
      }
    } catch {
      setTotalBaias(12);
    } finally {
      setBaiasStorageCarregado(true);
    }
  }, [totalBaiasStorageKey]);

  useEffect(() => {
    if (!baiasStorageCarregado) return;
    localStorage.setItem(totalBaiasStorageKey, String(totalBaias));
  }, [baiasStorageCarregado, totalBaias, totalBaiasStorageKey]);

  const pessoas = useMemo(() => {
    const mapa = new Map();
    for (const p of pets) {
      if (!p?.cliente_id) continue;
      if (mapa.has(String(p.cliente_id))) continue;
      mapa.set(String(p.cliente_id), {
        id: String(p.cliente_id),
        nome: p.cliente_nome ?? `Pessoa #${p.cliente_id}`,
      });
    }
    return Array.from(mapa.values()).sort((a, b) => a.nome.localeCompare(b.nome));
  }, [pets]);

  const petsDaPessoa = useMemo(() => {
    if (!formNova.pessoa_id) return [];
    return pets.filter(
      (p) => String(p.cliente_id) === String(formNova.pessoa_id) && p.ativo !== false
    );
  }, [pets, formNova.pessoa_id]);

  const tutorAtualInternacao = useMemo(() => {
    if (tutorNovaSelecionado?.id) return tutorNovaSelecionado;
    if (!formNova.pessoa_id) return null;
    return pessoas.find((item) => String(item.id) === String(formNova.pessoa_id)) || null;
  }, [pessoas, formNova.pessoa_id, tutorNovaSelecionado]);

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search, { abrir_nova: "1" }),
    [location.pathname, location.search]
  );

  const petsHistoricoDaPessoa = useMemo(() => {
    if (!filtroPessoaHistorico) return [];
    return pets.filter(
      (p) => String(p.cliente_id) === String(filtroPessoaHistorico) && p.ativo !== false
    );
  }, [pets, filtroPessoaHistorico]);

  const internacoesOrdenadas = useMemo(
    () => [...internacoes].sort((a, b) => new Date(b.data_entrada) - new Date(a.data_entrada)),
    [internacoes]
  );

  const ocupacaoPorBaia = useMemo(() => {
    const mapa = new Map();
    for (const i of internacoesOrdenadas) {
      const chave = (i.box || "").trim();
      if (!chave) continue;
      mapa.set(chave, i);
    }
    return mapa;
  }, [internacoesOrdenadas]);

  const mapaInternacao = useMemo(() => {
    const lista = [];
    for (let numero = 1; numero <= totalBaias; numero += 1) {
      const chave = String(numero);
      const ocupacao = ocupacaoPorBaia.get(chave) ?? null;
      lista.push({
        numero,
        ocupada: Boolean(ocupacao),
        internacao: ocupacao,
      });
    }

    // Baias fora da faixa configurada continuam visíveis para não esconder dados.
    for (const [chave, internacao] of ocupacaoPorBaia.entries()) {
      const asNumero = Number.parseInt(chave, 10);
      if (Number.isFinite(asNumero) && asNumero >= 1 && asNumero <= totalBaias) continue;
      lista.push({
        numero: chave,
        ocupada: true,
        internacao,
      });
    }

    return lista;
  }, [ocupacaoPorBaia, totalBaias]);

  const indicadoresInternacao = useMemo(() => {
    const total = internacoes.length;
    const semBaia = internacoes.filter((i) => !i.box).length;
    const comEvolucao = internacoes.filter((i) => (evolucoes[i.id] ?? []).length > 0).length;
    const procedimentosPendentes = agendaProcedimentos.filter((p) => !p.feito).length;
    const procedimentosAtrasados = agendaProcedimentos.filter((p) => !p.feito && new Date(p.horario).getTime() <= Date.now()).length;
    const mediaDias = total === 0
      ? 0
      : internacoes.reduce((acc, i) => {
          const dias = Math.max(0, Math.floor((Date.now() - new Date(i.data_entrada).getTime()) / 86400000));
          return acc + dias;
        }, 0) / total;

    return {
      total,
      semBaia,
      comEvolucao,
      semEvolucao: Math.max(0, total - comEvolucao),
      baiasOcupadas: ocupacaoPorBaia.size,
      baiasLivres: Math.max(0, totalBaias - ocupacaoPorBaia.size),
      procedimentosPendentes,
      procedimentosAtrasados,
      mediaDias: Number.isFinite(mediaDias) ? mediaDias.toFixed(1) : "0.0",
    };
  }, [internacoes, evolucoes, agendaProcedimentos, ocupacaoPorBaia, totalBaias]);

  const agendaOrdenada = useMemo(() => {
    return [...agendaProcedimentos].sort((a, b) => new Date(a.horario).getTime() - new Date(b.horario).getTime());
  }, [agendaProcedimentos]);

  const internacaoPorId = useMemo(() => {
    const mapa = new Map();
    for (const i of internacoes) mapa.set(String(i.id), i);
    return mapa;
  }, [internacoes]);

  const internacaoSelecionadaAgenda = useMemo(() => {
    if (!agendaForm.internacao_id) return null;
    return internacaoPorId.get(String(agendaForm.internacao_id)) ?? null;
  }, [agendaForm.internacao_id, internacaoPorId]);

  const sugestaoHorario = useMemo(() => {
    const d = new Date();
    d.setMinutes(d.getMinutes() + 30);
    const pad = (v) => String(v).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }, []);

  useEffect(() => {
    setAgendaForm((prev) => (prev.horario ? prev : { ...prev, horario: sugestaoHorario }));
  }, [sugestaoHorario]);

  useEffect(() => {
    setFormInsumoRapido((prev) => (prev.horario_execucao ? prev : { ...prev, horario_execucao: sugestaoHorario }));
  }, [sugestaoHorario]);

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      const params = aba === "ativas"
        ? { status: "internado" }
        : {
            status: "alta",
            data_saida_inicio: filtroDataAltaInicio || undefined,
            data_saida_fim: filtroDataAltaFim || undefined,
            cliente_id: filtroPessoaHistorico || undefined,
            pet_id: filtroPetHistorico || undefined,
          };
      const res = await vetApi.listarInternacoes(params);
      setInternacoes(Array.isArray(res.data) ? res.data : (res.data?.items ?? []));
    } catch {
      setErro("Erro ao carregar internações.");
    } finally {
      setCarregando(false);
    }
  }, [aba, filtroDataAltaInicio, filtroDataAltaFim, filtroPessoaHistorico, filtroPetHistorico]);

  useEffect(() => { carregar(); }, [carregar]);

  async function carregarDetalheInternacao(id, manterExpandido = true) {
    try {
      const res = await vetApi.obterInternacao(id);
      setEvolucoes((prev) => ({ ...prev, [id]: res.data?.evolucoes ?? [] }));
      setProcedimentosInternacao((prev) => ({ ...prev, [id]: res.data?.procedimentos ?? [] }));
      if (manterExpandido) setExpandida(id);
    } catch {}
  }

  async function abrirDetalhe(id) {
    const fechando = expandida === id;
    setExpandida(fechando ? null : id);
    if (!fechando) {
      await carregarDetalheInternacao(id, true);
    }
  }

  async function criarInternacao() {
    if (!formNova.pet_id || !formNova.motivo) return;
    if (!formNova.box) {
      setErro("Selecione uma baia livre no mapa para internar.");
      return;
    }
    setSalvando(true);
    try {
      await vetApi.criarInternacao({
        pet_id: formNova.pet_id,
        consulta_id: consultaIdQuery ? Number(consultaIdQuery) : undefined,
        motivo: formNova.motivo,
        box: formNova.box || undefined,
      });
      setModalNova(false);
      setFormNova({ pessoa_id: "", pet_id: "", motivo: "", box: "", responsavel: "" });
      setTutorNovaSelecionado(null);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao criar internação.");
    } finally {
      setSalvando(false);
    }
  }

  async function darAlta() {
    if (!modalAlta) return;
    setSalvando(true);
    try {
      await vetApi.darAlta(modalAlta, formAlta || undefined);
      setModalAlta(null);
      setFormAlta("");
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao dar alta.");
    } finally {
      setSalvando(false);
    }
  }

  async function registrarEvolucao() {
    if (!modalEvolucao) return;
    const internacaoId = modalEvolucao;
    setSalvando(true);
    try {
      await vetApi.registrarEvolucao(internacaoId, {
        temperatura: formEvolucao.temperatura ? Number.parseFloat(formEvolucao.temperatura) : undefined,
        frequencia_cardiaca: formEvolucao.fc ? Number.parseInt(formEvolucao.fc, 10) : undefined,
        frequencia_respiratoria: formEvolucao.fr ? Number.parseInt(formEvolucao.fr, 10) : undefined,
        observacoes: formEvolucao.observacoes || undefined,
      });
      await carregarDetalheInternacao(internacaoId, true);
      setModalEvolucao(null);
      setFormEvolucao({ temperatura: "", fc: "", fr: "", observacoes: "" });
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar evolução.");
    } finally {
      setSalvando(false);
    }
  }

  async function adicionarProcedimentoAgenda() {
    if (!agendaForm.internacao_id || !agendaForm.horario || !agendaForm.medicamento) {
      setErro("Preencha internação, horário e medicamento na agenda de procedimentos.");
      return;
    }

    setSalvando(true);

    try {
      const response = await vetApi.registrarProcedimentoInternacao(agendaForm.internacao_id, {
        status: "agendado",
        horario_agendado: agendaForm.horario,
        medicamento: agendaForm.medicamento,
        dose: agendaForm.dose || undefined,
        quantidade_prevista: parseQuantity(agendaForm.quantidade_prevista) ?? undefined,
        unidade_quantidade: agendaForm.unidade_quantidade?.trim() || undefined,
        via: agendaForm.via || undefined,
        observacoes_agenda: agendaForm.observacoes || undefined,
      });

      const internacao = internacaoPorId.get(String(agendaForm.internacao_id));
      const item = {
        id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        backend_id: response.data?.id,
        internacao_id: String(agendaForm.internacao_id),
        pet_nome: internacao?.pet_nome ?? "Pet",
        baia: (internacao?.box || "").trim() || "Sem baia",
        horario: agendaForm.horario,
        medicamento: agendaForm.medicamento,
        dose: agendaForm.dose,
        quantidade_prevista: agendaForm.quantidade_prevista,
        unidade_quantidade: agendaForm.unidade_quantidade,
        via: agendaForm.via,
        lembrete_min: Number.parseInt(agendaForm.lembrete_min || "30", 10),
        observacoes: agendaForm.observacoes,
        feito: false,
        feito_por: "",
        horario_execucao: "",
        observacao_execucao: "",
      };

      setAgendaProcedimentos((prev) => [item, ...prev]);
      await carregarDetalheInternacao(agendaForm.internacao_id, expandida === Number(agendaForm.internacao_id));
      setAgendaForm((prev) => ({
        ...prev,
        horario: sugestaoHorario,
        medicamento: "",
        dose: "",
        quantidade_prevista: "",
        unidade_quantidade: "",
        via: "",
        observacoes: "",
      }));
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar procedimento agendado.");
    } finally {
      setSalvando(false);
    }
  }

  function abrirModalFeito(item) {
    const agora = new Date();
    const pad = (v) => String(v).padStart(2, "0");
    const valorPadrao = `${agora.getFullYear()}-${pad(agora.getMonth() + 1)}-${pad(agora.getDate())}T${pad(agora.getHours())}:${pad(agora.getMinutes())}`;

    setModalFeito(item);
    setFormFeito({
      feito_por: item?.feito_por || "",
      horario_execucao: item?.horario_execucao || valorPadrao,
      observacao_execucao: item?.observacao_execucao || "",
      quantidade_prevista: item?.quantidade_prevista ?? "",
      quantidade_executada: item?.quantidade_executada ?? item?.quantidade_prevista ?? "",
      quantidade_desperdicio: item?.quantidade_desperdicio ?? "",
      unidade_quantidade: item?.unidade_quantidade ?? "",
    });
  }

  async function confirmarProcedimentoFeito() {
    if (!modalFeito) return;
    if (!formFeito.feito_por.trim()) {
      setErro("Informe quem executou o procedimento.");
      return;
    }
    if (!formFeito.horario_execucao) {
      setErro("Informe o horário da execução.");
      return;
    }

    setSalvando(true);

    try {
      await vetApi.registrarProcedimentoInternacao(modalFeito.internacao_id, {
        horario_agendado: modalFeito.horario || undefined,
        medicamento: modalFeito.medicamento,
        dose: modalFeito.dose || undefined,
        via: modalFeito.via || undefined,
        quantidade_prevista: parseQuantity(formFeito.quantidade_prevista) ?? undefined,
        quantidade_executada: parseQuantity(formFeito.quantidade_executada) ?? undefined,
        quantidade_desperdicio: parseQuantity(formFeito.quantidade_desperdicio) ?? undefined,
        unidade_quantidade: formFeito.unidade_quantidade?.trim() || undefined,
        observacoes_agenda: modalFeito.observacoes || undefined,
        executado_por: formFeito.feito_por.trim(),
        horario_execucao: formFeito.horario_execucao,
        observacao_execucao: formFeito.observacao_execucao?.trim() || undefined,
      });

      await carregarDetalheInternacao(modalFeito.internacao_id, expandida === modalFeito.internacao_id);

      setAgendaProcedimentos((prev) => prev.map((p) => {
        if (p.id !== modalFeito.id) return p;
        return {
          ...p,
          feito: true,
          feito_por: formFeito.feito_por.trim(),
          horario_execucao: formFeito.horario_execucao,
          observacao_execucao: formFeito.observacao_execucao?.trim() || "",
          quantidade_prevista: formFeito.quantidade_prevista,
          quantidade_executada: formFeito.quantidade_executada,
          quantidade_desperdicio: formFeito.quantidade_desperdicio,
          unidade_quantidade: formFeito.unidade_quantidade,
        };
      }));
      setModalFeito(null);
      setFormFeito({
        feito_por: "",
        horario_execucao: "",
        observacao_execucao: "",
        quantidade_prevista: "",
        quantidade_executada: "",
        quantidade_desperdicio: "",
        unidade_quantidade: "",
      });
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar procedimento concluído.");
    } finally {
      setSalvando(false);
    }
  }

  function abrirModalInsumoRapido(internacaoId = "") {
    setModalInsumoRapido(true);
    setInsumoRapidoSelecionado(null);
    setFormInsumoRapido({
      internacao_id: internacaoId ? String(internacaoId) : "",
      responsavel: "",
      horario_execucao: sugestaoHorario,
      quantidade_utilizada: "1",
      quantidade_desperdicio: "",
      observacoes: "",
    });
  }

  async function confirmarInsumoRapido() {
    if (!formInsumoRapido.internacao_id) {
      setErro("Selecione o internado para lançar o insumo.");
      return;
    }
    if (!insumoRapidoSelecionado?.id) {
      setErro("Selecione o insumo/produto utilizado.");
      return;
    }
    if (!formInsumoRapido.responsavel.trim()) {
      setErro("Informe quem realizou o uso do insumo.");
      return;
    }

    const quantidadeUtilizada = parseQuantity(formInsumoRapido.quantidade_utilizada);
    const quantidadeDesperdicio = parseQuantity(formInsumoRapido.quantidade_desperdicio) ?? 0;
    const quantidadeConsumida = (quantidadeUtilizada ?? 0) + quantidadeDesperdicio;

    if (!quantidadeUtilizada || quantidadeUtilizada <= 0) {
      setErro("Informe a quantidade efetivamente utilizada do insumo.");
      return;
    }
    if (quantidadeConsumida <= 0) {
      setErro("A baixa total do insumo precisa ser maior que zero.");
      return;
    }

    setSalvando(true);
    try {
      const unidade = insumoRapidoSelecionado.unidade || "un";
      const internacaoId = String(formInsumoRapido.internacao_id);

      await vetApi.registrarProcedimentoInternacao(internacaoId, {
        status: "concluido",
        tipo_registro: "insumo",
        medicamento: `Insumo: ${insumoRapidoSelecionado.nome}`,
        dose: formatQuantity(quantidadeUtilizada, unidade),
        quantidade_prevista: quantidadeUtilizada,
        quantidade_executada: quantidadeUtilizada,
        quantidade_desperdicio: quantidadeDesperdicio || undefined,
        unidade_quantidade: unidade,
        executado_por: formInsumoRapido.responsavel.trim(),
        horario_execucao: formInsumoRapido.horario_execucao,
        observacao_execucao: formInsumoRapido.observacoes?.trim() || undefined,
        insumos: [
          {
            produto_id: insumoRapidoSelecionado.id,
            nome: insumoRapidoSelecionado.nome,
            unidade,
            quantidade: quantidadeConsumida,
            baixar_estoque: true,
          },
        ],
      });

      await carregarDetalheInternacao(Number(internacaoId), expandida === Number(internacaoId));
      setModalInsumoRapido(false);
      setInsumoRapidoSelecionado(null);
      setFormInsumoRapido({
        internacao_id: "",
        responsavel: "",
        horario_execucao: sugestaoHorario,
        quantidade_utilizada: "1",
        quantidade_desperdicio: "",
        observacoes: "",
      });
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao lançar insumo rápido.");
    } finally {
      setSalvando(false);
    }
  }

  function reabrirProcedimento(id) {
    setAgendaProcedimentos((prev) => prev.map((p) => {
      if (p.id !== id) return p;
      return {
        ...p,
        feito: false,
        feito_por: "",
        horario_execucao: "",
        observacao_execucao: "",
      };
    }));
  }

  function removerProcedimentoAgenda(id) {
    setAgendaProcedimentos((prev) => prev.filter((p) => p.id !== id));
  }

  async function abrirHistoricoPet(petId, petNome) {
    setCarregandoHistoricoPet(true);
    setModalHistoricoPet({ petId, petNome });
    setHistoricoPet([]);
    try {
      const res = await vetApi.historicoInternacoesPet(petId);
      setHistoricoPet(Array.isArray(res.data?.historico) ? res.data.historico : []);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao carregar histórico do pet.");
      setHistoricoPet([]);
    } finally {
      setCarregandoHistoricoPet(false);
    }
  }

  return (
    <div className="p-6 space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-xl">
            <BedDouble size={22} className="text-purple-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Internações</h1>
        </div>
        <button
          onClick={() => {
            setAba("ativas");
            setTutorNovaSelecionado(null);
            setFormNova({ pessoa_id: "", pet_id: "", motivo: "", box: "", responsavel: "" });
            setModalNova(true);
          }}
          className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <Plus size={15} />
          Nova internação
        </button>
      </div>

      {/* Abas */}
      <div className="flex border-b border-gray-200">
        {[{ id: "ativas", label: "Ativas" }, { id: "historico", label: "Histórico" }].map((a) => (
          <button key={a.id} onClick={() => setAba(a.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${aba === a.id ? "border-purple-500 text-purple-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {a.label}
          </button>
        ))}
      </div>

      {/* Erro */}
      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
          <AlertCircle size={16} />
          <span>{erro}</span>
          <button className="ml-auto" onClick={() => setErro(null)}>✕</button>
        </div>
      )}

      {aba === "historico" && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <p className="text-sm font-semibold text-gray-700 mb-3">Filtros do histórico</p>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Alta de</label>
              <input
                type="date"
                value={filtroDataAltaInicio}
                onChange={(e) => setFiltroDataAltaInicio(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Alta até</label>
              <input
                type="date"
                value={filtroDataAltaFim}
                onChange={(e) => setFiltroDataAltaFim(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Pessoa (tutor)</label>
              <select
                value={filtroPessoaHistorico}
                onChange={(e) => {
                  setFiltroPessoaHistorico(e.target.value);
                  setFiltroPetHistorico("");
                }}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
              >
                <option value="">Todas</option>
                {pessoas.map((pessoa) => <option key={pessoa.id} value={pessoa.id}>{pessoa.nome}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Pet</label>
              <select
                value={filtroPetHistorico}
                onChange={(e) => setFiltroPetHistorico(e.target.value)}
                disabled={!filtroPessoaHistorico}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white disabled:opacity-60"
              >
                <option value="">Todos</option>
                {petsHistoricoDaPessoa.map((p) => <option key={p.id} value={p.id}>{p.nome}{p.especie ? ` (${p.especie})` : ""}</option>)}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Centro de Internação */}
      {carregando ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
        </div>
      ) : internacoes.length === 0 ? (
        <div className="p-10 text-center bg-white border border-gray-200 rounded-xl">
          <BedDouble size={36} className="mx-auto text-gray-200 mb-3" />
          <p className="text-gray-400 text-sm">Nenhuma internação {aba === "ativas" ? "ativa" : "registrada"}.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {aba === "ativas" && (
            <div className="flex flex-wrap gap-2 bg-white border border-gray-200 rounded-xl p-2">
              {[
                { id: "widget", label: "Widget (resumo)", icon: LayoutGrid },
                { id: "mapa", label: "Mapa da internação", icon: MapIcon },
                { id: "lista", label: "Lista de internados", icon: List },
                { id: "agenda", label: "Agenda de procedimentos", icon: BellRing },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setCentroAba(item.id)}
                    className={`flex items-center gap-2 px-3 py-2 text-xs rounded-lg border transition-colors ${
                      centroAba === item.id
                        ? "bg-purple-600 text-white border-purple-600"
                        : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    <Icon size={13} />
                    {item.label}
                  </button>
                );
              })}
            </div>
          )}

          {aba === "ativas" && centroAba === "mapa" && (
            <div className="space-y-3">
              <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col md:flex-row md:items-end gap-3">
                <div>
                  <p className="text-sm font-semibold text-gray-800">Mapa visual de baias</p>
                  <p className="text-xs text-gray-500">Estilo assento: vermelho ocupado, verde disponível.</p>
                </div>
                <div className="md:ml-auto w-full md:w-56">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Total de baias no local</label>
                  <input
                    type="number"
                    min="1"
                    max="200"
                    value={totalBaias}
                    onChange={(e) => {
                      const valor = Number.parseInt(e.target.value || "0", 10);
                      if (!Number.isFinite(valor)) return;
                      setTotalBaias(Math.max(1, Math.min(200, valor)));
                    }}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="bg-white border border-gray-200 rounded-xl p-4">
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-3">
                  {mapaInternacao.map((baia) => {
                    const ocupada = baia.ocupada;
                    const intern = baia.internacao;
                    return (
                      <div
                        key={String(baia.numero)}
                        onClick={() => {
                          if (!intern?.id) return;
                          setAba("ativas");
                          setCentroAba("lista");
                          abrirDetalhe(intern.id);
                        }}
                        className={`rounded-xl border p-3 min-h-[92px] transition-colors ${
                          ocupada
                            ? "border-red-300 bg-red-50"
                            : "border-emerald-300 bg-emerald-50"
                        } ${ocupada ? "cursor-pointer hover:shadow-sm" : ""}`}
                      >
                        <p className={`text-sm font-bold ${ocupada ? "text-red-700" : "text-emerald-700"}`}>
                          Baia {baia.numero}
                        </p>
                        {ocupada ? (
                          <>
                            <p className="text-xs font-semibold text-gray-800 mt-2 truncate">{intern?.pet_nome ?? "Internado"}</p>
                            <p className="text-[11px] text-gray-600 truncate">{intern?.motivo ?? "Sem motivo"}</p>
                          </>
                        ) : (
                          <p className="text-xs text-emerald-700 mt-2">Disponível</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="bg-white border border-gray-200 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-700 mb-2">Legenda</p>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="px-2 py-1 rounded-full bg-red-100 text-red-700 border border-red-200">Baia ocupada</span>
                  <span className="px-2 py-1 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">Baia disponível</span>
                </div>
              </div>
            </div>
          )}

          {(aba === "historico" || (aba === "ativas" && centroAba === "lista")) && (
            <div className="space-y-3">
              {aba === "ativas" && (
                <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
                  <p className="text-sm font-semibold text-gray-700">Ficha de internados</p>
                  <p className="text-xs text-gray-500">Evoluções + procedimentos concluídos ficam centralizados por internação.</p>
                </div>
              )}
              {internacoesOrdenadas.map((intern) => {
                const aberta = expandida === intern.id;
                return (
                  <div key={intern.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                    <div
                      className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
                      onClick={() => abrirDetalhe(intern.id)}
                    >
                      <BedDouble size={18} className="text-purple-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-gray-800">{intern.pet_nome ?? `Pet #${String(intern.pet_id ?? "").slice(0, 6)}`}</p>
                        {intern.tutor_nome && <p className="text-xs text-gray-500">Tutor: {intern.tutor_nome}</p>}
                        <p className="text-xs text-gray-400 truncate">{intern.motivo ?? intern.motivo_internacao}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-xs text-gray-400">Entrada: {formatData(intern.data_entrada)}</p>
                        {intern.data_saida && <p className="text-xs text-gray-400">Alta: {formatData(intern.data_saida)}</p>}
                        {intern.box && <p className="text-xs text-gray-500">Box: {intern.box}</p>}
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CORES[intern.status] ?? "bg-gray-100"}`}>
                        {intern.status}
                      </span>
                      {(intern.status === "ativa" || intern.status === "internado") && (
                        <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => abrirModalInsumoRapido(intern.id)}
                            className="flex items-center gap-1 text-xs px-2 py-1 border border-emerald-200 text-emerald-700 rounded-lg hover:bg-emerald-50"
                          >
                            + Insumo
                          </button>
                          <button
                            onClick={() => setModalEvolucao(intern.id)}
                            className="flex items-center gap-1 text-xs px-2 py-1 border border-blue-200 text-blue-600 rounded-lg hover:bg-blue-50"
                          >
                            <Activity size={12} />
                            Evolução
                          </button>
                          <button
                            onClick={() => setModalAlta(intern.id)}
                            className="flex items-center gap-1 text-xs px-2 py-1 border border-green-200 text-green-600 rounded-lg hover:bg-green-50"
                          >
                            <ArrowUpCircle size={12} />
                            Alta
                          </button>
                          <button
                            onClick={() => navigate(`/pets/${intern.pet_id}`)}
                            className="flex items-center gap-1 text-xs px-2 py-1 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50"
                          >
                            Ficha do pet
                          </button>
                          <button
                            onClick={() => abrirHistoricoPet(intern.pet_id, intern.pet_nome ?? `Pet #${intern.pet_id}`)}
                            className="flex items-center gap-1 text-xs px-2 py-1 border border-indigo-200 text-indigo-600 rounded-lg hover:bg-indigo-50"
                          >
                            Detalhes
                          </button>
                        </div>
                      )}
                    </div>

                    {aberta && (
                      <div className="border-t border-gray-100 bg-gray-50 px-5 py-4">
                        {(() => {
                          const serie = montarSerieEvolucao(evolucoes[intern.id] ?? []);
                          if (serie.length < 2) return null;
                          return (
                            <div className="mb-4 rounded-xl border border-blue-100 bg-white p-4">
                              <p className="text-xs font-semibold text-gray-500 mb-3">Curva de evolução</p>
                              <ResponsiveContainer width="100%" height={240}>
                                <LineChart data={serie}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                  <XAxis dataKey="horario" tick={{ fontSize: 11 }} />
                                  <YAxis yAxisId="vital" tick={{ fontSize: 11 }} />
                                  <YAxis yAxisId="peso" orientation="right" tick={{ fontSize: 11 }} />
                                  <Tooltip />
                                  <Legend />
                                  <Line yAxisId="vital" type="monotone" dataKey="temperatura" name="Temperatura" stroke="#ef4444" strokeWidth={2} dot={false} connectNulls />
                                  <Line yAxisId="vital" type="monotone" dataKey="fc" name="FC" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls />
                                  <Line yAxisId="vital" type="monotone" dataKey="fr" name="FR" stroke="#14b8a6" strokeWidth={2} dot={false} connectNulls />
                                  <Line yAxisId="peso" type="monotone" dataKey="peso" name="Peso" stroke="#7c3aed" strokeWidth={2} dot={false} connectNulls />
                                </LineChart>
                              </ResponsiveContainer>
                            </div>
                          );
                        })()}

                        {(intern.observacoes_alta || intern.observacoes) && (
                          <div className="mb-3 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                            <p className="text-xs font-semibold text-green-700 mb-1">Observação da alta</p>
                            <p className="text-xs text-green-800">{intern.observacoes_alta || intern.observacoes}</p>
                          </div>
                        )}
                        <p className="text-xs font-semibold text-gray-500 mb-3">Evoluções</p>
                        {(evolucoes[intern.id] ?? []).length === 0 ? (
                          <p className="text-xs text-gray-400">Nenhuma evolução registrada ainda.</p>
                        ) : (
                          <div className="space-y-2">
                            {(evolucoes[intern.id] ?? []).map((ev, i) => (
                              <div key={i} className="bg-white border border-gray-100 rounded-lg px-3 py-2 text-xs">
                                <div className="flex items-center gap-2 text-gray-400 mb-1">
                                  <Clock size={10} />
                                  <span>{formatDateTime(ev.data_hora)}</span>
                                </div>
                                <div className="flex gap-4 text-gray-600">
                                  {ev.temperatura && <span>Temp: {ev.temperatura}°C</span>}
                                  {ev.freq_cardiaca && <span>FC: {ev.freq_cardiaca} bpm</span>}
                                  {ev.freq_respiratoria && <span>FR: {ev.freq_respiratoria} rpm</span>}
                                </div>
                                {ev.observacoes && <p className="text-gray-500 mt-1">{ev.observacoes}</p>}
                              </div>
                            ))}
                          </div>
                        )}

                        <div className="mt-4">
                          <p className="text-xs font-semibold text-gray-500 mb-2">Procedimentos desta internação</p>
                          {(procedimentosInternacao[intern.id] ?? []).length === 0 ? (
                            <p className="text-xs text-gray-400">Nenhum procedimento registrado ainda.</p>
                          ) : (
                            <div className="space-y-2">
                              {(procedimentosInternacao[intern.id] ?? []).map((proc, idx) => (
                                <div key={`${proc.id ?? idx}_proc`} className="bg-white border border-emerald-100 rounded-lg px-3 py-2 text-xs">
                                  <div className="flex items-center gap-2 text-emerald-700 mb-1">
                                    <Clock size={10} />
                                    <span>{proc.horario_execucao ? formatDateTime(proc.horario_execucao) : formatDateTime(proc.data_hora)}</span>
                                  </div>
                                  <div className="mb-1">
                                    <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${proc.status === "agendado" ? "bg-amber-100 text-amber-700 border border-amber-200" : "bg-emerald-100 text-emerald-700 border border-emerald-200"}`}>
                                      {proc.status === "agendado" ? "Agendado" : "Concluído"}
                                    </span>
                                  </div>
                                  <p className="text-sm font-semibold text-emerald-800">{proc.medicamento || "Procedimento"}</p>
                                  <p className="text-gray-600">Dose: {proc.dose || "—"} • Via: {proc.via || "—"}</p>
                                  {(proc.quantidade_prevista != null || proc.quantidade_executada != null || proc.quantidade_desperdicio != null) && (
                                    <p className="text-gray-600">
                                      Previsto: {formatQuantity(proc.quantidade_prevista, proc.unidade_quantidade)} • Feito: {formatQuantity(proc.quantidade_executada, proc.unidade_quantidade)} • Desperdício: {formatQuantity(proc.quantidade_desperdicio, proc.unidade_quantidade)}
                                    </p>
                                  )}
                                  <p className="text-gray-500">Responsável: {proc.executado_por || "—"}</p>
                                  {Array.isArray(proc.insumos) && proc.insumos.length > 0 && (
                                    <div className="mt-2 flex flex-wrap gap-1.5">
                                      {proc.insumos.map((insumo, insumoIdx) => (
                                        <span key={`${proc.id ?? idx}_insumo_${insumoIdx}`} className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                                          {insumo.nome || `Produto #${insumo.produto_id}`} • {formatQuantity(insumo.quantidade, insumo.unidade)}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                  {proc.observacao_execucao && <p className="text-gray-500 mt-1">Obs.: {proc.observacao_execucao}</p>}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {aba === "ativas" && centroAba === "widget" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3">
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500">Internados agora</p>
                  <p className="text-2xl font-bold text-purple-700">{indicadoresInternacao.total}</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500">Sem baia definida</p>
                  <p className="text-2xl font-bold text-amber-600">{indicadoresInternacao.semBaia}</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500">Com evolução</p>
                  <p className="text-2xl font-bold text-green-600">{indicadoresInternacao.comEvolucao}</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500">Sem evolução</p>
                  <p className="text-2xl font-bold text-red-600">{indicadoresInternacao.semEvolucao}</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500">Média dias internado</p>
                  <p className="text-2xl font-bold text-blue-700">{indicadoresInternacao.mediaDias}</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500">Baias ocupadas</p>
                  <p className="text-2xl font-bold text-red-700">{indicadoresInternacao.baiasOcupadas}</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500">Baias livres</p>
                  <p className="text-2xl font-bold text-emerald-700">{indicadoresInternacao.baiasLivres}</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500">Procedimentos pendentes</p>
                  <p className="text-2xl font-bold text-amber-700">{indicadoresInternacao.procedimentosPendentes}</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <p className="text-xs text-gray-500">Procedimentos atrasados</p>
                  <p className="text-2xl font-bold text-rose-700">{indicadoresInternacao.procedimentosAtrasados}</p>
                </div>
              </div>
              <div className="bg-white border border-gray-200 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-700 mb-2">Widget rápido de internados</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {internacoesOrdenadas.map((intern) => (
                    <div key={intern.id} className="flex items-center justify-between border border-gray-100 rounded-lg px-3 py-2">
                      <div>
                        <p className="text-sm font-medium text-gray-800">{intern.pet_nome ?? `Pet #${intern.pet_id}`}</p>
                        <p className="text-xs text-gray-500">{intern.box || "Sem baia"} • {formatData(intern.data_entrada)}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CORES[intern.status] ?? "bg-gray-100"}`}>
                        {intern.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {aba === "ativas" && centroAba === "agenda" && (
            <div className="space-y-3">
              <div className="bg-white border border-gray-200 rounded-xl p-4">
                <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-700">Novo procedimento / lembrete</p>
                    <p className="mt-1 text-xs text-gray-500">
                      Preencha o que estava previsto para o paciente: horário, nome do medicamento/procedimento,
                      dose clínica, quantidade prevista e via. Se quiser apenas baixar um material usado na rotina,
                      use o botão de insumo rápido.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => abrirModalInsumoRapido(agendaForm.internacao_id)}
                    className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
                  >
                    + Lançar insumo rápido
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  <select
                    value={agendaForm.internacao_id}
                    onChange={(e) => setAgendaForm((p) => ({ ...p, internacao_id: e.target.value }))}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                  >
                    <option value="">Selecione o internado…</option>
                    {internacoesOrdenadas.map((i) => (
                      <option key={i.id} value={i.id}>{i.pet_nome ?? `Pet #${i.pet_id}`}{i.box ? ` (${i.box})` : ""}</option>
                    ))}
                  </select>
                  <input
                    type="datetime-local"
                    value={agendaForm.horario}
                    onChange={(e) => setAgendaForm((p) => ({ ...p, horario: e.target.value }))}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Medicamento / procedimento"
                    value={agendaForm.medicamento}
                    onChange={(e) => setAgendaForm((p) => ({ ...p, medicamento: e.target.value }))}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Dose"
                    value={agendaForm.dose}
                    onChange={(e) => setAgendaForm((p) => ({ ...p, dose: e.target.value }))}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="Qtd. prevista"
                    value={agendaForm.quantidade_prevista}
                    onChange={(e) => setAgendaForm((p) => ({ ...p, quantidade_prevista: e.target.value }))}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Unidade (mL, mg, comp, un...)"
                    value={agendaForm.unidade_quantidade}
                    onChange={(e) => setAgendaForm((p) => ({ ...p, unidade_quantidade: e.target.value }))}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Via (oral, IV, IM...)"
                    value={agendaForm.via}
                    onChange={(e) => setAgendaForm((p) => ({ ...p, via: e.target.value }))}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    value={agendaForm.internacao_id ? (internacaoSelecionadaAgenda?.box || "Sem baia") : "Selecione um internado"}
                    disabled
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-600"
                  />
                  <input
                    type="number"
                    min="0"
                    placeholder="Lembrete (min)"
                    value={agendaForm.lembrete_min}
                    onChange={(e) => setAgendaForm((p) => ({ ...p, lembrete_min: e.target.value }))}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Observações"
                    value={agendaForm.observacoes}
                    onChange={(e) => setAgendaForm((p) => ({ ...p, observacoes: e.target.value }))}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm md:col-span-2"
                  />
                  <button
                    onClick={adicionarProcedimentoAgenda}
                    className="bg-purple-600 hover:bg-purple-700 text-white rounded-lg px-3 py-2 text-sm"
                  >
                    Adicionar na agenda
                  </button>
                </div>
              </div>

              <div className="bg-white border border-gray-200 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-700 mb-3">Horários de hoje e próximos</p>
                {agendaOrdenada.length === 0 ? (
                  <p className="text-xs text-gray-400">Nenhum procedimento agendado ainda.</p>
                ) : (
                  <div className="space-y-2">
                    {agendaOrdenada.map((item) => {
                      const internacaoAtual = internacaoPorId.get(String(item.internacao_id));
                      const baiaExibicao = (internacaoAtual?.box || item.baia || "").trim() || "Sem baia";
                      const ts = new Date(item.horario).getTime();
                      const diffMin = Math.round((ts - Date.now()) / 60000);
                      const alerta = item.feito
                        ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
                        : diffMin <= 0
                        ? "bg-rose-100 text-rose-700 border border-rose-200"
                        : diffMin <= Number(item.lembrete_min || 30)
                        ? "bg-amber-100 text-amber-700 border border-amber-200"
                        : "bg-sky-100 text-sky-700 border border-sky-200";

                      return (
                        <div key={item.id} className="border border-slate-200 rounded-xl p-3 bg-gradient-to-r from-white to-slate-50/40 shadow-sm flex flex-col md:flex-row md:items-center gap-3 md:gap-4">
                          <div className="min-w-[160px] bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                            <p className="text-lg font-semibold text-slate-800 leading-none tabular-nums">{formatDateTime(item.horario)}</p>
                            <span className={`inline-block mt-2 text-[11px] px-2 py-0.5 rounded-full font-medium ${alerta}`}>
                              {item.feito ? "Concluído" : diffMin <= 0 ? "Atrasado" : `Em ${diffMin} min`}
                            </span>
                          </div>
                          <div className="flex-1">
                            <p className="text-base font-semibold text-indigo-800 leading-tight">{item.medicamento}</p>
                            <p className="text-sm text-slate-600 mt-0.5">{item.pet_nome} • Baia {baiaExibicao}</p>
                            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
                              <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-semibold">
                                Dose: {item.dose || "—"}
                              </span>
                              {(item.quantidade_prevista || item.unidade_quantidade) && (
                                <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 border border-blue-200">
                                  Previsto: {formatQuantity(item.quantidade_prevista, item.unidade_quantidade)}
                                </span>
                              )}
                              <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                                Via: {item.via || "—"}
                              </span>
                              <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                                Lembrete: {item.lembrete_min || 30} min
                              </span>
                            </div>
                            {item.observacoes && <p className="text-xs text-slate-500 mt-2 italic">{item.observacoes}</p>}
                            {item.feito && (
                              <div className="mt-2 bg-emerald-50 border border-emerald-200 rounded-md px-2 py-1.5">
                                <p className="text-[11px] text-emerald-700 font-semibold">
                                  Feito por: {item.feito_por || "—"} • {item.horario_execucao ? formatDateTime(item.horario_execucao) : "—"}
                                </p>
                                {(item.quantidade_executada || item.quantidade_desperdicio) && (
                                  <p className="text-[11px] text-emerald-800">
                                    Feito: {formatQuantity(item.quantidade_executada, item.unidade_quantidade)} • Desperdício: {formatQuantity(item.quantidade_desperdicio, item.unidade_quantidade)}
                                  </p>
                                )}
                                {item.observacao_execucao && (
                                  <p className="text-[11px] text-emerald-800">Obs. execução: {item.observacao_execucao}</p>
                                )}
                              </div>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => (item.feito ? reabrirProcedimento(item.id) : abrirModalFeito(item))}
                              className="px-2.5 py-1.5 text-xs border border-emerald-200 text-emerald-700 rounded-lg hover:bg-emerald-50 transition-colors flex items-center gap-1"
                            >
                              <Check size={12} />
                              {item.feito ? "Reabrir" : "Feito"}
                            </button>
                            <button
                              onClick={() => removerProcedimentoAgenda(item.id)}
                              className="px-2.5 py-1.5 text-xs border border-rose-200 text-rose-700 rounded-lg hover:bg-rose-50 transition-colors flex items-center gap-1"
                            >
                              <Trash2 size={12} />
                              Excluir
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal nova internação */}
      {modalNova && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="font-bold text-gray-800">Nova internação</h2>
            <div className="space-y-3">
              {consultaIdQuery && (
                <div className="rounded-lg border border-purple-200 bg-purple-50 px-4 py-3 text-sm text-purple-800">
                  Esta internação ficará vinculada à consulta <strong>#{consultaIdQuery}</strong>.
                </div>
              )}
              <div>
                <TutorAutocomplete
                  label="Pessoa (tutor) *"
                  inputId="internacao-tutor"
                  selectedTutor={tutorNovaSelecionado}
                  onSelect={(cliente) => {
                    setTutorNovaSelecionado(cliente);
                    setFormNova((prev) => ({
                      ...prev,
                      pessoa_id: cliente?.id ? String(cliente.id) : "",
                      pet_id: "",
                    }));
                  }}
                />
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between gap-2">
                  <label className="block text-xs font-medium text-gray-600">Pet da pessoa *</label>
                  <NovoPetButton
                    tutorId={formNova.pessoa_id}
                    tutorNome={tutorAtualInternacao?.nome}
                    returnTo={retornoNovoPet}
                    onBeforeNavigate={() => setModalNova(false)}
                  />
                </div>
                <select value={formNova.pet_id} onChange={(e) => setFormNova((p) => ({ ...p, pet_id: e.target.value }))}
                  disabled={!formNova.pessoa_id}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white disabled:opacity-60">
                  <option value="">Selecione…</option>
                  {petsDaPessoa.map((p) => <option key={p.id} value={p.id}>{p.nome}{p.especie ? ` (${p.especie})` : ""}</option>)}
                </select>
                {formNova.pessoa_id && petsDaPessoa.length === 0 && (
                  <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para esta pessoa.</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Motivo da internação *</label>
                <textarea value={formNova.motivo} onChange={(e) => setFormNova((p) => ({ ...p, motivo: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-20" />
              </div>
              <div>
                <div className="flex items-end justify-between mb-2">
                  <label className="block text-xs font-medium text-gray-600">Mapa de baias (selecione uma livre) *</label>
                  <div className="w-28">
                    <input
                      type="number"
                      min="1"
                      max="200"
                      value={totalBaias}
                      onChange={(e) => {
                        const valor = Number.parseInt(e.target.value || "0", 10);
                        if (!Number.isFinite(valor)) return;
                        setTotalBaias(Math.max(1, Math.min(200, valor)));
                      }}
                      className="w-full border border-gray-200 rounded-lg px-2 py-1 text-xs"
                      title="Total de baias"
                    />
                  </div>
                </div>
                <div className="border border-gray-200 rounded-lg p-2 max-h-44 overflow-auto">
                  <div className="grid grid-cols-3 gap-2">
                    {mapaInternacao
                      .filter((baia) => Number.isFinite(Number.parseInt(String(baia.numero), 10)))
                      .sort((a, b) => Number(a.numero) - Number(b.numero))
                      .map((baia) => {
                        const numero = String(baia.numero);
                        const ocupadaPorOutro = baia.ocupada;
                        const selecionada = formNova.box === numero;
                        return (
                          <button
                            key={`nova_baia_${numero}`}
                            type="button"
                            disabled={ocupadaPorOutro}
                            onClick={() => setFormNova((p) => ({ ...p, box: numero }))}
                            className={`rounded-md border px-2 py-2 text-left transition-colors ${
                              ocupadaPorOutro
                                ? "bg-red-50 border-red-200 text-red-700 cursor-not-allowed"
                                : selecionada
                                ? "bg-purple-600 border-purple-600 text-white"
                                : "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100"
                            }`}
                          >
                            <p className="text-xs font-bold">Baia {numero}</p>
                            <p className="text-[11px] truncate">
                              {ocupadaPorOutro ? (baia.internacao?.pet_nome ?? "Ocupada") : "Disponível"}
                            </p>
                          </button>
                        );
                      })}
                  </div>
                </div>
                <p className="text-xs mt-1 text-gray-500">
                  Selecionada: <span className="font-semibold text-gray-800">{formNova.box || "nenhuma"}</span>
                </p>
              </div>
            </div>
            <div className="flex gap-3 pt-1">
              <button
                onClick={() => {
                  setModalNova(false);
                  if (!consultaIdQuery) {
                    setTutorNovaSelecionado(null);
                    setFormNova({ pessoa_id: "", pet_id: "", motivo: "", box: "", responsavel: "" });
                  }
                }}
                className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button onClick={criarInternacao} disabled={salvando || !formNova.pet_id || !formNova.motivo}
                className="flex-1 px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-60">
                {salvando ? "Salvando…" : "Internar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal dar alta */}
      {modalAlta && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="font-bold text-gray-800">Dar alta</h2>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Observações de alta</label>
              <textarea value={formAlta} onChange={(e) => setFormAlta(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-28"
                placeholder="Instruções para o tutor, condição na saída…" />
            </div>
            <div className="flex gap-3 pt-1">
              <button onClick={() => setModalAlta(null)} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancelar</button>
              <button onClick={darAlta} disabled={salvando}
                className="flex-1 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60">
                {salvando ? "Processando…" : "Confirmar alta"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal evolução */}
      {modalEvolucao && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="font-bold text-gray-800">Registrar evolução</h2>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Temp. (°C)</label>
                <input type="number" step="0.1" value={formEvolucao.temperatura} onChange={(e) => setFormEvolucao((p) => ({ ...p, temperatura: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">FC (bpm)</label>
                <input type="number" value={formEvolucao.fc} onChange={(e) => setFormEvolucao((p) => ({ ...p, fc: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">FR (rpm)</label>
                <input type="number" value={formEvolucao.fr} onChange={(e) => setFormEvolucao((p) => ({ ...p, fr: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Observações</label>
              <textarea value={formEvolucao.observacoes} onChange={(e) => setFormEvolucao((p) => ({ ...p, observacoes: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-20" />
            </div>
            <div className="flex gap-3 pt-1">
              <button onClick={() => setModalEvolucao(null)} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancelar</button>
              <button onClick={registrarEvolucao} disabled={salvando}
                className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60">
                {salvando ? "Salvando…" : "Registrar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal concluir procedimento */}
      {modalFeito && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="font-bold text-gray-800">Concluir procedimento</h2>
            <div className="bg-purple-50 border border-purple-200 rounded-lg px-3 py-2">
              <p className="text-xs text-purple-700 font-semibold">{modalFeito.pet_nome}</p>
              <p className="text-sm font-bold text-purple-900">{modalFeito.medicamento}</p>
              <p className="text-xs text-purple-700">Dose: {modalFeito.dose || "—"} • Baia: {(internacaoPorId.get(String(modalFeito.internacao_id))?.box || modalFeito.baia || "Sem baia")}</p>
            </div>
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Informe o que estava previsto, quanto realmente foi administrado e quanto virou desperdício/excesso. Assim o registro clínico fica fiel ao que aconteceu no atendimento.
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Responsável veterinário *</label>
              <select
                value={formFeito.feito_por}
                onChange={(e) => setFormFeito((p) => ({ ...p, feito_por: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
              >
                <option value="">Selecione…</option>
                {veterinarios.map((vet) => (
                  <option key={vet.id} value={vet.nome}>
                    {vet.nome}{vet.crmv ? ` - CRMV ${vet.crmv}` : ""}
                  </option>
                ))}
                {formFeito.feito_por && !veterinarios.some((vet) => vet.nome === formFeito.feito_por) && (
                  <option value={formFeito.feito_por}>{formFeito.feito_por}</option>
                )}
              </select>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Qtd. prevista</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formFeito.quantidade_prevista}
                  onChange={(e) => setFormFeito((p) => ({ ...p, quantidade_prevista: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Unidade</label>
                <input
                  type="text"
                  value={formFeito.unidade_quantidade}
                  onChange={(e) => setFormFeito((p) => ({ ...p, unidade_quantidade: e.target.value }))}
                  placeholder="mL, mg, comp, un..."
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Qtd. efetivamente feita</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formFeito.quantidade_executada}
                  onChange={(e) => setFormFeito((p) => ({ ...p, quantidade_executada: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Desperdício / excesso</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formFeito.quantidade_desperdicio}
                  onChange={(e) => setFormFeito((p) => ({ ...p, quantidade_desperdicio: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Horário da execução *</label>
              <input
                type="datetime-local"
                value={formFeito.horario_execucao}
                onChange={(e) => setFormFeito((p) => ({ ...p, horario_execucao: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Observação da execução (opcional)</label>
              <textarea
                value={formFeito.observacao_execucao}
                onChange={(e) => setFormFeito((p) => ({ ...p, observacao_execucao: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-20"
                placeholder="Ex.: pet aceitou bem, sem reação"
              />
            </div>
            <div className="flex gap-3 pt-1">
              <button
                onClick={() => setModalFeito(null)}
                className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={confirmarProcedimentoFeito}
                disabled={salvando}
                className="flex-1 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60"
              >
                {salvando ? "Salvando..." : "Confirmar feito"}
              </button>
            </div>
          </div>
        </div>
      )}

      {modalHistoricoPet && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl p-6 max-h-[85vh] overflow-auto">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="font-bold text-gray-800">Histórico de internações</h2>
                <p className="text-sm text-gray-500">{modalHistoricoPet.petNome}</p>
              </div>
              <button
                onClick={() => setModalHistoricoPet(null)}
                className="px-2 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Fechar
              </button>
            </div>

            {carregandoHistoricoPet ? (
              <p className="text-sm text-gray-500">Carregando histórico...</p>
            ) : historicoPet.length === 0 ? (
              <p className="text-sm text-gray-500">Nenhuma internação encontrada para este pet.</p>
            ) : (
              <div className="space-y-3">
                {historicoPet.map((hist) => (
                  <div key={hist.internacao_id} className="border border-gray-200 rounded-xl p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-gray-800">Internação #{hist.internacao_id} • {hist.box ? `Baia ${hist.box}` : "Sem baia"}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CORES[hist.status] ?? "bg-gray-100 text-gray-700"}`}>{hist.status}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Entrada: {formatDateTime(hist.data_entrada)}{hist.data_saida ? ` • Alta: ${formatDateTime(hist.data_saida)}` : ""}</p>
                    <p className="text-xs text-gray-600 mt-1">Motivo: {hist.motivo || "—"}</p>
                    <p className="text-xs text-gray-600 mt-1">Evoluções: {hist.evolucoes?.length ?? 0} • Procedimentos: {hist.procedimentos?.length ?? 0}</p>
                    {Array.isArray(hist.procedimentos) && hist.procedimentos.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {hist.procedimentos.map((proc, idx) => (
                          <div key={`${hist.internacao_id}_proc_${proc.id ?? idx}`} className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-xs">
                            <p className="font-semibold text-gray-800">{proc.medicamento || "Procedimento"}</p>
                            <p className="text-gray-500">
                              {proc.horario_execucao ? formatDateTime(proc.horario_execucao) : formatDateTime(proc.data_hora)}
                            </p>
                            {(proc.quantidade_prevista != null || proc.quantidade_executada != null || proc.quantidade_desperdicio != null) && (
                              <p className="mt-1 text-gray-600">
                                Previsto: {formatQuantity(proc.quantidade_prevista, proc.unidade_quantidade)} • Feito: {formatQuantity(proc.quantidade_executada, proc.unidade_quantidade)} • Desperdício: {formatQuantity(proc.quantidade_desperdicio, proc.unidade_quantidade)}
                              </p>
                            )}
                            {Array.isArray(proc.insumos) && proc.insumos.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1.5">
                                {proc.insumos.map((insumo, insumoIdx) => (
                                  <span key={`${hist.internacao_id}_proc_${idx}_insumo_${insumoIdx}`} className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                                    {insumo.nome || `Produto #${insumo.produto_id}`} • {formatQuantity(insumo.quantidade, insumo.unidade)}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {modalInsumoRapido && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Lançar insumo rápido</h2>
                <p className="text-sm text-gray-500">
                  Registre materiais ou medicamentos consumidos durante a internação com baixa automática do estoque.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setModalInsumoRapido(false)}
                className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                aria-label="Fechar modal de insumo"
              >
                ✕
              </button>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Internado *</label>
                <select
                  value={formInsumoRapido.internacao_id}
                  onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, internacao_id: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white"
                >
                  <option value="">Selecione…</option>
                  {internacoesOrdenadas.map((internacao) => (
                    <option key={`insumo_internacao_${internacao.id}`} value={internacao.id}>
                      {internacao.pet_nome ?? `Pet #${internacao.pet_id}`}{internacao.box ? ` • ${internacao.box}` : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Responsável *</label>
                <select
                  value={formInsumoRapido.responsavel}
                  onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, responsavel: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white"
                >
                  <option value="">Selecione…</option>
                  {veterinarios.map((vet) => (
                    <option key={`insumo_vet_${vet.id}`} value={vet.nome}>
                      {vet.nome}{vet.crmv ? ` • CRMV ${vet.crmv}` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <ProdutoEstoqueAutocomplete
                  selectedProduct={insumoRapidoSelecionado}
                  onSelect={setInsumoRapidoSelecionado}
                  helperText="Pesquise pelo nome ou código do insumo que foi consumido na internação."
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Quantidade utilizada *</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formInsumoRapido.quantidade_utilizada}
                  onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, quantidade_utilizada: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Desperdício / perda</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formInsumoRapido.quantidade_desperdicio}
                  onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, quantidade_desperdicio: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Horário do uso *</label>
                <input
                  type="datetime-local"
                  value={formInsumoRapido.horario_execucao}
                  onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, horario_execucao: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-medium text-gray-600">Observações</label>
                <textarea
                  value={formInsumoRapido.observacoes}
                  onChange={(e) => setFormInsumoRapido((prev) => ({ ...prev, observacoes: e.target.value }))}
                  rows={3}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="Ex.: trocado tapete, perdido 5 mL na manipulação, pet removeu curativo..."
                />
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setModalInsumoRapido(false)}
                className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmarInsumoRapido}
                disabled={salvando}
                className="flex-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
              >
                {salvando ? "Salvando..." : "Registrar insumo"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
