import { ImageOff, PackageCheck } from "lucide-react";

import { formatMoneyBRL } from "../../utils/formatters";
import { resolveMediaUrl } from "../../utils/mediaUrl";
import { agruparPaginas, FORMATOS_OFERTA, layoutJornal } from "./ofertasEstudioUtils";

const TEMAS = {
  premium: { acento: "#f59e0b", fundo: "#052e2b", fundo2: "#0f766e", texto: "#ffffff" },
  natural: { acento: "#facc15", fundo: "#365314", fundo2: "#84cc16", texto: "#ffffff" },
  varejo: { acento: "#fde047", fundo: "#991b1b", fundo2: "#ef4444", texto: "#ffffff" },
};

function formatarData(value) {
  if (!value) return "";
  return new Date(value).toLocaleDateString("pt-BR", { timeZone: "UTC" });
}

function ImagemProduto({ item, className = "" }) {
  const url = resolveMediaUrl(item.imagem_url_arte || item.imagem_url);
  if (!url) {
    return (
      <div className={`flex items-center justify-center bg-slate-100 text-slate-400 ${className}`}>
        <ImageOff className="h-10 w-10" />
      </div>
    );
  }
  return (
    <img
      src={url}
      alt=""
      crossOrigin="anonymous"
      className={`block max-h-full max-w-full object-contain ${className}`}
    />
  );
}

function Validade({ item, compacto = false }) {
  if (!item.mostrar_validade || !item.lote_validade) return null;
  return (
    <div className={`font-bold text-amber-950 ${compacto ? "text-[9px]" : "text-sm"}`}>
      <span className="rounded-full bg-amber-300 px-2 py-1">
        Validade: {formatarData(item.lote_validade.data_validade)}
      </span>
      <p className={compacto ? "mt-1" : "mt-2"}>Quantidade limitada ao lote</p>
    </div>
  );
}

function JornalCard({ item, tema }) {
  return (
    <article
      style={{ containerType: "size" }}
      className="relative flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[1.1rem] bg-white p-[5%] text-slate-900 shadow-xl"
    >
      {item.motivo_sugestao ? (
        <span
          className="absolute left-2 top-2 z-10 max-w-[80%] truncate rounded-full px-2 py-1 text-[8px] font-black uppercase tracking-wide text-slate-950"
          style={{ backgroundColor: tema.acento }}
        >
          {item.motivo_sugestao}
        </span>
      ) : null}
      <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden">
        <ImagemProduto item={item} className="h-full w-full" />
      </div>
      <h3
        style={{ fontSize: "clamp(10px, 7cqw, 18px)", overflowWrap: "break-word" }}
        className="mt-[3cqh] line-clamp-2 min-h-[2.2em] shrink-0 overflow-hidden font-black leading-[1.08]"
      >
        {item.nome}
      </h3>
      <div className="mt-[2cqh] flex shrink-0 items-end justify-between gap-2 overflow-hidden">
        <div>
          {Number(item.preco_arte) < Number(item.preco_erp) ? (
            <p className="text-[9px] font-semibold text-slate-400 line-through">
              {formatMoneyBRL(item.preco_erp)}
            </p>
          ) : null}
          <p
            style={{ fontSize: "clamp(15px, 12cqw, 30px)" }}
            className="whitespace-nowrap font-black leading-none text-red-600"
          >
            {formatMoneyBRL(item.preco_arte)}
          </p>
        </div>
        <PackageCheck className="h-5 w-5 shrink-0" style={{ color: tema.fundo2 }} />
      </div>
      <div className="mt-[2cqh] shrink-0 overflow-hidden">
        <Validade item={item} compacto />
      </div>
    </article>
  );
}

function Cabecalho({ contexto, titulo, periodoLabel, tema }) {
  const logo = resolveMediaUrl(contexto?.logo_url);
  return (
    <header className="relative z-10 flex items-center justify-between gap-4">
      <div className="flex min-w-0 items-center gap-3">
        {logo ? (
          <div className="flex h-14 w-20 shrink-0 items-center justify-center rounded-xl bg-white p-2 shadow-lg">
            <img
              src={logo}
              alt=""
              crossOrigin="anonymous"
              className="max-h-full max-w-full object-contain"
            />
          </div>
        ) : null}
        <div className="min-w-0 text-left">
          <p className="truncate text-[10px] font-black uppercase tracking-[0.18em] text-white/75">
            {contexto?.nome || "Sua loja"}
          </p>
          <h2
            style={{ fontSize: "clamp(20px, 5cqw, 42px)", overflowWrap: "break-word" }}
            className="line-clamp-2 overflow-hidden font-black leading-[.95]"
          >
            {titulo || "Ofertas especiais"}
          </h2>
        </div>
      </div>
      <span
        className="shrink-0 rounded-full px-3 py-2 text-[10px] font-black uppercase text-slate-950"
        style={{ backgroundColor: tema.acento }}
      >
        {periodoLabel}
      </span>
    </header>
  );
}

