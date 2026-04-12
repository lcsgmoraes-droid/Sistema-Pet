import { FiPlus, FiSearch, FiUploadCloud } from "react-icons/fi";

const ClientesNovoActionsBar = ({
  searchTerm,
  setSearchTerm,
  abrirPessoaPorCodigoNoEnter,
  setShowModalImportacao,
  openModal,
  tipoFiltro,
}) => {
  const labelNovo =
    tipoFiltro === "cliente"
      ? "Cliente"
      : tipoFiltro === "fornecedor"
        ? "Fornecedor"
        : tipoFiltro === "veterinario"
          ? "Veterinario"
          : tipoFiltro === "funcionario"
            ? "Funcionario"
            : "Cadastro";

  return (
    <div className="bg-white rounded-lg shadow-sm p-4 mb-6 flex flex-col sm:flex-row gap-4 justify-between">
      <div className="relative flex-1 max-w-md">
        <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por codigo, nome, CPF/CNPJ, email ou telefone..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              abrirPessoaPorCodigoNoEnter();
            }
          }}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => setShowModalImportacao(true)}
          className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          <FiUploadCloud /> Importar Excel
        </button>
        <button
          onClick={() => openModal(null, tipoFiltro)}
          className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          <FiPlus /> Novo {labelNovo}
        </button>
      </div>
    </div>
  );
};

export default ClientesNovoActionsBar;
