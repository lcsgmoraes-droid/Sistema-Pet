import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";

import AgendaCalendarioCard from "./agenda/AgendaCalendarioCard";
import AgendaConteudo from "./agenda/AgendaConteudo";
import AgendaHeader from "./agenda/AgendaHeader";
import AgendaPeriodoNav from "./agenda/AgendaPeriodoNav";
import GerenciarAgendamentoModal from "./agenda/GerenciarAgendamentoModal";
import NovoAgendamentoModal from "./agenda/NovoAgendamentoModal";
import { FORM_NOVO_INICIAL } from "./agenda/agendaUtils";
import { useAgendaAcoes } from "./agenda/useAgendaAcoes";
import { useAgendaApoios } from "./agenda/useAgendaApoios";
import { useAgendaDerivados } from "./agenda/useAgendaDerivados";

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

  const {
    bloqueioCamposAgendamento,
    conflitoHorarioSelecionado,
    consultorioSelecionadoModal,
    diagnosticoConflitoSelecionado,
    diasMes,
    diasVisiveis,
    dicaTipoSelecionado,
    fimSemana,
    horariosAgendaModal,
    inicioSemana,
    labelAbrirAgendamentoSelecionado,
    labelVoltarStatus,
    mensagemAgendamentoSelecionado,
    motivoPlaceholderPorTipo,
    petSelecionadoModal,
    podeExcluirAgendamento,
    podeVoltarStatus,
    retornoNovoPet,
    tipoAgendamentoSelecionado,
    tipoSelecionado,
    tituloAgenda,
    veterinarioSelecionadoModal,
  } = useAgendaDerivados({
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

  const {
    abrirConfiguracoesVet,
    abrirGerenciarAgendamento,
    abrirModalNovo,
    agsDia,
    baixarCalendarioAgenda,
    carregar,
    copiarLinkCalendario,
    criarAgendamento,
    excluirAgendamentoSelecionado,
    fecharGerenciarAgendamento,
    fecharModalNovo,
    iniciarAgendamentoSelecionado,
    nav,
    voltarStatusAgendamento,
  } = useAgendaAcoes({
    agendamentoEditandoId,
    agendamentoSelecionado,
    agendamentos,
    bloqueioCamposAgendamento,
    calendarioMeta,
    conflitoHorarioSelecionado,
    dataRef,
    fimSemana,
    formNovo,
    inicioSemana,
    modo,
    navigate,
    petSelecionadoModal,
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
    carregar();
  }, [carregar]);

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