function PaginaJornal({ itens, contexto, titulo, periodoLabel, tema, pagina, total, formato }) {
  const layout = layoutJornal(formato);
  const linhasUsadas = Math.max(1, Math.ceil(itens.length / layout.colunas));
  return (
    <>
      <Cabecalho contexto={contexto} titulo={titulo} periodoLabel={periodoLabel} tema={tema} />
      <div
        style={{
          gridTemplateColumns: `repeat(${layout.colunas}, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(${Math.min(layout.linhas, linhasUsadas)}, minmax(0, 1fr))`,
        }}
        className="relative z-10 my-[4%] grid min-h-0 flex-1 gap-[2.6%] overflow-hidden"
      >
        {itens.map((item) => (
          <JornalCard key={item.produto_id} item={item} tema={tema} />
        ))}
      </div>
      <footer className="relative z-10 flex items-center justify-between text-[10px] font-semibold text-white/80">
        <span>Preços válidos durante o período indicado ou enquanto durarem os estoques.</span>
        {total > 1 ? (
          <span>
            {pagina}/{total}
          </span>
        ) : null}
      </footer>
    </>
  );
}

function PaginaIndividual({ item, contexto, titulo, periodoLabel, tema }) {
  return (
    <>
      <Cabecalho contexto={contexto} titulo={titulo} periodoLabel={periodoLabel} tema={tema} />
      <div className="relative z-10 my-[4%] flex min-h-0 flex-1 flex-col items-center justify-center overflow-hidden rounded-[2rem] bg-white/95 p-[7%] text-center text-slate-900 shadow-2xl">
        <div className="flex min-h-0 w-full flex-1 items-center justify-center overflow-hidden">
          <ImagemProduto item={item} className="h-full w-full" />
        </div>
        <p
          style={{ fontSize: "clamp(18px, 5cqw, 40px)", overflowWrap: "break-word" }}
          className="mt-[2.5cqw] line-clamp-3 max-w-[92%] shrink-0 overflow-hidden font-black leading-[1.08]"
        >
          {item.nome}
        </p>
        {Number(item.preco_arte) < Number(item.preco_erp) ? (
          <p className="mt-2 text-sm font-bold text-slate-400 line-through">
            De {formatMoneyBRL(item.preco_erp)}
          </p>
        ) : null}
        <p
          style={{ fontSize: "clamp(34px, 10cqw, 76px)" }}
          className="mt-1 shrink-0 whitespace-nowrap font-black leading-none text-red-600"
        >
          {formatMoneyBRL(item.preco_arte)}
        </p>
        <div className="mt-4">
          <Validade item={item} />
        </div>
      </div>
    </>
  );
}

function PaginaProduto({ item }) {
  return (
    <div className="relative z-10 flex h-full w-full items-center justify-center bg-white">
      <ImagemProduto item={item} className="h-full w-full" />
    </div>
  );
}

export default function OfertaCanvas({
  itens,
  contexto,
  titulo,
  periodicidadeLabel,
  tipoArte,
  formato,
  tema: temaKey,
  containerRef,
}) {
  const formatoConfig = FORMATOS_OFERTA[formato];
  const tema = TEMAS[temaKey] || TEMAS.premium;
  const paginas = agruparPaginas(itens, tipoArte, formato);

  if (!paginas.length) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
        Selecione produtos para montar a prévia.
      </div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-6">
      {paginas.map((paginaItens, index) => (
        <div key={`${tipoArte}-${index}`} className="mx-auto w-full max-w-[720px]">
          <div className="mb-2 text-center text-xs font-bold text-slate-500">
            Página {index + 1} de {paginas.length}
          </div>
          <section
            data-oferta-page
            style={{
              aspectRatio: formatoConfig.ratio,
              containerType: "inline-size",
              color: tema.texto,
              background:
                tipoArte === "produto"
                  ? "#ffffff"
                  : `linear-gradient(145deg, ${tema.fundo} 0%, ${tema.fundo2} 72%, ${tema.acento} 165%)`,
            }}
            className={`relative flex w-full flex-col overflow-hidden rounded-2xl shadow-2xl ${tipoArte === "produto" ? "p-0" : "p-[5%]"}`}
          >
            {tipoArte !== "produto" ? (
              <>
                <div className="absolute -right-[12%] -top-[8%] h-[35%] w-[48%] rounded-full bg-white/10" />
                <div className="absolute -bottom-[15%] -left-[8%] h-[36%] w-[45%] rounded-full bg-black/10" />
              </>
            ) : null}
            {tipoArte === "jornal" ? (
              <PaginaJornal
                itens={paginaItens}
                contexto={contexto}
                titulo={titulo}
                periodoLabel={periodicidadeLabel}
                tema={tema}
                pagina={index + 1}
                total={paginas.length}
                formato={formato}
              />
            ) : tipoArte === "individual" ? (
              <PaginaIndividual
                item={paginaItens[0]}
                contexto={contexto}
                titulo={titulo}
                periodoLabel={periodicidadeLabel}
                tema={tema}
              />
            ) : (
              <PaginaProduto item={paginaItens[0]} />
            )}
          </section>
        </div>
      ))}
    </div>
  );
}
