import { formatMoneyBRL } from "./formatters.js";

const LARGURA = 42;

function ascii(texto) {
  return String(texto || "")
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "")
    .replaceAll(/[^\x20-\x7E]/g, " ")
    .replaceAll(/\s+/g, " ")
    .trim();
}

function centralizar(texto) {
  const valor = ascii(texto).slice(0, LARGURA);
  const espacos = Math.max(0, LARGURA - valor.length);
  return `${" ".repeat(Math.floor(espacos / 2))}${valor}`;
}

function quebrar(texto) {
  const palavras = ascii(texto).split(" ");
  const linhas = [];
  let atual = "";
  for (const palavra of palavras) {
    const proxima = atual ? `${atual} ${palavra}` : palavra;
    if (proxima.length <= LARGURA) atual = proxima;
    else {
      if (atual) linhas.push(atual);
      atual = palavra;
    }
  }
  if (atual) linhas.push(atual);
  return linhas;
}

export function montarTextoSaldoCredito(cliente, saldo, emitidoEm = new Date()) {
  const separador = "-".repeat(LARGURA);
  const codigo = cliente?.codigo || cliente?.id || "-";
  return [
    centralizar("PET SHOP PRO"),
    centralizar("COMPROVANTE DE CREDITO"),
    centralizar(emitidoEm.toLocaleString("pt-BR")),
    separador,
    ...quebrar(`Cliente: ${cliente?.nome || "Nao informado"}`),
    `Codigo: ${ascii(codigo)}`,
    separador,
    centralizar("SALDO DISPONIVEL"),
    centralizar(formatMoneyBRL(saldo)),
    separador,
    ...quebrar("Saldo consultado na data e hora acima."),
  ].join("\n");
}

export function imprimirSaldoCredito(cliente, saldo) {
  const texto = montarTextoSaldoCredito(cliente, saldo);
  const frame = globalThis.document.createElement("iframe");
  frame.title = "Comprovante de credito";
  frame.setAttribute("aria-hidden", "true");
  frame.tabIndex = -1;
  frame.style.cssText = "position: fixed; width: 0; height: 0; border: 0;";

  // Um documento separado impede que o saldo e o cupom do PDV se sobreponham.
  frame.onload = () => {
    const janela = frame.contentWindow;
    frame.contentDocument.querySelector("pre").textContent = texto;
    janela.addEventListener("afterprint", () => frame.remove(), { once: true });
    try {
      janela.focus();
      janela.print();
    } catch (erro) {
      frame.remove();
      throw erro;
    }
  };
  frame.srcdoc = `<!doctype html>
    <html lang="pt-BR">
      <head>
        <meta charset="utf-8">
        <title>Comprovante de credito</title>
        <style>
          @page { size: 80mm auto; margin: 2mm; }
          body { margin: 0; color: #000; background: #fff; }
          pre {
            width: 76mm;
            font-family: Consolas, "Courier New", monospace;
            font-size: 13px;
            font-weight: 800;
            line-height: 1.28;
            margin: 0;
            padding: 0;
            white-space: pre;
          }
        </style>
      </head>
      <body><pre></pre></body>
    </html>`;
  globalThis.document.body.appendChild(frame);
}
