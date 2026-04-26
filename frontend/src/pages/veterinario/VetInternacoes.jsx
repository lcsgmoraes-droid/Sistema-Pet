import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle } from "lucide-react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import { buildReturnTo } from "../../utils/petReturnFlow";
import { useInternacaoOperacional } from "./useInternacaoOperacional";
import AgendaProcedimentosPanel from "./internacoes/AgendaProcedimentosPanel";
import AltaInternacaoModal from "./internacoes/AltaInternacaoModal";
import CentroInternacaoTabs from "./internacoes/CentroInternacaoTabs";
import ConcluirProcedimentoModal from "./internacoes/ConcluirProcedimentoModal";
import EvolucaoInternacaoModal from "./internacoes/EvolucaoInternacaoModal";
import HistoricoInternacoesFiltros from "./internacoes/HistoricoInternacoesFiltros";
import HistoricoInternacoesPetModal from "./internacoes/HistoricoInternacoesPetModal";
import InsumoRapidoInternacaoModal from "./internacoes/InsumoRapidoInternacaoModal";
import InternacoesHeader from "./internacoes/InternacoesHeader";
import InternacoesListaPanel from "./internacoes/InternacoesListaPanel";
import { InternacoesEmptyState, InternacoesLoadingState } from "./internacoes/InternacoesLoadingEmpty";
import InternacoesTabs from "./internacoes/InternacoesTabs";
import InternacoesWidgetPanel from "./internacoes/InternacoesWidgetPanel";
import MapaInternacaoPanel from "./internacoes/MapaInternacaoPanel";
import NovaInternacaoModal from "./internacoes/NovaInternacaoModal";
import {
  formatQuantity,
  parseQuantity,
} from "./internacoes/internacaoUtils";

const FORM_NOVA_INTERNACAO_INICIAL = {
  pessoa_id: "",
  pet_id: "",
  motivo: "",
  box: "",
  responsavel: "",
};

const FORM_EVOLUCAO_INICIAL = {
  temperatura: "",
  fc: "",
  fr: "",
  observacoes: "",
};

const AGENDA_FORM_INICIAL = {
  internacao_id: "",
  horario: "",
  medicamento: "",
  dose: "",
  quantidade_prevista: "",
  unidade_quantidade: "",
  via: "",
  lembrete_min: "30",
  observacoes: "",
};

const FORM_FEITO_INICIAL = {
  feito_por: "",
  horario_execucao: "",
  observacao_execucao: "",
  quantidade_prevista: "",
  quantidade_executada: "",
  quantidade_desperdicio: "",
  unidade_quantidade: "",
};

const FORM_INSUMO_RAPIDO_INICIAL = {
  internacao_id: "",
  responsavel: "",
  horario_execucao: "",
  quantidade_utilizada: "1",
  quantidade_desperdicio: "",
  observacoes: "",
};

