import { useEffect, useMemo, useRef, useState } from "react";

import OfertaCanvas from "./OfertaCanvas";
import { capturarPaginasOferta, criarPdfOferta } from "./ofertaCaptura";
import { FORMATOS_OFERTA, TIPOS_ARTE, itensPorPagina } from "./ofertasEstudioUtils";

const TEMAS = {
  premium: "Premium CorePet",
  natural: "Natural",
  varejo: "Oferta forte",
};

const IMAGENS = [
  "/demo/pets/thor-srd.webp",
  "/demo/pets/mia-gata.webp",
  "/demo/pets/luna-shih-tzu.webp",
  "/demo/pets/mel-cadela.webp",
  "/demo/pets/thor-caramelo.webp",
  "/demo/pets/luna-gata.webp",
];

const NOMES = [
  "Alimentação Premium para Cães Adultos de Raças Médias - Pacote Econômico 15kg",
  "Antipulgas, Carrapatos e Vermes para Cães de 10,1 a 25kg - 3 Tabletes",
  "Areia Sanitária Biodegradável com Controle Prolongado de Odores 12kg",
  "BISCOITO SPECIALDOG ULTRALIFE EDIÇÃO LIMITADA BANANA 10X250G",
  "Aditivo Antiodor Antibacterial para Areia de Gatos - Embalagem 500g",
  "Ração Super Premium para Cães Adultos de Raças Grandes com Frango, Arroz, Ômega 3 e Controle de Peso - Embalagem Econômica 15kg",
];

const ITENS_QA = NOMES.map((nome, index) => ({
  produto_id: index + 1,
  nome,
  preco_erp: index === 2 ? 15999.9 : 149.9 + index * 10,
  preco_arte: index === 2 ? 12999.9 : 99.9 + index * 10,
  imagem_url: IMAGENS[index],
  imagem_url_arte: IMAGENS[index],
  mostrar_validade: index % 2 === 0,
  lote_validade: {
    data_validade: "2026-09-30",
  },
  motivo_sugestao: index === 0 ? "Melhor margem" : null,
}));

function medirEstouro(container) {
  if (!container) return [];
  const seletores = [
    "[data-oferta-content]",
    "[data-oferta-header]",
    "[data-oferta-grid]",
    "[data-oferta-card]",
    "[data-oferta-image]",
    "[data-oferta-product-title]",
    "[data-oferta-price-row]",
    "[data-oferta-price]",
    "[data-oferta-individual]",
  ].join(",");
  return Array.from(container.querySelectorAll(seletores))
    .filter(
      (elemento) =>
        elemento.scrollHeight > elemento.clientHeight + 5 ||
        elemento.scrollWidth > elemento.clientWidth + 5,
    )
    .map((elemento) => {
      const nome = elemento
        .getAttributeNames()
        .find((atributo) => atributo.startsWith("data-oferta"));
      return `${nome}:${elemento.clientWidth}/${elemento.scrollWidth}x${elemento.clientHeight}/${elemento.scrollHeight}`;
    });
}

