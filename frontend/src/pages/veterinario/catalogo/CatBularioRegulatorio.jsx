import { useCallback, useEffect, useState } from "react";
import { ExternalLink, Globe2, Loader2, PlusCircle, Search, ShieldAlert } from "lucide-react";
import { vetApi } from "../vetApi";

const POR_PAGINA = 25;

export default function CatBularioRegulatorio() {
  const [busca, setBusca] = useState("");
  const [jurisdicao, setJurisdicao] = useState("ALL");
  const [pagina, setPagina] = useState(1);
  const [resultado, setResultado] = useState({ items: [], total: 0, aviso: "" });
  const [carregando, setCarregando] = useState(false);
  const [adicionandoId, setAdicionandoId] = useState(null);
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const response = await vetApi.listarBularioRegulatorio({
        busca: busca.trim().length >= 2 ? busca.trim() : undefined,
        jurisdicao,
        pagina,
        por_pagina: POR_PAGINA,
      });
      setResultado(response.data || { items: [], total: 0, aviso: "" });
    } catch (error) {
      setErro(error?.response?.data?.detail || "Não foi possível carregar o bulário oficial.");
    } finally {
      setCarregando(false);
    }
  }, [busca, jurisdicao, pagina]);

  useEffect(() => {
    const timer = globalThis.setTimeout(carregar, 250);
    return () => globalThis.clearTimeout(timer);
  }, [carregar]);

  async function adicionar(item) {
    setAdicionandoId(item.id);
    setMensagem("");
    setErro("");
    try {
      await vetApi.adicionarBularioAoCatalogo(item.id);
      setMensagem(
        `${item.nome_comercial || item.nome} foi adicionado ao catálogo da clínica para revisão.`,
      );
    } catch (error) {
      setErro(error?.response?.data?.detail || "Não foi possível adicionar este medicamento.");
    } finally {
      setAdicionandoId(null);
    }
  }

  const totalPaginas = Math.max(Math.ceil((resultado.total || 0) / POR_PAGINA), 1);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <div className="flex items-start gap-2">
          <ShieldAlert className="mt-0.5 shrink-0" size={17} />
          <div>
            <div className="font-semibold">Referências regulatórias oficiais</div>
            <p className="mt-1">
              {resultado.aviso ||
                "Fontes oficiais dos Estados Unidos e Reino Unido. Confirme registro no MAPA, espécie e apresentação brasileira antes de prescrever."}
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
        <label className="relative block w-full max-w-xl">
          <Search
            aria-hidden="true"
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            size={16}
          />
          <input
            type="search"
            value={busca}
            onChange={(event) => {
              setBusca(event.target.value);
              setPagina(1);
            }}
            placeholder="Buscar produto, princípio ativo ou fabricante"
            className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm focus:border-teal-400 focus:outline-none"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <label className="relative">
            <Globe2
              aria-hidden="true"
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              size={15}
            />
            <select
              value={jurisdicao}
              onChange={(event) => {
                setJurisdicao(event.target.value);
                setPagina(1);
              }}
              className="rounded-lg border border-gray-200 py-2 pl-9 pr-8 text-sm text-gray-700 focus:border-teal-400 focus:outline-none"
            >
              <option value="ALL">Todas as fontes</option>
              <option value="US">
                Estados Unidos ({resultado.jurisdicoes?.US || 0})
              </option>
              <option value="GB">Reino Unido ({resultado.jurisdicoes?.GB || 0})</option>
            </select>
          </label>
          <div className="text-sm text-gray-500">
            {resultado.total || 0} bula(s) veterinária(s)
          </div>
        </div>
      </div>

      {mensagem ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {mensagem}
        </div>
      ) : null}
      {erro ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {erro}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        {carregando ? (
          <div className="flex items-center justify-center gap-2 p-10 text-sm text-gray-500">
            <Loader2 className="animate-spin" size={17} /> Carregando bulas...
          </div>
        ) : resultado.items?.length ? (
          <div className="divide-y divide-gray-100">
            {resultado.items.map((item) => (
              <article key={item.id} className="space-y-2 p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <h3 className="font-semibold text-gray-900">
                      {item.nome_comercial || item.nome}
                    </h3>
                    {item.principio_ativo ? (
                      <p className="mt-1 text-sm text-gray-700">{item.principio_ativo}</p>
                    ) : null}
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                      <span>Fabricante: {item.fabricante || "não informado"}</span>
                      <span>Jurisdição: {item.jurisdicao}</span>
                      {item.metadados_fonte?.territory ? (
                        <span>Território: {item.metadados_fonte.territory}</span>
                      ) : null}
                      {item.metadados_fonte?.vm_number ? (
                        <span>Registro VMD: {item.metadados_fonte.vm_number}</span>
                      ) : null}
                      {item.especies_indicadas?.length ? (
                        <span>Espécies: {item.especies_indicadas.join(", ")}</span>
                      ) : null}
                      <span>
                        Publicação:{" "}
                        {item.publicado_em
                          ? new Date(`${item.publicado_em}T12:00:00`).toLocaleDateString("pt-BR")
                          : "não informada"}
                      </span>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <a
                      href={item.bula_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
                    >
                      <ExternalLink size={13} /> Abrir bula oficial
                    </a>
                    <button
                      type="button"
                      onClick={() => adicionar(item)}
                      disabled={adicionandoId === item.id}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-2 text-xs font-medium text-white hover:bg-teal-700 disabled:opacity-60"
                    >
                      {adicionandoId === item.id ? (
                        <Loader2 className="animate-spin" size={13} />
                      ) : (
                        <PlusCircle size={13} />
                      )}
                      Adicionar ao meu catálogo
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="p-10 text-center text-sm text-gray-500">
            Nenhuma bula encontrada. Execute a sincronização regulatória no ambiente DEV.
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-sm">
        <button
          type="button"
          disabled={pagina <= 1}
          onClick={() => setPagina((atual) => Math.max(atual - 1, 1))}
          className="rounded-lg border border-gray-200 px-3 py-2 text-gray-700 disabled:opacity-40"
        >
          Anterior
        </button>
        <span className="text-gray-500">
          Página {pagina} de {totalPaginas}
        </span>
        <button
          type="button"
          disabled={pagina >= totalPaginas}
          onClick={() => setPagina((atual) => Math.min(atual + 1, totalPaginas))}
          className="rounded-lg border border-gray-200 px-3 py-2 text-gray-700 disabled:opacity-40"
        >
          Próxima
        </button>
      </div>
    </div>
  );
}
