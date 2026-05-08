import React from "react";
import FornecedorSelector from "../fornecedores/FornecedorSelector";

function CampoSelect({ children, disabled = false, label, onChange, value }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      <select
        value={value}
        onChange={onChange}
        disabled={disabled}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
      >
        {children}
      </select>
    </div>
  );
}

export default function ProdutosFornecedoresLoteSection({
  dadosEdicaoLote,
  fornecedores = [],
  onAtualizarCampo,
}) {
  const fornecedorExigeSelecao =
    dadosEdicaoLote.fornecedor_operacao && dadosEdicaoLote.fornecedor_operacao !== "remover";
  const fornecedorSelecionado = fornecedores.find(
    (fornecedor) => String(fornecedor.id) === String(dadosEdicaoLote.fornecedor_id),
  );

  return (
    <section className="space-y-4 rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4">
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-emerald-900">
          Fornecedores
        </h3>
        <p className="text-xs text-emerald-800">
          Ajuste vinculos de fornecedor dos produtos selecionados, incluindo o fornecedor principal.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <CampoSelect
          label="Acao em lote"
          value={dadosEdicaoLote.fornecedor_operacao}
          onChange={(event) => {
            const operacao = event.target.value;
            onAtualizarCampo("fornecedor_operacao", operacao);
            if (!operacao || operacao === "remover") {
              onAtualizarCampo("fornecedor_id", "");
            }
          }}
        >
          <option value="">Nao alterar</option>
          <option value="definir_principal">Definir como principal</option>
          <option value="adicionar">Adicionar fornecedor</option>
          <option value="remover">Remover fornecedor</option>
        </CampoSelect>

        <FornecedorSelector
          fornecedores={fornecedores}
          fornecedorId={dadosEdicaoLote.fornecedor_id}
          fornecedorSelecionado={fornecedorSelecionado}
          disabled={!fornecedorExigeSelecao}
          label="Fornecedor"
          placeholder={
            fornecedorExigeSelecao
              ? "Digite o nome do fornecedor..."
              : dadosEdicaoLote.fornecedor_operacao === "remover"
                ? "Nao precisa selecionar"
                : "Escolha uma acao primeiro"
          }
          onSelect={(fornecedor) => onAtualizarCampo("fornecedor_id", String(fornecedor.id))}
          onClear={() => onAtualizarCampo("fornecedor_id", "")}
          onFornecedorCriado={(fornecedor) => onAtualizarCampo("fornecedor_id", String(fornecedor.id))}
        />
      </div>

      {dadosEdicaoLote.fornecedor_operacao === "definir_principal" && (
        <div className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs text-emerald-800">
          O fornecedor selecionado sera vinculado, ativado e marcado como principal. Ao salvar, voce escolhe se remove os outros fornecedores ou se mantem como alternativos.
        </div>
      )}
      {dadosEdicaoLote.fornecedor_operacao === "adicionar" && (
        <div className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs text-emerald-800">
          Adiciona ou reativa o fornecedor nos produtos selecionados sem alterar o principal atual.
        </div>
      )}
      {dadosEdicaoLote.fornecedor_operacao === "remover" && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Remove os fornecedores vinculados dos produtos selecionados. Para trocar por um novo principal, use "Definir como principal" e escolha remover os outros ao salvar.
        </div>
      )}
    </section>
  );
}
