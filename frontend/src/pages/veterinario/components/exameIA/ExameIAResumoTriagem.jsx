export default function ExameIAResumoTriagem({ exame }) {
  if (!exame.interpretacao_ia_resumo && !exame.interpretacao_ia) return null;

  return (
    <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-3">
      <p className="font-medium text-indigo-900">Resumo da triagem</p>
      <p className="mt-1 text-sm text-indigo-800">
        {exame.interpretacao_ia_resumo || exame.interpretacao_ia}
      </p>
      {exame.interpretacao_ia && exame.interpretacao_ia !== exame.interpretacao_ia_resumo && (
        <p className="mt-2 text-xs text-indigo-700">
          <strong>Conclusao:</strong> {exame.interpretacao_ia}
        </p>
      )}
      {exame.interpretacao_ia_confianca != null && (
        <p className="mt-2 text-[11px] text-indigo-600">
          Confianca estimada: {Math.round(Number(exame.interpretacao_ia_confianca || 0) * 100)}%
        </p>
      )}
    </div>
  );
}
