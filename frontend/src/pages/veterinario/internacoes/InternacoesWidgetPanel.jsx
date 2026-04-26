import { STATUS_CORES, formatData } from "./internacaoUtils";

const INDICADORES = [
  { chave: "total", label: "Internados agora", classe: "text-purple-700" },
  { chave: "semBaia", label: "Sem baia definida", classe: "text-amber-600" },
  { chave: "comEvolucao", label: "Com evolução", classe: "text-green-600" },
  { chave: "semEvolucao", label: "Sem evolução", classe: "text-red-600" },
  { chave: "mediaDias", label: "Média dias internado", classe: "text-blue-700" },
  { chave: "baiasOcupadas", label: "Baias ocupadas", classe: "text-red-700" },
  { chave: "baiasLivres", label: "Baias livres", classe: "text-emerald-700" },
  { chave: "procedimentosPendentes", label: "Procedimentos pendentes", classe: "text-amber-700" },
  { chave: "procedimentosAtrasados", label: "Procedimentos atrasados", classe: "text-rose-700" },
];

export default function InternacoesWidgetPanel({ indicadoresInternacao, internacoesOrdenadas }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3">
        {INDICADORES.map((indicador) => (
          <div key={indicador.chave} className="bg-white border border-gray-200 rounded-xl p-4">
            <p className="text-xs text-gray-500">{indicador.label}</p>
            <p className={`text-2xl font-bold ${indicador.classe}`}>
              {indicadoresInternacao[indicador.chave]}
            </p>
          </div>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <p className="text-sm font-semibold text-gray-700 mb-2">Widget rápido de internados</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {internacoesOrdenadas.map((internacao) => (
            <div
              key={internacao.id}
              className="flex items-center justify-between border border-gray-100 rounded-lg px-3 py-2"
            >
              <div>
                <p className="text-sm font-medium text-gray-800">
                  {internacao.pet_nome ?? `Pet #${internacao.pet_id}`}
                </p>
                <p className="text-xs text-gray-500">
                  {internacao.box || "Sem baia"} - {formatData(internacao.data_entrada)}
                </p>
              </div>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  STATUS_CORES[internacao.status] ?? "bg-gray-100"
                }`}
              >
                {internacao.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
