import AutocompleteSelect from "../../../components/ui/AutocompleteSelect";

const TIPOS_EXAME = [
  { value: "laboratorial", label: "Laboratorial" },
  { value: "imagem", label: "Imagem" },
  { value: "clinico", label: "Cl\u00ednico" },
  { value: "outro", label: "Outro" },
];

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
        <AutocompleteSelect
          value={novoExameForm.tipo}
          onChange={(tipo) => setNovoExameForm((prev) => ({ ...prev, tipo }))}
          options={TIPOS_EXAME}
          placeholder="Digite para buscar tipo..."
          emptyLabel="Nenhum tipo encontrado"
          showLabel={false}
          allowClear={false}
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">
          {"Data da solicita\u00e7\u00e3o"}
        </label>
        <input
          type="date"
          value={novoExameForm.data_solicitacao}
          onChange={(e) =>
            setNovoExameForm((prev) => ({ ...prev, data_solicitacao: e.target.value }))
          }
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
        <label className="mb-1 block text-xs font-medium text-gray-600">{"Laborat\u00f3rio"}</label>
        <input
          type="text"
          value={novoExameForm.laboratorio}
          onChange={(e) => setNovoExameForm((prev) => ({ ...prev, laboratorio: e.target.value }))}
          className={css.input}
        />
      </div>
      <div className="md:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">
          {"Observa\u00e7\u00f5es"}
        </label>
        <textarea
          value={novoExameForm.observacoes}
          onChange={(e) => setNovoExameForm((prev) => ({ ...prev, observacoes: e.target.value }))}
          rows={4}
          className={css.textarea}
          placeholder={"Contexto cl\u00ednico, o que espera confirmar, prioridade..."}
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
          {
            "Pode registrar sem arquivo agora e anexar depois, mas com anexo a IA ja ganha contexto melhor."
          }
        </p>
      </div>
    </div>
  );
}
