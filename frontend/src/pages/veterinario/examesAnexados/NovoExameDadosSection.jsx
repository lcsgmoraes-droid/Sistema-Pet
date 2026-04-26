import CampoTextoExame from "./CampoTextoExame";

export default function NovoExameDadosSection({ form, setArquivoNovo, setForm }) {
  return (
    <>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Tipo*</label>
        <select
          value={form.tipo}
          onChange={(event) => setForm((prev) => ({ ...prev, tipo: event.target.value }))}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
        >
          <option value="laboratorial">Laboratorial</option>
          <option value="imagem">Imagem</option>
          <option value="clinico">Clinico</option>
          <option value="outro">Outro</option>
        </select>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Data da solicitacao</label>
        <input
          type="date"
          value={form.data_solicitacao}
          onChange={(event) => setForm((prev) => ({ ...prev, data_solicitacao: event.target.value }))}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>

      <CampoTextoExame
        label="Nome do exame*"
        value={form.nome}
        onChange={(value) => setForm((prev) => ({ ...prev, nome: value }))}
        placeholder="Ex: Hemograma completo"
        className="sm:col-span-2"
      />

      <CampoTextoExame
        label="Laboratorio"
        value={form.laboratorio}
        onChange={(value) => setForm((prev) => ({ ...prev, laboratorio: value }))}
        placeholder="Opcional"
        className="sm:col-span-2"
      />

      <div className="sm:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Observacoes</label>
        <textarea
          value={form.observacoes}
          onChange={(event) => setForm((prev) => ({ ...prev, observacoes: event.target.value }))}
          rows={4}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          placeholder="Informacoes adicionais do exame agendado..."
        />
      </div>

      <div className="sm:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Arquivo do exame</label>
        <input
          type="file"
          onChange={(event) => setArquivoNovo(event.target.files?.[0] ?? null)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-orange-100 file:px-3 file:py-1.5 file:text-orange-700"
        />
        <p className="mt-1 text-xs text-gray-500">
          Se anexar agora, o exame ja aparece nesta tela e fica pronto para consulta pela IA.
        </p>
      </div>
    </>
  );
}
