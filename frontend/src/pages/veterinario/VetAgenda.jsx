import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import { buildReturnTo } from "../../utils/petReturnFlow";
import AgendaCalendarioCard from "./agenda/AgendaCalendarioCard";
import AgendaConteudo from "./agenda/AgendaConteudo";
import AgendaHeader from "./agenda/AgendaHeader";
import AgendaPeriodoNav from "./agenda/AgendaPeriodoNav";
import GerenciarAgendamentoModal from "./agenda/GerenciarAgendamentoModal";
import NovoAgendamentoModal from "./agenda/NovoAgendamentoModal";
import {
  FORM_NOVO_INICIAL,
  TIPO_ACAO,
  addDias,
  fimMes,
  inicioMes,
  isoDate,
  normalizarTipoAgendamento,
} from "./agenda/agendaUtils";
import {
  MOTIVO_PLACEHOLDER_POR_TIPO,
  diagnosticarConflitoAgendamento,
  formatTituloAgenda,
  listarAgendamentosDia,
  montarDiasMes,
  montarDiasVisiveis,
  montarHorariosAgendaModal,
  montarMensagemGerenciamento,
  obterDicaTipoAgendamento,
  sugerirHoraLivreAgenda,
} from "./agenda/agendaFormUtils";

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

  function agsDia(data) {
    return listarAgendamentosDia(agendamentos, data);
  }

  function sugerirHoraLivre(data) {
    return sugerirHoraLivreAgenda(agsDia(data));
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

  const tituloAgenda = formatTituloAgenda(modo, dataRef, inicioSemana, fimSemana);
  const diasVisiveis = montarDiasVisiveis(modo, dataRef, inicioSemana);
  const diasMes = montarDiasMes(modo, dataRef);

  const horariosAgendaModal = useMemo(() => {
    return montarHorariosAgendaModal(agendaDiaModal);
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
    return diagnosticarConflitoAgendamento({
      agendaDiaModal,
      agendamentoEditandoId,
      hora: formNovo.hora,
      veterinarioId: formNovo.veterinario_id,
      consultorioId: formNovo.consultorio_id,
    });
  }, [agendaDiaModal, agendamentoEditandoId, formNovo.hora, formNovo.veterinario_id, formNovo.consultorio_id]);

  const conflitoHorarioSelecionado =
    diagnosticoConflitoSelecionado.conflitosVeterinario.length > 0 ||
    diagnosticoConflitoSelecionado.conflitosConsultorio.length > 0;

  const tipoSelecionado = normalizarTipoAgendamento(formNovo.tipo);
  const dicaTipoSelecionado = obterDicaTipoAgendamento(tipoSelecionado);
  const motivoPlaceholderPorTipo = MOTIVO_PLACEHOLDER_POR_TIPO;

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

  const mensagemAgendamentoSelecionado = montarMensagemGerenciamento(
    agendamentoSelecionado,
    tipoAgendamentoSelecionado
  );

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
      <AgendaHeader
        modo={modo}
        onChangeModo={setModo}
        onAbrirNovo={() => abrirModalNovo(dataRef)}
      />

      <AgendaPeriodoNav
        titulo={tituloAgenda}
        onAnterior={() => nav(-1)}
        onHoje={() => setDataRef(new Date())}
        onProximo={() => nav(1)}
      />

      {erro && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      <AgendaCalendarioCard
        calendarioMeta={calendarioMeta}
        carregandoCalendario={carregandoCalendario}
        mensagemCalendario={mensagemCalendario}
        onBaixarCalendario={baixarCalendarioAgenda}
        onCopiarLink={copiarLinkCalendario}
      />

      <AgendaConteudo
        carregando={carregando}
        modo={modo}
        diasMes={diasMes}
        diasVisiveis={diasVisiveis}
        dataRef={dataRef}
        agsDia={agsDia}
        abrindoAgendamentoId={abrindoAgendamentoId}
        onAbrirNovo={abrirModalNovo}
        onGerenciarAgendamento={abrirGerenciarAgendamento}
      />

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