export default function VetInternacoes() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const abrirNovaQuery = searchParams.get("abrir_nova") === "1";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";
  const [aba, setAba] = useState("ativas");
  const [centroAba, setCentroAba] = useState("widget");
  const [internacoes, setInternacoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [expandida, setExpandida] = useState(null);
  const [evolucoes, setEvolucoes] = useState({});
  const [procedimentosInternacao, setProcedimentosInternacao] = useState({});
  const [modalNova, setModalNova] = useState(false);
  const [modalAlta, setModalAlta] = useState(null);
  const [modalEvolucao, setModalEvolucao] = useState(null);
  const [modalHistoricoPet, setModalHistoricoPet] = useState(null);
  const [historicoPet, setHistoricoPet] = useState([]);
  const [carregandoHistoricoPet, setCarregandoHistoricoPet] = useState(false);
  const [pets, setPets] = useState([]);
  const [veterinarios, setVeterinarios] = useState([]);
  const [formNova, setFormNova] = useState(() => ({ ...FORM_NOVA_INTERNACAO_INICIAL }));
  const [tutorNovaSelecionado, setTutorNovaSelecionado] = useState(null);
  const [formAlta, setFormAlta] = useState("");
  const [formEvolucao, setFormEvolucao] = useState(() => ({ ...FORM_EVOLUCAO_INICIAL }));
  const [filtroDataAltaInicio, setFiltroDataAltaInicio] = useState("");
  const [filtroDataAltaFim, setFiltroDataAltaFim] = useState("");
  const [filtroPessoaHistorico, setFiltroPessoaHistorico] = useState("");
  const [filtroPetHistorico, setFiltroPetHistorico] = useState("");
  const [agendaForm, setAgendaForm] = useState(() => ({ ...AGENDA_FORM_INICIAL }));
  const [modalFeito, setModalFeito] = useState(null);
  const [formFeito, setFormFeito] = useState(() => ({ ...FORM_FEITO_INICIAL }));
  const [modalInsumoRapido, setModalInsumoRapido] = useState(false);
  const [insumoRapidoSelecionado, setInsumoRapidoSelecionado] = useState(null);
  const [formInsumoRapido, setFormInsumoRapido] = useState(() => ({ ...FORM_INSUMO_RAPIDO_INICIAL }));
  const [salvando, setSalvando] = useState(false);
  const {
    agendaCarregando,
    agendaProcedimentos,
    carregarAgendaProcedimentos,
    setAgendaProcedimentos,
    setTotalBaias,
    totalBaias,
  } = useInternacaoOperacional({ setErro });

  useEffect(() => {
    api.get("/pets", { params: { limit: 500 } })
      .then((res) => setPets(res.data?.items ?? res.data ?? []))
      .catch(() => {});

    vetApi.listarVeterinarios()
      .then((res) => setVeterinarios(Array.isArray(res.data) ? res.data : []))
      .catch(() => setVeterinarios([]));
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

  const pessoas = useMemo(() => {
    const mapa = new Map();
    for (const pet of pets) {
      if (!pet?.cliente_id) continue;
      if (mapa.has(String(pet.cliente_id))) continue;
      mapa.set(String(pet.cliente_id), {
        id: String(pet.cliente_id),
        nome: pet.cliente_nome ?? `Pessoa #${pet.cliente_id}`,
      });
    }
    return Array.from(mapa.values()).sort((a, b) => a.nome.localeCompare(b.nome));
  }, [pets]);

  const petsDaPessoa = useMemo(() => {
    if (!formNova.pessoa_id) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(formNova.pessoa_id) && pet.ativo !== false
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
      (pet) => String(pet.cliente_id) === String(filtroPessoaHistorico) && pet.ativo !== false
    );
  }, [pets, filtroPessoaHistorico]);

  const internacoesOrdenadas = useMemo(
    () => [...internacoes].sort((a, b) => new Date(b.data_entrada) - new Date(a.data_entrada)),
    [internacoes]
  );

  const ocupacaoPorBaia = useMemo(() => {
    const mapa = new Map();
    for (const internacao of internacoesOrdenadas) {
      const chave = (internacao.box || "").trim();
      if (!chave) continue;
      mapa.set(chave, internacao);
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
    const semBaia = internacoes.filter((internacao) => !internacao.box).length;
    const comEvolucao = internacoes.filter((internacao) => (evolucoes[internacao.id] ?? []).length > 0).length;
    const procedimentosPendentes = agendaProcedimentos.filter((procedimento) => !procedimento.feito).length;
    const procedimentosAtrasados = agendaProcedimentos.filter(
      (procedimento) => !procedimento.feito && new Date(procedimento.horario).getTime() <= Date.now()
    ).length;
    const mediaDias = total === 0
      ? 0
      : internacoes.reduce((acc, internacao) => {
          const dias = Math.max(
            0,
            Math.floor((Date.now() - new Date(internacao.data_entrada).getTime()) / 86400000)
          );
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

  const agendaOrdenada = useMemo(
    () => [...agendaProcedimentos].sort((a, b) => new Date(a.horario).getTime() - new Date(b.horario).getTime()),
    [agendaProcedimentos]
  );

  const internacaoPorId = useMemo(() => {
    const mapa = new Map();
    for (const internacao of internacoes) mapa.set(String(internacao.id), internacao);
    return mapa;
  }, [internacoes]);

  const internacaoSelecionadaAgenda = useMemo(() => {
    if (!agendaForm.internacao_id) return null;
    return internacaoPorId.get(String(agendaForm.internacao_id)) ?? null;
  }, [agendaForm.internacao_id, internacaoPorId]);

  const sugestaoHorario = useMemo(() => {
    const data = new Date();
    data.setMinutes(data.getMinutes() + 30);
    const pad = (value) => String(value).padStart(2, "0");
    return `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}T${pad(data.getHours())}:${pad(data.getMinutes())}`;
  }, []);

  useEffect(() => {
    setAgendaForm((prev) => (prev.horario ? prev : { ...prev, horario: sugestaoHorario }));
  }, [sugestaoHorario]);

  useEffect(() => {
    setFormInsumoRapido((prev) => (
      prev.horario_execucao ? prev : { ...prev, horario_execucao: sugestaoHorario }
    ));
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

  useEffect(() => {
    carregar();
  }, [carregar]);

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

  function abrirNovaInternacao() {
    setAba("ativas");
    setTutorNovaSelecionado(null);
    setFormNova({ ...FORM_NOVA_INTERNACAO_INICIAL });
    setModalNova(true);
  }

  function selecionarInternacaoNoMapa(internacaoId) {
    setAba("ativas");
    setCentroAba("lista");
    abrirDetalhe(internacaoId);
  }

  function selecionarPessoaHistorico(pessoaId) {
    setFiltroPessoaHistorico(pessoaId);
    setFiltroPetHistorico("");
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
      setFormNova({ ...FORM_NOVA_INTERNACAO_INICIAL });
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
      setFormEvolucao({ ...FORM_EVOLUCAO_INICIAL });
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
      const lembreteMin = Number.parseInt(agendaForm.lembrete_min || "30", 10);
      const response = await vetApi.criarProcedimentoAgendaInternacao(agendaForm.internacao_id, {
        horario_agendado: agendaForm.horario,
        medicamento: agendaForm.medicamento.trim(),
        dose: agendaForm.dose || undefined,
        quantidade_prevista: parseQuantity(agendaForm.quantidade_prevista) ?? undefined,
        unidade_quantidade: agendaForm.unidade_quantidade?.trim() || undefined,
        via: agendaForm.via || undefined,
        lembrete_min: Number.isFinite(lembreteMin) ? lembreteMin : 30,
        observacoes_agenda: agendaForm.observacoes || undefined,
      });

      if (response.data?.id) {
        setAgendaProcedimentos((prev) => [response.data, ...prev]);
      } else {
        await carregarAgendaProcedimentos();
      }
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
    const pad = (value) => String(value).padStart(2, "0");
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
      const response = await vetApi.concluirProcedimentoAgendaInternacao(modalFeito.id, {
        quantidade_prevista: parseQuantity(formFeito.quantidade_prevista) ?? undefined,
        quantidade_executada: parseQuantity(formFeito.quantidade_executada) ?? undefined,
        quantidade_desperdicio: parseQuantity(formFeito.quantidade_desperdicio) ?? undefined,
        unidade_quantidade: formFeito.unidade_quantidade?.trim() || undefined,
        executado_por: formFeito.feito_por.trim(),
        horario_execucao: formFeito.horario_execucao,
        observacao_execucao: formFeito.observacao_execucao?.trim() || undefined,
      });

      await carregarDetalheInternacao(
        modalFeito.internacao_id,
        String(expandida) === String(modalFeito.internacao_id)
      );

      setAgendaProcedimentos((prev) => prev.map((procedimento) => {
        if (String(procedimento.id) !== String(modalFeito.id)) return procedimento;
        return response.data?.id ? response.data : {
          ...procedimento,
          feito: true,
          status: "concluido",
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
      setFormFeito({ ...FORM_FEITO_INICIAL });
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
      ...FORM_INSUMO_RAPIDO_INICIAL,
      internacao_id: internacaoId ? String(internacaoId) : "",
      horario_execucao: sugestaoHorario,
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
        ...FORM_INSUMO_RAPIDO_INICIAL,
        horario_execucao: sugestaoHorario,
      });
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao lançar insumo rápido.");
    } finally {
      setSalvando(false);
    }
  }

  function reabrirProcedimento() {
    setErro("Procedimento concluído já faz parte do histórico clínico. Para corrigir, registre um novo ajuste/evolução.");
  }

  async function removerProcedimentoAgenda(id) {
    setSalvando(true);
    try {
      await vetApi.removerProcedimentoAgendaInternacao(id);
      setAgendaProcedimentos((prev) => prev.filter((procedimento) => String(procedimento.id) !== String(id)));
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao remover procedimento da agenda.");
    } finally {
      setSalvando(false);
    }
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

  function fecharModalNovaInternacao() {
    setModalNova(false);
    if (!consultaIdQuery) {
      setTutorNovaSelecionado(null);
      setFormNova({ ...FORM_NOVA_INTERNACAO_INICIAL });
    }
  }

  return (
    <div className="p-6 space-y-5">
      <InternacoesHeader onNovaInternacao={abrirNovaInternacao} />

      <InternacoesTabs aba={aba} onChangeAba={setAba} />

      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
          <AlertCircle size={16} />
          <span>{erro}</span>
          <button type="button" className="ml-auto" onClick={() => setErro(null)} aria-label="Fechar alerta">
            x
          </button>
        </div>
      )}

      {aba === "historico" && (
        <HistoricoInternacoesFiltros
          pessoas={pessoas}
          petsHistoricoDaPessoa={petsHistoricoDaPessoa}
          filtroDataAltaInicio={filtroDataAltaInicio}
          filtroDataAltaFim={filtroDataAltaFim}
          filtroPessoaHistorico={filtroPessoaHistorico}
          filtroPetHistorico={filtroPetHistorico}
          onChangeDataAltaInicio={setFiltroDataAltaInicio}
          onChangeDataAltaFim={setFiltroDataAltaFim}
          onChangePessoaHistorico={selecionarPessoaHistorico}
          onChangePetHistorico={setFiltroPetHistorico}
        />
      )}

      {carregando ? (
        <InternacoesLoadingState />
      ) : internacoes.length === 0 ? (
        <InternacoesEmptyState aba={aba} />
      ) : (
        <div className="space-y-3">
          {aba === "ativas" && (
            <CentroInternacaoTabs
              centroAba={centroAba}
              onChangeCentroAba={setCentroAba}
            />
          )}

          {aba === "ativas" && centroAba === "mapa" && (
            <MapaInternacaoPanel
              mapaInternacao={mapaInternacao}
              totalBaias={totalBaias}
              setTotalBaias={setTotalBaias}
              onSelecionarInternacao={selecionarInternacaoNoMapa}
            />
          )}

          {(aba === "historico" || (aba === "ativas" && centroAba === "lista")) && (
            <InternacoesListaPanel
              aba={aba}
              internacoesOrdenadas={internacoesOrdenadas}
              expandida={expandida}
              evolucoes={evolucoes}
              procedimentosInternacao={procedimentosInternacao}
              onAbrirDetalhe={abrirDetalhe}
              onAbrirInsumoRapido={abrirModalInsumoRapido}
              onAbrirEvolucao={setModalEvolucao}
              onAbrirAlta={setModalAlta}
              onAbrirFichaPet={(petId) => navigate(`/pets/${petId}`)}
              onAbrirHistoricoPet={abrirHistoricoPet}
            />
          )}

          {aba === "ativas" && centroAba === "widget" && (
            <InternacoesWidgetPanel
              indicadoresInternacao={indicadoresInternacao}
              internacoesOrdenadas={internacoesOrdenadas}
            />
          )}

          {aba === "ativas" && centroAba === "agenda" && (
            <AgendaProcedimentosPanel
              agendaForm={agendaForm}
              setAgendaForm={setAgendaForm}
              internacoesOrdenadas={internacoesOrdenadas}
              internacaoSelecionadaAgenda={internacaoSelecionadaAgenda}
              agendaCarregando={agendaCarregando}
              agendaOrdenada={agendaOrdenada}
              internacaoPorId={internacaoPorId}
              salvando={salvando}
              onAdicionarProcedimentoAgenda={adicionarProcedimentoAgenda}
              onAbrirInsumoRapido={abrirModalInsumoRapido}
              onReabrirProcedimento={reabrirProcedimento}
              onAbrirModalFeito={abrirModalFeito}
              onRemoverProcedimentoAgenda={removerProcedimentoAgenda}
            />
          )}
        </div>
      )}

      <NovaInternacaoModal
        isOpen={modalNova}
        consultaIdQuery={consultaIdQuery}
        tutorNovaSelecionado={tutorNovaSelecionado}
        setTutorNovaSelecionado={setTutorNovaSelecionado}
        formNova={formNova}
        setFormNova={setFormNova}
        tutorAtualInternacao={tutorAtualInternacao}
        retornoNovoPet={retornoNovoPet}
        petsDaPessoa={petsDaPessoa}
        mapaInternacao={mapaInternacao}
        totalBaias={totalBaias}
        setTotalBaias={setTotalBaias}
        onClose={fecharModalNovaInternacao}
        onHideForNovoPet={() => setModalNova(false)}
        onConfirm={criarInternacao}
        salvando={salvando}
      />

      <AltaInternacaoModal
        isOpen={Boolean(modalAlta)}
        formAlta={formAlta}
        setFormAlta={setFormAlta}
        onClose={() => setModalAlta(null)}
        onConfirm={darAlta}
        salvando={salvando}
      />

      <EvolucaoInternacaoModal
        isOpen={Boolean(modalEvolucao)}
        formEvolucao={formEvolucao}
        setFormEvolucao={setFormEvolucao}
        onClose={() => setModalEvolucao(null)}
        onConfirm={registrarEvolucao}
        salvando={salvando}
      />

      <ConcluirProcedimentoModal
        procedimento={modalFeito}
        baiaExibicao={
          modalFeito
            ? (internacaoPorId.get(String(modalFeito.internacao_id))?.box || modalFeito.baia || "Sem baia")
            : "Sem baia"
        }
        formFeito={formFeito}
        setFormFeito={setFormFeito}
        veterinarios={veterinarios}
        onClose={() => setModalFeito(null)}
        onConfirm={confirmarProcedimentoFeito}
        salvando={salvando}
      />

      <HistoricoInternacoesPetModal
        historicoPetInfo={modalHistoricoPet}
        historicoPet={historicoPet}
        carregando={carregandoHistoricoPet}
        onClose={() => setModalHistoricoPet(null)}
      />

      <InsumoRapidoInternacaoModal
        isOpen={modalInsumoRapido}
        onClose={() => setModalInsumoRapido(false)}
        formInsumoRapido={formInsumoRapido}
        setFormInsumoRapido={setFormInsumoRapido}
        internacoesOrdenadas={internacoesOrdenadas}
        veterinarios={veterinarios}
        insumoRapidoSelecionado={insumoRapidoSelecionado}
        setInsumoRapidoSelecionado={setInsumoRapidoSelecionado}
        onConfirm={confirmarInsumoRapido}
        salvando={salvando}
      />
    </div>
  );
}
