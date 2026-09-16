import { BookOpen, ExternalLink, Loader2, Search, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import api from "../../api";

const CONFIANCA = {
  alta: "Alta",
  media: "Média",
  baixa: "Baixa",
};

const GUIAS = [
  ["cst_icms", "CSOSN", "csosn"],
  ["pis_cst", "CST do PIS", "pis"],
  ["cofins_cst", "CST da COFINS", "cofins"],
];

function mensagemErro(error) {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string" ? detail : "Não foi possível consultar a base fiscal agora.";
}

export default function FiscalReferenceSearch({ produto, contextoFiscal, onAplicar }) {
  const [aberto, setAberto] = useState(true);
  const [consulta, setConsulta] = useState(
    produto.codigo_barras || produto.nome || produto.sku || "",
  );
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const pendentes = useMemo(
    () => new Set((produto.pendencias || []).map((item) => item.campo)),
    [produto.pendencias],
  );

  const pesquisar = async () => {
    const termo = consulta.trim();
    if (termo.length < 2) {
      setErro("Digite ao menos 2 caracteres para pesquisar.");
      return;
    }
    setCarregando(true);
    setErro("");
    try {
      const { data } = await api.get("/fiscal/sugestao/pesquisar", {
        params: { q: termo, limite: 8 },
      });
      setDados(data);
    } catch (error) {
      setErro(mensagemErro(error));
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    let ativo = true;
    const termo = String(produto.codigo_barras || produto.nome || produto.sku || "").trim();
    if (termo.length < 2) return undefined;
    setConsulta(termo);
    setCarregando(true);
    setErro("");
    api
      .get("/fiscal/sugestao/pesquisar", { params: { q: termo, limite: 8 } })
      .then(({ data }) => {
        if (ativo) setDados(data);
      })
      .catch((error) => {
        if (ativo) setErro(mensagemErro(error));
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [produto.codigo_barras, produto.id, produto.nome, produto.sku]);

  const abrir = () => {
    setAberto(true);
    if (!dados) pesquisar();
  };

  return (
    <div className="mb-4 rounded-xl border border-indigo-200 bg-indigo-50/60 p-3 dark:border-indigo-800 dark:bg-indigo-950/20">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold text-indigo-950 dark:text-indigo-100">
            <BookOpen className="h-4 w-4" /> Base de consulta fiscal
          </p>
          <p className="mt-1 text-xs leading-5 text-indigo-800 dark:text-indigo-200">
            O CorePet consulta automaticamente o histórico, o catálogo aprendido e a tabela NCM
            vigente da Receita.
          </p>
        </div>
        <button
          type="button"
          onClick={aberto ? () => setAberto(false) : abrir}
          className="rounded-lg border border-indigo-300 bg-white px-3 py-2 text-xs font-semibold text-indigo-800 hover:bg-indigo-100 dark:border-indigo-700 dark:bg-slate-900 dark:text-indigo-200"
        >
          {aberto ? "Ocultar consulta" : "Ver sugestões encontradas"}
        </button>
      </div>

      {aberto && (
        <div className="mt-4 space-y-4 border-t border-indigo-200 pt-4 dark:border-indigo-800">
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={consulta}
                onChange={(event) => setConsulta(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    pesquisar();
                  }
                }}
                placeholder="Ex.: ração para cães, código de barras ou 23091000"
                className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>
            <button
              type="button"
              onClick={pesquisar}
              disabled={carregando}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-60"
            >
              {carregando ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              Buscar
            </button>
          </div>

          {erro && <p className="text-sm font-medium text-red-700 dark:text-red-300">{erro}</p>}

          {dados && (
            <>
              <div>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    NCM e CEST encontrados
                  </p>
                  <a
                    href="https://portalunico.siscomex.gov.br/classif/"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 hover:underline dark:text-indigo-300"
                  >
                    Consultar classificação oficial <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
                {dados.ncm_oficial?.disponivel && (
                  <p className="mb-2 text-[11px] leading-4 text-slate-500 dark:text-slate-400">
                    Tabela oficial {dados.ncm_oficial.atualizado_em || "vigente"}
                    {dados.ncm_oficial.ato ? ` · ${dados.ncm_oficial.ato}` : ""}. O CorePet mantém
                    essa fonte em cache e atualiza automaticamente.
                  </p>
                )}
                {dados.resultados?.length ? (
                  <div className="space-y-2">
                    {dados.resultados.map((resultado) => (
                      <div
                        key={`${resultado.ncm}-${resultado.cest || "sem-cest"}`}
                        className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
                      >
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                              NCM {resultado.ncm}
                              {resultado.cest ? ` · CEST ${resultado.cest}` : ""}
                            </p>
                            <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                              Exemplo encontrado: {resultado.descricao}
                            </p>
                            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                              Fonte: {resultado.fonte} · Confiança{" "}
                              {CONFIANCA[resultado.confianca] || resultado.confianca} (
                              {resultado.confianca_percentual}%)
                            </p>
                          </div>
                          <div className="flex shrink-0 flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => onAplicar("ncm", resultado.ncm)}
                              className="rounded-lg bg-indigo-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-800"
                            >
                              Usar NCM
                            </button>
                            {resultado.cest && (
                              <button
                                type="button"
                                onClick={() => onAplicar("cest", resultado.cest)}
                                className="rounded-lg border border-indigo-300 bg-white px-3 py-1.5 text-xs font-semibold text-indigo-800 hover:bg-indigo-50 dark:border-indigo-700 dark:bg-slate-950 dark:text-indigo-200"
                              >
                                Usar CEST
                              </button>
                            )}
                          </div>
                        </div>
                        <p className="mt-2 text-[11px] leading-4 text-amber-700 dark:text-amber-300">
                          {resultado.aviso}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="rounded-lg bg-white p-3 text-xs text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                    Nenhuma correspondência foi encontrada na base do CorePet. Use a consulta
                    oficial pelo link acima.
                  </p>
                )}
              </div>

              <details className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
                <summary className="cursor-pointer text-sm font-semibold text-slate-800 dark:text-slate-100">
                  Entender e escolher CSOSN, PIS e COFINS
                </summary>
                <p className="mt-2 text-xs leading-5 text-slate-600 dark:text-slate-300">
                  {contextoFiscal?.simples_nacional
                    ? "A empresa está no Simples Nacional, por isso o ICMS usa CSOSN. PIS e COFINS continuam sendo informados no XML; o código depende da tributação do produto e da operação."
                    : "Escolha o código conforme a tributação do produto e da operação. A lista explica os códigos, mas não substitui a regra fiscal aplicável."}
                </p>
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  {GUIAS.filter(([campo]) => pendentes.has(campo)).map(([campo, titulo, chave]) => (
                    <label
                      key={campo}
                      className="text-xs font-semibold text-slate-700 dark:text-slate-200"
                    >
                      {titulo}
                      <select
                        defaultValue=""
                        onChange={(event) => {
                          if (event.target.value) onAplicar(campo, event.target.value);
                        }}
                        className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-2 py-2 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                      >
                        <option value="">Consultar opções...</option>
                        {(dados.referencias?.[chave] || []).map((item) => (
                          <option key={item.codigo} value={item.codigo}>
                            {item.codigo} - {item.descricao}
                          </option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
                <a
                  href="https://sped.rfb.gov.br/item/show/1616"
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 hover:underline dark:text-indigo-300"
                >
                  Abrir tabelas oficiais do SPED <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </details>

              <p className="flex items-start gap-2 text-[11px] leading-4 text-slate-500 dark:text-slate-400">
                <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" />A base reduz a pesquisa manual,
                mas não inventa uma classificação quando não há evidência suficiente.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
