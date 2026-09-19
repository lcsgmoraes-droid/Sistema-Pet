import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";
import AnaliseProdutosKpis from "./AnaliseProdutosKpis";
import { agruparProdutos, resumirCurvaAbc } from "./analiseProdutosUtils";

const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(Number(valor || 0));

const formatarDia = (valor) => {
  if (!valor) return "-";
  const [ano, mes, dia] = valor.split("-");
  return `${dia}/${mes}/${ano.slice(-2)}`;
};

const nomeCurto = (valor, limite = 22) =>
  valor?.length > limite ? `${valor.slice(0, limite - 1)}…` : valor || "Sem nome";

function EstadoVazio() {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
      <p className="font-semibold text-slate-800">Nenhuma venda de produto neste recorte.</p>
      <p className="mt-2 text-sm text-slate-500">
        Altere o período ou remova algum filtro para ampliar a busca.
      </p>
    </div>
  );
}

function TituloBloco({ titulo, descricao, complemento }) {
  return (
    <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 className="text-lg font-bold text-slate-900">{titulo}</h2>
        {descricao && <p className="mt-1 text-sm text-slate-500">{descricao}</p>}
      </div>
      {complemento}
    </div>
  );
}

function TooltipGrafico({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const rotulo = /^\d{4}-\d{2}-\d{2}$/.test(String(label || "")) ? formatarDia(label) : label;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 text-xs shadow-xl">
      <p className="mb-2 font-semibold text-slate-800">{rotulo}</p>
      {payload.map((item) => (
        <p key={item.dataKey} style={{ color: item.color }} className="mt-1">
          {item.name}:{" "}
          {item.dataKey.includes("_pct")
            ? formatPercent(item.value)
            : item.dataKey.includes("faturamento") || item.dataKey.includes("lucro")
              ? formatMoneyBRL(item.value)
              : formatarQuantidade(item.value)}
        </p>
      ))}
    </div>
  );
}

