import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { formatMoneyBRL } from "../../utils/formatters";

export default function ImpressaoResumoCaixa({ resumo, onAfterPrint }) {
  const onAfterPrintRef = useRef(onAfterPrint);
  onAfterPrintRef.current = onAfterPrint;

  useEffect(() => {
    if (!resumo) return undefined;

    document.body.classList.add("imprimindo-resumo-caixa");
    const finalizar = () => onAfterPrintRef.current();
    window.addEventListener("afterprint", finalizar);
    const frame = requestAnimationFrame(() => window.print());

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("afterprint", finalizar);
      document.body.classList.remove("imprimindo-resumo-caixa");
    };
  }, [resumo]);

  if (!resumo) return null;

  const itensResumo = [
    ["Total vendido", resumo.total_vendido],
    ["Total recebido", resumo.total_recebido],
    ["Valor de abertura", resumo.caixa.valor_abertura],
    ["Suprimentos", resumo.totais.suprimentos],
    ["Sangria", resumo.totais.sangrias],
    ["Devoluções", resumo.totais.devolucoes],
    ["Despesas", resumo.totais.despesas],
  ];
  const formas = Object.entries(resumo.vendas_por_forma_pagamento || {});
  const recebimentosPorData = Object.entries(resumo.recebimentos_por_data_venda || {}).sort(
    ([dataA], [dataB]) => dataB.localeCompare(dataA),
  );
  const rotuloData = (data) =>
    data === "sem_venda" ? "Sem venda vinculada" : data.split("-").reverse().join("/");
  const totalPorData = (formasDoDia) =>
    Object.values(formasDoDia).reduce((total, dados) => total + dados.total, 0);

  return createPortal(
    <div id="caixa-formas-impressao">
      <style>{`
        @media screen { #caixa-formas-impressao { display: none; } }
        @media print {
          @page { margin: 2mm; }
          body.imprimindo-resumo-caixa > :not(#caixa-formas-impressao) { display: none !important; }
          #caixa-formas-impressao {
            display: block !important;
            box-sizing: border-box;
            width: 100%;
            max-width: 72mm;
            color: #111;
            font: 10pt/1.3 Arial, sans-serif;
          }
          #caixa-formas-impressao h1 { font-size: 12pt; margin: 0 0 2mm; }
          #caixa-formas-impressao h2 { font-size: 10pt; margin: 3mm 0 1mm; }
          #caixa-formas-impressao p { margin: 2mm 0; overflow-wrap: anywhere; }
          #caixa-formas-impressao .linha {
            display: flex;
            justify-content: space-between;
            gap: 2mm;
            border-bottom: 1px solid #bbb;
            padding: 1mm 0;
            break-inside: avoid;
          }
          #caixa-formas-impressao .linha span { flex: 1; min-width: 0; overflow-wrap: anywhere; }
          #caixa-formas-impressao .linha strong { flex-shrink: 0; white-space: nowrap; }
          #caixa-formas-impressao .grupo-data { break-inside: avoid; }
        }
      `}</style>
      <h1>Resumo do caixa</h1>
      <div>
        Caixa #{resumo.caixa.numero_caixa} — {resumo.caixa.usuario_nome}
      </div>
      <div>Abertura: {new Date(resumo.caixa.data_abertura).toLocaleString("pt-BR")}</div>
      {itensResumo.map(([titulo, valor]) => (
        <div className="linha" key={titulo}>
          <span>{titulo}</span>
          <strong>{formatMoneyBRL(valor)}</strong>
        </div>
      ))}
      <h2>Formas de pagamento</h2>
      {formas.map(([forma, dados]) => (
        <div className="linha" key={forma}>
          <span>
            {forma} · {dados.quantidade} {dados.tipo_contagem || "pagamento"}
            {dados.quantidade !== 1 ? "s" : ""}
          </span>
          <strong>{formatMoneyBRL(dados.total)}</strong>
        </div>
      ))}
      {recebimentosPorData.length > 0 && (
        <>
          <h2>Conferência por data da venda</h2>
          {recebimentosPorData.map(([data, formasDoDia]) => (
            <div className="grupo-data" key={data}>
              <div className="linha">
                <strong>{rotuloData(data)}</strong>
                <strong>{formatMoneyBRL(totalPorData(formasDoDia))}</strong>
              </div>
              {Object.entries(formasDoDia).map(([forma, dados]) => (
                <div className="linha" key={forma}>
                  <span>
                    {forma} · {dados.quantidade}
                  </span>
                  <strong>{formatMoneyBRL(dados.total)}</strong>
                </div>
              ))}
            </div>
          ))}
        </>
      )}
      <p>
        Dinheiro corresponde às entradas registradas no extrato deste caixa. As demais formas não
        afetam o saldo físico.
      </p>
    </div>,
    document.body,
  );
}
