import { AlertTriangle, CheckCircle2, Loader2, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import api from "../../api";
import {
  assinarCorrecaoFiscal,
  resolverCorrecaoFiscal,
} from "../../services/fiscalCorrectionDialog";
import FiscalReferenceSearch from "./FiscalReferenceSearch";

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

const CONFIANCA = {
  alta: {
    rotulo: "Alta confiança",
    classe: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200",
  },
  media: {
    rotulo: "Média confiança",
    classe: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200",
  },
  baixa: {
    rotulo: "Baixa confiança",
    classe: "bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-200",
  },
};

const FONTES_SUGESTAO = {
  catalogo_fiscal: "catálogo fiscal do CorePet",
  configuracao_fiscal_da_empresa: "configuração fiscal da empresa",
  xml_ou_cadastro_do_produto_e_regime_da_empresa: "XML/cadastro do produto e regime da empresa",
  regime_da_empresa_sem_historico_do_produto: "regime da empresa; sem histórico deste produto",
  regime_da_empresa_sem_padrao_configurado: "regime da empresa; sem padrão fiscal configurado",
  historico_de_produtos_semelhantes: "produtos semelhantes já cadastrados",
  palavras_da_descricao: "descrição do produto",
  correcao_de_codigo_incompleto: "correção de código fiscal incompleto",
  padrao_operacional_sem_origem_informada: "padrão operacional; origem não comprovada",
};

function fonteLegivel(fonte) {
  return FONTES_SUGESTAO[fonte] || String(fonte || "fonte não identificada").replaceAll("_", " ");
}

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
      codigo_barras: item.codigo_barras,
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
  const temSugestoesAutomaticas = agrupado.produtos.some((produto) =>
    produto.pendencias.some(
      (item) => item.valor_sugerido && item.preenchimento_automatico === true,
    ),
  );
  const contextoFiscal = dialogo?.validacao?.contexto_fiscal || {};
  const temCamposDeProduto = agrupado.produtos.length > 0;

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
          if (item.valor_sugerido && item.preenchimento_automatico === true) {
            fiscal[item.campo] = item.valor_sugerido;
          }
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
        if (item.campo === "ncm" && valor && (!/^\d{8}$/.test(valor) || valor === "00000000")) {
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
              {temCamposDeProduto
                ? "Complete os dados fiscais para emitir"
                : "Revise a pendência fiscal para emitir"}
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {temCamposDeProduto
                ? "A nota ainda não foi criada. Corrija os campos abaixo e o CorePet fará uma nova validação automaticamente."
                : "A nota ainda não foi criada. Confira abaixo o motivo informado pelo emissor."}
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

          {!carregando && (contextoFiscal.regime_tributario || contextoFiscal.uf) && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200">
              <p className="font-semibold">
                Contexto identificado: {contextoFiscal.regime_tributario || "regime não informado"}
                {contextoFiscal.uf ? ` · ${contextoFiscal.uf}` : ""}
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
                O CorePet já usa o regime e o estado nas sugestões. A confirmação ainda é necessária
                quando o cadastro e o histórico do produto não mostram se há ST, isenção ou outro
                tratamento específico.
              </p>
            </div>
          )}

          {!carregando && temSugestoes && (
            <div className="flex flex-col gap-3 rounded-xl border border-cyan-200 bg-cyan-50 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-cyan-800 dark:bg-cyan-950/30">
              <div>
                <p className="font-semibold text-cyan-900 dark:text-cyan-100">
                  O CorePet encontrou possíveis respostas para alguns campos
                </p>
                <p className="mt-1 text-sm text-cyan-800 dark:text-cyan-200">
                  Cada sugestão mostra a fonte e a confiança. Valores de baixa confiança só são
                  usados quando você escolher explicitamente.
                </p>
              </div>
              {temSugestoesAutomaticas && (
                <button
                  type="button"
                  onClick={preencherSugestoes}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-cyan-800"
                >
                  <Sparkles className="h-4 w-4" /> Preencher sugestões confiáveis
                </button>
              )}
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
                  <FiscalReferenceSearch
                    produto={produto}
                    contextoFiscal={contextoFiscal}
                    onAplicar={(campo, valor) => atualizarCampo(String(produto.id), campo, valor)}
                  />
                  <div className="grid gap-4 md:grid-cols-2">
                    {produto.pendencias.map((item) => {
                      const campo = CAMPOS[item.campo];
                      const opcoes = campo.tipo === "pis-cofins" ? OPCOES_PIS_COFINS : campo.opcoes;
                      const confianca = CONFIANCA[item.confianca];
                      const campoId = `fiscal-${produto.id}-${item.campo}`;
                      return (
                        <div key={item.campo} className="block">
                          <label
                            htmlFor={campoId}
                            className="mb-1.5 flex flex-wrap items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200"
                          >
                            {campo.rotulo}
                            {confianca && (
                              <span
                                className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${confianca.classe}`}
                              >
                                {confianca.rotulo}
                                {item.confianca_percentual
                                  ? ` · ${item.confianca_percentual}%`
                                  : ""}
                              </span>
                            )}
                          </label>
                          {campo.tipo === "select" || campo.tipo === "pis-cofins" ? (
                            <select
                              id={campoId}
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
                              id={campoId}
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
                          {item.valor_sugerido ? (
                            <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs leading-5 text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <p>
                                  Sugestão: <strong>{item.valor_sugerido}</strong>
                                </p>
                                <button
                                  type="button"
                                  onClick={() =>
                                    atualizarCampo(
                                      String(produto.id),
                                      item.campo,
                                      item.valor_sugerido,
                                    )
                                  }
                                  className="rounded-lg border border-cyan-300 bg-white px-2.5 py-1 font-semibold text-cyan-800 hover:bg-cyan-50 dark:border-cyan-700 dark:bg-slate-900 dark:text-cyan-200"
                                >
                                  Usar esta sugestão
                                </button>
                              </div>
                              <p className="mt-1">{item.motivo}</p>
                              <p className="mt-1 font-medium text-slate-500 dark:text-slate-400">
                                Fonte: {fonteLegivel(item.fonte_sugestao)}.
                              </p>
                            </div>
                          ) : (
                            <span className="mt-1.5 block text-xs leading-5 text-slate-500">
                              {item.mensagem}
                            </span>
                          )}
                        </div>
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
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            {temCamposDeProduto
              ? "Os dados ficam salvos no cadastro do produto para as próximas vendas."
              : "Nenhum documento fiscal foi criado nesta tentativa."}
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
                {dialogo?.apenasCorrigir
                  ? "Salvar e verificar novamente"
                  : "Salvar e tentar emitir novamente"}
              </button>
            )}
          </div>
        </footer>
      </section>
    </div>
  );
}
