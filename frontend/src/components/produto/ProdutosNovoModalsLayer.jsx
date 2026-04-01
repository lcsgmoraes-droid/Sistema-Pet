import ProdutosNovoEntradaModal from './ProdutosNovoEntradaModal';
import ProdutosNovoFornecedorModal from './ProdutosNovoFornecedorModal';
import ProdutosNovoLoteModal from './ProdutosNovoLoteModal';

export default function ProdutosNovoModalsLayer({
  entradaModalProps,
  fornecedorModalProps,
  loteModalProps,
}) {
  return (
    <>
      {entradaModalProps && <ProdutosNovoEntradaModal {...entradaModalProps} />}
      {loteModalProps && <ProdutosNovoLoteModal {...loteModalProps} />}
      {fornecedorModalProps && <ProdutosNovoFornecedorModal {...fornecedorModalProps} />}
    </>
  );
}
