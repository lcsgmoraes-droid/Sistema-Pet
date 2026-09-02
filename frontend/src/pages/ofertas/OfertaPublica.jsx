import { ChevronLeft, ChevronRight, Download, Expand, MessageCircle, Store } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import api from "../../api";
import { resolveMediaUrl } from "../../utils/mediaUrl";

function baixarImagem(url, indice) {
  const link = document.createElement("a");
  link.href = resolveMediaUrl(url);
  link.download = `oferta-pagina-${indice + 1}.png`;
  link.target = "_blank";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function limitarPagina(indice, totalPaginas) {
  return Math.max(0, Math.min(indice, Math.max(totalPaginas - 1, 0)));
}

export default function OfertaPublica() {
  const { token } = useParams();
  const [oferta, setOferta] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [paginaAtual, setPaginaAtual] = useState(0);
  const visualizadorRef = useRef(null);
  const toqueInicialXRef = useRef(null);

  const imagens = Array.isArray(oferta?.imagens_urls) ? oferta.imagens_urls : [];
  const totalPaginas = imagens.length;
  const paginaExibida = limitarPagina(paginaAtual, totalPaginas);
  const imagemAtual = imagens[paginaExibida];

  useEffect(() => {
    setPaginaAtual(0);
    api
      .get(`/ofertas/publicas/${encodeURIComponent(token)}`)
      .then(({ data }) => setOferta(data))
      .catch((error) => setErro(error?.response?.data?.detail || "Esta oferta não foi encontrada."))
      .finally(() => setCarregando(false));
  }, [token]);

  useEffect(() => {
    if (totalPaginas <= 1) return undefined;
    const navegarComTeclado = (event) => {
      if (event.key === "ArrowLeft") {
        setPaginaAtual((atual) => limitarPagina(atual - 1, totalPaginas));
      }
      if (event.key === "ArrowRight") {
        setPaginaAtual((atual) => limitarPagina(atual + 1, totalPaginas));
      }
    };
    window.addEventListener("keydown", navegarComTeclado);
    return () => window.removeEventListener("keydown", navegarComTeclado);
  }, [totalPaginas]);

  function navegarPagina(delta) {
    setPaginaAtual((atual) => limitarPagina(atual + delta, totalPaginas));
  }

  function iniciarDeslize(event) {
    toqueInicialXRef.current = event.changedTouches?.[0]?.clientX ?? null;
  }

  function concluirDeslize(event) {
    const inicio = toqueInicialXRef.current;
    const fim = event.changedTouches?.[0]?.clientX;
    toqueInicialXRef.current = null;
    if (inicio == null || fim == null || Math.abs(fim - inicio) < 45) return;
    navegarPagina(fim < inicio ? 1 : -1);
  }

  async function alternarTelaCheia() {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen?.();
      } else {
        await visualizadorRef.current?.requestFullscreen?.();
      }
    } catch {
      // O navegador pode bloquear tela cheia; a navegação continua funcionando.
    }
  }

  if (carregando) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 text-slate-500">
        Carregando ofertas...
      </div>
    );
  }

  if (erro || !oferta) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
        <div className="max-w-md rounded-2xl bg-white p-8 text-center shadow-xl">
          <Store className="mx-auto text-slate-300" size={44} />
          <h1 className="mt-4 text-xl font-black text-slate-950">Oferta indisponível</h1>
          <p className="mt-2 text-sm text-slate-600">{erro}</p>
        </div>
      </main>
    );
  }

  if (!oferta.ativa) {
    const agendada = oferta.status === "agendada";
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
        <div className="max-w-md rounded-2xl bg-white p-8 text-center shadow-xl">
          <Store className="mx-auto text-slate-300" size={44} />
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">
            {oferta.empresa}
          </p>
          <h1 className="mt-3 text-2xl font-black text-slate-950">
            {agendada ? "Oferta programada" : "Esta oferta não está mais disponível"}
          </h1>
          <p className="mt-3 text-sm text-slate-600">{oferta.motivo_encerramento}</p>
          {agendada ? (
            <p className="mt-2 text-sm font-black text-teal-700">
              Disponível a partir de {new Date(oferta.inicio_em).toLocaleString("pt-BR")}
            </p>
          ) : null}
        </div>
      </main>
    );
  }

  const compartilhar = encodeURIComponent(`${oferta.titulo}: ${window.location.href}`);
  return (
    <main className="min-h-screen bg-slate-100 px-3 py-4 sm:px-6 sm:py-6">
      <div className="mx-auto max-w-5xl">
        <header className="mb-4 flex flex-col gap-4 rounded-2xl bg-white p-4 shadow-sm sm:mb-6 sm:flex-row sm:items-center sm:justify-between sm:p-5">
          <div className="flex min-w-0 items-center gap-3">
            {oferta.logo_url ? (
              <div className="flex h-14 w-20 shrink-0 items-center justify-center rounded-xl border border-slate-200 p-2">
                <img
                  src={resolveMediaUrl(oferta.logo_url)}
                  alt={oferta.empresa}
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            ) : (
              <Store size={36} style={{ color: oferta.cor_primaria }} />
            )}
            <div className="min-w-0">
              <p className="truncate text-xs font-black uppercase tracking-[0.14em] text-slate-500">
                {oferta.empresa}
              </p>
              <h1 className="truncate text-xl font-black text-slate-950 sm:text-2xl">
                {oferta.titulo}
              </h1>
              <p className="mt-1 text-xs text-slate-500">
                Válida até {new Date(oferta.fim_em).toLocaleString("pt-BR")}, ou enquanto durarem os
                estoques.
              </p>
            </div>
          </div>
          <a
            href={`https://wa.me/?text=${compartilhar}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-black text-white no-underline"
          >
            <MessageCircle size={18} /> Compartilhar
          </a>
        </header>

        {imagemAtual ? (
          <article
            ref={visualizadorRef}
            className="overflow-hidden rounded-2xl bg-white shadow-xl fullscreen:flex fullscreen:h-screen fullscreen:w-screen fullscreen:flex-col fullscreen:rounded-none fullscreen:bg-slate-950"
          >
            <div
              className="relative flex min-h-[320px] select-none items-center justify-center bg-slate-950 sm:min-h-[560px] fullscreen:min-h-0 fullscreen:flex-1"
              onTouchStart={iniciarDeslize}
              onTouchEnd={concluirDeslize}
            >
              <img
                src={resolveMediaUrl(imagemAtual)}
                alt={`${oferta.titulo} — página ${paginaExibida + 1}`}
                className="max-h-[78vh] max-w-full object-contain fullscreen:max-h-full"
              />

              {totalPaginas > 1 ? (
                <>
                  <button
                    type="button"
                    onClick={() => navegarPagina(-1)}
                    disabled={paginaExibida === 0}
                    aria-label="Página anterior"
                    className="absolute left-2 top-1/2 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-slate-950/75 text-white shadow-lg disabled:cursor-not-allowed disabled:opacity-30 sm:left-4"
                  >
                    <ChevronLeft size={26} />
                  </button>
                  <button
                    type="button"
                    onClick={() => navegarPagina(1)}
                    disabled={paginaExibida >= totalPaginas - 1}
                    aria-label="Próxima página"
                    className="absolute right-2 top-1/2 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-slate-950/75 text-white shadow-lg disabled:cursor-not-allowed disabled:opacity-30 sm:right-4"
                  >
                    <ChevronRight size={26} />
                  </button>
                  <span
                    aria-live="polite"
                    className="absolute right-3 top-3 rounded-full bg-slate-950/80 px-3 py-1.5 text-xs font-black text-white sm:right-4 sm:top-4"
                  >
                    {paginaExibida + 1} de {totalPaginas}
                  </span>
                </>
              ) : null}

              <button
                type="button"
                onClick={alternarTelaCheia}
                aria-label="Expandir oferta em tela cheia"
                className="absolute bottom-3 right-3 inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/95 text-slate-800 shadow-lg sm:bottom-4 sm:right-4"
              >
                <Expand size={18} />
              </button>
            </div>

            <div className="flex flex-col gap-3 bg-white p-3 fullscreen:bg-slate-900 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center justify-between gap-3 sm:justify-start">
                <span className="text-xs font-bold text-slate-500 fullscreen:text-slate-300">
                  {totalPaginas > 1
                    ? `Página ${paginaExibida + 1} de ${totalPaginas}`
                    : "Oferta completa"}
                </span>
                <button
                  type="button"
                  onClick={() => baixarImagem(imagemAtual, paginaExibida)}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-xs font-black text-slate-700 fullscreen:border-slate-600 fullscreen:text-white"
                >
                  <Download size={15} /> Baixar imagem
                </button>
              </div>
              {totalPaginas > 1 ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => navegarPagina(-1)}
                    disabled={paginaExibida === 0}
                    className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-xs font-black text-slate-700 disabled:opacity-40 fullscreen:border-slate-600 fullscreen:text-white sm:flex-none"
                  >
                    Anterior
                  </button>
                  <button
                    type="button"
                    onClick={() => navegarPagina(1)}
                    disabled={paginaExibida >= totalPaginas - 1}
                    className="flex-1 rounded-lg bg-teal-700 px-4 py-2 text-xs font-black text-white disabled:opacity-40 sm:flex-none"
                  >
                    Próxima
                  </button>
                </div>
              ) : null}
            </div>
          </article>
        ) : null}

        {totalPaginas > 1 ? (
          <nav
            aria-label="Páginas do jornal"
            className="mt-4 flex gap-3 overflow-x-auto rounded-2xl bg-white p-3 shadow-sm"
          >
            {imagens.map((url, indice) => (
              <button
                key={url}
                type="button"
                onClick={() => setPaginaAtual(indice)}
                aria-label={`Abrir página ${indice + 1}`}
                aria-current={paginaExibida === indice ? "page" : undefined}
                className={`relative h-24 w-20 shrink-0 overflow-hidden rounded-lg border-2 bg-slate-950 p-0 ${
                  paginaExibida === indice
                    ? "border-teal-600 ring-2 ring-teal-200"
                    : "border-transparent"
                }`}
              >
                <img src={resolveMediaUrl(url)} alt="" className="h-full w-full object-contain" />
                <span className="absolute bottom-1 right-1 rounded bg-slate-950/80 px-1.5 py-0.5 text-[10px] font-black text-white">
                  {indice + 1}
                </span>
              </button>
            ))}
          </nav>
        ) : null}

        <p className="mt-3 text-center text-xs text-slate-500">
          {totalPaginas > 1
            ? "Deslize a arte ou use as setas para ver todas as páginas."
            : "Toque em expandir para visualizar a oferta em tela cheia."}
        </p>

        <footer className="py-8 text-center text-xs text-slate-500">
          Preços e disponibilidade são os informados pela loja. Produtos com aviso de validade têm
          quantidade limitada ao lote indicado.
        </footer>
      </div>
    </main>
  );
}
