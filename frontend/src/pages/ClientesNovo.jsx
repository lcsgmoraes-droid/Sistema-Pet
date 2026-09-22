import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle, UsersRound } from "lucide-react";
import toast from "react-hot-toast";
import api from "../api";
import ModalImportacaoPessoas from "../components/ModalImportacaoPessoas";
import ClientePessoaCriarModal from "../components/clientes/ClientePessoaCriarModal";
import ClientesNovoActionsBar from "../components/clientes/ClientesNovoActionsBar";
import ClientesOrigemResumo from "../components/clientes/ClientesOrigemResumo";
import ClientesNovoTabelaSection from "../components/clientes/ClientesNovoTabelaSection";
import ClientesNovoTabsBar from "../components/clientes/ClientesNovoTabsBar";
import PessoasDuplicidadeBanner from "../components/pessoas/PessoasDuplicidadeBanner";
import PessoasDuplicidadeCentralModal from "../components/pessoas/PessoasDuplicidadeCentralModal";
import PessoasFusaoModal from "../components/pessoas/PessoasFusaoModal";
import PessoasRelatorioModal from "../components/pessoas/PessoasRelatorioModal";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import {
  buscarSugestoesDuplicidadePessoas,
  executarFusoesAutomaticasPessoas,
  executarFusoesAssistidasPessoasPorNome,
} from "../api/clientes";
import { useClientesNovoListagem } from "../hooks/useClientesNovoListagem";
import { debugLog } from "../utils/debug";
import {
  CLIENTES_DASHBOARD_VIEWS,
  normalizarVisaoDashboardClientes,
} from "./clientes/clientesDashboardFilters";
import { confirmarCorePet } from "../services/corepetDialog";

const LIMITE_DUPLICIDADES_POR_PAGINA = 25;

function buildListaPessoasUrl({ searchTerm, paginaAtual, tipoFiltro }) {
  const params = new URLSearchParams();
  if (searchTerm) params.set("q", searchTerm);
  if (paginaAtual > 1) params.set("page", String(paginaAtual));
  if (tipoFiltro !== "todos") params.set("tipo", tipoFiltro);
  const query = params.toString();
  return query ? `/clientes?${query}` : "/clientes";
}

