import { useEffect } from "react";
import { createPortal } from "react-dom";
import { formatMoneyBRL } from "../../utils/formatters";
import { useDadosCupomEmpresa } from "../../hooks/useDadosCupomEmpresa";

const dataHora = (valor) => (valor ? new Date(valor).toLocaleString("pt-BR") : "—");

export default function ImpressaoTermicaCaixa({ documento, onAfterPrint }) {
  const { carregandoEmpresa, dadosEmpresa } = useDadosCupomEmpresa();
  useEffect(() => {
    if (!documento || carregandoEmpresa) return undefined;
    const finalizar = () => onAfterPrint();
    window.addEventListener("afterprint", finalizar);
    const frame = requestAnimationFrame(() => window.print());
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("afterprint", finalizar);
    };
  }, [documento, carregandoEmpresa, onAfterPrint]);

  if (!documento) return null;

  const { movimento, resumo } = documento;
  const linhas = resumo
    ? [
        ["Abertura", resumo.caixa.valor_abertura],
        ["Total vendido", resumo.total_vendido],
        ["Total recebido", resumo.total_recebido],
        ...Object.entries(resumo.vendas_por_forma_pagamento || {}).map(([forma, dados]) => [
          ["crediario", "crediário", "boleto"].includes(forma.trim().toLocaleLowerCase("pt-BR"))
            ? `${forma} (a prazo)`
            : forma,
          dados.total,
        ]),
        ["Suprimentos", resumo.totais.suprimentos],
        ["Entradas em dinheiro", resumo.totais.vendas + resumo.totais.suprimentos],
        ["Sangrias", resumo.totais.sangrias],
        ["Despesas", resumo.totais.despesas],
        ["Devoluções", resumo.totais.devolucoes],
        ["Transferências", resumo.totais.transferencias],
        ["Saldo esperado em dinheiro", resumo.totais.saldo_atual],
        ["Valor contado", resumo.caixa.valor_informado],
        ["Diferença", resumo.caixa.diferenca],
      ]
    : [];

  return createPortal(
    <div id="documento-termico-caixa">
      <style>{`
        @media screen { #documento-termico-caixa { display: none; } }
        @media print {
          @page { margin: 4mm; }
          body * { visibility: hidden !important; }
          #documento-termico-caixa, #documento-termico-caixa * { visibility: visible !important; }
          #documento-termico-caixa { display: block !important; position: absolute; left: 0; top: 0; width: 72mm; color: #000; font: 11px Arial, sans-serif; }
          #documento-termico-caixa h1 { font-size: 14px; text-align: center; margin: 0 0 7px; }
          #documento-termico-caixa p { margin: 3px 0; overflow-wrap: anywhere; }
          #documento-termico-caixa .linha { display: flex; justify-content: space-between; gap: 4px; margin: 3px 0; }
          #documento-termico-caixa .linha span:first-child { max-width: 52%; }
          #documento-termico-caixa .assinatura { margin-top: 22px; text-align: center; }
          #documento-termico-caixa hr { border: 0; border-top: 1px dashed #000; margin: 8px 0; }
        }
      `}</style>
      {movimento ? (
        <>
          <h1>{dadosEmpresa.nome_fantasia || dadosEmpresa.razao_social || "ESTABELECIMENTO"}</h1>
          {dadosEmpresa.cnpj && <p style={{ textAlign: "center" }}>CNPJ: {dadosEmpresa.cnpj}</p>}
          <h1>COMPROVANTE DE {movimento.tipo === "sangria" ? "SANGRIA" : "SUPRIMENTO"}</h1>
          <p>
            Caixa #{documento.numeroCaixa} · Lançamento #{movimento.id}
          </p>
          <p>Data: {dataHora(movimento.data_movimento)}</p>
          <p>Responsável: {movimento.usuario_nome}</p>
          <hr />
          <div className="linha">
            <strong>Valor</strong>
            <strong>{formatMoneyBRL(movimento.valor)}</strong>
          </div>
          <p>
            {movimento.tipo === "sangria" ? "Destino" : "Origem"}:{" "}
            {(movimento.tipo === "sangria"
              ? movimento.conta_destino_nome
              : movimento.conta_origem_nome) || "Não informado"}
          </p>
          <p>Motivo: {movimento.descricao || "Não informado"}</p>
          <hr />
          <div className="assinatura">
            ____________________________
            <br />
            Assinatura de quem entregou
          </div>
          <div className="assinatura">
            ____________________________
            <br />
            Assinatura de quem recebeu
          </div>
        </>
      ) : (
        <>
          <h1>{dadosEmpresa.nome_fantasia || dadosEmpresa.razao_social || "ESTABELECIMENTO"}</h1>
          {dadosEmpresa.cnpj && <p style={{ textAlign: "center" }}>CNPJ: {dadosEmpresa.cnpj}</p>}
          <h1>FECHAMENTO DE CAIXA</h1>
          <p>
            Caixa #{resumo.caixa.numero_caixa} · {resumo.caixa.usuario_nome}
          </p>
          <p>Abertura: {dataHora(resumo.caixa.data_abertura)}</p>
          <p>Fechamento: {dataHora(resumo.caixa.data_fechamento)}</p>
          <hr />
          {linhas.map(([rotulo, valor]) => (
            <div className="linha" key={rotulo}>
              <span>{rotulo}</span>
              <strong>{formatMoneyBRL(valor ?? 0)}</strong>
            </div>
          ))}
          <hr />
          <p>
            Vendido e recebido são indicadores separados. Formas a prazo não entram no recebido.
            Abertura e suprimentos não são vendas.
          </p>
          <div className="assinatura">
            ____________________________
            <br />
            Responsável pelo caixa
          </div>
          <div className="assinatura">
            ____________________________
            <br />
            Conferente
          </div>
        </>
      )}
    </div>,
    document.body,
  );
}
