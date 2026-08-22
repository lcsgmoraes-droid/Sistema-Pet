import ProdutosNovoEntradaModal from "./ProdutosNovoEntradaModal";
import ProdutosNovoFornecedorModal from "./ProdutosNovoFornecedorModal";
import ProdutosNovoLoteModal from "./ProdutosNovoLoteModal";
import ProdutosCompostosPrecoVendaModal from "./ProdutosCompostosPrecoVendaModal";

export default function ProdutosNovoModalsLayer({
  entradaModalProps,
  fornecedorModalProps,
  loteModalProps,
  precosCompostosModalProps,
}) {
  return (
    <>
      {entradaModalProps && <ProdutosNovoEntradaModal {...entradaModalProps} />}
      {loteModalProps && <ProdutosNovoLoteModal {...loteModalProps} />}
      {fornecedorModalProps && <ProdutosNovoFornecedorModal {...fornecedorModalProps} />}
      {precosCompostosModalProps && (
        <ProdutosCompostosPrecoVendaModal {...precosCompostosModalProps} />
      )}
    </>
  );
}
