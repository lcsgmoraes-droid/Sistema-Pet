import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  Building2,
  Calculator,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Gauge,
  Landmark,
  Save,
  Settings2,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import api from "../api";
import LoadingState from "../components/ui/LoadingState";
import MetricCard from "../components/ui/MetricCard";
import MetricGrid from "../components/ui/MetricGrid";
import PageHeader from "../components/ui/PageHeader";
import { formatMoneyBRL } from "../utils/formatters";

const inputClasses =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

function mensagemErro(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

function moeda(valor) {
  return formatMoneyBRL(Number(valor || 0));
}

function percentual(valor) {
  return `${Number(valor || 0).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
}

function Campo({ label, hint, children }) {
  return (
    <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
      <span>{label}</span>
      {children}
      {hint ? <span className="text-xs font-normal text-slate-500">{hint}</span> : null}
    </label>
  );
}

function CampoNumero({ value, onChange, suffix, min = 0, step = "0.01" }) {
  return (
    <div className="relative">
      <input
        className={`${inputClasses} ${suffix ? "pr-14" : ""}`}
        type="number"
        min={min}
        step={step}
        value={value ?? ""}
        onChange={(event) =>
          onChange(event.target.value === "" ? null : Number(event.target.value))
        }
      />
      {suffix ? (
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-slate-500">
          {suffix}
        </span>
      ) : null}
    </div>
  );
}

function CenarioCard({ cenario, destaque }) {
  const estilos = destaque
    ? "border-blue-500 bg-gradient-to-br from-blue-600 to-indigo-700 text-white shadow-lg"
    : "border-slate-200 bg-white text-slate-900 shadow-sm";
  return (
    <article className={`relative rounded-2xl border p-5 ${estilos}`}>
      {destaque ? (
        <span className="absolute right-4 top-4 rounded-full bg-white/20 px-2.5 py-1 text-xs font-semibold">
          Referência
        </span>
      ) : null}
      <p className={`text-sm font-semibold ${destaque ? "text-blue-100" : "text-slate-500"}`}>
        Cenário {cenario.nome.toLowerCase()}
      </p>
      <p className="mt-2 text-3xl font-bold tracking-tight">{moeda(cenario.valor_sugerido)}</p>
      <div className={`mt-4 space-y-1.5 text-xs ${destaque ? "text-blue-100" : "text-slate-500"}`}>
        <p>{cenario.multiplo_lucro_meses} meses de lucro operacional</p>
        <p>{percentual(cenario.desconto_estoque_lento_percentual)} de ajuste no estoque lento</p>
      </div>
    </article>
  );
}

export default function ValorEmpresa() {
  const [dados, setDados] = useState(null);
  const [form, setForm] = useState(null);
  const [fornecedores, setFornecedores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [simulando, setSimulando] = useState(false);
  const [configAberta, setConfigAberta] = useState(false);
  const [faturamentoSimulado, setFaturamentoSimulado] = useState(0);

  const carregar = async () => {
    setLoading(true);
    try {
      const [avaliacao, listaFornecedores] = await Promise.all([
        api.get("/financeiro/valor-empresa"),
        api.get("/financeiro/valor-empresa/fornecedores"),
      ]);
      setDados(avaliacao.data);
      setForm(avaliacao.data.configuracao);
      setFaturamentoSimulado(avaliacao.data.operacao.faturamento_mensal_normalizado || 0);
      setFornecedores(listaFornecedores.data || []);
    } catch (error) {
      console.error("Erro ao carregar valor da empresa:", error);
      toast.error(mensagemErro(error, "Não foi possível calcular o valor da empresa."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregar();
  }, []);

  const atualizar = (campo, valor) => setForm((atual) => ({ ...atual, [campo]: valor }));

  const alternarFornecedor = (id) => {
    const atuais = form.fornecedor_ids_excluidos || [];
    atualizar(
      "fornecedor_ids_excluidos",
      atuais.includes(id) ? atuais.filter((item) => item !== id) : [...atuais, id],
    );
  };

  const payloadConfiguracao = () => {
    const { id: _id, fornecedores_excluidos: _fornecedores, ...payload } = form;
    return payload;
  };

  const salvar = async () => {
    setSalvando(true);
    try {
      const response = await api.put(
        "/financeiro/valor-empresa/configuracao",
        payloadConfiguracao(),
      );
      setDados(response.data);
      setForm(response.data.configuracao);
      setFaturamentoSimulado(response.data.operacao.faturamento_mensal_normalizado || 0);
      toast.success("Premissas salvas e avaliação recalculada.");
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível salvar as premissas."));
    } finally {
      setSalvando(false);
    }
  };

  const simular = async () => {
    setSimulando(true);
    try {
      const response = await api.post("/financeiro/valor-empresa/simular", {
        faturamento_mensal: Number(faturamentoSimulado || 0),
      });
      setDados(response.data);
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível executar a simulação."));
    } finally {
      setSimulando(false);
    }
  };

  const provavel = useMemo(
    () => dados?.cenarios?.find((item) => item.chave === "provavel"),
    [dados],
  );
  const provavelSimulado = useMemo(
    () => dados?.simulacao?.cenarios?.find((item) => item.chave === "provavel"),
    [dados],
  );

  if (loading) return <LoadingState message="Calculando o valor da empresa..." />;
  if (!dados || !form) return null;

  const confianca = dados.confianca || {};
  const operacao = dados.operacao || {};
  const estoque = dados.ativos?.estoque || {};
  const imobilizado = dados.ativos?.imobilizado || {};

  return (
    <div className="space-y-6 pb-10">
      <PageHeader
        title="Valor da Empresa"
        subtitle={`Estimativa gerencial com base nos últimos ${dados.periodo.dias} dias, de ${new Date(`${dados.periodo.inicio}T12:00:00`).toLocaleDateString("pt-BR")} a ${new Date(`${dados.periodo.fim}T12:00:00`).toLocaleDateString("pt-BR")}.`}
        icon={Landmark}
      />

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <div className="flex gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">Estimativa para negociação, não laudo contábil.</p>
            <p className="mt-1 text-amber-800">
              O preço final também depende do contrato, riscos fiscais, ponto comercial, marca e
              validação dos números pelo comprador.
            </p>
          </div>
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <div className="grid gap-4 md:grid-cols-3">
          {dados.cenarios.map((cenario) => (
            <CenarioCard
              key={cenario.chave}
              cenario={cenario}
              destaque={cenario.chave === "provavel"}
            />
          ))}
        </div>
        <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-500">Confiança dos dados</p>
              <p className="mt-1 text-2xl font-bold capitalize text-slate-900">{confianca.nivel}</p>
            </div>
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-lg font-bold text-slate-800">
              {confianca.pontuacao}
            </div>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-blue-600"
              style={{ width: `${confianca.pontuacao}%` }}
            />
          </div>
          <div className="mt-4 space-y-2 text-xs text-slate-600">
            {(confianca.alertas || []).length ? (
              confianca.alertas.map((alerta) => <p key={alerta}>• {alerta}</p>)
            ) : (
              <p className="flex items-center gap-2 text-emerald-700">
                <CheckCircle2 className="h-4 w-4" /> Base completa para estimativa.
              </p>
            )}
          </div>
        </aside>
      </section>

      <MetricGrid>
        <MetricCard
          label="Faturamento mensal"
          value={moeda(operacao.faturamento_mensal_normalizado)}
          icon={<TrendingUp className="h-5 w-5" />}
          intent="blue"
        />
        <MetricCard
          label="Lucro operacional mensal"
          value={moeda(operacao.lucro_operacional_mensal)}
          icon={<BarChart3 className="h-5 w-5" />}
          intent={operacao.lucro_operacional_mensal >= 0 ? "emerald" : "red"}
        />
        <MetricCard
          label="Estoque a custo"
          value={moeda(estoque.valor_custo)}
          icon={<Boxes className="h-5 w-5" />}
          intent="amber"
        />
        <MetricCard
          label="Imobilizado usado"
          value={moeda(imobilizado.valor_usado)}
          icon={<Building2 className="h-5 w-5" />}
          intent="violet"
        />
      </MetricGrid>

      <section className="grid gap-5 xl:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Calculator className="h-5 w-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-slate-900">
              Como o cenário provável foi formado
            </h2>
          </div>
          <div className="mt-5 divide-y divide-slate-100 text-sm">
            {[
              ["Estoque negociável", provavel?.estoque_negociavel],
              ["Imobilizado pelo valor de mercado", provavel?.imobilizado],
              [
                `Fundo de comércio (${provavel?.multiplo_lucro_meses || 0} meses de lucro)`,
                provavel?.fundo_comercio,
              ],
              ["Outros ativos", provavel?.outros_ativos],
              ["Dívidas assumidas pelo comprador", -(provavel?.dividas || 0)],
            ].map(([label, valor]) => (
              <div key={label} className="flex items-center justify-between gap-4 py-3">
                <span className="text-slate-600">{label}</span>
                <span className={`font-semibold ${valor < 0 ? "text-rose-600" : "text-slate-900"}`}>
                  {moeda(valor)}
                </span>
              </div>
            ))}
            <div className="flex items-center justify-between gap-4 py-4 text-base">
              <span className="font-bold text-slate-900">Valor sugerido</span>
              <span className="font-bold text-blue-700">{moeda(provavel?.valor_sugerido)}</span>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Gauge className="h-5 w-5 text-indigo-600" />
            <h2 className="text-lg font-semibold text-slate-900">Simulador de faturamento</h2>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Veja quanto a empresa pode valer mantendo a margem e a estrutura de custos atuais.
          </p>
          <div className="mt-5 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
            <Campo label="Faturamento mensal simulado">
              <CampoNumero value={faturamentoSimulado} onChange={setFaturamentoSimulado} />
            </Campo>
            <button
              type="button"
              onClick={simular}
              disabled={simulando}
              className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {simulando ? "Calculando..." : "Simular"}
            </button>
          </div>
          <input
            className="mt-5 w-full accent-indigo-600"
            type="range"
            min="0"
            max={Math.max(200000, operacao.faturamento_mensal_normalizado * 2)}
            step="1000"
            value={faturamentoSimulado}
            onChange={(event) => setFaturamentoSimulado(Number(event.target.value))}
          />
          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Lucro projetado
              </p>
              <p className="mt-1 text-xl font-bold text-slate-900">
                {moeda(dados.simulacao.lucro_mensal)}
              </p>
            </div>
            <div className="rounded-xl bg-indigo-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                Valor provável
              </p>
              <p className="mt-1 text-xl font-bold text-indigo-800">
                {moeda(provavelSimulado?.valor_sugerido)}
              </p>
            </div>
          </div>
        </article>
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <button
          type="button"
          onClick={() => setConfigAberta((valor) => !valor)}
          className="flex w-full items-center justify-between gap-4 p-5 text-left hover:bg-slate-50"
        >
          <div className="flex items-center gap-3">
            <Settings2 className="h-5 w-5 text-slate-600" />
            <div>
              <h2 className="font-semibold text-slate-900">Premissas da avaliação</h2>
              <p className="text-sm text-slate-500">
                Revise exclusões, folha, imobilizado, descontos e múltiplos.
              </p>
            </div>
          </div>
          {configAberta ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </button>
        {configAberta ? (
          <div className="border-t border-slate-200 p-5">
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              <Campo label="Período principal" hint="Entre 30 e 730 dias">
                <CampoNumero
                  value={form.periodo_dias}
                  onChange={(valor) => atualizar("periodo_dias", valor)}
                  suffix="dias"
                  step="1"
                />
              </Campo>
              <Campo label="Canais" hint="Separe por vírgula">
                <input
                  className={inputClasses}
                  value={form.canais || ""}
                  onChange={(event) => atualizar("canais", event.target.value)}
                />
              </Campo>
              <Campo
                label="Folha mensal ajustada"
                hint={`Sistema: ${moeda(operacao.folha_mensal_sistema)}`}
              >
                <CampoNumero
                  value={form.folha_mensal_override}
                  onChange={(valor) => atualizar("folha_mensal_override", valor)}
                />
              </Campo>
              <Campo
                label="Outras despesas fixas/mês"
                hint={`Calculado: ${moeda(operacao.outras_despesas_fixas_mensais)}`}
              >
                <CampoNumero
                  value={form.despesas_fixas_mensais_override}
                  onChange={(valor) => atualizar("despesas_fixas_mensais_override", valor)}
                />
              </Campo>
              <Campo
                label="Margem de contribuição"
                hint={`Calculada: ${percentual(operacao.margem_contribuicao_percentual)}`}
              >
                <CampoNumero
                  value={form.margem_contribuicao_override}
                  onChange={(valor) => atualizar("margem_contribuicao_override", valor)}
                  suffix="%"
                />
              </Campo>
              <Campo label="Imobilizado manual" hint={`Cadastro: ${moeda(imobilizado.valor)}`}>
                <CampoNumero
                  value={form.imobilizado_override}
                  onChange={(valor) => atualizar("imobilizado_override", valor)}
                />
              </Campo>
              <Campo label="Outros ativos">
                <CampoNumero
                  value={form.outros_ativos}
                  onChange={(valor) => atualizar("outros_ativos", valor)}
                />
              </Campo>
              <Campo label="Estoque considerado lento">
                <CampoNumero
                  value={form.dias_estoque_lento}
                  onChange={(valor) => atualizar("dias_estoque_lento", valor)}
                  suffix="dias"
                  step="1"
                />
              </Campo>
            </div>

            <div className="mt-6 grid gap-5 xl:grid-cols-2">
              <div className="rounded-xl border border-slate-200 p-4">
                <p className="text-sm font-semibold text-slate-800">
                  Fornecedores fora da avaliação
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Exclui tanto o estoque quanto as contas a pagar desses fornecedores.
                </p>
                <div className="mt-3 max-h-44 space-y-2 overflow-y-auto pr-1">
                  {fornecedores.map((fornecedor) => (
                    <label
                      key={fornecedor.id}
                      className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-50"
                    >
                      <input
                        type="checkbox"
                        checked={(form.fornecedor_ids_excluidos || []).includes(fornecedor.id)}
                        onChange={() => alternarFornecedor(fornecedor.id)}
                        className="h-4 w-4 accent-blue-600"
                      />
                      <span>{fornecedor.nome}</span>
                      <span className="text-xs text-slate-400">#{fornecedor.id}</span>
                    </label>
                  ))}
                  {!fornecedores.length ? (
                    <p className="text-sm text-slate-500">Nenhum fornecedor encontrado.</p>
                  ) : null}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <label className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-800">
                      Comprador assume dívidas?
                    </p>
                    <p className="text-xs text-slate-500">
                      Saldo aberto elegível: {moeda(dados.dividas.saldo_aberto)}
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={form.incluir_dividas}
                    onChange={(event) => atualizar("incluir_dividas", event.target.checked)}
                    className="h-5 w-5 accent-blue-600"
                  />
                </label>
                {form.incluir_dividas ? (
                  <div className="mt-4">
                    <Campo label="Percentual assumido">
                      <CampoNumero
                        value={form.percentual_dividas_assumidas}
                        onChange={(valor) => atualizar("percentual_dividas_assumidas", valor)}
                        suffix="%"
                      />
                    </Campo>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2">Cenário</th>
                    <th className="py-2">Desconto estoque lento</th>
                    <th className="py-2">Múltiplo do lucro mensal</th>
                  </tr>
                </thead>
                <tbody>
                  {["conservador", "provavel", "otimista"].map((chave) => (
                    <tr key={chave} className="border-b border-slate-100 last:border-0">
                      <td className="py-3 font-medium capitalize">
                        {chave === "provavel" ? "provável" : chave}
                      </td>
                      <td className="py-3 pr-4">
                        <CampoNumero
                          value={form[`desconto_estoque_${chave}`]}
                          onChange={(valor) => atualizar(`desconto_estoque_${chave}`, valor)}
                          suffix="%"
                        />
                      </td>
                      <td className="py-3">
                        <CampoNumero
                          value={form[`multiplo_lucro_${chave}`]}
                          onChange={(valor) => atualizar(`multiplo_lucro_${chave}`, valor)}
                          suffix="meses"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Campo label="Observações">
              <textarea
                className={`${inputClasses} mt-1 min-h-24`}
                value={form.observacoes || ""}
                onChange={(event) => atualizar("observacoes", event.target.value)}
                placeholder="Ex.: operação física sem a operação Buendia; proprietário não trabalha diretamente..."
              />
            </Campo>
            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={salvar}
                disabled={salvando}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
              >
                <Save className="h-4 w-4" />
                {salvando ? "Salvando..." : "Salvar e recalcular"}
              </button>
            </div>
          </div>
        ) : null}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-slate-900">Fontes usadas no cálculo</h2>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {dados.fontes.map((fonte) => (
            <Link
              key={fonte.rota}
              to={fonte.rota}
              className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:border-blue-300 hover:text-blue-700"
            >
              <span>{fonte.nome}</span>
              <ExternalLink className="h-4 w-4" />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
