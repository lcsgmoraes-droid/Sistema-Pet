import { Building2, ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";

export default function ConsultoriosSection({
  consultorios,
  form,
  mostrarForm,
  onCancel,
  onChangeForm,
  onRemover,
  onSave,
  onToggleAtivo,
  onToggleForm,
  salvando,
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between p-5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Building2 size={20} className="text-emerald-500" />
          <h2 className="text-lg font-semibold text-gray-900">Consultórios / Salas</h2>
          <span className="ml-1 text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
            {consultorios.length}
          </span>
        </div>
        <button
          onClick={onToggleForm}
          className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 transition-colors"
        >
          <Plus size={16} />
          Novo consultório
          {mostrarForm ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {mostrarForm && (
        <div className="p-5 bg-emerald-50 border-b border-emerald-100 space-y-4">
          <h3 className="font-medium text-gray-800">Cadastrar consultório</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
              <input
                type="text"
                value={form.nome}
                onChange={(event) => onChangeForm({ nome: event.target.value })}
                placeholder="Ex: Consultório 1"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ordem</label>
              <input
                type="number"
                min="1"
                max="999"
                value={form.ordem}
                onChange={(event) => onChangeForm({ ordem: event.target.value })}
                placeholder="Ex: 1"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              />
            </div>
            <div className="sm:col-span-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
              <input
                type="text"
                value={form.descricao}
                onChange={(event) => onChangeForm({ descricao: event.target.value })}
                placeholder="Opcional. Ex: Sala com ultrassom"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={onSave}
              disabled={salvando || !form.nome.trim()}
              className="px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {salvando ? "Salvando..." : "Salvar consultório"}
            </button>
            <button
              onClick={onCancel}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {consultorios.length === 0 ? (
        <div className="p-8 text-center text-gray-500">
          <Building2 size={36} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Nenhum consultório cadastrado</p>
          <p className="text-sm mt-1">
            Cadastre as salas para a agenda alertar conflito por consultório.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-gray-100">
          {consultorios.map((consultorio) => (
            <div key={consultorio.id} className="flex items-center gap-4 p-4">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                <Building2 size={20} className="text-emerald-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{consultorio.nome}</p>
                <p className="text-xs text-gray-500">
                  Ordem {consultorio.ordem}
                  {consultorio.descricao ? ` · ${consultorio.descricao}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onToggleAtivo(consultorio)}
                  className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                    consultorio.ativo
                      ? "bg-green-100 text-green-700 hover:bg-green-200"
                      : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                  }`}
                >
                  {consultorio.ativo ? "Ativo" : "Inativo"}
                </button>
                <button
                  onClick={() => onRemover(consultorio)}
                  className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                  title="Remover consultório"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
