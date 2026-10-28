import { AlertTriangle, ExternalLink } from "lucide-react";
import BotaoInteracao from "../BotaoInteracao/BotaoInteracao";
import { urlConsultaVendaPdv } from "../../../utils/conferenciaFechamentoUtils";
import { formatMoneyBRL } from "../../../utils/formatters";
import { pagamentoLegadoParaConferir, pagamentoPrecisaConferencia } from "./pagamentosPresentation";

export function abrirConsultaPagamentoVenda(vendaId) {
  const url = urlConsultaVendaPdv(vendaId);
  if (url) window.open(url, "_blank", "noopener,noreferrer");
}

export default function AvisoPagamentoVenda({ venda, diferenca }) {
  if (!pagamentoPrecisaConferencia(venda, diferenca)) return null;
  const legado = pagamentoLegadoParaConferir(venda);
  const diferencaConferir = diferenca?.motivo === "devolucao" ? null : diferenca;
  const url = urlConsultaVendaPdv(venda.venda_id);
  return (
    <aside
      aria-label="Pagamento a conferir"
      className="mt-3 space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 font-bold">
          <AlertTriangle className="h-4 w-4" aria-hidden="true" /> Conferir pagamento
        </p>
        {url && (
          <BotaoInteracao
            tamanho="pequeno"
            icon={ExternalLink}
            onClick={() => abrirConsultaPagamentoVenda(venda.venda_id)}
            aria-label={`Corrigir pagamento da venda ${venda.numero_venda || venda.venda_id} em outra aba`}
          >
            Corrigir
          </BotaoInteracao>
        )}
      </div>
      {diferencaConferir ? (
        <>
          <p>
            Pagamentos registrados:{" "}
            <strong>{formatMoneyBRL(diferencaConferir.total_pagamentos_registrados)}</strong>
            {" · "}Aplicado à venda: <strong>{formatMoneyBRL(diferencaConferir.valor_pago)}</strong>
            {" · "}Diferença: <strong>{formatMoneyBRL(diferencaConferir.diferenca)}</strong>
          </p>
          {(diferencaConferir.formas_pagamento || []).map((forma) => (
            <p key={forma.forma_pagamento}>
              {forma.forma_pagamento}: {formatMoneyBRL(forma.total)}
            </p>
          ))}
          <p>
            {diferencaConferir.motivo === "pagamento_acima_total_venda"
              ? "Os pagamentos registrados estão acima do valor aplicado à venda. Confira os descontos, os créditos utilizados e os pagamentos."
              : "A quitação considerada na venda não corresponde ao histórico de pagamentos recuperado. Confira os registros."}
          </p>
        </>
      ) : (
        <p>
          {legado.forma_pagamento === "Quitação legada pelo status da venda"
            ? "A venda foi considerada quitada pelo status, sem histórico detalhado do recebimento. Confira os registros e a forma de pagamento."
            : "Este recebimento legado não tem a forma detalhada neste histórico. Confira os registros da venda."}
        </p>
      )}
      <p>Corrigir abre a venda para consulta em outra aba e uso do procedimento normal.</p>
    </aside>
  );
}
