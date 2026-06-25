import { Filter, X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";

export default function ComissoesListagemFiltros({ controller }) {
  const {
    aplicarFiltros,
    comissoes,
    filtros,
    funcionariosFiltrados,
    gruposDisponiveis,
    handleFiltroChange,
    limparFiltros,
    loading,
    loadingFuncionarios,
    mostrarDropdownFuncionario,
    mostrarDropdownGrupo,
    mostrarDropdownProduto,
    produtosDisponiveis,
    selecionarFuncionario,
    selecionarGrupo,
    selecionarProduto,
    setFiltros,
    setFuncionarioSelecionado,
    setGrupoSelecionado,
    setMostrarDropdownFuncionario,
    setMostrarDropdownGrupo,
    setMostrarDropdownProduto,
    setProdutoSelecionado,
    setTermoBuscaFuncionario,
    setTermoBuscaGrupo,
    setTermoBuscaProduto,
    setTipoFiltroData,
    termoBuscaFuncionario,
    termoBuscaGrupo,
    termoBuscaProduto,
    tipoFiltroData,
  } = controller;
  // Filtrar produtos e grupos
  const produtosFiltrados = (produtosDisponiveis || []).filter((p) =>
    p?.nome?.toLowerCase().includes(termoBuscaProduto.toLowerCase()),
  );

  const gruposFiltrados = (gruposDisponiveis || []).filter((g) =>
    g?.nome?.toLowerCase().includes(termoBuscaGrupo.toLowerCase()),
  );

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800">Filtros</h3>
        <span className="text-xs text-gray-500">
          {comissoes.length} registro{comissoes.length !== 1 ? "s" : ""} encontrado
          {comissoes.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Filtro de Período */}
      <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">📅 Período</h4>
        <div className="flex gap-4 mb-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="ate_hoje"
              checked={tipoFiltroData === "ate_hoje"}
              onChange={(e) => {
                setTipoFiltroData(e.target.value);
                const hoje = new Date().toISOString().split("T")[0];
                setFiltros((prev) => ({ ...prev, data_inicio: "", data_fim: hoje }));
              }}
              className="text-blue-600"
            />
            <span className="text-sm font-medium">Até hoje</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="personalizado"
              checked={tipoFiltroData === "personalizado"}
              onChange={(e) => setTipoFiltroData(e.target.value)}
              className="text-blue-600"
            />
            <span className="text-sm font-medium">Período personalizado</span>
          </label>
        </div>

        {tipoFiltroData === "personalizado" && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Data Início</label>
              <input
                type="date"
                value={filtros.data_inicio}
                onChange={(e) => handleFiltroChange("data_inicio", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Data Fim</label>
              <input
                type="date"
                value={filtros.data_fim}
                onChange={(e) => handleFiltroChange("data_fim", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        {/* Funcionário (Autocomplete) */}
        <div className="relative autocomplete-container">
          <label className="block text-sm font-medium text-gray-700 mb-1">Funcionário</label>
          <input
            type="text"
            value={termoBuscaFuncionario}
            onChange={(e) => {
              setTermoBuscaFuncionario(e.target.value);
              setMostrarDropdownFuncionario(true);
              if (e.target.value === "") {
                setFuncionarioSelecionado(null);
                setFiltros((prev) => ({ ...prev, funcionario_id: "" }));
              }
            }}
            onFocus={() => setMostrarDropdownFuncionario(true)}
            disabled={loadingFuncionarios}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            placeholder={loadingFuncionarios ? "Carregando..." : "Digite o nome"}
          />

          {mostrarDropdownFuncionario && termoBuscaFuncionario && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
              {funcionariosFiltrados.length > 0 ? (
                funcionariosFiltrados.map((func) => (
                  <div
                    key={func.id}
                    onClick={() => selecionarFuncionario(func)}
                    className="px-3 py-2 hover:bg-blue-50 cursor-pointer transition-colors"
                  >
                    <div className="font-medium text-gray-900">{func.nome}</div>
                    <div className="text-xs text-gray-500">ID: {func.id}</div>
                  </div>
                ))
              ) : (
                <div className="px-3 py-2 text-gray-500 text-sm">Nenhum funcionário encontrado</div>
              )}
            </div>
          )}
        </div>

        {/* Produto (Autocomplete) */}
        <div className="relative autocomplete-container">
          <label className="block text-sm font-medium text-gray-700 mb-1">Produto</label>
          <input
            type="text"
            value={termoBuscaProduto}
            onChange={(e) => {
              setTermoBuscaProduto(e.target.value);
              setMostrarDropdownProduto(true);
              if (e.target.value === "") {
                setProdutoSelecionado(null);
                setFiltros((prev) => ({ ...prev, produto_id: "" }));
              }
            }}
            onFocus={() => setMostrarDropdownProduto(true)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="Digite o nome do produto"
          />

          {mostrarDropdownProduto && termoBuscaProduto && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
              {produtosFiltrados.length > 0 ? (
                produtosFiltrados.map((prod) => (
                  <div
                    key={prod.id}
                    onClick={() => selecionarProduto(prod)}
                    className="px-3 py-2 hover:bg-blue-50 cursor-pointer transition-colors"
                  >
                    <div className="font-medium text-gray-900">{prod.nome}</div>
                    <div className="text-xs text-gray-500">ID: {prod.id}</div>
                  </div>
                ))
              ) : (
                <div className="px-3 py-2 text-gray-500 text-sm">Nenhum produto encontrado</div>
              )}
            </div>
          )}
        </div>

        {/* Grupo/Categoria (Autocomplete) */}
        <div className="relative autocomplete-container">
          <label className="block text-sm font-medium text-gray-700 mb-1">Grupo/Categoria</label>
          <input
            type="text"
            value={termoBuscaGrupo}
            onChange={(e) => {
              setTermoBuscaGrupo(e.target.value);
              setMostrarDropdownGrupo(true);
              if (e.target.value === "") {
                setGrupoSelecionado(null);
                setFiltros((prev) => ({ ...prev, grupo_id: "" }));
              }
            }}
            onFocus={() => setMostrarDropdownGrupo(true)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="Digite o nome do grupo"
          />

          {mostrarDropdownGrupo && termoBuscaGrupo && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
              {gruposFiltrados.length > 0 ? (
                gruposFiltrados.map((grupo) => (
                  <div
                    key={grupo.id}
                    onClick={() => selecionarGrupo(grupo)}
                    className="px-3 py-2 hover:bg-blue-50 cursor-pointer transition-colors"
                  >
                    <div className="font-medium text-gray-900">{grupo.nome}</div>
                    <div className="text-xs text-gray-500">ID: {grupo.id}</div>
                  </div>
                ))
              ) : (
                <div className="px-3 py-2 text-gray-500 text-sm">Nenhum grupo encontrado</div>
              )}
            </div>
          )}
        </div>

        {/* Status */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select
            value={filtros.status}
            onChange={(e) => handleFiltroChange("status", e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos</option>
            <option value="pendente">Pendente</option>
            <option value="pago">Pago</option>
            <option value="estornado">Estornado</option>
          </select>
        </div>
      </div>

      {/* Botões de Ação */}
      <div className="flex gap-3">
        <ActionButton
          onClick={aplicarFiltros}
          disabled={loading}
          icon={Filter}
          intent="edit"
          size="md"
        >
          Filtrar
        </ActionButton>

        <ActionButton
          onClick={limparFiltros}
          disabled={loading}
          icon={X}
          intent="neutral"
          size="md"
          tone="soft"
        >
          Limpar Filtros
        </ActionButton>
      </div>
    </div>
  );
}
