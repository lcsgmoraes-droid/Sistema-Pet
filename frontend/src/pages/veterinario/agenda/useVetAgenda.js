import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { FORM_NOVO_INICIAL } from "./agendaUtils";
import { useAgendaAcoes } from "./useAgendaAcoes";
import { useAgendaApoios } from "./useAgendaApoios";
import { useAgendaDerivados } from "./useAgendaDerivados";

export function useVetAgenda() {
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

  const derivados = useAgendaDerivados({
    agendaDiaModal,
    agendamentoEditandoId,
    agendamentoSelecionado,
    consultorios,
    dataRef,
    formNovo,
    location,
    modo,
    petsDoTutor,
    veterinarios,
  });

  const acoes = useAgendaAcoes({
    agendamentoEditandoId,
    agendamentoSelecionado,
    agendamentos,
    bloqueioCamposAgendamento: derivados.bloqueioCamposAgendamento,
    calendarioMeta,
    conflitoHorarioSelecionado: derivados.conflitoHorarioSelecionado,
    dataRef,
    fimSemana: derivados.fimSemana,
    formNovo,
    inicioSemana: derivados.inicioSemana,
    modo,
    navigate,
    petSelecionadoModal: derivados.petSelecionadoModal,
    setAbrindoAgendamentoId,
    setAgendaDiaModal,
    setAgendamentoEditandoId,
    setAgendamentos,
    setAgendamentoSelecionado,
    setCarregando,
    setDataRef,
    setErro,
    setErroNovo,
    setFormNovo,
    setMensagemCalendario,
    setNovoAberto,
    setPetsDoTutor,
    setProcessandoAgendamentoId,
    setSalvandoNovo,
    setTutorSelecionado,
    tutorSelecionado,
  });

  useEffect(() => {
    acoes.carregar();
  }, [acoes.carregar]);

  useAgendaApoios({
    abrirNovoQuery,
    formNovoData: formNovo.data,
    novoAberto,
    novoPetIdQuery,
    petsDoTutor,
    setAgendaDiaModal,
    setCalendarioMeta,
    setCarregandoAgendaDiaModal,
    setCarregandoCalendario,
    setCarregandoPetsTutor,
    setConsultorios,
    setFormNovo,
    setNovoAberto,
    setPetsDoTutor,
    setTutorSelecionado,
    setVeterinarios,
    tutorIdQuery,
    tutorNomeQuery,
    tutorSelecionado,
  });

  function selecionarTutorNovoAgendamento(tutor) {
    setTutorSelecionado(tutor);
    setPetsDoTutor([]);
    setFormNovo((prev) => ({ ...prev, pet_id: "" }));
  }

  function ocultarNovoParaNovoPet() {
    setNovoAberto(false);
  }

  function editarAgendamentoSelecionado() {
    if (!agendamentoSelecionado) return;
    acoes.abrirModalNovo(new Date(agendamentoSelecionado.data_hora), agendamentoSelecionado);
  }

  return {
    ...derivados,
    ...acoes,
    abrindoAgendamentoId,
    agendaDiaModal,
    agendamentoEditandoId,
    agendamentoSelecionado,
    calendarioMeta,
    carregando,
    carregandoAgendaDiaModal,
    carregandoCalendario,
    carregandoPetsTutor,
    consultorios,
    dataRef,
    editarAgendamentoSelecionado,
    erro,
    erroNovo,
    formNovo,
    mensagemCalendario,
    modo,
    novoAberto,
    ocultarNovoParaNovoPet,
    petsDoTutor,
    processandoAgendamentoId,
    salvandoNovo,
    selecionarTutorNovoAgendamento,
    setDataRef,
    setFormNovo,
    setModo,
    tutorSelecionado,
    veterinarios,
  };
}
