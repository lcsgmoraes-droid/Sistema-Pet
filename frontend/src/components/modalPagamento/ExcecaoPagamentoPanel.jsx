import { useId, useState } from "react";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";
import { formatMoneyBRL } from "../../utils/formatters";
import { excecaoPagamentoAutorizada } from "./modalPagamentoExcedente";

export default function ExcecaoPagamentoPanel({
  composicao,
  autorizacao,
  onConfirmar,
  disabled = false,
}) {
  const id = useId();
  const [justificativa, setJustificativa] = useState("");
  const [erro, setErro] = useState("");
  if (!composicao || composicao.excedente <= 0) return null;
  const confirmada = excecaoPagamentoAutorizada(composicao, autorizacao);
  return (
    <section
      aria-label="Exceção de pagamento excedente"
      className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-100"
    >
      <h3 className="text-sm font-bold">Pagamento acima do total líquido</h3>
      <dl className="space-y-1 text-sm">
        {[
          ["Total líquido da venda", composicao.valorTotal],
          ["Pagamentos já registrados", composicao.totalPagoExistente],
          ["Novos pagamentos", composicao.novosPagamentos],
          ...(composicao.contexto
            ? [["Crediário pendente (a receber)", composicao.contexto.crediario_pendente]]
            : []),
          ["Excedente", composicao.excedente],
        ].map(([rotulo, valor]) => (
          <div key={rotulo} className="flex justify-between gap-3">
            <dt>{rotulo}</dt>
            <dd className="font-semibold">{formatMoneyBRL(valor)}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs">
        Confira os valores. Uma exceção registra o pagamento integral com motivo; não cria troco em
        cartão, Pix ou outras formas.
      </p>
      {confirmada ? (
        <div className="space-y-1 text-xs" role="status">
          <p className="font-semibold">Exceção confirmada para estes valores.</p>
          <p className="whitespace-pre-wrap break-words">{autorizacao.justificativa}</p>
        </div>
      ) : (
        <>
          <InputTextoLongo
            id={`justificativa-excedente-${id}`}
            label="Justificativa do pagamento excedente"
            value={justificativa}
            required
            disabled={disabled}
            linhas={3}
            maxLength={1000}
            error={erro}
            help="Descreva o motivo com pelo menos 10 caracteres. Alterar os valores exige nova confirmação."
            onChange={(valor) => {
              setJustificativa(valor);
              setErro("");
            }}
          />
          <BotaoInteracao
            disabled={disabled}
            onClick={() => {
              const motivo = justificativa.trim();
              if (motivo.length < 10 || motivo.length > 1000) {
                setErro("Informe uma justificativa de 10 a 1000 caracteres.");
                return;
              }
              onConfirmar({
                chave: composicao.chave,
                justificativa: motivo,
                contexto: composicao.contexto,
              });
            }}
          >
            Confirmar exceção com justificativa
          </BotaoInteracao>
        </>
      )}
    </section>
  );
}