export default function OfertaCanvasPreview() {
  const containerRef = useRef(null);
  const [tipoArte, setTipoArte] = useState("jornal");
  const [formato, setFormato] = useState("quadrado");
  const [tema, setTema] = useState("premium");
  const [quantidade, setQuantidade] = useState(6);
  const [capturas, setCapturas] = useState([]);
  const [problemas, setProblemas] = useState([]);
  const [capturando, setCapturando] = useState(false);

  const itens = useMemo(() => ITENS_QA.slice(0, quantidade), [quantidade]);

  useEffect(() => {
    setCapturas([]);
    const frame = window.requestAnimationFrame(() =>
      setProblemas(medirEstouro(containerRef.current)),
    );
    return () => window.cancelAnimationFrame(frame);
  }, [formato, itens, tema, tipoArte]);

  async function capturar() {
    setCapturando(true);
    try {
      const canvases = await capturarPaginasOferta(containerRef.current, formato);
      setCapturas(canvases.map((canvas) => canvas.toDataURL("image/png", 1)));
    } finally {
      setCapturando(false);
    }
  }

  async function baixarPdfTeste() {
    setCapturando(true);
    try {
      const canvases = await capturarPaginasOferta(containerRef.current, formato);
      criarPdfOferta(canvases, formato).save(`qa-${tipoArte}-${formato}-${tema}.pdf`);
    } finally {
      setCapturando(false);
    }
  }

  const limite = itensPorPagina(tipoArte, formato);

  return (
    <main className="min-h-screen bg-slate-100 p-6 text-slate-950">
      <div className="mx-auto max-w-[1500px]">
        <h1 className="text-2xl font-black">QA visual - Estúdio de Ofertas</h1>
        <p className="mt-1 text-sm text-slate-600">
          Rota disponível somente em desenvolvimento para validar todas as proporções e exportações.
        </p>

        <section className="mt-5 grid gap-3 rounded-2xl bg-white p-4 shadow-sm sm:grid-cols-4">
          <label className="text-xs font-bold">
            Tipo de arte
            <select
              aria-label="Tipo de arte QA"
              value={tipoArte}
              onChange={(event) => setTipoArte(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border px-3"
            >
              {Object.entries(TIPOS_ARTE).map(([value, item]) => (
                <option key={value} value={value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-bold">
            Formato
            <select
              aria-label="Formato QA"
              value={formato}
              onChange={(event) => setFormato(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border px-3"
            >
              {Object.entries(FORMATOS_OFERTA).map(([value, item]) => (
                <option key={value} value={value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-bold">
            Visual
            <select
              aria-label="Visual QA"
              value={tema}
              onChange={(event) => setTema(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border px-3"
            >
              {Object.entries(TEMAS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-bold">
            Produtos
            <select
              aria-label="Quantidade QA"
              value={quantidade}
              onChange={(event) => setQuantidade(Number(event.target.value))}
              className="mt-1 h-10 w-full rounded-lg border px-3"
            >
              {[1, 2, 4, 6].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-center gap-3 sm:col-span-4">
            <button
              type="button"
              onClick={capturar}
              disabled={capturando}
              className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-black text-white disabled:opacity-50"
            >
              {capturando ? "Capturando..." : "Gerar captura de teste"}
            </button>
            <button
              type="button"
              onClick={baixarPdfTeste}
              disabled={capturando}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-black disabled:opacity-50"
            >
              Gerar PDF de teste
            </button>
            <span
              data-testid="qa-layout-status"
              data-problemas={problemas.join(",")}
              className="text-sm font-bold"
            >
              {problemas.length ? `${problemas.length} estouro(s)` : "Sem estouros"} - limite{" "}
              {limite}
              /página
            </span>
          </div>
        </section>

        <div className="mt-6 grid items-start gap-6 xl:grid-cols-2">
          <section>
            <h2 className="mb-2 font-black">Prévia React</h2>
            <OfertaCanvas
              itens={itens}
              contexto={{
                nome: "Loja de Teste com Nome Comprido",
                logo_url: "/brand/corepet/corepet-horizontal.png",
              }}
              titulo="Ofertas imperdíveis da semana para toda a família pet"
              periodicidadeLabel="Jornal semanal"
              tipoArte={tipoArte}
              formato={formato}
              tema={tema}
              containerRef={containerRef}
            />
          </section>
          <section>
            <h2 className="mb-2 font-black">Captura real do html2canvas</h2>
            <div className="space-y-4" data-testid="qa-capturas">
              {capturas.map((src, index) => (
                <img
                  key={`${formato}-${tipoArte}-${index}`}
                  src={src}
                  alt={`Captura ${index + 1}`}
                  className="mx-auto w-full max-w-[720px] rounded-2xl shadow-xl"
                />
              ))}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
