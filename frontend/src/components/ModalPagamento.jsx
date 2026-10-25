import ModalPerguntaNFe from "./ModalPerguntaNFe";
import ModalPagamentoView from "./modalPagamento/ModalPagamentoView";
import useModalPagamentoController from "./modalPagamento/useModalPagamentoController";
import { isIfoodManualPaymentBlocked } from "../utils/ifoodPdvPilot";
import IfoodPdvOnlineResumo from "./ifood/IfoodPdvOnlineResumo";
import BotaoCancelar from "./v2/BotaoCancelar/BotaoCancelar";

function ModalPagamentoPadrao(props) {
  const { mostrarPerguntaNFe, modalPerguntaNFeProps, viewProps } =
    useModalPagamentoController(props);

  if (mostrarPerguntaNFe) {
    return <ModalPerguntaNFe {...modalPerguntaNFeProps} />;
  }

  return <ModalPagamentoView {...viewProps} onClose={props.onClose} />;
}

export default function ModalPagamento(props) {
  if (isIfoodManualPaymentBlocked(props.venda)) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
        <section
          role="dialog"
          aria-modal="true"
          aria-label="Pagamento externo do iFood"
          className="w-full max-w-lg rounded-xl bg-white p-5 dark:bg-slate-900"
        >
          <IfoodPdvOnlineResumo bridge={props.venda.ifood_pdv_pilot} />
          <p className="my-3 text-sm text-slate-700 dark:text-slate-200">
            A cobrança manual deste pedido iFood está bloqueada. Confira o resumo do piloto no
            pedido; não registre um novo pagamento.
          </p>
          <BotaoCancelar onClick={props.onClose}>Fechar</BotaoCancelar>
        </section>
      </div>
    );
  }
  return <ModalPagamentoPadrao {...props} />;
}
