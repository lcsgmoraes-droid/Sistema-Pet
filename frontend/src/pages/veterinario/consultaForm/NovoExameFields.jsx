export default function NovoExameFields({
  css,
  novoExameForm,
  setNovoExameForm,
  setNovoExameArquivo,
}) {
  return (
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
  );
}
