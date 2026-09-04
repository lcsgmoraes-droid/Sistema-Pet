import { Printer } from "lucide-react";
import { createPortal } from "react-dom";

import { montarTextoSaldoCredito } from "../utils/saldoCreditoPrint";
import ActionButton from "./ui/ActionButton";

function SaldoCreditoPrintArea({ cliente, saldo }) {
  const conteudo = (
    <>
      <style>{`
        @media print {
          body * { visibility: hidden; }
          .saldo-credito-impressao, .saldo-credito-impressao * { visibility: visible; }
          .saldo-credito-impressao {
            position: absolute;
            left: 0;
            top: 0;
            width: 76mm;
            margin: 0;
            padding: 0 1mm;
            color: #000 !important;
          }
          @page { size: 80mm auto; margin: 2mm; }
        }
      `}</style>
      <pre
        className="saldo-credito-impressao hidden print:block"
        style={{
          width: "76mm",
          fontFamily: 'Consolas, "Courier New", monospace',
          fontSize: "13px",
          fontWeight: 800,
          lineHeight: 1.28,
          margin: 0,
          padding: 0,
          whiteSpace: "pre",
        }}
      >
        {montarTextoSaldoCredito(cliente, saldo)}
      </pre>
    </>
  );

  return globalThis.document?.body ? createPortal(conteudo, globalThis.document.body) : conteudo;
}

export default function ImprimirSaldoCredito({ cliente, saldo }) {
  if (!cliente || Number(saldo || 0) <= 0) return null;

  return (
    <>
      <ActionButton
        type="button"
        onClick={() => globalThis.print()}
        icon={Printer}
        intent="neutral"
        tone="soft"
        size="xs"
        className="print:hidden"
        title="Imprimir saldo de crédito do cliente"
      >
        Imprimir saldo
      </ActionButton>
      <SaldoCreditoPrintArea cliente={cliente} saldo={saldo} />
    </>
  );
}
