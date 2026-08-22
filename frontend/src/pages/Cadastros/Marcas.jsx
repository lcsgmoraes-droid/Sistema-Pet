import { useEffect, useState } from "react";
import { FiAlertCircle, FiEdit2, FiPlus, FiTrash2 } from "react-icons/fi";
import { deleteMarca, getMarcas } from "../../api/produtos";
import CatalogoProdutoModal from "../../components/produtos/CatalogoProdutoModal";
import ActionButton from "../../components/ui/ActionButton";
import EmptyState from "../../components/ui/EmptyState";
import IconActionButton from "../../components/ui/IconActionButton";
import LoadingState from "../../components/ui/LoadingState";
import { confirmarCorePet } from "../../services/corepetDialog";

const Marcas = () => {
  const [marcas, setMarcas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState(null);

  useEffect(() => {
    carregarMarcas();
  }, []);

  const carregarMarcas = async () => {
    try {
      setLoading(true);
      const response = await getMarcas();
      setMarcas(response.data || []);
    } catch (error) {
      console.error("Erro ao carregar marcas:", error);
      alert("Nao foi possivel carregar as marcas.");
    } finally {
      setLoading(false);
    }
  };

  const handleEditar = (marca) => {
    setEditando(marca);
    setShowModal(true);
  };

  const handleExcluir = async (marca) => {
    if (!await confirmarCorePet(`Deseja realmente excluir a marca "${marca.nome}"?`)) {
      return;
    }

    try {
      await deleteMarca(marca.id);
      sessionStorage.removeItem("produtos_catalogos_cache_v1");
      await carregarMarcas();
    } catch (error) {
      console.error("Erro ao excluir marca:", error);
      alert(error.response?.data?.detail || "Nao foi possivel excluir a marca.");
    }
  };

  const handleNovaMarca = () => {
    setEditando(null);
    setShowModal(true);
  };

  const fecharModal = () => {
    setShowModal(false);
    setEditando(null);
  };

  const handleMarcaSalva = async () => {
    fecharModal();
    await carregarMarcas();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingState label="Carregando marcas..." />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Marcas</h1>
          <p className="text-gray-600 mt-1">
            Marcas ajudam a organizar produtos, filtros e relatorios de estoque.
          </p>
        </div>
        <ActionButton onClick={handleNovaMarca} icon={FiPlus} intent="create" size="md">
          Nova Marca
        </ActionButton>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {marcas.length === 0 ? (
          <EmptyState
            className="m-4"
            description="Crie a primeira marca para classificar produtos no cadastro e nos filtros."
            icon={FiAlertCircle}
            title="Nenhuma marca cadastrada"
            action={
              <ActionButton onClick={handleNovaMarca} icon={FiPlus} intent="create" tone="soft">
                Criar primeira marca
              </ActionButton>
            }
          />
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600">Nome</th>
                <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600">
                  Descricao
                </th>
                <th className="text-right px-4 py-3 text-sm font-semibold text-gray-600">Acoes</th>
              </tr>
            </thead>
            <tbody>
              {marcas.map((marca) => (
                <tr key={marca.id} className="border-b hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{marca.nome}</td>
                  <td className="px-4 py-3 text-gray-600 text-sm">{marca.descricao || "-"}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <IconActionButton
                        onClick={() => handleEditar(marca)}
                        icon={FiEdit2}
                        intent="edit"
                        title="Editar"
                      />
                      <IconActionButton
                        onClick={() => handleExcluir(marca)}
                        icon={FiTrash2}
                        intent="delete"
                        title="Excluir"
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <CatalogoProdutoModal
          tipo="marca"
          item={editando}
          onClose={fecharModal}
          onSaved={handleMarcaSalva}
        />
      )}
    </div>
  );
};

export default Marcas;
