import { useEffect, useMemo, useState } from "react";
import { AlertCircle, UsersRound } from "lucide-react";
import toast from "react-hot-toast";
import api from "../api";
import ClientesNovoActionsBar from "../components/clientes/ClientesNovoActionsBar";
import ClientesNovoCadastroRecenteBanner from "../components/clientes/ClientesNovoCadastroRecenteBanner";
import ClientesNovoModalsLayer from "../components/clientes/ClientesNovoModalsLayer";
import ClientesNovoTabelaSection from "../components/clientes/ClientesNovoTabelaSection";
import ClientesNovoTabsBar from "../components/clientes/ClientesNovoTabsBar";
import PessoasDuplicidadeBanner from "../components/pessoas/PessoasDuplicidadeBanner";
import PessoasDuplicidadeCentralModal from "../components/pessoas/PessoasDuplicidadeCentralModal";
import PessoasFusaoModal from "../components/pessoas/PessoasFusaoModal";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import {
  buscarSugestoesDuplicidadePessoas,
  executarFusoesAutomaticasPessoas,
  executarFusoesAssistidasPessoasPorNome,
} from "../api/clientes";
import { useClientesNovoCadastro } from "../hooks/useClientesNovoCadastro";
import { useClientesNovoListagem } from "../hooks/useClientesNovoListagem";
import { debugLog } from "../utils/debug";

const LIMITE_DUPLICIDADES_POR_PAGINA = 25;

