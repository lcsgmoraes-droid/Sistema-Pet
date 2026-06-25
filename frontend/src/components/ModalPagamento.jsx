import ModalPerguntaNFe from "./ModalPerguntaNFe";
import ModalPagamentoView from "./modalPagamento/ModalPagamentoView";
import useModalPagamentoController from "./modalPagamento/useModalPagamentoController";

export default function ModalPagamento(props) {
  const { mostrarPerguntaNFe, modalPerguntaNFeProps, viewProps } =
    useModalPagamentoController(props);

  if (mostrarPerguntaNFe) {
    return <ModalPerguntaNFe {...modalPerguntaNFeProps} />;
  }

  return <ModalPagamentoView {...viewProps} onClose={props.onClose} />;
}
