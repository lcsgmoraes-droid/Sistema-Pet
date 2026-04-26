export default function ParceiroFormPanel({
  form,
  onCancel,
  onChangeForm,
  onSave,
  salvando,
  tenantsVet,
}) {
  return (
    <div className="p-5 bg-blue-50 border-b border-blue-100 space-y-4">
      <h3 className="font-medium text-gray-800">Novo vinculo de parceria</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Tenant veterinario *
          </label>
          {tenantsVet.length === 0 ? (
            <p className="text-sm text-gray-500 italic">
              Nenhum tenant veterinario cadastrado no sistema. O veterinario precisa ter uma conta propria no sistema.
            </p>
          ) : (
            <select
              value={form.vetTenantId}
              onChange={(event) => onChangeForm({ vetTenantId: event.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Selecione...</option>
              {tenantsVet.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.nome} {tenant.cnpj ? `- CNPJ ${tenant.cnpj}` : ""}
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Tipo de relacao
          </label>
          <select
            value={form.tipoRelacao}
            onChange={(event) => onChangeForm({ tipoRelacao: event.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="parceiro">Parceiro (tenant proprio)</option>
            <option value="funcionario">Funcionario (mesmo tenant)</option>
          </select>
        </div>

        {form.tipoRelacao === "parceiro" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Comissao da empresa (%)
            </label>
            <input
              type="number"
              min="0"
              max="100"
              step="0.5"
              placeholder="Ex: 20"
              value={form.comissao}
              onChange={(event) => onChangeForm({ comissao: event.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Percentual que vai para a empresa sobre os procedimentos do veterinario parceiro.
            </p>
          </div>
        )}
      </div>
      <div className="flex gap-3">
        <button
          onClick={onSave}
          disabled={salvando || !form.vetTenantId}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {salvando ? "Salvando..." : "Salvar parceiro"}
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 transition-colors"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