function TabelaProdutos({ produtos }) {
  const [ordenacao, setOrdenacao] = useState("faturamento");
  const ordenados = useMemo(
    () => [...produtos].sort((a, b) => Number(b[ordenacao] || 0) - Number(a[ordenacao] || 0)),
    [ordenacao, produtos],
  );
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <TituloBloco
        titulo="Resultado por produto"
        descricao={`${produtos.length} produto(s) com venda no filtro aplicado.`}
        complemento={
          <select
            value={ordenacao}
            onChange={(event) => setOrdenacao(event.target.value)}
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-700"
            aria-label="Ordenar produtos"
          >
            <option value="faturamento">Maior faturamento</option>
            <option value="quantidade">Maior quantidade</option>
            <option value="lucro_estimado">Maior lucro estimado</option>
            <option value="margem_estimada_pct">Maior margem estimada</option>
          </select>
        }
      />
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3 text-left">Produto</th>
              <th className="px-5 py-3 text-left">Grupo</th>
              <th className="px-5 py-3 text-right">Quantidade</th>
              <th className="px-5 py-3 text-right">Faturamento</th>
              <th className="px-5 py-3 text-right">Lucro estimado</th>
              <th className="px-5 py-3 text-right">Margem</th>
              <th className="px-5 py-3 text-right">Estoque / cobertura</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {ordenados.map((item) => (
              <tr key={item.produto_id} className="hover:bg-slate-50">
                <td className="px-5 py-3">
                  <p className="font-semibold text-slate-900">{item.produto_nome}</p>
                  <p className="text-xs text-slate-500">{item.codigo || "Sem código"}</p>
                </td>
                <td className="px-5 py-3 text-sm text-slate-600">
                  <p>{item.categoria_nome || "Sem categoria"}</p>
                  <p className="text-xs text-slate-400">{item.marca_nome || "Sem marca"}</p>
                </td>
                <td className="px-5 py-3 text-right text-sm font-semibold text-slate-800">
                  {formatarQuantidade(item.quantidade)}
                </td>
                <td className="px-5 py-3 text-right text-sm font-semibold text-slate-900">
                  {formatMoneyBRL(item.faturamento)}
                </td>
                <td
                  className={`px-5 py-3 text-right text-sm font-semibold ${Number(item.lucro_estimado) < 0 ? "text-rose-700" : "text-emerald-700"}`}
                >
                  {formatMoneyBRL(item.lucro_estimado)}
                </td>
                <td className="px-5 py-3 text-right text-sm text-slate-700">
                  {formatPercent(item.margem_estimada_pct)}
                </td>
                <td className="px-5 py-3 text-right text-sm text-slate-700">
                  <p>{formatarQuantidade(item.estoque_atual)} un.</p>
                  <p className="text-xs text-slate-500">
                    {item.cobertura_estoque_dias == null
                      ? "Sem giro para estimar"
                      : `${formatarQuantidade(item.cobertura_estoque_dias)} dias`}
                  </p>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function VisaoGeralProdutos({ dados }) {
  const topFaturamento = dados.produtos
    .slice(0, 10)
    .map((item) => ({ ...item, nome_curto: nomeCurto(item.produto_nome) }));
  const topQuantidade = [...dados.produtos]
    .sort((a, b) => b.quantidade - a.quantidade)
    .slice(0, 10)
    .map((item) => ({ ...item, nome_curto: nomeCurto(item.produto_nome) }));

  if (!dados.produtos.length) return <EstadoVazio />;
  return (
    <div className="space-y-5">
      <AnaliseProdutosKpis resumo={dados.resumo} />
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <TituloBloco
          titulo="Evolução das vendas"
          descricao="Faturamento e quantidade diária dentro do período selecionado."
        />
        <div className="h-80 p-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dados.evolucao} margin={{ left: 8, right: 12, top: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="data"
                tickFormatter={formatarDia}
                minTickGap={30}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                yAxisId="valor"
                tickFormatter={(valor) => `R$ ${Number(valor) / 1000}k`}
                tick={{ fontSize: 11 }}
              />
              <YAxis yAxisId="qtd" orientation="right" tick={{ fontSize: 11 }} />
              <Tooltip content={<TooltipGrafico />} labelFormatter={formatarDia} />
              <Legend />
              <Line
                yAxisId="valor"
                type="monotone"
                dataKey="faturamento"
                name="Faturamento"
                stroke="#2563eb"
                strokeWidth={3}
                dot={false}
              />
              <Line
                yAxisId="qtd"
                type="monotone"
                dataKey="quantidade"
                name="Quantidade"
                stroke="#0f766e"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        {[
          {
            titulo: "Mais vendidos em faturamento",
            data: topFaturamento,
            campo: "faturamento",
            cor: "#2563eb",
          },
          {
            titulo: "Mais vendidos em quantidade",
            data: topQuantidade,
            campo: "quantidade",
            cor: "#0f766e",
          },
        ].map((grafico) => (
          <div
            key={grafico.campo}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-base font-bold text-slate-900">{grafico.titulo}</h2>
            <div className="mt-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={grafico.data} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" hide />
                  <YAxis dataKey="nome_curto" type="category" width={145} tick={{ fontSize: 11 }} />
                  <Tooltip content={<TooltipGrafico />} />
                  <Bar
                    dataKey={grafico.campo}
                    name={grafico.campo === "faturamento" ? "Faturamento" : "Quantidade"}
                    fill={grafico.cor}
                    radius={[0, 6, 6, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>
      <TabelaProdutos produtos={dados.produtos} />
    </div>
  );
}

const CORES_ABC = {
  A: "bg-emerald-100 text-emerald-800",
  B: "bg-amber-100 text-amber-800",
  C: "bg-slate-200 text-slate-700",
};

export function CurvaAbcProdutos({ produtos }) {
  const [base, setBase] = useState("faturamento");
  const classeCampo = `abc_${base}`;
  const acumuladoCampo = `acumulado_${base}_pct`;
  const ordenados = useMemo(
    () => [...produtos].sort((a, b) => Number(b[base] || 0) - Number(a[base] || 0)),
    [base, produtos],
  );
  const resumo = useMemo(() => resumirCurvaAbc(produtos, base), [base, produtos]);
  const grafico = ordenados
    .slice(0, 25)
    .map((item) => ({ ...item, nome_curto: nomeCurto(item.produto_nome, 16) }));

  if (!produtos.length) return <EstadoVazio />;
  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-blue-100 bg-blue-50 p-5 text-sm text-blue-950 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-100">
        <p className="font-bold">Como ler a Curva ABC</p>
        <p className="mt-1">
          Classe A concentra aproximadamente os primeiros 80% do resultado; B, os 15% seguintes; C,
          os 5% restantes. O item que cruza cada limite permanece na classe anterior.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {[
          { id: "faturamento", label: "Por faturamento" },
          { id: "quantidade", label: "Por quantidade" },
        ].map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setBase(item.id)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold ${base === item.id ? "bg-blue-600 text-white" : "border border-slate-300 bg-white text-slate-700"}`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {resumo.map((item) => (
          <div
            key={item.classe}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <span
                className={`rounded-full px-3 py-1 text-sm font-bold ${CORES_ABC[item.classe]}`}
              >
                Classe {item.classe}
              </span>
              <span className="text-sm font-semibold text-slate-500">{item.produtos} produtos</span>
            </div>
            <p className="mt-4 text-2xl font-bold text-slate-950">
              {base === "faturamento" ? formatMoneyBRL(item.valor) : formatarQuantidade(item.valor)}
            </p>
            <p className="mt-1 text-sm text-slate-500">
              {formatPercent(item.participacao_pct)} do total
            </p>
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <TituloBloco
          titulo="Pareto dos produtos"
          descricao="Barras mostram o resultado individual; a linha mostra o percentual acumulado. Exibindo os primeiros 25 produtos."
        />
        <div className="h-96 p-4">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={grafico} margin={{ left: 8, right: 12, top: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="nome_curto"
                angle={-35}
                textAnchor="end"
                height={85}
                interval={0}
                tick={{ fontSize: 10 }}
              />
              <YAxis yAxisId="valor" tick={{ fontSize: 11 }} />
              <YAxis
                yAxisId="pct"
                orientation="right"
                domain={[0, 100]}
                tickFormatter={(valor) => `${valor}%`}
                tick={{ fontSize: 11 }}
              />
              <Tooltip content={<TooltipGrafico />} />
              <Legend />
              <Bar
                yAxisId="valor"
                dataKey={base}
                name={base === "faturamento" ? "Faturamento" : "Quantidade"}
                fill="#2563eb"
                radius={[5, 5, 0, 0]}
              />
              <Line
                yAxisId="pct"
                type="monotone"
                dataKey={acumuladoCampo}
                name="Acumulado (%)"
                stroke="#ea580c"
                strokeWidth={3}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <TituloBloco titulo="Classificação completa" descricao={`Ordenada por ${base}.`} />
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3 text-left">Posição / produto</th>
                <th className="px-5 py-3 text-center">Classe</th>
                <th className="px-5 py-3 text-right">Quantidade</th>
                <th className="px-5 py-3 text-right">Faturamento</th>
                <th className="px-5 py-3 text-right">Acumulado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {ordenados.map((item, indice) => (
                <tr key={item.produto_id} className="hover:bg-slate-50">
                  <td className="px-5 py-3">
                    <p className="font-semibold text-slate-900">
                      {indice + 1}. {item.produto_nome}
                    </p>
                    <p className="text-xs text-slate-500">{item.codigo || "Sem código"}</p>
                  </td>
                  <td className="px-5 py-3 text-center">
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-bold ${CORES_ABC[item[classeCampo]]}`}
                    >
                      {item[classeCampo]}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right text-sm">
                    {formatarQuantidade(item.quantidade)}
                  </td>
                  <td className="px-5 py-3 text-right text-sm font-semibold">
                    {formatMoneyBRL(item.faturamento)}
                  </td>
                  <td className="px-5 py-3 text-right text-sm">
                    {formatPercent(item[acumuladoCampo])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function GruposProdutos({ produtos }) {
  const [dimensao, setDimensao] = useState("categoria");
  const grupos = useMemo(() => agruparProdutos(produtos, dimensao), [dimensao, produtos]);
  const rotulos = {
    categoria: "Categoria",
    marca: "Marca",
    departamento: "Departamento",
    fornecedor: "Fornecedor",
  };
  const grafico = grupos
    .slice(0, 15)
    .map((item) => ({ ...item, nome_curto: nomeCurto(item.nome) }));

  if (!produtos.length) return <EstadoVazio />;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {Object.entries(rotulos).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setDimensao(id)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold ${dimensao === id ? "bg-blue-600 text-white" : "border border-slate-300 bg-white text-slate-700"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <TituloBloco
          titulo={`Faturamento por ${rotulos[dimensao].toLowerCase()}`}
          descricao="Os 15 grupos com maior faturamento no recorte atual."
        />
        <div className="h-80 p-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={grafico} margin={{ left: 8, right: 12, top: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="nome_curto"
                angle={-25}
                textAnchor="end"
                height={70}
                interval={0}
                tick={{ fontSize: 10 }}
              />
              <YAxis
                tickFormatter={(valor) => `R$ ${Number(valor) / 1000}k`}
                tick={{ fontSize: 11 }}
              />
              <Tooltip content={<TooltipGrafico />} />
              <Bar dataKey="faturamento" name="Faturamento" fill="#2563eb" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <TituloBloco
          titulo={`Resultado por ${rotulos[dimensao].toLowerCase()}`}
          descricao={`${grupos.length} grupo(s) encontrados.`}
        />
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3 text-left">{rotulos[dimensao]}</th>
                <th className="px-5 py-3 text-right">Produtos</th>
                <th className="px-5 py-3 text-right">Quantidade</th>
                <th className="px-5 py-3 text-right">Faturamento</th>
                <th className="px-5 py-3 text-right">Lucro estimado</th>
                <th className="px-5 py-3 text-right">Participação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {grupos.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3 font-semibold text-slate-900">{item.nome}</td>
                  <td className="px-5 py-3 text-right text-sm">{item.produtos}</td>
                  <td className="px-5 py-3 text-right text-sm">
                    {formatarQuantidade(item.quantidade)}
                  </td>
                  <td className="px-5 py-3 text-right text-sm font-semibold">
                    {formatMoneyBRL(item.faturamento)}
                  </td>
                  <td
                    className={`px-5 py-3 text-right text-sm font-semibold ${item.lucro_estimado < 0 ? "text-rose-700" : "text-emerald-700"}`}
                  >
                    {formatMoneyBRL(item.lucro_estimado)}
                  </td>
                  <td className="px-5 py-3 text-right text-sm">
                    {formatPercent(item.participacao_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
