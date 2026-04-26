import { useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { buildReturnTo } from "../../../utils/petReturnFlow";
import useAssistenteIAChatHandlers from "./useAssistenteIAChatHandlers";
import useAssistenteIADataEffects from "./useAssistenteIADataEffects";

export default function useAssistenteIAController() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const exameIdQuery = searchParams.get("exame_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";

  const [modo, setModo] = useState("atendimento");
  const [conversaId, setConversaId] = useState("");
  const [filtrarConversasContexto, setFiltrarConversasContexto] = useState(false);
  const [memoriaAtiva, setMemoriaAtiva] = useState(null);
  const [conversas, setConversas] = useState([]);
  const [pets, setPets] = useState([]);
  const [consultas, setConsultas] = useState([]);
  const [exames, setExames] = useState([]);
  const [tutorSelecionado, setTutorSelecionado] = useState(null);
  const [petId, setPetId] = useState("");
  const [consultaId, setConsultaId] = useState("");
  const [exameId, setExameId] = useState("");
  const [med1, setMed1] = useState("");
  const [med2, setMed2] = useState("");
  const [pesoKg, setPesoKg] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [historico, setHistorico] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [salvandoFeedbackId, setSalvandoFeedbackId] = useState("");
  const [erro, setErro] = useState("");

  const petSelecionado = useMemo(
    () => pets.find((p) => String(p.id) === String(petId)) || null,
    [pets, petId]
  );
  const petsDoTutor = useMemo(() => {
    if (!tutorSelecionado?.id) return [];
    return pets.filter((pet) => String(pet.cliente_id) === String(tutorSelecionado.id) && pet.ativo !== false);
  }, [pets, tutorSelecionado]);
  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search),
    [location.pathname, location.search]
  );
  const consultaSelecionada = useMemo(
    () => consultas.find((item) => String(item.id) === String(consultaId)) ?? null,
    [consultas, consultaId]
  );
  const exameSelecionado = useMemo(
    () => exames.find((item) => String(item.id) === String(exameId)) ?? null,
    [exames, exameId]
  );

  const chat = useAssistenteIAChatHandlers({
    carregando,
    consultaId,
    conversaId,
    exameId,
    filtrarConversasContexto,
    med1,
    med2,
    mensagem,
    modo,
    pesoKg,
    petId,
    salvandoFeedbackId,
    setCarregando,
    setCarregandoHistorico,
    setConversaId,
    setConversas,
    setErro,
    setHistorico,
    setMensagem,
    setSalvandoFeedbackId,
  });

  useAssistenteIADataEffects({
    carregarConversas: chat.carregarConversas,
    carregarMensagensConversa: chat.carregarMensagensConversa,
    consultaId,
    consultaIdQuery,
    consultas,
    conversaId,
    exameId,
    exameIdQuery,
    exames,
    filtrarConversasContexto,
    novoPetIdQuery,
    petId,
    petIdQuery,
    pets,
    petSelecionado,
    pesoKg,
    setConsultaId,
    setConsultas,
    setExameId,
    setExames,
    setHistorico,
    setMemoriaAtiva,
    setPets,
    setPesoKg,
    setPetId,
    setTutorSelecionado,
    tutorIdQuery,
    tutorNomeQuery,
    tutorSelecionado,
  });

  function selecionarTutor(cliente) {
    setTutorSelecionado(cliente);
    setPetId("");
    setConsultaId("");
    setExameId("");
  }

  function selecionarPet(proximoPetId) {
    setPetId(proximoPetId);
    setConsultaId("");
    setExameId("");
  }

  function abrirConsulta(consultaIdAlvo) {
    navigate(`/veterinario/consultas/${consultaIdAlvo}`);
  }

  return {
    ...chat,
    abrirConsulta,
    carregando,
    carregandoHistorico,
    consultaId,
    consultaSelecionada,
    consultas,
    conversaId,
    conversas,
    erro,
    exameId,
    exameSelecionado,
    exames,
    filtrarConversasContexto,
    historico,
    med1,
    med2,
    memoriaAtiva,
    mensagem,
    modo,
    pesoKg,
    petId,
    petsDoTutor,
    retornoNovoPet,
    salvandoFeedbackId,
    selecionarPet,
    selecionarTutor,
    setConsultaId,
    setConversaId,
    setExameId,
    setFiltrarConversasContexto,
    setMed1,
    setMed2,
    setMensagem,
    setModo,
    setPesoKg,
    tutorSelecionado,
  };
}
