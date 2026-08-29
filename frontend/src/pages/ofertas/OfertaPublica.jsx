import { Download, MessageCircle, Store } from "lucide-react";
import { useEffect, useState } from "react";
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

export default function OfertaPublica() {
  const { token } = useParams();
  const [oferta, setOferta] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api
      .get(`/ofertas/publicas/${encodeURIComponent(token)}`)
      .then(({ data }) => setOferta(data))
      .catch((error) => setErro(error?.response?.data?.detail || "Esta oferta não foi encontrada."))
      .finally(() => setCarregando(false));
  }, [token]);

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
    <main className="min-h-screen bg-slate-100 px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-4xl">
        <header className="mb-6 flex flex-col gap-4 rounded-2xl bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
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
              <h1 className="truncate text-2xl font-black text-slate-950">{oferta.titulo}</h1>
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

        <div className="space-y-6">
          {oferta.imagens_urls.map((url, indice) => (
            <article key={url} className="overflow-hidden rounded-2xl bg-white shadow-xl">
              <img
                src={resolveMediaUrl(url)}
                alt={`${oferta.titulo} — página ${indice + 1}`}
                className="h-auto w-full"
              />
              <div className="flex items-center justify-between gap-3 p-3">
                <span className="text-xs font-bold text-slate-500">
                  Página {indice + 1} de {oferta.imagens_urls.length}
                </span>
                <button
                  type="button"
                  onClick={() => baixarImagem(url, indice)}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-xs font-black text-slate-700"
                >
                  <Download size={15} /> Baixar imagem
                </button>
              </div>
            </article>
          ))}
        </div>

        <footer className="py-8 text-center text-xs text-slate-500">
          Preços e disponibilidade são os informados pela loja. Produtos com aviso de validade têm
          quantidade limitada ao lote indicado.
        </footer>
      </div>
    </main>
  );
}
