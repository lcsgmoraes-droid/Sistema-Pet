import { AlertTriangle, CheckCircle2, Loader2, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import api from "../../api";
import {
  assinarCorrecaoFiscal,
  resolverCorrecaoFiscal,
} from "../../services/fiscalCorrectionDialog";
import FiscalReferenceSearch from "./FiscalReferenceSearch";
import FiscalCorrectionNoteContext from "./FiscalCorrectionNoteContext";
import FiscalCorrectionField from "./FiscalCorrectionField";
import {
  agruparPendenciasFiscais,
  camposFiscaisAlterados,
} from "../../utils/fiscalCorrectionFields.mjs";
import {
  MENSAGEM_SUPORTE_RESPONSAVEL_TECNICO,
  rejeicaoResponsavelTecnico,
  SUPORTE_FISCAL_COREPET_URL,
} from "../../utils/fiscalRejectionGuidance.mjs";

const CAMPOS = {
  ncm: { rotulo: "NCM", tipo: "texto", placeholder: "8 dígitos", tamanho: 8 },
  cest: { rotulo: "CEST", tipo: "texto", placeholder: "7 dígitos, quando aplicável", tamanho: 7 },
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

function normalizarFiscal(data = {}) {
  return {
    ...data,
    cfop: data.cfop ?? data.cfop_venda ?? "",
    origem_mercadoria: data.origem_mercadoria ?? "",
    ncm: data.ncm ?? "",
    cst_icms: data.cst_icms ?? "",
    pis_cst: data.pis_cst ?? data.cst_pis ?? "",
    cofins_cst: data.cofins_cst ?? data.cst_cofins ?? "",
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

function destinoPendenciaGeral(dialogo, gerais, rejeicao, clienteId) {
  const texto = [rejeicao?.motivo, ...gerais.map((item) => item.mensagem)]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase("pt-BR");
  if (/intnfe|integração|integracao|credencial|certificado|csc/.test(texto)) {
    return { url: "/configuracoes/integracoes", rotulo: "Abrir integração fiscal" };
  }
  if (/empresa|emitente|regime tributário|regime tributario/.test(texto)) {
    return { url: "/configuracoes/fiscal", rotulo: "Abrir configuração fiscal da empresa" };
  }
  if (
    /cliente|consumidor|destinatário|destinatario|cpf|cnpj|endereço|endereco|código ibge|codigo ibge/.test(
      texto,
    )
  ) {
    if (clienteId) {
      const ehEndereco = /endereço|endereco|cep|ibge|município|municipio/.test(texto);
      const aba = ehEndereco ? "endereco" : "dados-gerais";
      return {
        url: `/clientes/${encodeURIComponent(clienteId)}/editar?aba=${aba}`,
        rotulo: ehEndereco ? "Corrigir endereço deste cliente" : "Corrigir cadastro deste cliente",
      };
    }
    return { url: "/clientes", rotulo: "Abrir cadastro de clientes" };
  }
  if (dialogo?.vendaId) {
    return {
      url: `/pdv?venda_id=${encodeURIComponent(dialogo.vendaId)}`,
      rotulo: "Abrir esta venda no PDV",
    };
  }
  return null;
}

function FiscalSupportDialog({ fechar }) {
  return (
    <div className="fixed inset-0 z-[140] flex items-center justify-center bg-slate-950/55 p-3 backdrop-blur-sm">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="fiscal-support-title"
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900"
      >
        <h2
          id="fiscal-support-title"
          className="text-lg font-semibold text-slate-900 dark:text-slate-100"
        >
          Não foi possível emitir esta nota
        </h2>
        <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-200">
          {MENSAGEM_SUPORTE_RESPONSAVEL_TECNICO}
        </p>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          O suporte precisa verificar a integração fiscal antes de uma nova tentativa.
        </p>
        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={fechar}
            className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 dark:border-slate-700 dark:text-slate-200"
          >
            Fechar
          </button>
          <a
            href={SUPORTE_FISCAL_COREPET_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            Falar com o suporte
          </a>
        </div>
      </section>
    </div>
  );
}

export default function FiscalCorrectionDialogHost() {
  const [dialogo, setDialogo] = useState(null);
  const [formularios, setFormularios] = useState({});
  const [originais, setOriginais] = useState({});
  const [camposAplicados, setCamposAplicados] = useState({});
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [clienteDestino, setClienteDestino] = useState(null);

  useEffect(() => assinarCorrecaoFiscal(setDialogo), []);

  const agrupado = useMemo(() => agruparPendenciasFiscais(dialogo?.validacao, CAMPOS), [dialogo]);
  const correcaoDaNota = Boolean(
    dialogo?.nota?.provedor === "intnfe" &&
    dialogo?.nota?.status?.toLowerCase() === "rejeitada" &&
    dialogo?.vendaId,
  );
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
  const rejeicao = dialogo?.rejeicao || dialogo?.validacao?.rejeicao;
  const erroResponsavelTecnico = rejeicaoResponsavelTecnico(rejeicao);
  const destinoBase = destinoPendenciaGeral(dialogo, agrupado.gerais, rejeicao);
  const clienteResolvido =
    Boolean(dialogo?.vendaId) && String(clienteDestino?.vendaId) === String(dialogo.vendaId);
  const clienteId = clienteResolvido ? clienteDestino?.clienteId : null;
  const aguardandoCliente =
    destinoBase?.url === "/clientes" && dialogo?.vendaId && !clienteResolvido;
  const destinoGeral = destinoPendenciaGeral(dialogo, agrupado.gerais, rejeicao, clienteId);

  useEffect(() => {
    if (!dialogo?.vendaId || destinoBase?.url !== "/clientes" || erroResponsavelTecnico) {
      return undefined;
    }
    let ativo = true;
    api
      .get(`/vendas/${dialogo.vendaId}`)
      .then(({ data }) => {
        if (ativo) setClienteDestino({ vendaId: dialogo.vendaId, clienteId: data?.cliente_id });
      })
      .catch(() => {
        if (ativo) setClienteDestino({ vendaId: dialogo.vendaId, clienteId: null });
      });
    return () => {
      ativo = false;
    };
  }, [dialogo?.vendaId, destinoBase?.url, erroResponsavelTecnico]);

  useEffect(() => {
    if (!dialogo || erroResponsavelTecnico) return undefined;
    let ativo = true;
    setCarregando(true);
    setErro("");
    setFormularios({});
    setOriginais({});
    setCamposAplicados({});
    Promise.all(
      agrupado.produtos.map(async (produto) => {
        if (correcaoDaNota && !produto.itemId) {
          throw new Error(
            "Não foi possível identificar o item desta nota para corrigir. Atualize a lista e abra a nota novamente.",
          );
        }
        const endpoint = correcaoDaNota
          ? `/nfe/vendas/${dialogo.vendaId}/itens/${produto.itemId}/fiscal`
          : produto.tipo === "KIT"
            ? `/produtos/${produto.id}/kit/fiscal`
            : `/produtos/${produto.id}/fiscal`;
        const { data } = await api.get(endpoint);
        return [
          produto.chave,
          {
            ...normalizarFiscal(correcaoDaNota ? data.fiscal : data),
            fontesFiscais: data.fontes_fiscais,
          },
        ];
      }),
    )
      .then((entradas) => {
        if (ativo) {
          const carregados = Object.fromEntries(entradas);
          setFormularios(carregados);
          setOriginais(carregados);
        }
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
  }, [dialogo, agrupado.produtos, erroResponsavelTecnico, correcaoDaNota]);

  if (!dialogo) return null;

  const fechar = () => {
    if (!salvando) resolverCorrecaoFiscal(false);
  };
  if (erroResponsavelTecnico) return <FiscalSupportDialog fechar={fechar} />;
  const atualizarCampo = (produtoId, campo, valor) => {
    setFormularios((atuais) => ({
      ...atuais,
      [produtoId]: { ...atuais[produtoId], [campo]: valor },
    }));
    setErro("");
  };
  const aplicarReferencia = (produto, campo, valor) => {
    if (!CAMPOS[campo] || salvando) return;
    atualizarCampo(produto.chave, campo, valor);
    setCamposAplicados((atuais) => ({
      ...atuais,
      [produto.chave]: [...new Set([...(atuais[produto.chave] || []), campo])],
    }));
  };
  const pendenciasDoEditor = (produto) => [
    ...produto.pendencias,
    ...(camposAplicados[produto.chave] || [])
      .filter((campo) => !produto.pendencias.some((item) => item.campo === campo))
      .map((campo) => ({
        campo,
        aplicado_na_consulta: true,
        valor_atual: originais[produto.chave]?.[campo],
        mensagem:
          "Valor aplicado pela consulta fiscal. Revise este campo antes de salvar; ele também será atualizado.",
      })),
  ];

  const preencherSugestoes = () => {
    setFormularios((atuais) => {
      const proximos = { ...atuais };
      agrupado.produtos.forEach((produto) => {
        const chave = produto.chave;
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
      const fiscal = formularios[produto.chave] || {};
      pendenciasDoEditor(produto).forEach((item) => {
        const valor = String(fiscal[item.campo] ?? "").trim();
        if (!valor && item.campo !== "cest")
          faltantes.push(`${produto.nome}: ${CAMPOS[item.campo].rotulo}`);
        if (item.campo === "ncm" && valor && (!/^\d{8}$/.test(valor) || valor === "00000000")) {
          faltantes.push(`${produto.nome}: informe um NCM válido com 8 dígitos`);
        }
        if (item.campo === "cfop" && valor && !/^\d{4}$/.test(valor)) {
          faltantes.push(`${produto.nome}: o CFOP precisa ter 4 dígitos`);
        }
        if (item.campo === "cest" && valor && !/^\d{7}$/.test(valor)) {
          faltantes.push(`${produto.nome}: o CEST precisa ter 7 dígitos`);
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
      for (const produto of agrupado.produtos) {
        const fiscal = formularios[produto.chave];
        if (correcaoDaNota) {
          const alterados = camposFiscaisAlterados(produto, fiscal, originais[produto.chave]);
          if (Object.keys(alterados).length) {
            await api.put(
              `/nfe/vendas/${dialogo.vendaId}/itens/${produto.itemId}/fiscal`,
              alterados,
            );
          }
        } else {
          const endpoint =
            produto.tipo === "KIT"
              ? `/produtos/${produto.id}/kit/fiscal`
              : `/produtos/${produto.id}/fiscal`;
          const { fontesFiscais: _fontesFiscais, ...cadastroFiscal } = fiscal;
          await api.put(endpoint, cadastroFiscal);
        }
      }
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
              {correcaoDaNota
                ? "Corrigir nota fiscal rejeitada"
                : temCamposDeProduto
                  ? "Complete os dados fiscais para emitir"
                  : "Revise a pendência fiscal para emitir"}
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {temCamposDeProduto
                ? "Corrija os campos destacados. Os dados serão validados novamente antes de qualquer nova transmissão."
                : "Confira o motivo informado pelo emissor e a orientação abaixo."}
            </p>
          </div>
          <button
            type="button"
            onClick={fechar}
            disabled={salvando}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Fechar"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5">
          <FiscalCorrectionNoteContext
            nota={dialogo.nota}
            detalheNota={dialogo.detalheNota}
            produtos={agrupado.produtos}
          />
          {(rejeicao?.motivo || rejeicao?.codigo) && (
            <div
              className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-900"
              role="alert"
            >
              <p className="font-semibold">Erro informado na tentativa anterior</p>
              {rejeicao.codigo && <p className="mt-1">Código: {rejeicao.codigo}</p>}
              {rejeicao.motivo && <p className="mt-1">{rejeicao.motivo}</p>}
            </div>
          )}
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
              const fiscal = formularios[produto.chave] || {};
              return (
                <article
                  key={produto.chave}
                  className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700"
                >
                  <div className="mb-4">
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                      {produto.itemNumero ? `Item ${produto.itemNumero} · ` : ""}
                      {produto.nome}
                    </h3>
                    {produto.sku && (
                      <p className="mt-1 text-xs text-slate-500">SKU {produto.sku}</p>
                    )}
                  </div>
                  <FiscalReferenceSearch
                    produto={produto}
                    contextoFiscal={contextoFiscal}
                    onAplicar={(campo, valor) => aplicarReferencia(produto, campo, valor)}
                    valoresAtuais={fiscal}
                  />
                  <div className="grid gap-4 md:grid-cols-2">
                    {pendenciasDoEditor(produto).map((item) => (
                      <FiscalCorrectionField
                        key={item.campo}
                        produto={produto}
                        item={item}
                        fiscal={fiscal}
                        contextoFiscal={contextoFiscal}
                        campo={CAMPOS[item.campo]}
                        opcoesPisCofins={OPCOES_PIS_COFINS}
                        correcaoDaNota={correcaoDaNota}
                        salvando={salvando}
                        onChange={(valor) => atualizarCampo(produto.chave, item.campo, valor)}
                      />
                    ))}
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
              {destinoGeral && !aguardandoCliente && (
                <a href={destinoGeral.url} className="mt-3 inline-block font-semibold underline">
                  {destinoGeral.rotulo}
                </a>
              )}
            </div>
          )}
          {!carregando && !temCamposDeProduto && agrupado.gerais.length === 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              Os dados atuais passaram na validação, mas a rejeição anterior ainda precisa ser
              conferida. Revise o motivo acima antes de tentar transmitir novamente.
              {destinoGeral && !aguardandoCliente && (
                <a href={destinoGeral.url} className="mt-3 block font-semibold underline">
                  {destinoGeral.rotulo}
                </a>
              )}
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
            {correcaoDaNota && temCamposDeProduto
              ? "A correção atualiza o cadastro fiscal usado pela nota. O reenvio exige sua confirmação."
              : temCamposDeProduto
                ? "Os dados ficam salvos no cadastro do produto para as próximas vendas."
                : "Esta tela não transmite uma nova nota."}
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
                disabled={
                  carregando ||
                  salvando ||
                  agrupado.produtos.some((produto) => !formularios[produto.chave])
                }
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {salvando && <Loader2 className="h-4 w-4 animate-spin" />}
                {dialogo?.apenasCorrigir
                  ? "Salvar e verificar novamente"
                  : "Salvar e tentar emitir novamente"}
              </button>
            )}
            {!temCamposDeProduto && rejeicao && dialogo.apenasCorrigir && (
              <button
                type="button"
                onClick={() => resolverCorrecaoFiscal(true)}
                className="rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Verificar correção e tentar novamente
              </button>
            )}
          </div>
        </footer>
      </section>
    </div>
  );
}
