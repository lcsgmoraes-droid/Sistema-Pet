import { useEffect, useMemo, useState } from "react";
import {
  FiAlertCircle,
  FiCheckCircle,
  FiCircle,
  FiExternalLink,
  FiRefreshCcw,
  FiRotateCcw,
} from "react-icons/fi";
import api from "../api";

const STORAGE_KEY = "introducao_guiada_v1";

const SECOES = [
  {
    id: "empresa",
    titulo: "1) Base da empresa e fiscal",
    itens: [
      {
        id: "empresa-fiscal",
        titulo: "Preencher configuracao fiscal da empresa",
        obrigatorio: true,
        onde: "/configuracoes/fiscal",
        resultado: "Impostos e analise de margem ficam coerentes.",
        autoCheckKey: "empresaFiscal",
      },
      {
        id: "empresa-dados",
        titulo: "Preencher dados cadastrais (CNPJ, razao social, endereco)",
        obrigatorio: true,
        onde: "/configuracoes/fiscal",
        resultado: "Base pronta para emissao e documentos.",
        autoCheckKey: "empresaDados",
      },
      {
        id: "empresa-margens-pdv",
        titulo: "Definir limites de margem do PDV (verde/amarelo/vermelho)",
        obrigatorio: false,
        onde: "/configuracoes/geral",
        resultado: "Analise do PDV passa a seguir a sua regra de margem.",
      },
      {
        id: "empresa-mensagens-pdv",
        titulo: "Ajustar mensagens da analise de margem no PDV",
        obrigatorio: false,
        onde: "/configuracoes/geral",
        resultado: "Equipe recebe alertas claros no fechamento da venda.",
      },
      {
        id: "empresa-meta-faturamento",
        titulo: "Configurar meta de faturamento mensal",
        obrigatorio: false,
        onde: "/configuracoes/geral",
        resultado: "Dashboard passa a comparar a operacao contra a meta.",
      },
      {
        id: "empresa-alertas-estoque",
        titulo: "Definir alertas de estoque (percentual e dias parado)",
        obrigatorio: false,
        onde: "/configuracoes/geral",
        resultado: "Sistema antecipa ruptura e produtos sem giro.",
      },
    ],
  },
  {
    id: "financeiro-estrutura",
    titulo: "2) Estrutura financeira obrigatoria",
    itens: [
      {
        id: "contas-bancarias",
        titulo: "Cadastrar bancos/caixas/carteiras",
        obrigatorio: true,
        onde: "/cadastros/financeiro/bancos",
        resultado: "Sistema sabe de onde vem e para onde vai o dinheiro.",
        autoCheckKey: "contasBancarias",
      },
      {
        id: "formas-pagamento",
        titulo: "Cadastrar formas de pagamento",
        obrigatorio: true,
        onde: "/cadastros/financeiro/formas-pagamento",
        resultado: "PDV consegue finalizar vendas e gerar recebiveis.",
        autoCheckKey: "formasPagamento",
      },
      {
        id: "operadoras-cartao",
        titulo: "Cadastrar operadoras de cartao (se usar cartao)",
        obrigatorio: false,
        condicao: "Obrigatorio se vender em cartao",
        onde: "/cadastros/financeiro/operadoras",
        resultado: "Consolidacao e conciliacao de cartao mais confiaveis.",
        autoCheckKey: "operadoras",
      },
      {
        id: "categorias-financeiras",
        titulo: "Cadastrar categorias financeiras (receita/custo/despesa)",
        obrigatorio: true,
        onde: "/cadastros/categorias-financeiras",
        resultado: "Fluxo de caixa e DRE passam a classificar corretamente.",
      },
    ],
  },
  {
    id: "cadastros-base",
    titulo: "3) Cadastros base de operacao",
    itens: [
      {
        id: "categorias-produto",
        titulo: "Cadastrar categorias e subcategorias de produto",
        obrigatorio: true,
        onde: "/cadastros/categorias",
        resultado: "Produtos ficam organizados e comissao por categoria funciona.",
        autoCheckKey: "categoriasProduto",
      },
      {
        id: "produtos",
        titulo: "Cadastrar produtos vendaveis",
        obrigatorio: true,
        onde: "/produtos",
        resultado: "PDV e estoque conseguem operar normalmente.",
        autoCheckKey: "produtos",
      },
      {
        id: "pessoas",
        titulo: "Cadastrar pessoas (clientes/fornecedores/vet/funcionarios)",
        obrigatorio: true,
        onde: "/pessoas",
        resultado: "Vendas, compras e financeiro com vinculo correto.",
        autoCheckKey: "pessoas",
      },
      {
        id: "pets",
        titulo: "Cadastrar pets (opcional, recomendado)",
        obrigatorio: false,
        onde: "/pets",
        resultado: "Historico de atendimento e recorrencia por pet.",
        autoCheckKey: "pets",
      },
      {
        id: "especies-racas",
        titulo: "Revisar especies e racas",
        obrigatorio: false,
        onde: "/cadastros/especies-racas",
        resultado: "Cadastro de pets mais padronizado.",
      },
    ],
  },
  {
    id: "config-vertical",
    titulo: "4) Configuracoes por tipo de operacao",
    itens: [
      {
        id: "entrega-config",
        titulo: "Configurar entregas (taxas, raio, origem)",
        obrigatorio: false,
        condicao: "Obrigatorio se usar entrega",
        onde: "/configuracoes/entregas",
        resultado: "Vendas com entrega calculam valor e rota corretamente.",
        autoCheckKey: "configEntrega",
      },
      {
        id: "entregador",
        titulo: "Cadastrar entregador(es)",
        obrigatorio: false,
        condicao: "Obrigatorio se usar entrega",
        onde: "/pessoas",
        resultado: "Venda com entrega passa na validacao de entregador.",
        autoCheckKey: "entregadores",
      },
      {
        id: "comissao-func",
        titulo: "Definir funcionarios comissionados",
        obrigatorio: false,
        condicao: "Obrigatorio se pagar comissao",
        onde: "/comissoes",
        resultado: "Sistema identifica quem recebe comissao.",
      },
      {
        id: "comissao-regras",
        titulo: "Configurar regras de comissao (categoria/subcategoria/produto)",
        obrigatorio: false,
        condicao: "Obrigatorio se pagar comissao",
        onde: "/comissoes",
        resultado: "Calculo de comissao automatico na finalizacao da venda.",
        autoCheckKey: "comissoesConfig",
      },
      {
        id: "racao-opcoes",
        titulo: "Cadastrar opcoes de classificacao de racao",
        obrigatorio: false,
        condicao: "Obrigatorio se vender racao com analise",
        onde: "/cadastros/opcoes-racao",
        resultado: "Alertas e analises de racao mais completos.",
        autoCheckKey: "opcoesRacao",
      },
      {
        id: "estoque-config",
        titulo: "Revisar configuracoes de estoque",
        obrigatorio: false,
        onde: "/configuracoes/estoque",
        resultado: "Menos ruptura e menos erro de movimentacao.",
      },
    ],
  },
  {
    id: "operacao",
    titulo: "5) Validacao da operacao ponta a ponta",
    itens: [
      {
        id: "abrir-caixa",
        titulo: "Abrir caixa no PDV com saldo inicial",
        obrigatorio: true,
        onde: "/pdv",
        resultado: "Usuario pronto para venda presencial.",
        autoCheckKey: "caixaAberto",
      },
      {
        id: "venda-sem-entrega",
        titulo: "Lancar 1 venda sem entrega",
        obrigatorio: true,
        onde: "/pdv",
        resultado: "Fluxo basico de venda validado.",
        autoCheckKey: "temVendas",
      },
      {
        id: "venda-com-entrega",
        titulo: "Lancar 1 venda com entrega",
        obrigatorio: false,
        condicao: "Se usar entrega",
        onde: "/pdv",
        resultado: "Fluxo de entrega validado do inicio ao fim.",
      },
      {
        id: "venda-com-comissao",
        titulo: "Lancar 1 venda com comissao",
        obrigatorio: false,
        condicao: "Se usar comissao",
        onde: "/pdv",
        resultado: "Comissao gerada conforme regra configurada.",
      },
      {
        id: "fechar-caixa",
        titulo: "Fechar caixa e conferir diferenca",
        obrigatorio: true,
        onde: "/meus-caixas",
        resultado: "Conferencia diaria finalizada sem pendencias.",
      },
    ],
  },
  {
    id: "gestao",
    titulo: "6) Gestao e acompanhamento",
    itens: [
      {
        id: "contas-receber",
        titulo: "Conferir contas a receber geradas",
        obrigatorio: true,
        onde: "/financeiro/contas-receber",
        resultado: "Ciclo de recebimento funcionando.",
      },
      {
        id: "contas-pagar",
        titulo: "Lancar contas a pagar iniciais",
        obrigatorio: true,
        onde: "/financeiro/contas-pagar",
        resultado: "Resultado financeiro com custos reais.",
      },
      {
        id: "fluxo-caixa",
        titulo: "Validar fluxo de caixa",
        obrigatorio: true,
        onde: "/financeiro/fluxo-caixa",
        resultado: "Entrada e saida batendo com a operacao.",
      },
      {
        id: "dre",
        titulo: "Classificar e revisar DRE",
        obrigatorio: true,
        onde: "/financeiro/dre",
        resultado: "Indicadores de lucro e margem confiaveis.",
      },
      {
        id: "relatorios-vendas",
        titulo: "Revisar relatorios de vendas",
        obrigatorio: true,
        onde: "/financeiro/relatorio-vendas",
        resultado: "Visao gerencial pronta para decisao.",
      },
    ],
  },
];

