import { X } from "lucide-react";

export default function NovoExameConsultaModal({
  isOpen,
  onClose,
  css,
  consultaIdAtual,
  petSelecionadoLabel,
  petId,
  novoExameForm,
  setNovoExameForm,
  setNovoExameArquivo,
  salvarNovoExameRapido,
  salvandoNovoExame,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Novo exame vinculado à consulta</h2>
            <p className="text-sm text-gray-500">
              Consulta #{consultaIdAtual || "—"} • {petSelecionadoLabel}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar modal de exame"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Tipo</label>
            <select
              value={novoExameForm.tipo}
              onChange={(e) => setNovoExameForm((prev) => ({ ...prev, tipo: e.target.value }))}
              className={css.select}
            >
              <option value="laboratorial">Laboratorial</option>
              <option value="imagem">Imagem</option>
              <option value="clinico">Clínico</option>
              <option value="outro">Outro</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Data da solicitação</label>
            <input
              type="date"
              value={novoExameForm.data_solicitacao}
              onChange={(e) => setNovoExameForm((prev) => ({ ...prev, data_solicitacao: e.target.value }))}
              className={css.input}
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-gray-600">Nome do exame</label>
            <input
              type="text"
              value={novoExameForm.nome}
              onChange={(e) => setNovoExameForm((prev) => ({ ...prev, nome: e.target.value }))}
              placeholder="Ex: hemograma, ultrassom, perfil renal..."
              className={css.input}
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-gray-600">Laboratório</label>
            <input
              type="text"
              value={novoExameForm.laboratorio}
              onChange={(e) => setNovoExameForm((prev) => ({ ...prev, laboratorio: e.target.value }))}
              className={css.input}
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-gray-600">Observações</label>
            <textarea
              value={novoExameForm.observacoes}
              onChange={(e) => setNovoExameForm((prev) => ({ ...prev, observacoes: e.target.value }))}
              rows={4}
              className={css.textarea}
              placeholder="Contexto clínico, o que espera confirmar, prioridade..."
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-gray-600">Arquivo do exame</label>
            <input
              type="file"
              onChange={(e) => setNovoExameArquivo(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-blue-100 file:px-3 file:py-1.5 file:text-blue-700"
            />
            <p className="mt-1 text-xs text-gray-500">
              Pode registrar sem arquivo agora e anexar depois, mas com anexo a IA já ganha contexto melhor.
            </p>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={salvarNovoExameRapido}
            disabled={salvandoNovoExame || !petId || !novoExameForm.nome.trim()}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {salvandoNovoExame ? "Salvando..." : "Salvar exame"}
          </button>
        </div>
      </div>
    </div>
  );
}