const Pessoas = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const visaoDashboard = normalizarVisaoDashboardClientes(searchParams);
  const [error, setError] = useState("");
  const [tipoFiltro, setTipoFiltro] = useState(() => {
    if (visaoDashboard) return "cliente";
    return searchParams.get("tipo") || "todos";
  });
  const [expandedPets, setExpandedPets] = useState({});
  const [highlightedPetId, setHighlightedPetId] = useState(null);
  const [criarModalAberto, setCriarModalAberto] = useState(false);
  const [tipoParaCriar, setTipoParaCriar] = useState(null);
  const [showModalImportacao, setShowModalImportacao] = useState(false);
  const [pessoasSelecionadasFusao, setPessoasSelecionadasFusao] = useState([]);
  const [pessoasSugestaoFusao, setPessoasSugestaoFusao] = useState(null);
  const [modalFusaoAberto, setModalFusaoAberto] = useState(false);
  const [modalRelatorioAberto, setModalRelatorioAberto] = useState(false);
  const [filaRevisaoFusao, setFilaRevisaoFusao] = useState([]);
  const [reabrirCentralAposFusao, setReabrirCentralAposFusao] = useState(false);
  const [centralDuplicidades, setCentralDuplicidades] = useState({
    aberta: false,
    sugestoes: [],
    totalSugestoes: 0,
    totalAutomaticas: 0,
    skip: 0,
    limit: LIMITE_DUPLICIDADES_POR_PAGINA,
    verificando: false,
  });
  const [duplicidade, setDuplicidade] = useState({
    sugestoes: [],
    totalSugestoes: 0,
    totalAutomaticas: 0,
    verificando: false,
    varreduraInicialExecutada: false,
  });
  const {
    loading,
    carregamentoInicialConcluido,
    searchTerm,
    setSearchTerm,
    paginaAtual,
    setPaginaAtual,
    totalRegistros,
    registrosPorPagina,
    setRegistrosPorPagina,
    filteredClientes,
    loadClientes,
    getClientePorCodigoExato,
    filtrosOrigem,
    alterarFiltrosOrigem,
    resumoOrigens,
  } = useClientesNovoListagem({
    tipoFiltro,
    visaoDashboard,
    setError,
    initialSearchTerm: searchParams.get("q") || "",
    initialPaginaAtual: Number(searchParams.get("page")) || 1,
  });

  // Mantém a busca, a página e o tipo de filtro na própria URL — assim, ao voltar da tela de
  // edição de uma pessoa (ou usar o botão voltar do navegador), a consulta e o resultado da
  // lista não se perdem.
  const listaUrl = buildListaPessoasUrl({ searchTerm, paginaAtual, tipoFiltro });

  useEffect(() => {
    setSearchParams(
      (params) => {
        const proximos = new URLSearchParams(params);
        if (searchTerm) proximos.set("q", searchTerm);
        else proximos.delete("q");
        if (paginaAtual > 1) proximos.set("page", String(paginaAtual));
        else proximos.delete("page");
        if (tipoFiltro !== "todos") proximos.set("tipo", tipoFiltro);
        else proximos.delete("tipo");
        return proximos;
      },
      { replace: true },
    );
  }, [searchTerm, paginaAtual, tipoFiltro, setSearchParams]);

  const setTipoFiltroComContexto = (proximoTipo) => {
    setTipoFiltro(proximoTipo);
    if (visaoDashboard) setSearchParams({}, { replace: true });
  };

  const pessoasParaFusao = useMemo(() => {
    if (pessoasSugestaoFusao?.length === 2) return pessoasSugestaoFusao;
    return filteredClientes.filter((cliente) => pessoasSelecionadasFusao.includes(cliente.id));
  }, [filteredClientes, pessoasSelecionadasFusao, pessoasSugestaoFusao]);

  const handleSearchTermChange = (value) => {
    setPaginaAtual(1);
    setSearchTerm(value);
    setPessoasSelecionadasFusao([]);
    setPessoasSugestaoFusao(null);
  };

  const abrirModalCriacao = (tipo = null) => {
    setTipoParaCriar(tipo);
    setCriarModalAberto(true);
  };

  const handleClienteCriado = (cliente) => {
    setCriarModalAberto(false);
    navigate(`/clientes/${cliente.id}/editar`, { state: { from: listaUrl } });
  };

  const handleDelete = async (id) => {
    if (!(await confirmarCorePet("Tem certeza que deseja excluir este cliente?"))) return;

    try {
      debugLog("Excluindo cliente ID:", id);
      const response = await api.delete(`/clientes/${id}`);
      debugLog("Cliente excluído com sucesso:", response);
      setPessoasSelecionadasFusao((prev) => prev.filter((pessoaId) => pessoaId !== id));
      await loadClientes();
    } catch (err) {
      console.error("Erro ao excluir cliente:", err);
      console.error("Resposta do erro:", err.response);
      setError(err.response?.data?.detail || "Erro ao excluir cliente");
    }
  };

  const handleDeletePet = async (petId) => {
    if (!(await confirmarCorePet("Tem certeza que deseja excluir este pet?"))) return;

    try {
      debugLog("Excluindo pet ID:", petId);
      await api.delete(`/clientes/pets/${petId}`);
      debugLog("Pet excluído com sucesso");

      // Limpar estado de expansão para forçar re-render
      setExpandedPets({});
      setHighlightedPetId(null);

      // Atualizar lista de clientes
      await loadClientes();
      debugLog("Lista de clientes atualizada");
    } catch (err) {
      console.error("Erro ao excluir pet:", err);
      alert(err.response?.data?.detail || "Erro ao excluir pet");
    }
  };

  const abrirPessoaPorCodigoNoEnter = async () => {
    const termo = String(searchTerm || "").trim();
    if (!termo) return;

    const clientesEncontrados = await loadClientes({
      searchTerm: termo,
      paginaAtual: 1,
    });
    const clienteCodigoExato =
      clientesEncontrados.find((cliente) => String(cliente?.codigo || "").trim() === termo) ||
      getClientePorCodigoExato(termo);

    if (clienteCodigoExato) {
      setPaginaAtual(1);
      const from = buildListaPessoasUrl({ searchTerm: termo, paginaAtual: 1, tipoFiltro });
      navigate(`/clientes/${clienteCodigoExato.id}/editar`, { state: { from } });
    }
  };

  const togglePessoaFusao = (clienteId) => {
    setPessoasSugestaoFusao(null);
    setPessoasSelecionadasFusao((prev) => {
      if (prev.includes(clienteId)) {
        return prev.filter((id) => id !== clienteId);
      }

      if (prev.length >= 2) {
        toast("Selecione no maximo 2 pessoas para fundir.");
        return prev;
      }

      return [...prev, clienteId];
    });
  };

  const limparSelecaoFusao = () => {
    setPessoasSelecionadasFusao([]);
    setPessoasSugestaoFusao(null);
  };

  const abrirModalFusao = () => {
    if (pessoasSelecionadasFusao.length !== 2) {
      toast.error("Selecione exatamente 2 pessoas para fundir.");
      return;
    }
    setFilaRevisaoFusao([]);
    setReabrirCentralAposFusao(false);
    setModalFusaoAberto(true);
  };

  const carregarPaginaCentralDuplicidades = async (skip = 0) => {
    const proximoSkip = Math.max(Number(skip || 0), 0);
    setCentralDuplicidades((prev) => ({
      ...prev,
      skip: proximoSkip,
      verificando: true,
    }));
    try {
      const { data } = await buscarSugestoesDuplicidadePessoas({
        skip: proximoSkip,
        limit: LIMITE_DUPLICIDADES_POR_PAGINA,
      });
      setCentralDuplicidades((prev) => ({
        ...prev,
        sugestoes: data?.sugestoes || [],
        totalSugestoes: Number(data?.total || 0),
        totalAutomaticas: Number(data?.total_automaticas || 0),
        skip: Number(data?.skip ?? proximoSkip),
        limit: Number(data?.limit || LIMITE_DUPLICIDADES_POR_PAGINA),
      }));
    } catch (err) {
      console.error("Erro ao carregar central de duplicidades:", err);
      toast.error(err?.response?.data?.detail || "Não foi possível carregar as duplicidades.");
    } finally {
      setCentralDuplicidades((prev) => ({ ...prev, verificando: false }));
    }
  };

  const abrirCentralDuplicidades = async () => {
    setCentralDuplicidades((prev) => ({ ...prev, aberta: true }));
    await carregarPaginaCentralDuplicidades(0);
  };

  const carregarSugestoesDuplicidade = async () => {
    setDuplicidade((prev) => ({ ...prev, verificando: true }));
    try {
      const { data } = await buscarSugestoesDuplicidadePessoas({ limit: 20 });
      setDuplicidade((prev) => ({
        ...prev,
        sugestoes: data?.sugestoes || [],
        totalSugestoes: Number(data?.total || 0),
        totalAutomaticas: Number(data?.total_automaticas || 0),
        varreduraInicialExecutada: true,
      }));
    } catch (err) {
      console.error("Erro ao buscar sugestoes de duplicidade:", err);
    } finally {
      setDuplicidade((prev) => ({
        ...prev,
        verificando: false,
        varreduraInicialExecutada: true,
      }));
    }
  };

  const executarVarreduraDuplicidade = async ({ silencioso = false } = {}) => {
    if (
      !silencioso &&
      duplicidade.totalAutomaticas > 0 &&
      !(await confirmarCorePet(
        `Fundir agora ate ${Math.min(
          duplicidade.totalAutomaticas,
          25,
        )} duplicidade(s) com documento valido e igual?`,
      ))
    ) {
      return;
    }
    setDuplicidade((prev) => ({ ...prev, verificando: true }));
    try {
      const { data } = await executarFusoesAutomaticasPessoas();
      const totalAutomaticas = Number(data?.total_automaticas || 0);
      setDuplicidade((prev) => ({
        ...prev,
        totalAutomaticas: 0,
        sugestoes: data?.sugestoes || prev.sugestoes,
        totalSugestoes: (data?.sugestoes || prev.sugestoes).length,
        varreduraInicialExecutada: true,
      }));
      if (totalAutomaticas > 0) {
        toast.success(`${totalAutomaticas} cadastro(s) duplicado(s) fundido(s).`);
        await loadClientes();
      } else if (!silencioso) {
        toast("Nenhuma duplicidade segura para fundir automaticamente.");
      }
      await carregarSugestoesDuplicidade();
      if (centralDuplicidades.aberta) {
        await carregarPaginaCentralDuplicidades(0);
      }
    } catch (err) {
      console.error("Erro ao executar varredura de duplicidade:", err);
      if (!silencioso) {
        toast.error(err?.response?.data?.detail || "Nao foi possivel verificar duplicidades.");
      }
    } finally {
      setDuplicidade((prev) => ({
        ...prev,
        verificando: false,
        varreduraInicialExecutada: true,
      }));
    }
  };

  const executarFusoesAssistidasNome = async () => {
    setCentralDuplicidades((prev) => ({ ...prev, verificando: true }));
    try {
      const { data: simulacao } = await executarFusoesAssistidasPessoasPorNome({
        confirmar: false,
        aceitar_nome_igual: true,
        limit: 200,
      });
      const elegiveis = Number(simulacao?.total_elegiveis || 0);
      const bloqueadas = Number(simulacao?.total_bloqueadas || 0);
      if (elegiveis === 0) {
        toast(
          bloqueadas > 0
            ? `${bloqueadas} par(es) continuam bloqueados por conflito objetivo de identidade.`
            : "Nenhum nome igual foi encontrado para fusão.",
        );
        return;
      }

      const confirmou = await confirmarCorePet(
        `Foram encontrados ${elegiveis} par(es) elegíveis e ${bloqueadas} bloqueado(s).\n\n` +
          "Você confirmou que nomes exatamente iguais representam a mesma pessoa. " +
          "A fusão preencherá campos vazios, preservará históricos, créditos e acessos, " +
          "e usará telefone/celular do cadastro mais recente. Conflitos objetivos de " +
          "identidade continuarão bloqueados.\n\nConfirmar agora?",
      );
      if (!confirmou) return;

      const { data: resultado } = await executarFusoesAssistidasPessoasPorNome({
        confirmar: true,
        aceitar_nome_igual: true,
        limit: 200,
      });
      const fundidas = Number(resultado?.total_fundidas || 0);
      const aindaBloqueadas = Number(resultado?.total_bloqueadas || 0);
      if (fundidas > 0) {
        toast.success(
          `${fundidas} cadastro(s) fundido(s); ${aindaBloqueadas} par(es) mantido(s) para revisão.`,
        );
        await loadClientes();
      } else {
        toast("Nenhum cadastro passou pelos critérios seguros no momento da confirmação.");
      }
      await carregarSugestoesDuplicidade();
      await carregarPaginaCentralDuplicidades(0);
    } catch (err) {
      console.error("Erro ao executar fusões assistidas por nome:", err);
      toast.error(err?.response?.data?.detail || "Não foi possível executar as fusões assistidas.");
    } finally {
      setCentralDuplicidades((prev) => ({ ...prev, verificando: false }));
    }
  };

  const revisarSugestaoDuplicidade = (sugestao, { fila = [], origemCentral = true } = {}) => {
    if (!sugestao?.principal || !sugestao?.duplicado) {
      toast.error("Esta sugestão não possui os dois cadastros necessários para revisão.");
      return;
    }
    setPessoasSelecionadasFusao([]);
    setPessoasSugestaoFusao([sugestao.principal, sugestao.duplicado].filter(Boolean));
    setFilaRevisaoFusao(fila);
    setReabrirCentralAposFusao(origemCentral);
    if (origemCentral) {
      setCentralDuplicidades((prev) => ({ ...prev, aberta: false }));
    }
    setModalFusaoAberto(true);
  };

  const revisarSugestoesSelecionadas = (sugestoes) => {
    const fila = (sugestoes || []).filter((sugestao) => sugestao?.principal && sugestao?.duplicado);
    if (fila.length === 0) {
      toast.error("Selecione ao menos uma duplicidade para revisar.");
      return;
    }

    const [primeira, ...restantes] = fila;
    revisarSugestaoDuplicidade(primeira, {
      fila: restantes,
      origemCentral: true,
    });
  };

  const fecharModalFusao = () => {
    setModalFusaoAberto(false);
    setPessoasSugestaoFusao(null);
    setFilaRevisaoFusao([]);
    if (reabrirCentralAposFusao) {
      setCentralDuplicidades((prev) => ({ ...prev, aberta: true }));
    }
    setReabrirCentralAposFusao(false);
  };

  const concluirFusaoPessoa = async () => {
    setPessoasSelecionadasFusao([]);
    await loadClientes();
    await carregarSugestoesDuplicidade();

    if (filaRevisaoFusao.length > 0) {
      const [proxima, ...restantes] = filaRevisaoFusao;
      setFilaRevisaoFusao(restantes);
      setPessoasSugestaoFusao([proxima.principal, proxima.duplicado].filter(Boolean));
      toast(`Próxima revisão da fila. Restam ${restantes.length} depois desta.`);
      return false;
    }

    if (reabrirCentralAposFusao) {
      await carregarPaginaCentralDuplicidades(0);
      setCentralDuplicidades((prev) => ({ ...prev, aberta: true }));
    }
    return true;
  };

  useEffect(() => {
    limparSelecaoFusao();
  }, [tipoFiltro, paginaAtual, registrosPorPagina]);

  useEffect(() => {
    if (!carregamentoInicialConcluido || duplicidade.varreduraInicialExecutada) return;
    carregarSugestoesDuplicidade();
  }, [carregamentoInicialConcluido, duplicidade.varreduraInicialExecutada]);

  useEffect(() => {
    setPessoasSelecionadasFusao((prev) => {
      const idsVisiveis = new Set(filteredClientes.map((cliente) => cliente.id));
      const proximaSelecao = prev.filter((id) => idsVisiveis.has(id));
      return proximaSelecao.length === prev.length ? prev : proximaSelecao;
    });
  }, [filteredClientes]);

  // ============================================================================
  // COMPONENTE: ClienteSegmentoBadgeWrapper (lazy load badge na lista)
  const isCarregamentoInicial = loading && !carregamentoInicialConcluido;

  if (isCarregamentoInicial) {
    return <LoadingState className="h-96" label="Carregando pessoas..." />;
  }

  return (
    <div className="p-6">
      <PageHeader
        className="mb-6"
        icon={UsersRound}
        iconClassName="bg-emerald-50 text-emerald-600"
        title="Pessoas"
        subtitle="Gerenciamento de clientes, fornecedores, veterinarios, funcionarios e pets"
      />

      <ClientesNovoTabsBar
        tipoFiltro={tipoFiltro}
        setTipoFiltro={setTipoFiltroComContexto}
        setPaginaAtual={setPaginaAtual}
      />
      {visaoDashboard ? (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-950">
          <div>
            <p className="font-semibold">{CLIENTES_DASHBOARD_VIEWS[visaoDashboard].title}</p>
            <p className="text-teal-800">
              {CLIENTES_DASHBOARD_VIEWS[visaoDashboard].description} {totalRegistros} encontrado(s).
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg border border-teal-300 bg-white px-3 py-2 font-medium text-teal-800 hover:bg-teal-100"
            onClick={() => setSearchParams({}, { replace: true })}
          >
            Ver todos os clientes
          </button>
        </div>
      ) : null}
      <ClientesNovoActionsBar
        searchTerm={searchTerm}
        setSearchTerm={handleSearchTermChange}
        abrirPessoaPorCodigoNoEnter={abrirPessoaPorCodigoNoEnter}
        setShowModalImportacao={setShowModalImportacao}
        openModal={abrirModalCriacao}
        tipoFiltro={tipoFiltro}
        pessoasSelecionadasFusao={pessoasSelecionadasFusao}
        onAbrirFusao={abrirModalFusao}
        onAbrirRelatorio={() => setModalRelatorioAberto(true)}
        onLimparSelecaoFusao={limparSelecaoFusao}
      />
      {tipoFiltro === "cliente" && (
        <ClientesOrigemResumo
          filtros={filtrosOrigem}
          onChange={alterarFiltrosOrigem}
          resumo={resumoOrigens}
          loading={loading}
        />
      )}
      <PessoasDuplicidadeBanner
        sugestoes={duplicidade.sugestoes}
        totalSugestoes={duplicidade.totalSugestoes}
        totalAutomaticas={duplicidade.totalAutomaticas}
        verificando={duplicidade.verificando}
        onVerificar={carregarSugestoesDuplicidade}
        onFundirAutomaticas={() => executarVarreduraDuplicidade({ silencioso: false })}
        onAbrirCentral={abrirCentralDuplicidades}
      />
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <AlertCircle className="h-5 w-5" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
      <ClientesNovoTabelaSection
        loading={loading}
        totalRegistros={totalRegistros}
        paginaAtual={paginaAtual}
        registrosPorPagina={registrosPorPagina}
        setRegistrosPorPagina={setRegistrosPorPagina}
        setPaginaAtual={setPaginaAtual}
        filteredClientes={filteredClientes}
        listaUrl={listaUrl}
        expandedPets={expandedPets}
        setExpandedPets={setExpandedPets}
        highlightedPetId={highlightedPetId}
        setHighlightedPetId={setHighlightedPetId}
        handleDelete={handleDelete}
        handleDeletePet={handleDeletePet}
        pessoasSelecionadasFusao={pessoasSelecionadasFusao}
        togglePessoaFusao={togglePessoaFusao}
      />

      <ClientePessoaCriarModal
        aberto={criarModalAberto}
        tipoInicial={tipoParaCriar}
        onCriado={handleClienteCriado}
        onFechar={() => setCriarModalAberto(false)}
      />
      <ModalImportacaoPessoas
        isOpen={showModalImportacao}
        onClose={() => {
          setShowModalImportacao(false);
          loadClientes();
        }}
      />
      <PessoasDuplicidadeCentralModal
        isOpen={centralDuplicidades.aberta}
        sugestoes={centralDuplicidades.sugestoes}
        totalSugestoes={centralDuplicidades.totalSugestoes}
        totalAutomaticas={centralDuplicidades.totalAutomaticas}
        skip={centralDuplicidades.skip}
        limit={centralDuplicidades.limit}
        verificando={centralDuplicidades.verificando}
        onClose={() => setCentralDuplicidades((prev) => ({ ...prev, aberta: false }))}
        onAtualizar={() => carregarPaginaCentralDuplicidades(centralDuplicidades.skip)}
        onMudarPagina={carregarPaginaCentralDuplicidades}
        onRevisarSugestao={(sugestao) =>
          revisarSugestaoDuplicidade(sugestao, { origemCentral: true })
        }
        onRevisarSelecionadas={revisarSugestoesSelecionadas}
        onFundirAutomaticas={() => executarVarreduraDuplicidade({ silencioso: false })}
        onFundirAssistidasNome={executarFusoesAssistidasNome}
      />
      <PessoasFusaoModal
        isOpen={modalFusaoAberto}
        onClose={fecharModalFusao}
        onSuccess={concluirFusaoPessoa}
        pessoasSelecionadas={pessoasParaFusao}
      />
      {modalRelatorioAberto ? (
        <PessoasRelatorioModal
          buscaInicial={searchTerm}
          isOpen
          onClose={() => setModalRelatorioAberto(false)}
          tipoInicial={tipoFiltro}
        />
      ) : null}

      {/* Estilos para animação do badge de parceiro */}
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .animate-fade-in {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default Pessoas;
