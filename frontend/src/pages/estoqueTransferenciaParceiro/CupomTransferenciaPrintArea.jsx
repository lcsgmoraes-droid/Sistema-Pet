export default function CupomTransferenciaPrintArea({ cupomTransferencia }) {
  return (
    <>
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }

          .transferencia-cupom-impressao,
          .transferencia-cupom-impressao * {
            visibility: visible;
          }

          .transferencia-cupom-impressao {
            position: absolute;
            left: 0;
            top: 0;
            width: 76mm;
            margin: 0;
            padding: 0 1mm;
            color: #000 !important;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }

          @page {
            size: 80mm auto;
            margin: 2mm;
          }
        }
      `}</style>
      <pre
        className="transferencia-cupom-impressao hidden print:block"
        style={{
          width: "76mm",
          fontFamily: 'Consolas, "Courier New", monospace',
          fontSize: "13px",
          fontWeight: 800,
          letterSpacing: "0.1px",
          lineHeight: 1.28,
          margin: 0,
          padding: 0,
          whiteSpace: "pre",
        }}
      >
        {cupomTransferencia}
      </pre>
    </>
  );
}
