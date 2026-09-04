import { Printer, X } from "lucide-react";
import { createPortal } from "react-dom";

import { formatMoneyBRL } from "../../utils/formatters";
import {
  formatarDataComprovante,
  montarTextoComprovanteRecebimento,
} from "../../utils/comprovanteRecebimento";
import ActionButton from "../ui/ActionButton";

function ComprovantePrintArea({ comprovante }) {
  const conteudo = (
    <>
      <style>{`
        @media print {
          body * { visibility: hidden; }
          .comprovante-recebimento-impressao,
          .comprovante-recebimento-impressao * { visibility: visible; }
          .comprovante-recebimento-impressao {
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
        className="comprovante-recebimento-impressao hidden print:block"
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
        {montarTextoComprovanteRecebimento(comprovante)}
      </pre>
    </>
  );

  return globalThis.document?.body ? createPortal(conteudo, globalThis.document.body) : conteudo;
}

export default function ComprovanteRecebimentoModal({ comprovante, onClose }) {
  if (!comprovante) return null;

  return (
    <>
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black bg-opacity-50">
        <div className="mx-4 w-full max-w-md rounded-lg bg-white shadow-xl">
          <div className="flex items-center justify-between border-b p-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Comprovante de recebimento</h3>
              <p className="text-xs text-gray-500">
                Baixa #{comprovante.id || "-"} da conta #{comprovante.contaId || "-"}
              </p>
            </div>
            <ActionButton
              type="button"
              onClick={onClose}
              icon={X}
              intent="neutral"
              tone="ghost"
              size="sm"
              aria-label="Fechar comprovante"
            />
          </div>
          <div className="space-y-3 p-5 text-sm">
            <div>
              <strong>Cliente:</strong> {comprovante.clienteNome}
            </div>
            <div>
              <strong>Conta:</strong> {comprovante.descricao}
            </div>
            <div>
              <strong>Data:</strong> {formatarDataComprovante(comprovante.data)}
            </div>
            <div>
              <strong>Forma:</strong> {comprovante.formaPagamento}
            </div>
            <div className="rounded-lg border border-green-200 bg-green-50 p-3">
              <div className="text-xs font-semibold uppercase text-green-700">Valor recebido</div>
              <div className="text-2xl font-bold text-green-800">
                {formatMoneyBRL(comprovante.valor)}
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-3 border-t p-4">
            <ActionButton type="button" onClick={onClose} intent="neutral" tone="soft" size="md">
              Fechar
            </ActionButton>
            <ActionButton
              type="button"
              onClick={() => globalThis.print()}
              icon={Printer}
              intent="create"
              size="md"
            >
              Imprimir comprovante
            </ActionButton>
          </div>
        </div>
      </div>
      <ComprovantePrintArea comprovante={comprovante} />
    </>
  );
}
