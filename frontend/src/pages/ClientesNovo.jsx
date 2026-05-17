import { useEffect, useMemo, useState } from "react";
import { AlertCircle, UsersRound } from "lucide-react";
import toast from "react-hot-toast";
import api from "../api";
import ClientesNovoActionsBar from "../components/clientes/ClientesNovoActionsBar";
import ClientesNovoCadastroRecenteBanner from "../components/clientes/ClientesNovoCadastroRecenteBanner";
import ClientesNovoModalsLayer from "../components/clientes/ClientesNovoModalsLayer";
import ClientesNovoTabelaSection from "../components/clientes/ClientesNovoTabelaSection";
import ClientesNovoTabsBar from "../components/clientes/ClientesNovoTabsBar";
import PessoasFusaoModal from "../components/pessoas/PessoasFusaoModal";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import { useClientesNovoCadastro } from "../hooks/useClientesNovoCadastro";
import { useClientesNovoListagem } from "../hooks/useClientesNovoListagem";
import { debugLog } from "../utils/debug";

const Pessoas = () => {
  const [error, setError] = useState("");
  const [tipoFiltro, setTipoFiltro] = useState("todos"); // Filtro por tipo: todos, cliente, fornecedor, veterinario, funcionario
  const [expandedPets, setExpandedPets] = useState({});
  const [clienteRecemCriado, setClienteRecemCriado] = useState(null);
  const [campoCopiadoRecente, setCampoCopiadoRecente] = useState("");
  const [pessoasSelecionadasFusao, setPessoasSelecionadasFusao] = useState([]);
  const [modalFusaoAberto, setModalFusaoAberto] = useState(false);
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

  const pessoasParaFusao = useMemo(
    () => filteredClientes.filter((cliente) => pessoasSelecionadasFusao.includes(cliente.id)),
    [filteredClientes, pessoasSelecionadasFusao],
  );

  const handleSearchTermChange = (value) => {
    setPaginaAtual(1);
    setSearchTerm(value);
    setPessoasSelecionadasFusao([]);
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
      clientesEncontrados.find(
        (cliente) => String(cliente?.codigo || "").trim() === termo,
      ) || getClientePorCodigoExato(termo);

    if (clienteCodigoExato) {
      setPaginaAtual(1);
      cadastro.openModal(clienteCodigoExato);
    }
  };

  const togglePessoaFusao = (clienteId) => {
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

  const limparSelecaoFusao = () => setPessoasSelecionadasFusao([]);

  const abrirModalFusao = () => {
    if (pessoasSelecionadasFusao.length !== 2) {
      toast.error("Selecione exatamente 2 pessoas para fundir.");
      return;
    }
    setModalFusaoAberto(true);
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

    const clienteNaLista = filteredClientes.some(
      (cliente) => cliente.id === clienteRecemCriado.id,
    );
    if (!clienteNaLista) return;

    const elemento = document.getElementById(
      `cliente-${clienteRecemCriado.id}`,
    );
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
      <PessoasFusaoModal
        isOpen={modalFusaoAberto}
        onClose={() => setModalFusaoAberto(false)}
        onSuccess={async () => {
          setModalFusaoAberto(false);
          limparSelecaoFusao();
          await loadClientes();
        }}
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



