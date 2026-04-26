import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import { useInternacaoOperacional } from "./useInternacaoOperacional";
import InternacoesAlert from "./internacoes/InternacoesAlert";
import InternacoesConteudo from "./internacoes/InternacoesConteudo";
import HistoricoInternacoesFiltros from "./internacoes/HistoricoInternacoesFiltros";
import InternacoesHeader from "./internacoes/InternacoesHeader";
import InternacoesModais from "./internacoes/InternacoesModais";
import InternacoesTabs from "./internacoes/InternacoesTabs";
import {
  AGENDA_FORM_INICIAL,
  FORM_EVOLUCAO_INICIAL,
  FORM_FEITO_INICIAL,
  FORM_INSUMO_RAPIDO_INICIAL,
  FORM_NOVA_INTERNACAO_INICIAL,
} from "./internacoes/internacoesInitialState";
import { useInternacoesAcoes } from "./internacoes/useInternacoesAcoes";
import { useInternacoesDerivados } from "./internacoes/useInternacoesDerivados";

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

  const {
    agendaOrdenada,
    indicadoresInternacao,
    internacaoPorId,
    internacaoSelecionadaAgenda,
    internacoesOrdenadas,
    mapaInternacao,
    pessoas,
    petsDaPessoa,
    petsHistoricoDaPessoa,
    retornoNovoPet,
    sugestaoHorario,
    tutorAtualInternacao,
  } = useInternacoesDerivados({
    agendaForm,
    agendaProcedimentos,
    evolucoes,
    filtroPessoaHistorico,
    formNova,
    internacoes,
    location,
    pets,
    totalBaias,
    tutorNovaSelecionado,
  });

  const {
    abrirDetalhe,
    abrirHistoricoPet,
    abrirModalFeito,
    abrirModalInsumoRapido,
    abrirNovaInternacao,
    adicionarProcedimentoAgenda,
    carregar,
    confirmarInsumoRapido,
    confirmarProcedimentoFeito,
    criarInternacao,
    darAlta,
    fecharModalNovaInternacao,
    reabrirProcedimento,
    registrarEvolucao,
    removerProcedimentoAgenda,
    selecionarInternacaoNoMapa,
    selecionarPessoaHistorico,
  } = useInternacoesAcoes({
    aba,
    agendaForm,
    carregarAgendaProcedimentos,
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
    setAgendaProcedimentos,
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
    sugestaoHorario,
  });

  useEffect(() => {
    setAgendaForm((prev) => (prev.horario ? prev : { ...prev, horario: sugestaoHorario }));
  }, [sugestaoHorario]);

  useEffect(() => {
    setFormInsumoRapido((prev) => (
      prev.horario_execucao ? prev : { ...prev, horario_execucao: sugestaoHorario }
    ));
  }, [sugestaoHorario]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  return (
    <div className="p-6 space-y-5">
      <InternacoesHeader onNovaInternacao={abrirNovaInternacao} />

      <InternacoesTabs aba={aba} onChangeAba={setAba} />

      <InternacoesAlert erro={erro} onClose={() => setErro(null)} />

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

      <InternacoesConteudo
        aba={aba}
        agendaCarregando={agendaCarregando}
        agendaForm={agendaForm}
        agendaOrdenada={agendaOrdenada}
        centroAba={centroAba}
        carregando={carregando}
        evolucoes={evolucoes}
        expandida={expandida}
        indicadoresInternacao={indicadoresInternacao}
        internacaoPorId={internacaoPorId}
        internacaoSelecionadaAgenda={internacaoSelecionadaAgenda}
        internacoes={internacoes}
        internacoesOrdenadas={internacoesOrdenadas}
        mapaInternacao={mapaInternacao}
        onAbrirAlta={setModalAlta}
        onAbrirDetalhe={abrirDetalhe}
        onAbrirEvolucao={setModalEvolucao}
        onAbrirFichaPet={(petId) => navigate(`/pets/${petId}`)}
        onAbrirHistoricoPet={abrirHistoricoPet}
        onAbrirInsumoRapido={abrirModalInsumoRapido}
        onAbrirModalFeito={abrirModalFeito}
        onAdicionarProcedimentoAgenda={adicionarProcedimentoAgenda}
        onChangeCentroAba={setCentroAba}
        onReabrirProcedimento={reabrirProcedimento}
        onRemoverProcedimentoAgenda={removerProcedimentoAgenda}
        onSelecionarInternacaoMapa={selecionarInternacaoNoMapa}
        procedimentosInternacao={procedimentosInternacao}
        salvando={salvando}
        setAgendaForm={setAgendaForm}
        setTotalBaias={setTotalBaias}
        totalBaias={totalBaias}
      />

      <InternacoesModais
        carregandoHistoricoPet={carregandoHistoricoPet}
        consultaIdQuery={consultaIdQuery}
        formAlta={formAlta}
        formEvolucao={formEvolucao}
        formFeito={formFeito}
        formInsumoRapido={formInsumoRapido}
        formNova={formNova}
        historicoPet={historicoPet}
        insumoRapidoSelecionado={insumoRapidoSelecionado}
        internacaoPorId={internacaoPorId}
        internacoesOrdenadas={internacoesOrdenadas}
        mapaInternacao={mapaInternacao}
        modalAlta={modalAlta}
        modalEvolucao={modalEvolucao}
        modalFeito={modalFeito}
        modalHistoricoPet={modalHistoricoPet}
        modalInsumoRapido={modalInsumoRapido}
        modalNova={modalNova}
        onCloseAlta={() => setModalAlta(null)}
        onCloseEvolucao={() => setModalEvolucao(null)}
        onCloseFeito={() => setModalFeito(null)}
        onCloseHistoricoPet={() => setModalHistoricoPet(null)}
        onCloseInsumoRapido={() => setModalInsumoRapido(false)}
        onCloseNova={fecharModalNovaInternacao}
        onConfirmAlta={darAlta}
        onConfirmEvolucao={registrarEvolucao}
        onConfirmFeito={confirmarProcedimentoFeito}
        onConfirmInsumoRapido={confirmarInsumoRapido}
        onConfirmNova={criarInternacao}
        onHideNovaForNovoPet={() => setModalNova(false)}
        petsDaPessoa={petsDaPessoa}
        retornoNovoPet={retornoNovoPet}
        salvando={salvando}
        setFormAlta={setFormAlta}
        setFormEvolucao={setFormEvolucao}
        setFormFeito={setFormFeito}
        setFormInsumoRapido={setFormInsumoRapido}
        setFormNova={setFormNova}
        setInsumoRapidoSelecionado={setInsumoRapidoSelecionado}
        setTotalBaias={setTotalBaias}
        setTutorNovaSelecionado={setTutorNovaSelecionado}
        totalBaias={totalBaias}
        tutorAtualInternacao={tutorAtualInternacao}
        tutorNovaSelecionado={tutorNovaSelecionado}
        veterinarios={veterinarios}
      />
    </div>
  );
}
