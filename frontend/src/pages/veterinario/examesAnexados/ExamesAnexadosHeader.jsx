import { FlaskConical, Plus } from "lucide-react";

export default function ExamesAnexadosHeader({ onNovoExame, onVerPets }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-orange-100 rounded-xl">
          <FlaskConical size={20} className="text-orange-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-800">Exames Anexados</h1>
          <p className="text-xs text-gray-500">
            Lista enxuta por data de upload, com foco no que já tem arquivo.
          </p>
        </div>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onNovoExame}
          className="inline-flex items-center gap-2 rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600"
        >
          <Plus size={15} />
          Novo exame
        </button>
        <button
          type="button"
          onClick={onVerPets}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          Ver pets
        </button>
      </div>
    </div>
  );
}