const Pessoas = () => {
  const [error, setError] = useState("");
  const [tipoFiltro, setTipoFiltro] = useState("todos"); // Filtro por tipo: todos, cliente, fornecedor, veterinario, funcionario
  const [expandedPets, setExpandedPets] = useState({});
  const [clienteRecemCriado, setClienteRecemCriado] = useState(null);
  const [campoCopiadoRecente, setCampoCopiadoRecente] = useState("");
  const [pessoasSelecionadasFusao, setPessoasSelecionadasFusao] = useState([]);
  const [pessoasSugestaoFusao, setPessoasSugestaoFusao] = useState(null);
  const [modalFusaoAberto, setModalFusaoAberto] = useState(false);
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
    clientes,
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
  } = useClientesNovoListagem({ tipoFiltro, setError });

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

  const handleClienteCriado = async (cliente) => {
    const termoFiltro = String(cliente?.codigo || cliente?.nome || "").trim();

    setError("");
    setExpandedPets({});
    setCampoCopiadoRecente("");
    setClienteRecemCriado({
      ...cliente,
      termoFiltro,
    });

    if (!termoFiltro) {
      await loadClientes({ paginaAtual: 1 });
      return;
    }

    setPaginaAtual(1);
    setSearchTerm(termoFiltro);
    await loadClientes({ searchTerm: termoFiltro, paginaAtual: 1 });
  };

  const cadastro = useClientesNovoCadastro({
    tipoFiltro,
    clientes,
    loadClientes,
    onClienteCriado: handleClienteCriado,
    error,
    setError,
  });

  const handleDelete = async (id) => {
    if (!confirm("Tem certeza que deseja excluir este cliente?")) return;

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
    if (!confirm("Tem certeza que deseja excluir este pet?")) return;

    try {
      debugLog("Excluindo pet ID:", petId);
      await api.delete(`/clientes/pets/${petId}`);
      debugLog("Pet excluído com sucesso");

      // Limpar estado de expansão para forçar re-render
      setExpandedPets({});
      cadastro.setHighlightedPetId(null);

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
      cadastro.openModal(clienteCodigoExato);
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
      !window.confirm(
        `Fundir agora ate ${Math.min(
          duplicidade.totalAutomaticas,
          25,
        )} duplicidade(s) com documento valido e igual?`,
      )
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
        limit: 200,
      });
      const elegiveis = Number(simulacao?.total_elegiveis || 0);
      const bloqueadas = Number(simulacao?.total_bloqueadas || 0);
      if (elegiveis === 0) {
        toast(
          bloqueadas > 0
            ? `${bloqueadas} par(es) continuam bloqueados por falta de evidência ou conflito.`
            : "Nenhuma fusão assistida elegível foi encontrada.",
        );
        return;
      }

      const confirmou = window.confirm(
        `Foram encontrados ${elegiveis} par(es) elegíveis e ${bloqueadas} bloqueado(s).\n\n` +
          "A fusão preencherá campos vazios, preservará históricos, créditos e acessos, " +
          "e usará telefone/celular do cadastro mais recente. Pares sem outra evidência " +
          "compartilhada ou com conflito de identidade não serão fundidos.\n\nConfirmar agora?",
      );
      if (!confirmou) return;

      const { data: resultado } = await executarFusoesAssistidasPessoasPorNome({
        confirmar: true,
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

  const handleCopiarCampoRecente = async (valor, campo) => {
    if (!valor) return;

    try {
      await navigator.clipboard.writeText(String(valor));
      setCampoCopiadoRecente(campo);
      toast.success(
        campo === "codigo" ? "Codigo copiado com sucesso!" : "Nome copiado com sucesso!",
      );
    } catch (err) {
      console.error("Erro ao copiar dados do cliente:", err);
      toast.error("Nao foi possivel copiar os dados do cliente.");
    }
  };

  const handleLimparFiltroRecente = async () => {
    setClienteRecemCriado(null);
    setCampoCopiadoRecente("");
    handleSearchTermChange("");
    await loadClientes({ searchTerm: "", paginaAtual: 1 });
  };

  useEffect(() => {
    if (!campoCopiadoRecente) return undefined;

    const timeoutId = window.setTimeout(() => {
      setCampoCopiadoRecente("");
    }, 2000);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [campoCopiadoRecente]);

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

  useEffect(() => {
    if (!clienteRecemCriado?.termoFiltro) return;

    const termoAtual = String(searchTerm || "").trim();
    if (termoAtual && termoAtual === clienteRecemCriado.termoFiltro) return;

    setClienteRecemCriado(null);
    setCampoCopiadoRecente("");
  }, [clienteRecemCriado?.termoFiltro, searchTerm]);

  useEffect(() => {
    if (!clienteRecemCriado?.id || loading) return;

    const clienteNaLista = filteredClientes.some((cliente) => cliente.id === clienteRecemCriado.id);
    if (!clienteNaLista) return;

    const elemento = document.getElementById(`cliente-${clienteRecemCriado.id}`);
    if (!elemento) return;

    elemento.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [clienteRecemCriado?.id, filteredClientes, loading]);

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
        title="Cadastros"
        subtitle="Gerenciamento de clientes, fornecedores, veterinarios, funcionarios e pets"
      />

      <ClientesNovoTabsBar
        tipoFiltro={tipoFiltro}
        setTipoFiltro={setTipoFiltro}
        setPaginaAtual={setPaginaAtual}
      />
      <ClientesNovoActionsBar
        searchTerm={searchTerm}
        setSearchTerm={handleSearchTermChange}
        abrirPessoaPorCodigoNoEnter={abrirPessoaPorCodigoNoEnter}
        setShowModalImportacao={cadastro.setShowModalImportacao}
        openModal={cadastro.openModal}
        tipoFiltro={tipoFiltro}
        pessoasSelecionadasFusao={pessoasSelecionadasFusao}
        onAbrirFusao={abrirModalFusao}
        onLimparSelecaoFusao={limparSelecaoFusao}
      />
      <ClientesNovoCadastroRecenteBanner
        cliente={clienteRecemCriado}
        campoCopiado={campoCopiadoRecente}
        onCopiarCampo={handleCopiarCampoRecente}
        onLimparFiltro={handleLimparFiltroRecente}
      />
      <PessoasDuplicidadeBanner
        sugestoes={duplicidade.sugestoes}
        totalSugestoes={duplicidade.totalSugestoes}
        totalAutomaticas={duplicidade.totalAutomaticas}
        verificando={duplicidade.verificando}
        onVerificar={carregarSugestoesDuplicidade}
        onFundirAutomaticas={() => executarVarreduraDuplicidade({ silencioso: false })}
        onAbrirCentral={abrirCentralDuplicidades}
      />
      {error && !cadastro.showModal && (
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
        highlightedClienteId={clienteRecemCriado?.id}
        expandedPets={expandedPets}
        setExpandedPets={setExpandedPets}
        highlightedPetId={cadastro.highlightedPetId}
        setHighlightedPetId={cadastro.setHighlightedPetId}
        openModal={cadastro.openModal}
        handleDelete={handleDelete}
        handleDeletePet={handleDeletePet}
        pessoasSelecionadasFusao={pessoasSelecionadasFusao}
        togglePessoaFusao={togglePessoaFusao}
      />

      <ClientesNovoModalsLayer {...cadastro.modalsLayerProps} />
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
