import { useState } from "react";

import {
  AGENDA_FORM_INICIAL,
  FORM_EVOLUCAO_INICIAL,
  FORM_FEITO_INICIAL,
  FORM_INSUMO_RAPIDO_INICIAL,
  FORM_NOVA_INTERNACAO_INICIAL,
} from "./internacoesInitialState";

export function useInternacoesState() {
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

  return {
    aba,
    agendaForm,
    carregando,
    carregandoHistoricoPet,
    centroAba,
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
    procedimentosInternacao,
    salvando,
    setAba,
    setAgendaForm,
    setCarregando,
    setCarregandoHistoricoPet,
    setCentroAba,
    setErro,
    setEvolucoes,
    setExpandida,
    setFiltroDataAltaFim,
    setFiltroDataAltaInicio,
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
    tutorNovaSelecionado,
  };
}
