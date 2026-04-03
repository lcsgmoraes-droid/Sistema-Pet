import { useState } from "react";
import { FiAlertCircle } from "react-icons/fi";
import api from "../api";
import ClientesNovoActionsBar from "../components/clientes/ClientesNovoActionsBar";
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


  const cadastro = useClientesNovoCadastro({
    tipoFiltro,
    clientes,
    loadClientes,
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

  const abrirPessoaPorCodigoNoEnter = () => {
    const termo = String(searchTerm || "").trim();
    if (!termo) return;

    const clienteCodigoExato = getClientePorCodigoExato(termo);

    if (clienteCodigoExato) {
      cadastro.openModal(clienteCodigoExato);
    }
  };

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
        setSearchTerm={setSearchTerm}
        abrirPessoaPorCodigoNoEnter={abrirPessoaPorCodigoNoEnter}
        setShowModalImportacao={cadastro.setShowModalImportacao}
        openModal={cadastro.openModal}
        tipoFiltro={tipoFiltro}
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



