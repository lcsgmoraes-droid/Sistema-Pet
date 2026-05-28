import {
  ArrowLeftRight,
  Banknote,
  CreditCard,
  QrCode,
  Receipt,
  Wallet,
} from "lucide-react";

import { identificarIconeFormaPagamento } from "./modalPagamentoUtils";

const ICONES_FORMA_PAGAMENTO = {
  qr_code: QrCode,
  banknote: Banknote,
  credit_card: CreditCard,
  transfer: ArrowLeftRight,
  receipt: Receipt,
  wallet: Wallet,
};

export default function PaymentMethodIcon({ icone, nome, className = "w-6 h-6" }) {
  const Icone =
    ICONES_FORMA_PAGAMENTO[identificarIconeFormaPagamento(icone, nome)] ||
    CreditCard;

  return <Icone className={className} />;
}
