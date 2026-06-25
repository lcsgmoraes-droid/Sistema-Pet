import ModalFornecedor from "../ModalFornecedorProduto";
import ModalMovimentoEstoque from "../ModalMovimentoEstoqueProduto";

export default function ProdutosFormModals({
  clientes,
  fornecedorEdit,
  handleSaveFornecedor,
  handleSaveMovimento,
  setShowModalFornecedor,
  setShowModalLote,
  showModalFornecedor,
  showModalLote,
  tipoMovimento,
}) {
  return (
    <>
      {showModalFornecedor && (
        <ModalFornecedor
          fornecedor={fornecedorEdit}
          clientes={clientes}
          onSave={handleSaveFornecedor}
          onClose={() => setShowModalFornecedor(false)}
        />
      )}

      {showModalLote && (
        <ModalMovimentoEstoque
          tipo={tipoMovimento}
          onSave={handleSaveMovimento}
          onClose={() => setShowModalLote(false)}
        />
      )}
    </>
  );
}
