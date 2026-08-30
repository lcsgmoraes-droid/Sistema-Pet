import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";

import { calcularDimensoesCaptura, FORMATOS_OFERTA } from "./ofertasEstudioUtils";

async function aguardarImagens(elemento) {
  const imagens = Array.from(elemento.querySelectorAll("img"));
  const imagensDeProduto = Array.from(elemento.querySelectorAll("[data-oferta-image-url]"))
    .map((imagem) => imagem.dataset.ofertaImageUrl)
    .filter(Boolean);
  await Promise.all([
    ...imagensDeProduto.map(
      (url) =>
        new Promise((resolve, reject) => {
          const imagem = new Image();
          imagem.crossOrigin = "anonymous";
          imagem.onload = resolve;
          imagem.onerror = () => reject(new Error("Uma imagem da arte não pôde ser carregada."));
          imagem.src = url;
        }),
    ),
    ...imagens.map(
      (imagem) =>
        new Promise((resolve, reject) => {
          if (imagem.complete) {
            if (imagem.naturalWidth > 0) resolve();
            else reject(new Error("Uma imagem da arte não pôde ser carregada."));
            return;
          }
          imagem.addEventListener("load", resolve, { once: true });
          imagem.addEventListener(
            "error",
            () => reject(new Error("Uma imagem da arte não pôde ser carregada.")),
            { once: true },
          );
        }),
    ),
  ]);
}

export async function capturarPaginasOferta(container, formato) {
  const elementos = Array.from(container?.querySelectorAll("[data-oferta-page]") || []);
  if (!elementos.length) throw new Error("Selecione ao menos um produto.");

  const dimensoes = calcularDimensoesCaptura(formato);
  const canvases = [];
  for (const elemento of elementos) {
    const palco = document.createElement("div");
    const pagina = elemento.cloneNode(true);
    Object.assign(palco.style, {
      position: "fixed",
      inset: "0 auto auto 0",
      width: `${dimensoes.largura}px`,
      height: `${dimensoes.altura}px`,
      pointerEvents: "none",
      zIndex: "-2147483647",
    });
    Object.assign(pagina.style, {
      width: `${dimensoes.largura}px`,
      height: `${dimensoes.altura}px`,
      maxWidth: "none",
      aspectRatio: "auto",
    });
    pagina.dataset.ofertaExportando = "true";
    palco.appendChild(pagina);
    document.body.appendChild(palco);
    try {
      await aguardarImagens(pagina);
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      canvases.push(
        await html2canvas(pagina, {
          scale: dimensoes.escala,
          width: dimensoes.largura,
          height: dimensoes.altura,
          windowWidth: dimensoes.largura,
          windowHeight: Math.ceil(dimensoes.altura),
          scrollX: 0,
          scrollY: 0,
          useCORS: true,
          backgroundColor: "#ffffff",
          logging: false,
        }),
      );
    } finally {
      palco.remove();
    }
  }
  return canvases;
}

export function criarPdfOferta(canvases, formato) {
  const dimensoes = FORMATOS_OFERTA[formato] || FORMATOS_OFERTA.quadrado;
  const pdf = new jsPDF({
    orientation: dimensoes.width > dimensoes.height ? "landscape" : "portrait",
    unit: "px",
    format: [dimensoes.width, dimensoes.height],
    hotfixes: ["px_scaling"],
  });
  canvases.forEach((canvas, indice) => {
    if (indice) pdf.addPage([dimensoes.width, dimensoes.height]);
    pdf.addImage(canvas.toDataURL("image/png", 1), "PNG", 0, 0, dimensoes.width, dimensoes.height);
  });
  return pdf;
}
