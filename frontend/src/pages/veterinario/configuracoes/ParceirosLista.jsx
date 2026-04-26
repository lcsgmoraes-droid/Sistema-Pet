import { Building2, Trash2 } from "lucide-react";

import { TIPO_RELACAO_LABEL } from "./configuracoesConstants";

export default function ParceirosLista({ onRemover, onToggleAtivo, parceiros }) {
  if (parceiros.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        <Building2 size={36} className="mx-auto mb-3 text-gray-300" />
        <p className="font-medium">Nenhum parceiro vinculado</p>
        <p className="text-sm mt-1">
          Clique em &quot;Vincular parceiro&quot; para conectar um veterinario com conta propria no sistema.
        </p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-100">
      {parceiros.map((parceiro) => (
        <ParceiroRow
          key={parceiro.id}
          onRemover={onRemover}
          onToggleAtivo={onToggleAtivo}
          parceiro={parceiro}
        />
      ))}
    </div>
  );
}

function ParceiroRow({ onRemover, onToggleAtivo, parceiro }) {
  return (
    <div className="flex items-center gap-4 p-4">
      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
        <Building2 size={20} className="text-blue-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">
          {parceiro.vet_tenant_nome || "Veterinario"}
        </p>
        <p className="text-xs text-gray-500">
          {TIPO_RELACAO_LABEL[parceiro.tipo_relacao] ?? parceiro.tipo_relacao}
          {parceiro.comissao_empresa_pct != null && parceiro.tipo_relacao === "parceiro" && (
            <> - Comissao empresa: <strong>{parceiro.comissao_empresa_pct}%</strong></>
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
          title="Remover vinculo"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}
