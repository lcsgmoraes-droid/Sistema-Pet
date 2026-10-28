import { Printer } from "lucide-react";
import { createPortal } from "react-dom";

import { formatMoneyBRL } from "../../utils/formatters";
import {
  formatarDataComprovante,
  montarTextoComprovanteRecebimento,
} from "../../utils/comprovanteRecebimento";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";

function ComprovantePrintArea({ comprovantes }) {
  const conteudo = (
    <>
      <style>{`
        @media print {
          body > :not(.comprovante-recebimento-impressao) { display: none !important; }
          .comprovante-recebimento-impressao {
            display: block !important;
            width: 76mm;
            margin: 0;
            padding: 0 1mm;
            color: #000 !important;
          }
          .comprovante-recebimento-impressao pre + pre {
            break-before: page;
            page-break-before: always;
          }
          @page { size: 80mm auto; margin: 2mm; }
        }
      `}</style>
      <div className="comprovante-recebimento-impressao hidden print:block">
        {comprovantes.map((comprovante) => (
          <pre
            key={`${comprovante.contaId}-${comprovante.id}`}
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
        ))}
      </div>
    </>
  );

  return globalThis.document?.body ? createPortal(conteudo, globalThis.document.body) : conteudo;
}

export default function ComprovanteRecebimentoModal({
  comprovantes = [],
  perguntarImpressao = false,
  onClose,
}) {
  if (comprovantes.length === 0) return null;

  const lote = comprovantes.length > 1;
  const titulo = perguntarImpressao
    ? lote
      ? "Deseja imprimir os comprovantes?"
      : "Deseja imprimir o comprovante?"
    : "Comprovante de recebimento";

  return (
    <>
      <div className="fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-label={titulo}>
        <ModalPadrao
          titulo={titulo}
          tamanho="pequena"
          onFechar={onClose}
          rodape={
            <div className="flex w-full flex-wrap justify-end gap-3">
              <BotaoCancelar onClick={onClose}>
                {perguntarImpressao ? "Agora não" : "Fechar"}
              </BotaoCancelar>
              <BotaoInteracao onClick={() => globalThis.print()} icon={Printer}>
                {perguntarImpressao ? "Sim, imprimir" : "Imprimir comprovante"}
              </BotaoInteracao>
            </div>
          }
        >
          <div className="space-y-4 text-sm text-gray-900 dark:text-slate-100">
            {perguntarImpressao && (
              <p className="font-medium text-green-700 dark:text-green-400">
                {lote ? "Pagamentos registrados com sucesso." : "Pagamento registrado com sucesso."}
              </p>
            )}
            {comprovantes.map((comprovante) => (
              <article
                key={`${comprovante.contaId}-${comprovante.id}`}
                className="space-y-3 rounded-lg border border-gray-200 p-3 dark:border-slate-700"
              >
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  Baixa #{comprovante.id || "-"} da conta #{comprovante.contaId || "-"}
                </p>
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
                <div className="rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-950/40">
                  <div className="text-xs font-semibold uppercase text-green-700 dark:text-green-400">
                    Valor recebido
                  </div>
                  <div className="text-2xl font-bold text-green-800 dark:text-green-300">
                    {formatMoneyBRL(comprovante.valor)}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </ModalPadrao>
      </div>
      <ComprovantePrintArea comprovantes={comprovantes} />
    </>
  );
}
