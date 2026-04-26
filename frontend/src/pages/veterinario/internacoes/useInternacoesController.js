import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../../../services/api";
import { useInternacaoOperacional } from "../useInternacaoOperacional";
import { vetApi } from "../vetApi";
import {
  AGENDA_FORM_INICIAL,
  FORM_EVOLUCAO_INICIAL,
  FORM_FEITO_INICIAL,
  FORM_INSUMO_RAPIDO_INICIAL,
  FORM_NOVA_INTERNACAO_INICIAL,
} from "./internacoesInitialState";
import { useInternacoesAcoes } from "./useInternacoesAcoes";
import { useInternacoesDerivados } from "./useInternacoesDerivados";

export default function useInternacoesController() {
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

  const operacional = useInternacaoOperacional({ setErro });

  useEffect(() => {
    api
      .get("/pets", { params: { limit: 500 } })
      .then((res) => setPets(res.data?.items ?? res.data ?? []))
      .catch(() => {});

    vetApi
      .listarVeterinarios()
      .then((res) => setVeterinarios(Array.isArray(res.data) ? res.data : []))
      .catch(() => setVeterinarios([]));
  }, []);

  useEffect(() => {
    if (abrirNovaQuery) setModalNova(true);
  }, [abrirNovaQuery]);

  useEffect(() => {
    if (!tutorIdQuery) return;

    setFormNova((prev) => ({
      ...prev,
      pessoa_id: prev.pessoa_id || String(tutorIdQuery),
    }));
    setTutorNovaSelecionado(
      (prev) =>
        prev || {
          id: String(tutorIdQuery),
          nome: tutorNomeQuery || `Pessoa #${tutorIdQuery}`,
        }
    );
  }, [tutorIdQuery, tutorNomeQuery]);

  useEffect(() => {
    if (!novoPetIdQuery) return;

    setModalNova(true);
    setFormNova((prev) => ({
      ...prev,
      pet_id: String(novoPetIdQuery),
    }));
  }, [novoPetIdQuery]);

  const derivados = useInternacoesDerivados({
    agendaForm,
    agendaProcedimentos: operacional.agendaProcedimentos,
    evolucoes,
    filtroPessoaHistorico,
    formNova,
    internacoes,
    location,
    pets,
    totalBaias: operacional.totalBaias,
    tutorNovaSelecionado,
  });

  const acoes = useInternacoesAcoes({
    aba,
    agendaForm,
    carregarAgendaProcedimentos: operacional.carregarAgendaProcedimentos,
    consultaIdQuery,
    expandida,
    filtroDataAltaFim,
    filtroDataAltaInicio,
    filtroPessoaHistorico,
    filtroPetHistorico,
    formAlta,
    formEvolucao,
    formFeito,
    formInsumoRapido,
    formNova,
    insumoRapidoSelecionado,
    modalAlta,
    modalEvolucao,
    modalFeito,
    setAba,
    setAgendaForm,
    setAgendaProcedimentos: operacional.setAgendaProcedimentos,
    setCarregando,
    setCarregandoHistoricoPet,
    setCentroAba,
    setErro,
    setEvolucoes,
    setExpandida,
    setFiltroPessoaHistorico,
    setFiltroPetHistorico,
    setFormAlta,
    setFormEvolucao,
    setFormFeito,
    setFormInsumoRapido,
    setFormNova,
    setHistoricoPet,
    setInsumoRapidoSelecionado,
    setInternacoes,
    setModalAlta,
    setModalEvolucao,
    setModalFeito,
    setModalHistoricoPet,
    setModalInsumoRapido,
    setModalNova,
    setProcedimentosInternacao,
    setSalvando,
    setTutorNovaSelecionado,
    sugestaoHorario: derivados.sugestaoHorario,
  });

  useEffect(() => {
    setAgendaForm((prev) => (prev.horario ? prev : { ...prev, horario: derivados.sugestaoHorario }));
  }, [derivados.sugestaoHorario]);

  useEffect(() => {
    setFormInsumoRapido((prev) =>
      prev.horario_execucao ? prev : { ...prev, horario_execucao: derivados.sugestaoHorario }
    );
  }, [derivados.sugestaoHorario]);

  useEffect(() => {
    acoes.carregar();
  }, [acoes.carregar]);

  return {
    ...acoes,
    ...derivados,
    ...operacional,
    aba,
    agendaForm,
    carregando,
    carregandoHistoricoPet,
    centroAba,
    consultaIdQuery,
    erro,
    evolucoes,
    expandida,
    filtroDataAltaFim,
    filtroDataAltaInicio,
    filtroPessoaHistorico,
    filtroPetHistorico,
    formAlta,
    formEvolucao,
    formFeito,
    formInsumoRapido,
    formNova,
    historicoPet,
    insumoRapidoSelecionado,
    internacoes,
    modalAlta,
    modalEvolucao,
    modalFeito,
    modalHistoricoPet,
    modalInsumoRapido,
    modalNova,
    onAbrirFichaPet: (petId) => navigate(`/pets/${petId}`),
    procedimentosInternacao,
    salvando,
    setAba,
    setAgendaForm,
    setCentroAba,
    setErro,
    setFiltroDataAltaFim,
    setFiltroDataAltaInicio,
    setFiltroPetHistorico,
    setFormAlta,
    setFormEvolucao,
    setFormFeito,
    setFormInsumoRapido,
    setFormNova,
    setInsumoRapidoSelecionado,
    setModalAlta,
    setModalEvolucao,
    setModalFeito,
    setModalHistoricoPet,
    setModalInsumoRapido,
    setModalNova,
    setTutorNovaSelecionado,
    tutorNovaSelecionado,
    veterinarios,
  };
}
