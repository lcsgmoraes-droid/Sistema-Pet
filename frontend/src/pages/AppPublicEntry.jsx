import { ArrowRight, Search, ShieldCheck, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import ecommerceApi from "../services/ecommerceApi";

function extractStoreSlug(input) {
  const raw = String(input || "").trim();
  if (!raw) return "";

  try {
    const url = new URL(raw);
    const querySlug =
      url.searchParams.get("loja") ||
      url.searchParams.get("slug") ||
      url.searchParams.get("tenant");
    if (querySlug) return sanitizeSlug(querySlug);

    const segments = url.pathname.split("/").filter(Boolean);
    return sanitizeSlug(firstUsefulSegment(segments));
  } catch {
    const queryText = raw.includes("?") ? raw.split("?")[1] : "";
    if (queryText) {
      const queryParams = new URLSearchParams(queryText);
      const querySlug =
        queryParams.get("loja") || queryParams.get("slug") || queryParams.get("tenant");
      if (querySlug) return sanitizeSlug(querySlug);
    }

    const withoutQuery = raw.split("?")[0];
    return sanitizeSlug(
      firstUsefulSegment(withoutQuery.split("/").filter(Boolean)) || withoutQuery,
    );
  }
}

function firstUsefulSegment(segments) {
  const reserved = new Set(["loja", "store", "ecommerce", "app", "tenant"]);
  return segments.find((segment) => !reserved.has(String(segment).toLowerCase())) || "";
}

function sanitizeSlug(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "");
}

export default function AppPublicEntry() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialCode = useMemo(() => {
    return searchParams.get("loja") || searchParams.get("slug") || searchParams.get("tenant") || "";
  }, [searchParams]);

  const [storeCode, setStoreCode] = useState(initialCode);
  const [store, setStore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function searchStore(nextCode = storeCode) {
    const slug = extractStoreSlug(nextCode);
    setError("");
    setStore(null);

    if (!slug) {
      setError("Informe o codigo, slug ou URL da loja.");
      return;
    }

    setLoading(true);
    try {
      const response = await ecommerceApi.get(`/api/ecommerce/tenant-slug/${slug}`);
      setStore(response.data || null);
      setStoreCode(slug);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || "Loja nao encontrada. Confira o codigo e tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  function enterStore() {
    const slug = store?.slug || extractStoreSlug(storeCode);
    if (slug) {
      navigate(`/${slug}`);
    }
  }

  useEffect(() => {
    if (initialCode) {
      searchStore(initialCode);
    }
  }, [initialCode]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <section className="mx-auto flex min-h-screen w-full max-w-3xl flex-col justify-center px-5 py-12">
        <div className="mb-7 flex items-center gap-3">
          <img
            src="/brand/corepet/corepet-icon-64.png"
            alt=""
            className="h-11 w-11 rounded-xl shadow-sm"
          />
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">CorePet</p>
            <h1 className="text-2xl font-bold tracking-normal text-slate-950">
              Entrar na loja pelo app
            </h1>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <label className="mb-2 block text-sm font-semibold text-slate-800">
            Codigo ou URL da loja
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Search
                size={18}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                value={storeCode}
                onChange={(event) => {
                  setStoreCode(event.target.value);
                  setStore(null);
                  setError("");
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    searchStore();
                  }
                }}
                className="h-11 w-full rounded-lg border border-slate-300 pl-10 pr-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                placeholder="Ex: atacadao ou corepet.com.br/atacadao"
              />
            </div>
            <button
              type="button"
              onClick={() => searchStore()}
              disabled={loading}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Search size={17} />
              {loading ? "Buscando..." : "Buscar"}
            </button>
          </div>

          {error ? (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700">
              <XCircle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}

          {store ? (
            <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-lg bg-white text-emerald-700 ring-1 ring-emerald-200">
                    {store.logo_url ? (
                      <img src={store.logo_url} alt="" className="h-full w-full object-contain" />
                    ) : (
                      <ShieldCheck size={24} />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-bold text-slate-950">{store.nome}</p>
                    <p className="text-xs text-slate-600">
                      {[store.cidade, store.uf].filter(Boolean).join(" / ") || "Loja encontrada"}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={enterStore}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-semibold text-white transition hover:bg-emerald-700"
                >
                  Entrar nesta loja
                  <ArrowRight size={17} />
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