function toCount(data) {
  if (Array.isArray(data)) return data.length;
  if (!data || typeof data !== "object") return 0;
  if (Array.isArray(data.items)) return data.items.length;
  if (Array.isArray(data.data)) return data.data.length;
  if (typeof data.total === "number") return data.total;
  if (typeof data.count === "number") return data.count;
  return 0;
}

function makeStorageKey() {
  try {
    const raw = localStorage.getItem("user");
    if (!raw) return STORAGE_KEY;
    const user = JSON.parse(raw);
    return `${STORAGE_KEY}_${user?.id || "anon"}_${user?.tenant_id || "tenant"}`;
  } catch {
    return STORAGE_KEY;
  }
}

function buildGuiaHref(path, guiaId) {
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}guia=${encodeURIComponent(guiaId)}`;
}

export default function IntroducaoGuiada() {
  const [marcados, setMarcados] = useState({});
  const [autoChecks, setAutoChecks] = useState({});
  const [carregandoChecks, setCarregandoChecks] = useState(false);

  const storageKey = useMemo(() => makeStorageKey(), []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        setMarcados(parsed);
      }
    } catch {
      // Ignora leitura invalida do localStorage
    }
  }, [storageKey]);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(marcados));
  }, [marcados, storageKey]);

  const executarChecksAutomaticos = async () => {
    setCarregandoChecks(true);

    const results = {
      empresaFiscal: false,
      empresaDados: false,
      contasBancarias: false,
      formasPagamento: false,
      operadoras: false,
      categoriasProduto: false,
      produtos: false,
      pessoas: false,
      pets: false,
      configEntrega: false,
      entregadores: false,
      comissoesConfig: false,
      opcoesRacao: false,
      caixaAberto: false,
      temVendas: false,
    };

    const chamadas = [
      api.get("/empresa/fiscal").then((res) => {
        const data = res.data || {};
        results.empresaFiscal = Boolean(data.regime_tributario || data.cnae_principal || data.aliquota_simples_vigente);
      }),
      api.get("/empresa/dados-cadastrais").then((res) => {
        const data = res.data || {};
        results.empresaDados = Boolean(
          data.cnpj &&
            data.razao_social &&
            data.endereco &&
            data.numero &&
            data.bairro &&
            data.cidade &&
            data.uf,
        );
      }),
      api.get("/contas-bancarias?apenas_ativas=true").then((res) => {
        results.contasBancarias = toCount(res.data) > 0;
      }),
      api.get("/financeiro/formas-pagamento?apenas_ativas=true").then((res) => {
        results.formasPagamento = toCount(res.data) > 0;
      }),
      api.get("/operadoras-cartao?apenas_ativas=true").then((res) => {
        results.operadoras = toCount(res.data) > 0;
      }),
      api.get("/produtos/categorias").then((res) => {
        results.categoriasProduto = toCount(res.data) > 0;
      }),
      api.get("/produtos?per_page=1").then((res) => {
        const data = res.data || {};
        results.produtos = Boolean((Array.isArray(data.produtos) && data.produtos.length > 0) || data.total > 0);
      }),
      api.get("/clientes/?limit=1").then((res) => {
        results.pessoas = toCount(res.data) > 0;
      }),
      api.get("/pets?limit=1").then((res) => {
        results.pets = toCount(res.data) > 0;
      }),
      api.get("/configuracoes/entregas").then((res) => {
        const data = res.data || {};
        results.configEntrega = Object.keys(data).length > 0;
      }),
      api.get("/clientes/?is_entregador=true&incluir_inativos=false&limit=1").then((res) => {
        results.entregadores = toCount(res.data) > 0;
      }),
      api.get("/comissoes/configuracoes/funcionarios").then((res) => {
        const lista = res.data?.data || [];
        results.comissoesConfig = lista.some((f) => Number(f.total_configuracoes || 0) > 0);
      }),
      api.get("/opcoes-racao/linhas?apenas_ativos=false").then((res) => {
        results.opcoesRacao = toCount(res.data) > 0;
      }),
      api.get("/caixas/aberto").then((res) => {
        results.caixaAberto = Boolean(res.data?.id);
      }),
      api.get("/vendas?page=1&per_page=1").then((res) => {
        const data = res.data || {};
        results.temVendas = Number(data.total || 0) > 0;
      }),
    ];

    await Promise.all(chamadas.map((p) => p.catch(() => null)));
    setAutoChecks(results);
    setCarregandoChecks(false);
  };

  useEffect(() => {
    executarChecksAutomaticos();
  }, []);

  const todosItens = useMemo(() => SECOES.flatMap((secao) => secao.itens), []);

  const total = todosItens.length;
  const concluidos = todosItens.filter((item) => {
    const auto = item.autoCheckKey ? autoChecks[item.autoCheckKey] : false;
    return Boolean(auto || marcados[item.id]);
  }).length;

  const percentual = total > 0 ? Math.round((concluidos / total) * 100) : 0;

  const alternarItem = (itemId) => {
    setMarcados((prev) => ({ ...prev, [itemId]: !prev[itemId] }));
  };

  const resetarChecklist = () => {
    setMarcados({});
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Preparando seu sistema</h2>
            <p className="text-sm text-gray-600 mt-1">
              Sequencia guiada para configurar o sistema do jeito certo e evitar falhas no dia a dia.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={executarChecksAutomaticos}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <FiRefreshCcw className="w-4 h-4" />
              Atualizar checagem
            </button>
            <button
              onClick={resetarChecklist}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <FiRotateCcw className="w-4 h-4" />
              Resetar
            </button>
          </div>
        </div>

        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="text-gray-600">Progresso geral</span>
          <span className="font-semibold text-gray-900">{concluidos}/{total} ({percentual}%)</span>
        </div>
        <div className="h-3 w-full bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 transition-all"
            style={{ width: `${percentual}%` }}
          />
        </div>

        {carregandoChecks && (
          <div className="mt-3 text-xs text-gray-500">Verificando situacao real no sistema...</div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4">
        {SECOES.map((secao) => (
          <section key={secao.id} className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
            <h3 className="text-lg font-bold text-gray-900 mb-4">{secao.titulo}</h3>

            <div className="space-y-3">
              {secao.itens.map((item) => {
                const autoConcluido = item.autoCheckKey ? Boolean(autoChecks[item.autoCheckKey]) : false;
                const concluido = autoConcluido || Boolean(marcados[item.id]);
                const badgeObrigatorio = item.obrigatorio ? "Obrigatorio" : "Opcional";

                return (
                  <div
                    key={item.id}
                    className={`border rounded-xl p-4 ${concluido ? "border-emerald-200 bg-emerald-50/40" : "border-gray-200"}`}
                  >
                    <div className="flex items-start gap-3">
                      <button
                        type="button"
                        onClick={() => alternarItem(item.id)}
                        disabled={autoConcluido}
                        className={`mt-0.5 ${autoConcluido ? "cursor-not-allowed" : "cursor-pointer"}`}
                        aria-label={`Marcar item ${item.titulo}`}
                      >
                        {concluido ? (
                          <FiCheckCircle className="w-5 h-5 text-emerald-600" />
                        ) : (
                          <FiCircle className="w-5 h-5 text-gray-400" />
                        )}
                      </button>

                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <p className="text-sm font-semibold text-gray-900">{item.titulo}</p>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${item.obrigatorio ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600"}`}>
                            {badgeObrigatorio}
                          </span>
                          {autoConcluido && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                              Confirmado automaticamente
                            </span>
                          )}
                        </div>

                        {item.condicao && (
                          <p className="text-xs text-amber-700 inline-flex items-center gap-1 mb-1">
                            <FiAlertCircle className="w-3 h-3" />
                            {item.condicao}
                          </p>
                        )}

                        <div className="text-xs text-gray-600 space-y-1">
                          <p>
                            <span className="font-medium">Onde fazer:</span>{" "}
                            <a
                              href={buildGuiaHref(item.onde, item.id)}
                              target="_blank"
                              rel="noreferrer"
                              className="text-indigo-700 hover:underline inline-flex items-center gap-1"
                            >
                              {item.onde} <FiExternalLink className="w-3 h-3" />
                            </a>
                          </p>
                          <p>
                            <span className="font-medium">Resultado:</span> {item.resultado}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-2xl p-5">
        <p className="text-sm font-semibold text-blue-900 mb-1">Proxima evolucao (ja planejada)</p>
        <p className="text-sm text-blue-800">
          Pre-configuracao automatica com 1 clique para criar cadastros padrao (formas de pagamento, categorias e ajustes iniciais),
          reduzindo o trabalho manual na implantacao.
        </p>
      </div>
    </div>
  );
}
