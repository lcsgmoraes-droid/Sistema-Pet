import { ArrowDown, ArrowUp } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import VendasComparativoPeriodoTable from "./VendasComparativoPeriodoTable";

const TIPOS_COMPARACAO = [
  { value: "financeiro", label: "Comparacao Financeira" },
  { value: "formas_pagamento", label: "Por Forma de Pagamento" },
  { value: "produtos", label: "Por Grupo de Produtos" },
  { value: "funcionarios", label: "Por Funcionario" },
];

function numero(valor) {
  return Number(valor || 0);
}

function valorRecebido(resumo) {
  return numero(resumo.venda_liquida) - numero(resumo.em_aberto);
}

function ResumoPeriodoCard({
  borderClass,
  headerClass,
  periodo,
  resumo,
  titulo,
  formatarMoeda,
}) {
  return (
    <div className={`bg-white rounded-lg shadow-lg border-2 ${borderClass}`}>
      <div className={`${headerClass} text-white px-4 py-3 rounded-t-lg`}>
        <h3 className="font-bold text-lg">{titulo}</h3>
        <p className="text-xs opacity-90 mt-1">{periodo}</p>
      </div>
      <div className="p-4 space-y-3">
        <div className="border-b pb-2">
          <div className="text-xs text-gray-600">Quantidade de Vendas</div>
          <div className="text-2xl font-bold text-gray-700">
            {resumo.quantidade_vendas || 0}
          </div>
        </div>
        <div className="border-b pb-2">
          <div className="text-xs text-gray-600">Valor Bruto</div>
          <div className="text-xl font-bold text-gray-700">
            {formatarMoeda(resumo.venda_bruta)}
          </div>
        </div>
        <div className="border-b pb-2">
          <div className="text-xs text-gray-600">Valor Liquido</div>
          <div className="text-xl font-bold text-blue-600">
            {formatarMoeda(resumo.venda_liquida)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-600">Valor Recebido</div>
          <div className="text-xl font-bold text-green-600">
            {formatarMoeda(valorRecebido(resumo))}
          </div>
        </div>
      </div>
    </div>
  );
}

function VariacaoLinha({ formatarValor, label, variacao }) {
  const positiva = variacao.percentual >= 0;
  const Icon = positiva ? ArrowUp : ArrowDown;

  return (
    <div className="border-b pb-2 last:border-b-0 last:pb-0">
      <div className="text-xs text-gray-600">{label}</div>
      <div
        className={`text-xl font-bold flex items-center gap-2 ${
          positiva ? "text-green-600" : "text-red-600"
        }`}
      >
        <Icon className="w-5 h-5" />
        {Math.abs(variacao.percentual)}%
      </div>
      <div className="text-xs text-gray-500 mt-1">
        {formatarValor(variacao.valor)}
      </div>
    </div>
  );
}

function VariacaoCard({
  calcularVariacao,
  formatarMoeda,
  resumo,
  resumoComparacao,
}) {
  const variacoes = [
    {
      label: "Qtd de Vendas",
      formatarValor: (valor) => `${valor >= 0 ? "+" : ""}${valor.toFixed(0)} vendas`,
      value: calcularVariacao(
        resumo.quantidade_vendas,
        resumoComparacao.quantidade_vendas,
      ),
    },
    {
      label: "Valor Bruto",
      formatarValor: formatarMoeda,
      value: calcularVariacao(resumo.venda_bruta, resumoComparacao.venda_bruta),
    },
    {
      label: "Valor Liquido",
      formatarValor: formatarMoeda,
      value: calcularVariacao(resumo.venda_liquida, resumoComparacao.venda_liquida),
    },
    {
      label: "Valor Recebido",
      formatarValor: formatarMoeda,
      value: calcularVariacao(valorRecebido(resumo), valorRecebido(resumoComparacao)),
    },
  ];

  return (
    <div className="bg-white rounded-lg shadow-lg border-2 border-green-500">
      <div className="bg-green-600 text-white px-4 py-3 rounded-t-lg">
        <h3 className="font-bold text-lg">Diferenca</h3>
        <p className="text-xs opacity-90 mt-1">
          Variacao vs periodo anterior
        </p>
      </div>
      <div className="p-4 space-y-3">
        {variacoes.map((item) => (
          <VariacaoLinha
            key={item.label}
            formatarValor={item.formatarValor}
            label={item.label}
            variacao={item.value}
          />
        ))}
      </div>
    </div>
  );
}

function ComparacaoFinanceira({
  calcularVariacao,
  dataFim,
  dataInicio,
  formatarData,
  formatarMoeda,
  getTextoComparacao,
  resumo,
  resumoComparacao,
}) {
  const dados = [
    {
      nome: "Qtd Vendas",
      Anterior: numero(resumoComparacao.quantidade_vendas),
      Atual: numero(resumo.quantidade_vendas),
    },
    {
      nome: "Vl. Bruto (mil)",
      Anterior: numero(resumoComparacao.venda_bruta) / 1000,
      Atual: numero(resumo.venda_bruta) / 1000,
    },
    {
      nome: "Vl. Liquido (mil)",
      Anterior: numero(resumoComparacao.venda_liquida) / 1000,
      Atual: numero(resumo.venda_liquida) / 1000,
    },
    {
      nome: "Vl. Recebido (mil)",
      Anterior: valorRecebido(resumoComparacao) / 1000,
      Atual: valorRecebido(resumo) / 1000,
    },
  ];

  return (
    <>
      <div className="grid grid-cols-3 gap-6 mb-6">
        <ResumoPeriodoCard
          borderClass="border-gray-300"
          formatarMoeda={formatarMoeda}
          headerClass="bg-gray-500"
          periodo={getTextoComparacao()}
          resumo={resumoComparacao}
          titulo="Periodo Anterior"
        />
        <ResumoPeriodoCard
          borderClass="border-blue-500"
          formatarMoeda={formatarMoeda}
          headerClass="bg-blue-600"
          periodo={`${formatarData(dataInicio)} - ${formatarData(dataFim)}`}
          resumo={resumo}
          titulo="Periodo Atual"
        />
        <VariacaoCard
          calcularVariacao={calcularVariacao}
          formatarMoeda={formatarMoeda}
          resumo={resumo}
          resumoComparacao={resumoComparacao}
        />
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          Comparacao Visual
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={dados}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="nome" />
            <YAxis />
            <Tooltip
              formatter={(value, name) => [
                String(name).includes("mil") ? `R$ ${value.toFixed(1)}k` : value.toFixed(0),
                name,
              ]}
            />
            <Legend />
            <Bar dataKey="Anterior" fill="#9CA3AF" name="Periodo Anterior" />
            <Bar dataKey="Atual" fill="#3B82F6" name="Periodo Atual" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}

function ComparacaoBarras({
  corAtual,
  data,
  titulo = "Comparacao Visual",
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">{titulo}</h3>
      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="nome" angle={-15} textAnchor="end" height={80} />
          <YAxis tickFormatter={(value) => `R$ ${value.toFixed(0)}k`} />
          <Tooltip formatter={(value) => `R$ ${value.toFixed(1)}k`} />
          <Legend />
          <Bar dataKey="Anterior" fill="#9CA3AF" name="Periodo Anterior" />
          <Bar dataKey="Atual" fill={corAtual} name="Periodo Atual" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function GraficoPizzaGrupo({ coresGraficos, data, formatarMoeda, titulo }) {
  const total = data.reduce((sum, item) => sum + numero(item.valor_liquido), 0);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">{titulo}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            dataKey="valor_liquido"
            nameKey="grupo"
            cx="50%"
            cy="50%"
            outerRadius={80}
            label={(entry) => {
              if (!total) return "";
              const percent = ((numero(entry.valor_liquido) / total) * 100).toFixed(1);
              return Number(percent) > 5 ? `${percent}%` : "";
            }}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-grupo-${titulo}-${entry.grupo || index}`}
                fill={coresGraficos[index % coresGraficos.length]}
              />
            ))}
          </Pie>
          <Tooltip formatter={(value) => formatarMoeda(value)} />
          <Legend verticalAlign="bottom" height={36} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function VendasComparacaoPanel({
  calcularVariacao,
  coresGraficos,
  dataFim,
  dataInicio,
  formasRecebimentoComparacaoConsolidadas,
  formasRecebimentoConsolidadas,
  formatarData,
  formatarMoeda,
  getTextoComparacao,
  resumo,
  resumoComparacao,
  setTipoComparacao,
  tipoComparacao,
  vendasPorFuncionario,
  vendasPorFuncionarioComparacao,
  vendasPorGrupo,
  vendasPorGrupoComparacao,
}) {
  const dadosFormasPagamento = formasRecebimentoConsolidadas.map((forma) => ({
    nome: forma.forma_pagamento,
    Anterior:
      numero(
        formasRecebimentoComparacaoConsolidadas.find(
          (anterior) => anterior.forma_pagamento === forma.forma_pagamento,
        )?.valor_total,
      ) / 1000,
    Atual: numero(forma.valor_total) / 1000,
  }));

  const dadosFuncionarios = vendasPorFuncionario.map((funcionario) => ({
    nome: funcionario.funcionario,
    Anterior:
      numero(
        vendasPorFuncionarioComparacao.find(
          (anterior) => anterior.funcionario === funcionario.funcionario,
        )?.valor_liquido,
      ) / 1000,
    Atual: numero(funcionario.valor_liquido) / 1000,
  }));

  return (
    <div>
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center gap-4">
          <label
            htmlFor="tipo-comparacao-vendas"
            className="text-sm font-medium text-gray-700"
          >
            Tipo de Analise:
          </label>
          <select
            id="tipo-comparacao-vendas"
            value={tipoComparacao}
            onChange={(event) => setTipoComparacao(event.target.value)}
            className="border rounded px-4 py-2 text-sm bg-blue-50 font-medium min-w-[250px]"
          >
            {TIPOS_COMPARACAO.map((tipo) => (
              <option key={tipo.value} value={tipo.value}>
                {tipo.label}
              </option>
            ))}
          </select>

          <div className="ml-auto text-sm text-gray-600">
            <span className="font-medium">Periodo Atual:</span>{" "}
            {formatarData(dataInicio)} - {formatarData(dataFim)}
          </div>
        </div>
      </div>

      {tipoComparacao === "financeiro" && (
        <ComparacaoFinanceira
          calcularVariacao={calcularVariacao}
          dataFim={dataFim}
          dataInicio={dataInicio}
          formatarData={formatarData}
          formatarMoeda={formatarMoeda}
          getTextoComparacao={getTextoComparacao}
          resumo={resumo}
          resumoComparacao={resumoComparacao}
        />
      )}

      {tipoComparacao === "formas_pagamento" && (
        <>
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Comparacao por Forma de Pagamento
            </h3>
            <VendasComparativoPeriodoTable
              emptyMessage="Nenhuma forma de pagamento encontrada"
              labelHeader="Forma de pagamento"
              labelKey="forma_pagamento"
              linhasAnteriores={formasRecebimentoComparacaoConsolidadas}
              linhasAtuais={formasRecebimentoConsolidadas}
              rowKeyPrefix="comp-forma"
              valueKey="valor_total"
            />
          </div>
          <ComparacaoBarras corAtual="#10B981" data={dadosFormasPagamento} />
        </>
      )}

      {tipoComparacao === "produtos" && (
        <>
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Comparacao por Grupo de Produtos
            </h3>
            <VendasComparativoPeriodoTable
              emptyMessage="Nenhum grupo encontrado"
              labelHeader="Grupo"
              labelKey="grupo"
              linhasAnteriores={vendasPorGrupoComparacao}
              linhasAtuais={vendasPorGrupo}
              rowKeyPrefix="comp-grupo"
              valueKey="valor_liquido"
            />
          </div>

          <div className="grid grid-cols-2 gap-6">
            <GraficoPizzaGrupo
              coresGraficos={coresGraficos}
              data={vendasPorGrupoComparacao}
              formatarMoeda={formatarMoeda}
              titulo="Periodo Anterior"
            />
            <GraficoPizzaGrupo
              coresGraficos={coresGraficos}
              data={vendasPorGrupo}
              formatarMoeda={formatarMoeda}
              titulo="Periodo Atual"
            />
          </div>
        </>
      )}

      {tipoComparacao === "funcionarios" && (
        <>
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Comparacao por Funcionario
            </h3>
            <VendasComparativoPeriodoTable
              emptyMessage="Nenhum funcionario encontrado"
              includeQuantidade
              labelHeader="Funcionario"
              labelKey="funcionario"
              linhasAnteriores={vendasPorFuncionarioComparacao}
              linhasAtuais={vendasPorFuncionario}
              rowKeyPrefix="comp-func"
              valueKey="valor_liquido"
            />
          </div>
          <ComparacaoBarras
            corAtual="#8B5CF6"
            data={dadosFuncionarios}
            titulo="Comparacao Visual - Valor Liquido"
          />
        </>
      )}
    </div>
  );
}
