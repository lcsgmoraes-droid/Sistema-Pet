import { formatarDataExame } from "./exameIAUtils";

export default function ExameIACabecalho({ exame, resumo, temAnaliseIA, temArquivo, temResultadoBase }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="font-semibold text-indigo-900">
          Exame #{exame.id} - {exame.nome || exame.tipo || "Exame"}
        </div>
        <p className="mt-1 text-indigo-600">
          Tipo: {exame.tipo || "nao informado"}
          {exame.data_solicitacao ? ` - solicitado em ${formatarDataExame(exame.data_solicitacao)}` : ""}
        </p>
        {resumo && (
          <p className="mt-1 text-indigo-600">
            Tutor: {resumo.tutor_nome || "-"} | Pet: {resumo.pet_nome || "-"}
          </p>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <StatusBadge
          ativo={temArquivo}
          ativoClass="bg-emerald-100 text-emerald-700"
          ativoLabel="Arquivo anexado"
          inativoClass="bg-amber-100 text-amber-700"
          inativoLabel="Sem arquivo"
        />
        <StatusBadge
          ativo={temAnaliseIA}
          ativoClass="bg-indigo-100 text-indigo-700"
          ativoLabel="IA pronta"
          inativoClass="bg-gray-100 text-gray-600"
          inativoLabel="IA pendente"
        />
        <StatusBadge
          ativo={temResultadoBase}
          ativoClass="bg-blue-100 text-blue-700"
          ativoLabel="Resultado carregado"
          inativoClass="bg-gray-100 text-gray-600"
          inativoLabel="Sem resultado base"
        />
      </div>
    </div>
  );
}

function StatusBadge({ ativo, ativoClass, ativoLabel, inativoClass, inativoLabel }) {
  return (
    <span className={`rounded-full px-2 py-1 font-medium ${ativo ? ativoClass : inativoClass}`}>
      {ativo ? ativoLabel : inativoLabel}
    </span>
  );
}
