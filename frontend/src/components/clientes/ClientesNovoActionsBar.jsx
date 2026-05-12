import { FiPlus, FiSearch, FiUploadCloud } from "react-icons/fi";
import { GitMerge, X } from "lucide-react";

const ClientesNovoActionsBar = ({
  searchTerm,
  setSearchTerm,
  abrirPessoaPorCodigoNoEnter,
  setShowModalImportacao,
  openModal,
  tipoFiltro,
  pessoasSelecionadasFusao = [],
  onAbrirFusao,
  onLimparSelecaoFusao,
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
        {pessoasSelecionadasFusao.length > 0 && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-2 py-1">
            <button
              type="button"
              onClick={onAbrirFusao}
              disabled={pessoasSelecionadasFusao.length !== 2}
              className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-semibold transition-colors ${
                pessoasSelecionadasFusao.length === 2
                  ? "bg-amber-500 text-white hover:bg-amber-600"
                  : "bg-amber-100 text-amber-500 cursor-not-allowed"
              }`}
              title={
                pessoasSelecionadasFusao.length === 2
                  ? "Fundir pessoas selecionadas"
                  : "Selecione exatamente 2 pessoas"
              }
            >
              <GitMerge size={16} />
              Fundir ({pessoasSelecionadasFusao.length})
            </button>
            <button
              type="button"
              onClick={onLimparSelecaoFusao}
              className="rounded-md p-2 text-amber-700 hover:bg-amber-100"
              title="Limpar selecao"
            >
              <X size={16} />
            </button>
          </div>
        )}
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
