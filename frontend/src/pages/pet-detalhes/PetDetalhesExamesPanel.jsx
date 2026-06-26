import PetDetalhesNovoExameForm from "./PetDetalhesNovoExameForm";
import { formatarData } from "./petDetalhesUtils";

export default function PetDetalhesExamesPanel({
  exames,
  loadingExames,
  novoExame,
  onInterpretarExameIA,
  onRefresh,
  onSalvarNovoExame,
  salvandoExame,
  setNovoExame,
}) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_0.95fr] gap-4">
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Exames recentes</h3>
          <button
            type="button"
            onClick={onRefresh}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Atualizar
          </button>
        </div>

        {loadingExames ? (
          <div className="text-sm text-gray-500">Carregando exames...</div>
        ) : exames.length === 0 ? (
          <div className="text-sm text-gray-500">Nenhum exame registrado ainda.</div>
        ) : (
          <div className="space-y-3">
            {exames.map((exame) => (
              <div
                key={exame.id}
                className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-gray-900">{exame.nome}</p>
                    <p className="text-sm text-gray-500">
                      {exame.tipo || "Exame"} â€¢ {formatarData(exame.data_solicitacao)} â€¢{" "}
                      {exame.status || "-"}
                    </p>
                  </div>
                  {exame.arquivo_url && (
                    <a
                      href={exame.arquivo_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-blue-600 hover:text-blue-700"
                    >
                      Abrir arquivo
                    </a>
                  )}
                </div>
                {exame.laboratorio && (
                  <p className="text-sm text-gray-600 mt-2">LaboratÃ³rio: {exame.laboratorio}</p>
                )}
                {exame.interpretacao_ia_resumo && (
                  <div className="mt-2 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2">
                    <p className="text-xs font-semibold text-cyan-800">Triagem IA</p>
                    <p className="text-sm text-cyan-900">{exame.interpretacao_ia_resumo}</p>
                  </div>
                )}
                {exame.observacoes && (
                  <p className="text-sm text-gray-600 mt-2">Obs.: {exame.observacoes}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => onInterpretarExameIA(exame.id)}
                    className="text-sm text-cyan-700 hover:text-cyan-800"
                  >
                    {exame.interpretacao_ia_resumo
                      ? "Reprocessar triagem IA"
                      : "Interpretar com IA"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <PetDetalhesNovoExameForm
        novoExame={novoExame}
        onSalvar={onSalvarNovoExame}
        salvandoExame={salvandoExame}
        setNovoExame={setNovoExame}
      />
    </div>
  );
}
