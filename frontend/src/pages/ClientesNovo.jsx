import { useEffect, useState } from "react";
import { FiAlertCircle } from "react-icons/fi";
import toast from "react-hot-toast";
import api from "../api";
import ClientesNovoActionsBar from "../components/clientes/ClientesNovoActionsBar";
import ClientesNovoCadastroRecenteBanner from "../components/clientes/ClientesNovoCadastroRecenteBanner";
import ClientesNovoModalsLayer from "../components/clientes/ClientesNovoModalsLayer";
import ClientesNovoTabelaSection from "../components/clientes/ClientesNovoTabelaSection";
import ClientesNovoTabsBar from "../components/clientes/ClientesNovoTabsBar";
import { useClientesNovoCadastro } from "../hooks/useClientesNovoCadastro";
import { useClientesNovoListagem } from "../hooks/useClientesNovoListagem";
import { debugLog } from "../utils/debug";

const Pessoas = () => {
  const [error, setError] = useState("");
  const [tipoFiltro, setTipoFiltro] = useState("todos"); // Filtro por tipo: todos, cliente, fornecedor, veterinario, funcionario
  const [expandedPets, setExpandedPets] = useState({});
  const [clienteRecemCriado, setClienteRecemCriado] = useState(null);
  const [campoCopiadoRecente, setCampoCopiadoRecente] = useState("");
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

  const handleSearchTermChange = (value) => {
    setPaginaAtual(1);
    setSearchTerm(value);
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
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Cadastros</h1>
        <p className="text-gray-600 mt-1">
          Gerenciamento de clientes, fornecedores, veterinários, funcionários e
          pets
        </p>
      </div>

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
      />
      <ClientesNovoCadastroRecenteBanner
        cliente={clienteRecemCriado}
        campoCopiado={campoCopiadoRecente}
        onCopiarCampo={handleCopiarCampoRecente}
        onLimparFiltro={handleLimparFiltroRecente}
      />
      {error && !cadastro.showModal && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <FiAlertCircle />
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
      />

      <ClientesNovoModalsLayer {...cadastro.modalsLayerProps} />

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



