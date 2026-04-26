import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { montarSerieEvolucao } from "./internacaoUtils";

export default function CurvaEvolucaoInternacao({ evolucoes }) {
  const serie = montarSerieEvolucao(evolucoes);
  if (serie.length < 2) return null;

  return (
    <div className="mb-4 rounded-xl border border-blue-100 bg-white p-4">
      <p className="text-xs font-semibold text-gray-500 mb-3">Curva de evolução</p>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={serie}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="horario" tick={{ fontSize: 11 }} />
          <YAxis yAxisId="vital" tick={{ fontSize: 11 }} />
          <YAxis yAxisId="peso" orientation="right" tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Line
            yAxisId="vital"
            type="monotone"
            dataKey="temperatura"
            name="Temperatura"
            stroke="#ef4444"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            yAxisId="vital"
            type="monotone"
            dataKey="fc"
            name="FC"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            yAxisId="vital"
            type="monotone"
            dataKey="fr"
            name="FR"
            stroke="#14b8a6"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            yAxisId="peso"
            type="monotone"
            dataKey="peso"
            name="Peso"
            stroke="#7c3aed"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
