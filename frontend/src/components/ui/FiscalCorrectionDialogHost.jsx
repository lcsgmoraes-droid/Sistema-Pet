import { AlertTriangle, CheckCircle2, Loader2, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import api from "../../api";
import {
  assinarCorrecaoFiscal,
  resolverCorrecaoFiscal,
} from "../../services/fiscalCorrectionDialog";

const CAMPOS = {
  ncm: { rotulo: "NCM", tipo: "texto", placeholder: "8 dígitos", tamanho: 8 },
  origem_mercadoria: {
    rotulo: "Origem da mercadoria",
    tipo: "select",
    opcoes: [
      ["0", "0 - Nacional"],
      ["1", "1 - Estrangeira, importação direta"],
      ["2", "2 - Estrangeira, adquirida no mercado interno"],
      ["3", "3 - Nacional, conteúdo importado superior a 40%"],
      ["4", "4 - Nacional, processo produtivo básico"],
      ["5", "5 - Nacional, conteúdo importado até 40%"],
      ["6", "6 - Estrangeira, importação direta sem similar"],
      ["7", "7 - Estrangeira, mercado interno sem similar"],
      ["8", "8 - Nacional, conteúdo importado superior a 70%"],
    ],
  },
  cfop: { rotulo: "CFOP de venda", tipo: "texto", placeholder: "4 dígitos", tamanho: 4 },
  cst_icms: {
    rotulo: "CSOSN/CST do ICMS",
    tipo: "select",
    opcoes: [
      ["00", "00 - Tributada integralmente"],
      ["10", "10 - Tributada com ICMS por ST"],
      ["20", "20 - Redução de base"],
      ["30", "30 - Isenta com ICMS por ST"],
      ["40", "40 - Isenta"],
      ["41", "41 - Não tributada"],
      ["50", "50 - Suspensão"],
      ["51", "51 - Diferimento"],
      ["60", "60 - ICMS cobrado anteriormente por ST"],
      ["70", "70 - Redução de base com ICMS por ST"],
      ["90", "90 - Outros"],
      ["101", "101 - Simples Nacional com crédito"],
      ["102", "102 - Simples Nacional sem crédito"],
      ["103", "103 - Simples Nacional com isenção"],
      ["201", "201 - Simples com crédito e ICMS por ST"],
      ["202", "202 - Simples sem crédito e com ICMS por ST"],
      ["203", "203 - Simples com isenção e ICMS por ST"],
      ["300", "300 - Simples Nacional, imune"],
      ["400", "400 - Simples Nacional, não tributada"],
      ["500", "500 - Simples, ICMS cobrado anteriormente por ST"],
      ["900", "900 - Simples Nacional, outros"],
    ],
  },
  pis_cst: { rotulo: "CST do PIS", tipo: "pis-cofins" },
  cofins_cst: { rotulo: "CST da COFINS", tipo: "pis-cofins" },
};

const OPCOES_PIS_COFINS = [
  ["01", "01 - Operação tributável, alíquota normal"],
  ["02", "02 - Operação tributável, alíquota diferenciada"],
  ["03", "03 - Operação tributável por unidade"],
  ["04", "04 - Tributação monofásica, alíquota zero"],
  ["05", "05 - Substituição tributária"],
  ["06", "06 - Alíquota zero"],
  ["07", "07 - Isenta"],
  ["08", "08 - Sem incidência"],
  ["09", "09 - Suspensão"],
  ["49", "49 - Outras operações de saída"],
  ["99", "99 - Outras operações"],
];

function agruparPendencias(validacao) {
  const itens = [...(validacao?.bloqueios || []), ...(validacao?.correcoes || [])];
  const produtos = new Map();
  const gerais = [];

  itens.forEach((item) => {
    if (!item?.produto_id || !CAMPOS[item.campo]) {
      gerais.push(item);
      return;
    }
    const chave = String(item.produto_id);
    const atual = produtos.get(chave) || {
      id: item.produto_id,
      nome: item.produto_nome || `Produto ${item.produto_id}`,
      sku: item.sku,
      tipo: item.produto_tipo,
      pendencias: [],
    };
    if (!atual.pendencias.some((pendencia) => pendencia.campo === item.campo)) {
      atual.pendencias.push(item);
    }
    produtos.set(chave, atual);
  });

  return { produtos: [...produtos.values()], gerais };
}

function normalizarFiscal(data = {}) {
  return {
    ...data,
    cfop: data.cfop ?? data.cfop_venda ?? "",
    origem_mercadoria: data.origem_mercadoria ?? "",
    ncm: data.ncm ?? "",
    cst_icms: data.cst_icms ?? "",
    pis_cst: data.pis_cst ?? "",
    cofins_cst: data.cofins_cst ?? "",
  };
}

function mensagemErroApi(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return (
    detail?.mensagem ||
    detail?.erro ||
    error?.message ||
    "Não foi possível salvar os dados fiscais."
  );
}

export default function FiscalCorrectionDialogHost() {
  const [dialogo, setDialogo] = useState(null);
  const [formularios, setFormularios] = useState({});
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => assinarCorrecaoFiscal(setDialogo), []);

  const agrupado = useMemo(() => agruparPendencias(dialogo?.validacao), [dialogo]);
  const temSugestoes = agrupado.produtos.some((produto) =>
    produto.pendencias.some((item) => item.valor_sugerido),
  );

  useEffect(() => {
    if (!dialogo) return undefined;
    let ativo = true;
    setCarregando(true);
    setErro("");
    Promise.all(
      agrupado.produtos.map(async (produto) => {
        const endpoint =
          produto.tipo === "KIT"
            ? `/produtos/${produto.id}/kit/fiscal`
            : `/produtos/${produto.id}/fiscal`;
        const { data } = await api.get(endpoint);
        return [String(produto.id), normalizarFiscal(data)];
      }),
    )
      .then((entradas) => {
        if (ativo) setFormularios(Object.fromEntries(entradas));
      })
      .catch((error) => {
        if (ativo) setErro(mensagemErroApi(error));
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [dialogo, agrupado.produtos]);

  if (!dialogo) return null;

  const fechar = () => resolverCorrecaoFiscal(false);
  const atualizarCampo = (produtoId, campo, valor) => {
    setFormularios((atuais) => ({
      ...atuais,
      [produtoId]: { ...atuais[produtoId], [campo]: valor },
    }));
    setErro("");
  };

  const preencherSugestoes = () => {
    setFormularios((atuais) => {
      const proximos = { ...atuais };
      agrupado.produtos.forEach((produto) => {
        const chave = String(produto.id);
        const fiscal = { ...(proximos[chave] || {}) };
        produto.pendencias.forEach((item) => {
          if (item.valor_sugerido) fiscal[item.campo] = item.valor_sugerido;
        });
        proximos[chave] = fiscal;
      });
      return proximos;
    });
  };

  const salvarETentarNovamente = async () => {
    const faltantes = [];
    agrupado.produtos.forEach((produto) => {
      const fiscal = formularios[String(produto.id)] || {};
      produto.pendencias.forEach((item) => {
        const valor = String(fiscal[item.campo] ?? "").trim();
        if (!valor) faltantes.push(`${produto.nome}: ${CAMPOS[item.campo].rotulo}`);
        if (
          item.campo === "ncm" &&
          valor &&
          (!/^\d{8}$/.test(valor) || valor === "00000000")
        ) {
          faltantes.push(`${produto.nome}: informe um NCM válido com 8 dígitos`);
        }
        if (item.campo === "cfop" && valor && !/^\d{4}$/.test(valor)) {
          faltantes.push(`${produto.nome}: o CFOP precisa ter 4 dígitos`);
        }
        if (item.valor_invalido && valor === String(item.valor_atual || "")) {
          faltantes.push(`${produto.nome}: altere ${CAMPOS[item.campo].rotulo}`);
        }
      });
    });
    if (faltantes.length) {
      setErro(`Confira antes de continuar:\n${faltantes.map((item) => `• ${item}`).join("\n")}`);
      return;
    }

    setSalvando(true);
    setErro("");
    try {
      await Promise.all(
        agrupado.produtos.map((produto) => {
          const endpoint =
            produto.tipo === "KIT"
              ? `/produtos/${produto.id}/kit/fiscal`
              : `/produtos/${produto.id}/fiscal`;
          return api.put(endpoint, formularios[String(produto.id)]);
        }),
      );
      resolverCorrecaoFiscal(true);
    } catch (error) {
      setErro(mensagemErroApi(error));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[140] flex items-center justify-center bg-slate-950/55 p-3 backdrop-blur-sm">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="fiscal-correction-title"
        className="flex max-h-[94vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-white/70 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900"
      >
        <header className="flex items-start gap-4 border-b border-slate-200 px-5 py-5 dark:border-slate-700">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <h2
              id="fiscal-correction-title"
              className="text-lg font-semibold text-slate-900 dark:text-slate-100"
            >
              Complete os dados fiscais para emitir
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
              A nota ainda não foi criada. Corrija os campos abaixo e o CorePet fará uma nova
              validação automaticamente.
            </p>
          </div>
          <button
            type="button"
            onClick={fechar}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Fechar"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5">
          {carregando && (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-600 dark:text-slate-300">
              <Loader2 className="h-5 w-5 animate-spin" /> Carregando os cadastros fiscais...
            </div>
          )}

          {!carregando && temSugestoes && (
            <div className="flex flex-col gap-3 rounded-xl border border-cyan-200 bg-cyan-50 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-cyan-800 dark:bg-cyan-950/30">
              <div>
                <p className="font-semibold text-cyan-900 dark:text-cyan-100">
                  O CorePet encontrou sugestões para alguns campos
                </p>
                <p className="mt-1 text-sm text-cyan-800 dark:text-cyan-200">
                  Revise os valores sugeridos antes de salvar.
                </p>
              </div>
              <button
                type="button"
                onClick={preencherSugestoes}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800"
              >
                <Sparkles className="h-4 w-4" /> Preencher sugestões
              </button>
            </div>
          )}

          {!carregando &&
            agrupado.produtos.map((produto) => {
              const fiscal = formularios[String(produto.id)] || {};
              return (
                <article
                  key={produto.id}
                  className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700"
                >
                  <div className="mb-4">
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                      {produto.nome}
                    </h3>
                    {produto.sku && (
                      <p className="mt-1 text-xs text-slate-500">SKU {produto.sku}</p>
                    )}
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    {produto.pendencias.map((item) => {
                      const campo = CAMPOS[item.campo];
                      const opcoes = campo.tipo === "pis-cofins" ? OPCOES_PIS_COFINS : campo.opcoes;
                      return (
                        <label key={item.campo} className="block">
                          <span className="mb-1.5 flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                            {campo.rotulo}
                            {item.valor_sugerido && (
                              <span className="rounded-full bg-cyan-100 px-2 py-0.5 text-[11px] font-semibold text-cyan-800">
                                sugestão disponível
                              </span>
                            )}
                          </span>
                          {campo.tipo === "select" || campo.tipo === "pis-cofins" ? (
                            <select
                              value={fiscal[item.campo] || ""}
                              onChange={(event) =>
                                atualizarCampo(String(produto.id), item.campo, event.target.value)
                              }
                              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                            >
                              <option value="">Selecione...</option>
                              {opcoes.map(([valor, rotulo]) => (
                                <option key={valor} value={valor}>
                                  {rotulo}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <input
                              value={fiscal[item.campo] || ""}
                              inputMode="numeric"
                              maxLength={campo.tamanho}
                              placeholder={campo.placeholder}
                              onChange={(event) =>
                                atualizarCampo(
                                  String(produto.id),
                                  item.campo,
                                  event.target.value.replace(/\D/g, ""),
                                )
                              }
                              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                            />
                          )}
                          <span className="mt-1.5 block text-xs leading-5 text-slate-500">
                            {item.valor_sugerido ? item.motivo : item.mensagem}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </article>
              );
            })}

          {!carregando && agrupado.gerais.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/30">
              <p className="font-semibold text-amber-900 dark:text-amber-100">
                Também é necessário revisar:
              </p>
              <ul className="mt-2 space-y-1 text-sm text-amber-900 dark:text-amber-200">
                {agrupado.gerais.map((item, index) => (
                  <li key={`${item.campo}-${index}`}>• {item.mensagem || item.campo}</li>
                ))}
              </ul>
            </div>
          )}

          {erro && (
            <div className="whitespace-pre-line rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-200">
              {erro}
            </div>
          )}
        </div>

        <footer className="flex flex-col-reverse gap-2 border-t border-slate-200 bg-slate-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-700 dark:bg-slate-950/40">
          <p className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Os dados ficam salvos no cadastro
            do produto para as próximas vendas.
          </p>
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <button
              type="button"
              onClick={fechar}
              disabled={salvando}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              Corrigir depois
            </button>
            {agrupado.produtos.length > 0 && (
              <button
                type="button"
                onClick={salvarETentarNovamente}
                disabled={carregando || salvando}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {salvando && <Loader2 className="h-4 w-4 animate-spin" />}
                Salvar e tentar emitir novamente
              </button>
            )}
          </div>
        </footer>
      </section>
    </div>
  );
}
