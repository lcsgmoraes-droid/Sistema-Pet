import ResponsiveTabs from "../../../components/ResponsiveTabs";
import { montarAbasProdutoFormulario } from "../../produtosFormUtils";
import ProdutosFormDadosTab from "./ProdutosFormDadosTab";
import ProdutosFormFornecedoresTab from "./ProdutosFormFornecedoresTab";
import ProdutosFormImagensTab from "./ProdutosFormImagensTab";
import ProdutosFormLotesTab from "./ProdutosFormLotesTab";
import ProdutosFormModals from "./ProdutosFormModals";
import ProdutosFormVariacoesTab from "./ProdutosFormVariacoesTab";

export default function ProdutosFormView({ controller }) {
  const {
    abaAtiva,
    abrirNovaVariacao,
    categorias,
    clientes,
    departamentos,
    editarVariacao,
    fornecedorEdit,
    fornecedores,
    handleAddFornecedor,
    handleChange,
    handleDeleteFornecedor,
    handleDeleteImagem,
    handleEditFornecedor,
    handleGerarCodigo,
    handleMovimentoEstoque,
    handleSaveFornecedor,
    handleSaveMovimento,
    handleSetPrincipal,
    handleSubmit,
    handleUploadImagem,
    imagens,
    isEdit,
    loading,
    loadingVariacoes,
    lotes,
    marcas,
    produto,
    salvando,
    setAbaAtiva,
    setProduto,
    setShowModalFornecedor,
    setShowModalLote,
    showModalFornecedor,
    showModalLote,
    tipoMovimento,
    uploadingImage,
    variacoes,
    voltarParaProdutos,
  } = controller;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {isEdit ? "Editar Produto" : "Novo Produto"}
            </h1>
            <p className="text-gray-600 mt-1">
              {isEdit ? `Codigo: ${produto.codigo}` : "Preencha os dados do produto"}
            </p>
          </div>

          <button
            onClick={voltarParaProdutos}
            className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition"
          >
            Fechar
          </button>
        </div>
      </div>

      <ResponsiveTabs
        tabs={montarAbasProdutoFormulario({
          isEdit,
          imagens,
          fornecedores,
          lotes,
          variacoes,
          produto,
        })}
        activeTab={abaAtiva}
        onChange={setAbaAtiva}
      />

      {abaAtiva === "dados" && (
        <ProdutosFormDadosTab
          categorias={categorias}
          departamentos={departamentos}
          handleChange={handleChange}
          handleGerarCodigo={handleGerarCodigo}
          handleSubmit={handleSubmit}
          isEdit={isEdit}
          marcas={marcas}
          onCancel={voltarParaProdutos}
          produto={produto}
          salvando={salvando}
          setProduto={setProduto}
        />
      )}

      {abaAtiva === "imagens" && isEdit && (
        <ProdutosFormImagensTab
          handleDeleteImagem={handleDeleteImagem}
          handleSetPrincipal={handleSetPrincipal}
          handleUploadImagem={handleUploadImagem}
          imagens={imagens}
          uploadingImage={uploadingImage}
        />
      )}

      {abaAtiva === "fornecedores" && isEdit && (
        <ProdutosFormFornecedoresTab
          fornecedores={fornecedores}
          handleAddFornecedor={handleAddFornecedor}
          handleDeleteFornecedor={handleDeleteFornecedor}
          handleEditFornecedor={handleEditFornecedor}
        />
      )}

      {abaAtiva === "lotes" && isEdit && produto.controle_lote && (
        <ProdutosFormLotesTab handleMovimentoEstoque={handleMovimentoEstoque} lotes={lotes} />
      )}

      {abaAtiva === "variacoes" && isEdit && produto.tipo_produto === "PAI" && (
        <ProdutosFormVariacoesTab
          loadingVariacoes={loadingVariacoes}
          onEditarVariacao={editarVariacao}
          onNovaVariacao={abrirNovaVariacao}
          variacoes={variacoes}
        />
      )}

      <ProdutosFormModals
        clientes={clientes}
        fornecedorEdit={fornecedorEdit}
        handleSaveFornecedor={handleSaveFornecedor}
        handleSaveMovimento={handleSaveMovimento}
        setShowModalFornecedor={setShowModalFornecedor}
        setShowModalLote={setShowModalLote}
        showModalFornecedor={showModalFornecedor}
        showModalLote={showModalLote}
        tipoMovimento={tipoMovimento}
      />
    </div>
  );
}
