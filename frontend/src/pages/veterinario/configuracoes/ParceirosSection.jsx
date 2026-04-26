import { Building2, ChevronDown, ChevronUp, Link2, Plus, Trash2 } from "lucide-react";

import { TIPO_RELACAO_LABEL } from "./configuracoesConstants";

export default function ParceirosSection({
  form,
  mostrarForm,
  onCancel,
  onChangeForm,
  onRemover,
  onSave,
  onToggleAtivo,
  onToggleForm,
  parceiros,
  salvando,
  tenantsVet,
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between p-5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Link2 size={20} className="text-blue-500" />
          <h2 className="text-lg font-semibold text-gray-900">Veterinários Parceiros</h2>
          <span className="ml-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
            {parceiros.length}
          </span>
        </div>
        <button
          onClick={onToggleForm}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} />
          Vincular parceiro
          {mostrarForm ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {mostrarForm && (
        <div className="p-5 bg-blue-50 border-b border-blue-100 space-y-4">
          <h3 className="font-medium text-gray-800">Novo vínculo de parceria</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tenant veterinário *
              </label>
              {tenantsVet.length === 0 ? (
                <p className="text-sm text-gray-500 italic">
                  Nenhum tenant veterinário cadastrado no sistema. O veterinário precisa ter uma conta própria no sistema.
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
                Tipo de relação
              </label>
              <select
                value={form.tipoRelacao}
                onChange={(event) => onChangeForm({ tipoRelacao: event.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="parceiro">Parceiro (tenant próprio)</option>
                <option value="funcionario">Funcionário (mesmo tenant)</option>
              </select>
            </div>

            {form.tipoRelacao === "parceiro" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Comissão da empresa (%)
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
                  Percentual que vai para a empresa sobre os procedimentos do veterinário parceiro.
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
      )}

      {parceiros.length === 0 ? (
        <div className="p-8 text-center text-gray-500">
          <Building2 size={36} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Nenhum parceiro vinculado</p>
          <p className="text-sm mt-1">
            Clique em &quot;Vincular parceiro&quot; para conectar um veterinário com conta própria no sistema.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-gray-100">
          {parceiros.map((parceiro) => (
            <div key={parceiro.id} className="flex items-center gap-4 p-4">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <Building2 size={20} className="text-blue-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {parceiro.vet_tenant_nome || "Veterinário"}
                </p>
                <p className="text-xs text-gray-500">
                  {TIPO_RELACAO_LABEL[parceiro.tipo_relacao] ?? parceiro.tipo_relacao}
                  {parceiro.comissao_empresa_pct != null && parceiro.tipo_relacao === "parceiro" && (
                    <> · Comissão empresa: <strong>{parceiro.comissao_empresa_pct}%</strong></>
                  )}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onToggleAtivo(parceiro)}
                  className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                    parceiro.ativo
                      ? "bg-green-100 text-green-700 hover:bg-green-200"
                      : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                  }`}
                >
                  {parceiro.ativo ? "Ativo" : "Inativo"}
                </button>
                <button
                  onClick={() => onRemover(parceiro.id)}
                  className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                  title="Remover vínculo"
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
