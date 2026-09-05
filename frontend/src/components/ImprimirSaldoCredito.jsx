import { Printer } from "lucide-react";

import { imprimirSaldoCredito } from "../utils/saldoCreditoPrint";
import ActionButton from "./ui/ActionButton";

export default function ImprimirSaldoCredito({ cliente, saldo }) {
  if (!cliente || Number(saldo || 0) <= 0) return null;

  return (
    <ActionButton
      type="button"
      onClick={() => imprimirSaldoCredito(cliente, saldo)}
      icon={Printer}
      intent="neutral"
      tone="soft"
      size="xs"
      className="print:hidden"
      title="Imprimir saldo de crédito do cliente"
    >
      Imprimir saldo
    </ActionButton>
  );
}
