import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Download,
  Link2,
  Plus,
} from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import { buildReturnTo } from "../../utils/petReturnFlow";
import AgendaDiasView from "./agenda/AgendaDiasView";
import AgendaMesView from "./agenda/AgendaMesView";
import GerenciarAgendamentoModal from "./agenda/GerenciarAgendamentoModal";
import NovoAgendamentoModal from "./agenda/NovoAgendamentoModal";
import {
  FORM_NOVO_INICIAL,
  HORARIOS_BASE,
  TIPO_ACAO,
  TIPO_LABEL,
  TIPO_OPTIONS,
  addDias,
  fimMes,
  inicioDaGradeMensal,
  inicioMes,
  isoDate,
  normalizarTipoAgendamento,
} from "./agenda/agendaUtils";

export default function VetAgenda() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const abrirNovoQuery = searchParams.get("abrir_novo") === "1";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";
  const [dataRef, setDataRef] = useState(new Date());
  const [modo, setModo] = useState("dia");
  const [agendamentos, setAgendamentos] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [novoAberto, setNovoAberto] = useState(false);
  const [veterinarios, setVeterinarios] = useState([]);
  const [consultorios, setConsultorios] = useState([]);
  const [tutorSelecionado, setTutorSelecionado] = useState(null);
  const [petsDoTutor, setPetsDoTutor] = useState([]);
  const [carregandoPetsTutor, setCarregandoPetsTutor] = useState(false);
  const [formNovo, setFormNovo] = useState(FORM_NOVO_INICIAL);
  const [erroNovo, setErroNovo] = useState(null);
  const [salvandoNovo, setSalvandoNovo] = useState(false);
  const [agendaDiaModal, setAgendaDiaModal] = useState([]);
  const [carregandoAgendaDiaModal, setCarregandoAgendaDiaModal] = useState(false);
  const [abrindoAgendamentoId, setAbrindoAgendamentoId] = useState(null);
  const [processandoAgendamentoId, setProcessandoAgendamentoId] = useState(null);
  const [agendamentoSelecionado, setAgendamentoSelecionado] = useState(null);
  const [agendamentoEditandoId, setAgendamentoEditandoId] = useState(null);
  const [calendarioMeta, setCalendarioMeta] = useState(null);
  const [carregandoCalendario, setCarregandoCalendario] = useState(false);
  const [mensagemCalendario, setMensagemCalendario] = useState("");

  const inicioSemana =
    modo === "semana" || modo === "mes" ? addDias(dataRef, -dataRef.getDay()) : dataRef;
  const fimSemana = modo === "semana" || modo === "mes" ? addDias(inicioSemana, 6) : dataRef;

  async function carregar() {
    const dataInicioConsulta = modo === "mes" ? inicioMes(dataRef) : inicioSemana;
    const dataFimConsulta = modo === "mes" ? fimMes(dataRef) : fimSemana;

    try {
      setCarregando(true);
      setErro(null);
      const res = await vetApi.listarAgendamentos({
        data_inicio: isoDate(dataInicioConsulta),
        data_fim: isoDate(dataFimConsulta),
      });
      const data = res.data;
      setAgendamentos(Array.isArray(data) ? data : data.items ?? []);
    } catch {
      setErro("Erro ao carregar agenda.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, [modo, dataRef]);

  useEffect(() => {
    if (!abrirNovoQuery) return;
    setNovoAberto(true);
  }, [abrirNovoQuery]);

  useEffect(() => {
    let ativo = true;

    async function carregarApoiosAgenda() {
      try {
        const [veterinariosRes, consultoriosRes] = await Promise.all([
          vetApi.listarVeterinarios(),
          vetApi.listarConsultorios({ ativos_only: true }),
        ]);
        if (!ativo) return;
        setVeterinarios(Array.isArray(veterinariosRes.data) ? veterinariosRes.data : []);
        setConsultorios(Array.isArray(consultoriosRes.data) ? consultoriosRes.data : []);
      } catch {
        if (!ativo) return;
        setVeterinarios([]);
        setConsultorios([]);
      }
    }

    carregarApoiosAgenda();

    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    let ativo = true;

    async function carregarCalendarioAgenda() {
      try {
        setCarregandoCalendario(true);
        const res = await vetApi.obterCalendarioAgendaMeta();
        if (!ativo) return;
        setCalendarioMeta(res.data || null);
      } catch {
        if (!ativo) return;
        setCalendarioMeta(null);
      } finally {
        if (ativo) {
          setCarregandoCalendario(false);
        }
      }
    }

    carregarCalendarioAgenda();

    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    if (!novoAberto || !tutorIdQuery) return;
    setTutorSelecionado((prev) => {
      if (prev?.id && String(prev.id) === String(tutorIdQuery)) {
        return prev;
      }
      return {
        id: String(tutorIdQuery),
        nome: tutorNomeQuery || `Tutor #${tutorIdQuery}`,
      };
    });
  }, [novoAberto, tutorIdQuery, tutorNomeQuery]);

  useEffect(() => {
    if (!novoAberto || !tutorSelecionado?.id) {
      setPetsDoTutor([]);
      setCarregandoPetsTutor(false);
      return;
    }

    let ativo = true;

    async function carregarPetsTutor() {
      try {
        setCarregandoPetsTutor(true);
        const resposta = await api.get("/vet/pets", {
          params: {
            cliente_id: tutorSelecionado.id,
            limit: 100,
          },
        });
        if (!ativo) return;
        const lista = resposta.data?.items ?? resposta.data ?? [];
        setPetsDoTutor(Array.isArray(lista) ? lista : []);
      } catch {
        if (!ativo) return;
        setPetsDoTutor([]);
      } finally {
        if (ativo) {
          setCarregandoPetsTutor(false);
        }
      }
    }

    carregarPetsTutor();

    return () => {
      ativo = false;
    };
  }, [novoAberto, tutorSelecionado?.id]);

  useEffect(() => {
    if (!novoAberto || !novoPetIdQuery || !petsDoTutor.length) return;
    const petNovo = petsDoTutor.find((pet) => String(pet.id) === String(novoPetIdQuery));
    if (!petNovo) return;
    setFormNovo((prev) => ({ ...prev, pet_id: String(petNovo.id) }));
  }, [novoAberto, novoPetIdQuery, petsDoTutor]);

  useEffect(() => {
    if (!novoAberto || !formNovo.data) {
      setAgendaDiaModal([]);
      setCarregandoAgendaDiaModal(false);
      return;
    }

    let ativo = true;

    async function carregarAgendaDiaModal() {
      try {
        setCarregandoAgendaDiaModal(true);
        const resposta = await vetApi.listarAgendamentos({
          data_inicio: formNovo.data,
          data_fim: formNovo.data,
        });
        if (!ativo) return;
        const lista = resposta.data?.items ?? resposta.data ?? [];
        const ordenados = (Array.isArray(lista) ? lista : []).sort((a, b) =>
          String(a.data_hora || "").localeCompare(String(b.data_hora || ""))
        );
        setAgendaDiaModal(ordenados);
      } catch {
        if (!ativo) return;
        setAgendaDiaModal([]);
      } finally {
        if (ativo) {
          setCarregandoAgendaDiaModal(false);
        }
      }
    }

    carregarAgendaDiaModal();

    return () => {
      ativo = false;
    };
  }, [novoAberto, formNovo.data]);

  function nav(direcao) {
    if (modo === "mes") {
      setDataRef((d) => new Date(d.getFullYear(), d.getMonth() + direcao, 1));
      return;
    }
    const delta = modo === "dia" ? 1 : 7;
    setDataRef((d) => addDias(d, direcao * delta));
  }

  function formatTitulo() {
    if (modo === "dia") {
      return dataRef.toLocaleDateString("pt-BR", {
        weekday: "long",
        day: "2-digit",
        month: "long",
        year: "numeric",
      });
    }
    if (modo === "mes") {
      return dataRef.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
    }
    return `${inicioSemana.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "short",
    })} - ${fimSemana.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    })}`;
  }

  function agsDia(data) {
    const key = isoDate(data);
    return agendamentos
      .filter((a) => (a.data_hora ?? "").startsWith(key))
      .sort((a, b) => (a.data_hora ?? "").localeCompare(b.data_hora ?? ""));
  }

  function sugerirHoraLivre(data) {
    const ocupados = new Set(
      agsDia(data)
        .filter((ag) => ag.status !== "cancelado")
        .map((ag) => String(ag.data_hora || "").slice(11, 16))
        .filter(Boolean)
    );
    return HORARIOS_BASE.find((horario) => !ocupados.has(horario)) || "09:00";
  }

  function abrirModalNovo(dataBase = dataRef, agendamentoBase = null) {
    setErro(null);
    setErroNovo(null);
    setAgendamentoSelecionado(null);
    setNovoAberto(true);

    if (agendamentoBase) {
      const dataHoraTexto = String(agendamentoBase.data_hora || "");
      setAgendamentoEditandoId(agendamentoBase.id);
      setTutorSelecionado({
        id: agendamentoBase.cliente_id,
        nome: agendamentoBase.cliente_nome || `Tutor #${agendamentoBase.cliente_id}`,
      });
      setFormNovo({
        pet_id: String(agendamentoBase.pet_id || ""),
        veterinario_id: String(agendamentoBase.veterinario_id || ""),
        consultorio_id: String(agendamentoBase.consultorio_id || ""),
        tipo: normalizarTipoAgendamento(agendamentoBase.tipo),
        data: dataHoraTexto.slice(0, 10) || isoDate(dataBase),
        hora: dataHoraTexto.slice(11, 16) || sugerirHoraLivre(dataBase),
        motivo: agendamentoBase.motivo || "",
        emergencia: Boolean(agendamentoBase.is_emergencia),
      });
      return;
    }

    setAgendamentoEditandoId(null);
    setTutorSelecionado(null);
    setPetsDoTutor([]);
    setFormNovo({
      ...FORM_NOVO_INICIAL,
      data: isoDate(dataBase),
      hora: sugerirHoraLivre(dataBase),
    });
  }

  async function criarAgendamento() {
    if (!formNovo.pet_id || !formNovo.data || !formNovo.hora) return;
    if (bloqueioCamposAgendamento.veterinario || bloqueioCamposAgendamento.consultorio || conflitoHorarioSelecionado) {
      return;
    }
    setSalvandoNovo(true);
    setErroNovo(null);
    try {
      const payload = {
        pet_id: Number(formNovo.pet_id),
        cliente_id: tutorSelecionado?.id || petSelecionadoModal?.cliente_id,
        veterinario_id: formNovo.veterinario_id ? Number(formNovo.veterinario_id) : undefined,
        consultorio_id: formNovo.consultorio_id ? Number(formNovo.consultorio_id) : undefined,
        data_hora: `${formNovo.data}T${formNovo.hora}`,
        tipo: normalizarTipoAgendamento(formNovo.tipo),
        motivo: formNovo.motivo || undefined,
        is_emergencia: formNovo.emergencia,
      };

      if (agendamentoEditandoId) {
        await vetApi.atualizarAgendamento(agendamentoEditandoId, payload);
      } else {
        await vetApi.criarAgendamento(payload);
      }
      setNovoAberto(false);
      setAgendamentoEditandoId(null);
      setTutorSelecionado(null);
      setPetsDoTutor([]);
      setAgendaDiaModal([]);
      setFormNovo(FORM_NOVO_INICIAL);
      await carregar();
    } catch (e) {
      setErroNovo(e?.response?.data?.detail ?? "Erro ao criar agendamento.");
    } finally {
      setSalvandoNovo(false);
    }
  }

  function fecharModalNovo() {
    setNovoAberto(false);
    setErroNovo(null);
    setAgendamentoEditandoId(null);
    setTutorSelecionado(null);
    setPetsDoTutor([]);
    setAgendaDiaModal([]);
    setFormNovo(FORM_NOVO_INICIAL);
  }

  function abrirConfiguracoesVet() {
    setNovoAberto(false);
    navigate("/veterinario/configuracoes");
  }

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search, { abrir_novo: "1" }),
    [location.pathname, location.search]
  );

  async function baixarCalendarioAgenda() {
    try {
      setMensagemCalendario("");
      const resposta = await vetApi.baixarCalendarioAgendaIcs();
      const blob = new Blob([resposta.data], { type: "text/calendar;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "agenda-veterinaria.ics";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch {
      setMensagemCalendario("Nao foi possivel baixar o calendario agora.");
    }
  }

  async function copiarLinkCalendario() {
    if (!calendarioMeta?.feed_url) return;
    try {
      await navigator.clipboard.writeText(calendarioMeta.feed_url);
      setMensagemCalendario("Link privado copiado. Agora voce pode assinar no calendario do celular.");
    } catch {
      setMensagemCalendario("Nao foi possivel copiar o link automaticamente.");
    }
  }

  const diasVisiveis =
    modo === "semana" ? Array.from({ length: 7 }, (_, i) => addDias(inicioSemana, i)) : [dataRef];

  const diasMes =
    modo === "mes"
      ? Array.from({ length: 42 }, (_, i) => addDias(inicioDaGradeMensal(dataRef), i))
      : [];

  const horariosAgendaModal = useMemo(() => {
    const ocupados = new Map();
    for (const ag of agendaDiaModal) {
      if (ag.status === "cancelado") continue;
      const hora = String(ag.data_hora || "").slice(11, 16);
      if (!hora) continue;
      const atual = ocupados.get(hora) || [];
      atual.push(ag);
      ocupados.set(hora, atual);
    }

    return HORARIOS_BASE.map((horario) => ({
      horario,
      ocupados: ocupados.get(horario) || [],
      livre: !ocupados.has(horario),
    }));
  }, [agendaDiaModal]);

  const petSelecionadoModal = useMemo(
    () => petsDoTutor.find((pet) => String(pet.id) === String(formNovo.pet_id)) || null,
    [petsDoTutor, formNovo.pet_id]
  );

  const veterinarioSelecionadoModal = useMemo(
    () => veterinarios.find((vet) => String(vet.id) === String(formNovo.veterinario_id)) || null,
    [veterinarios, formNovo.veterinario_id]
  );

  const consultorioSelecionadoModal = useMemo(
    () => consultorios.find((item) => String(item.id) === String(formNovo.consultorio_id)) || null,
    [consultorios, formNovo.consultorio_id]
  );

  const diagnosticoConflitoSelecionado = useMemo(() => {
    if (!formNovo.hora) {
      return {
        conflitosVeterinario: [],
        conflitosConsultorio: [],
        outrosNoHorario: [],
      };
    }

    const ocupadosMesmoHorario = agendaDiaModal.filter((ag) => {
      if (ag.status === "cancelado") return false;
      if (agendamentoEditandoId && Number(ag.id) === Number(agendamentoEditandoId)) return false;
      return String(ag.data_hora || "").slice(11, 16) === formNovo.hora;
    });

    const conflitosVeterinario = formNovo.veterinario_id
      ? ocupadosMesmoHorario.filter(
          (ag) => String(ag.veterinario_id || "") === String(formNovo.veterinario_id)
        )
      : [];

    const conflitosConsultorio = formNovo.consultorio_id
      ? ocupadosMesmoHorario.filter(
          (ag) => String(ag.consultorio_id || "") === String(formNovo.consultorio_id)
        )
      : [];

    return {
      conflitosVeterinario,
      conflitosConsultorio,
      outrosNoHorario: ocupadosMesmoHorario,
    };
  }, [agendaDiaModal, agendamentoEditandoId, formNovo.hora, formNovo.veterinario_id, formNovo.consultorio_id]);

  const conflitoHorarioSelecionado =
    diagnosticoConflitoSelecionado.conflitosVeterinario.length > 0 ||
    diagnosticoConflitoSelecionado.conflitosConsultorio.length > 0;

  const tipoSelecionado = normalizarTipoAgendamento(formNovo.tipo);
  const dicaTipoSelecionado =
    TIPO_OPTIONS.find((item) => item.value === tipoSelecionado)?.hint ||
    "Escolha o fluxo para o proximo passo operacional.";

  const motivoPlaceholderPorTipo = {
    consulta: "Ex: Consulta dermatologica, retorno clinico...",
    retorno: "Ex: Retorno pos-cirurgico, reavaliacao...",
    vacina: "Ex: V10 anual, antirrabica...",
    exame: "Ex: Hemograma, ultrassom, bioquimico...",
  };

  const tipoAgendamentoSelecionado = agendamentoSelecionado
    ? normalizarTipoAgendamento(agendamentoSelecionado.tipo)
    : "consulta";

  const podeExcluirAgendamento =
    agendamentoSelecionado &&
    !agendamentoSelecionado.consulta_id &&
    agendamentoSelecionado.status !== "finalizado";

  const podeVoltarStatus =
    agendamentoSelecionado &&
    (agendamentoSelecionado.status === "em_atendimento" || Boolean(agendamentoSelecionado.consulta_id));

  const labelVoltarStatus = agendamentoSelecionado?.consulta_id
    ? "Desfazer inicio do atendimento"
    : "Voltar para agendado";

  const labelAbrirAgendamentoSelecionado = agendamentoSelecionado?.consulta_id
    ? "Continuar atendimento"
    : TIPO_ACAO[tipoAgendamentoSelecionado] ?? "Abrir atendimento";

  const mensagemAgendamentoSelecionado = agendamentoSelecionado
    ? agendamentoSelecionado.status === "em_atendimento"
      ? "Esse agendamento ja esta em atendimento. Voce pode continuar, editar ou desfazer o inicio se foi aberto por engano."
      : `Deseja iniciar o fluxo de ${TIPO_LABEL[tipoAgendamentoSelecionado] ?? "Consulta"} agora?`
    : "";

  const bloqueioCamposAgendamento = {
    veterinario: veterinarios.length > 0 && !formNovo.veterinario_id,
    consultorio: consultorios.length > 0 && !formNovo.consultorio_id,
  };

  function abrirGerenciarAgendamento(ag) {
    setErro(null);
    setAgendamentoSelecionado(ag);
  }

  function fecharGerenciarAgendamento() {
    setAgendamentoSelecionado(null);
  }

  async function abrirFluxoAgendamento(ag) {
    if (!ag?.id) return;
    const tipoAgendamento = normalizarTipoAgendamento(ag.tipo);
    setErro(null);
    setErroNovo(null);
    setAbrindoAgendamentoId(ag.id);

    try {
      if (ag.consulta_id) {
        if (ag.status !== "em_atendimento" && ag.status !== "finalizado") {
          await vetApi.atualizarAgendamento(ag.id, { status: "em_atendimento" });
          await carregar();
        }
        navigate(`/veterinario/consultas/${ag.consulta_id}`);
        return;
      }

      if (tipoAgendamento === "consulta" || tipoAgendamento === "retorno") {
        const res = await vetApi.criarConsulta({
          pet_id: ag.pet_id,
          cliente_id: ag.cliente_id,
          veterinario_id: ag.veterinario_id || undefined,
          tipo: tipoAgendamento,
          agendamento_id: ag.id,
          queixa_principal: ag.motivo || undefined,
        });
        await carregar();
        navigate(`/veterinario/consultas/${res.data.id}`);
        return;
      }

      if (tipoAgendamento === "vacina") {
        navigate(`/veterinario/vacinas?pet_id=${ag.pet_id}&acao=novo&agendamento_id=${ag.id}`);
        return;
      }

      if (tipoAgendamento === "exame") {
        navigate(`/veterinario/exames?pet_id=${ag.pet_id}&acao=novo&agendamento_id=${ag.id}`);
        return;
      }

      navigate(`/veterinario/consultas/nova?pet_id=${ag.pet_id}`);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Nao foi possivel abrir o fluxo deste agendamento.");
    } finally {
      setAbrindoAgendamentoId(null);
    }
  }

  async function iniciarAgendamentoSelecionado() {
    if (!agendamentoSelecionado) return;
    const ag = agendamentoSelecionado;
    setAgendamentoSelecionado(null);
    await abrirFluxoAgendamento(ag);
  }

  async function voltarStatusAgendamento() {
    if (!agendamentoSelecionado?.id) return;
    setProcessandoAgendamentoId(agendamentoSelecionado.id);
    setErro(null);
    try {
      const res = await vetApi.desfazerInicioAgendamento(agendamentoSelecionado.id);
      setAgendamentoSelecionado(res.data);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Nao foi possivel desfazer o inicio do atendimento.");
    } finally {
      setProcessandoAgendamentoId(null);
    }
  }

  async function excluirAgendamentoSelecionado() {
    if (!agendamentoSelecionado?.id) return;
    const confirmado = window.confirm("Deseja excluir este agendamento?");
    if (!confirmado) return;
    setProcessandoAgendamentoId(agendamentoSelecionado.id);
    setErro(null);
    try {
      await vetApi.removerAgendamento(agendamentoSelecionado.id);
      setAgendamentoSelecionado(null);
      await carregar();
    } catch (e) {
      setErro(
        e?.response?.data?.detail ||
          "Nao foi possivel excluir o agendamento. Se ele ja gerou atendimento, desfaca o inicio primeiro."
      );
    } finally {
      setProcessandoAgendamentoId(null);
    }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-blue-100 p-2">
            <Calendar size={22} className="text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Agenda</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex overflow-hidden rounded-lg border border-gray-200 text-sm">
            <button
              onClick={() => setModo("dia")}
              className={`px-3 py-1.5 ${modo === "dia" ? "bg-blue-600 text-white" : "hover:bg-gray-50"}`}
            >
              Dia
            </button>
            <button
              onClick={() => setModo("semana")}
              className={`px-3 py-1.5 ${modo === "semana" ? "bg-blue-600 text-white" : "hover:bg-gray-50"}`}
            >
              Semana
            </button>
            <button
              onClick={() => setModo("mes")}
              className={`px-3 py-1.5 ${modo === "mes" ? "bg-blue-600 text-white" : "hover:bg-gray-50"}`}
            >
              Mes
            </button>
          </div>
          <button
            onClick={() => abrirModalNovo(dataRef)}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            <Plus size={15} />
            Agendar
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3">
        <button onClick={() => nav(-1)} className="rounded-full p-1 hover:bg-gray-100">
          <ChevronLeft size={18} className="text-gray-600" />
        </button>
        <button
          onClick={() => setDataRef(new Date())}
          className="flex-1 text-center text-sm font-medium capitalize text-gray-700"
        >
          {formatTitulo()}
        </button>
        <button onClick={() => nav(1)} className="rounded-full p-1 hover:bg-gray-100">
          <ChevronRight size={18} className="text-gray-600" />
        </button>
      </div>

      {erro && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      <div className="rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-cyan-900">Agenda no celular</h2>
            <p className="mt-1 text-sm text-cyan-800">
              Assine sua agenda veterinaria no calendario do celular com um link privado ou baixe um arquivo .ics.
            </p>
            {calendarioMeta?.mensagem_escopo && (
              <p className="mt-2 text-xs text-cyan-700">{calendarioMeta.mensagem_escopo}</p>
            )}
            {mensagemCalendario && (
              <p className="mt-2 text-xs font-medium text-cyan-700">{mensagemCalendario}</p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={baixarCalendarioAgenda}
              className="inline-flex items-center gap-2 rounded-lg border border-cyan-300 bg-white px-3 py-2 text-sm font-medium text-cyan-800 hover:bg-cyan-100"
            >
              <Download size={14} />
              Baixar .ics
            </button>
            <button
              type="button"
              onClick={copiarLinkCalendario}
              disabled={carregandoCalendario || !calendarioMeta?.feed_url}
              className="inline-flex items-center gap-2 rounded-lg border border-cyan-300 bg-white px-3 py-2 text-sm font-medium text-cyan-800 hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Link2 size={14} />
              Copiar link privado
            </button>
          </div>
        </div>
      </div>

      {carregando ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-500" />
        </div>
      ) : modo === "mes" ? (
        <AgendaMesView
          diasMes={diasMes}
          dataRef={dataRef}
          agsDia={agsDia}
          abrindoAgendamentoId={abrindoAgendamentoId}
          onAbrirNovo={abrirModalNovo}
          onGerenciarAgendamento={abrirGerenciarAgendamento}
        />
      ) : (
        <AgendaDiasView
          modo={modo}
          diasVisiveis={diasVisiveis}
          agsDia={agsDia}
          abrindoAgendamentoId={abrindoAgendamentoId}
          onAbrirNovo={abrirModalNovo}
          onGerenciarAgendamento={abrirGerenciarAgendamento}
        />
      )}

      <GerenciarAgendamentoModal
        agendamento={agendamentoSelecionado}
        tipoAgendamento={tipoAgendamentoSelecionado}
        mensagem={mensagemAgendamentoSelecionado}
        podeVoltarStatus={podeVoltarStatus}
        labelVoltarStatus={labelVoltarStatus}
        podeExcluir={podeExcluirAgendamento}
        labelAbrir={labelAbrirAgendamentoSelecionado}
        abrindoAgendamentoId={abrindoAgendamentoId}
        processandoAgendamentoId={processandoAgendamentoId}
        onClose={fecharGerenciarAgendamento}
        onEdit={() => abrirModalNovo(new Date(agendamentoSelecionado.data_hora), agendamentoSelecionado)}
        onVoltarStatus={voltarStatusAgendamento}
        onExcluir={excluirAgendamentoSelecionado}
        onIniciar={iniciarAgendamentoSelecionado}
      />

      <NovoAgendamentoModal
        isOpen={novoAberto}
        agendamentoEditandoId={agendamentoEditandoId}
        erroNovo={erroNovo}
        tutorSelecionado={tutorSelecionado}
        formNovo={formNovo}
        setFormNovo={setFormNovo}
        petsDoTutor={petsDoTutor}
        carregandoPetsTutor={carregandoPetsTutor}
        retornoNovoPet={retornoNovoPet}
        veterinarios={veterinarios}
        consultorios={consultorios}
        dicaTipoSelecionado={dicaTipoSelecionado}
        tipoSelecionado={tipoSelecionado}
        motivoPlaceholderPorTipo={motivoPlaceholderPorTipo}
        conflitoHorarioSelecionado={conflitoHorarioSelecionado}
        diagnosticoConflitoSelecionado={diagnosticoConflitoSelecionado}
        veterinarioSelecionadoModal={veterinarioSelecionadoModal}
        consultorioSelecionadoModal={consultorioSelecionadoModal}
        agendaDiaModal={agendaDiaModal}
        horariosAgendaModal={horariosAgendaModal}
        carregandoAgendaDiaModal={carregandoAgendaDiaModal}
        abrindoAgendamentoId={abrindoAgendamentoId}
        salvandoNovo={salvandoNovo}
        bloqueioCamposAgendamento={bloqueioCamposAgendamento}
        onClose={fecharModalNovo}
        onTutorSelect={(tutor) => {
          setTutorSelecionado(tutor);
          setPetsDoTutor([]);
          setFormNovo((prev) => ({ ...prev, pet_id: "" }));
        }}
        onHideForNovoPet={() => setNovoAberto(false)}
        onConfiguracoesVet={abrirConfiguracoesVet}
        onOpenAgendamento={abrirGerenciarAgendamento}
        onConfirm={criarAgendamento}
      />
    </div>
  );
}
