import { COST_CLASSIFICATION_OPTIONS } from "./categoriasFinanceirasConstants";

export default function CategoriaFinanceiraFormFields({
  colors,
  editando,
  formData,
  icons,
  setFormData,
}) {
  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
        <input
          type="text"
          value={formData.nome}
          onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Tipo *</label>
        <select
          value={formData.tipo}
          onChange={(e) =>
            setFormData({
              ...formData,
              tipo: e.target.value,
              tipo_custo: e.target.value === "receita" ? null : formData.tipo_custo,
            })
          }
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          required
        >
          <option value="despesa">Despesa</option>
          <option value="receita">Receita</option>
        </select>
      </div>

      {formData.tipo === "despesa" && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            ðŸ’° ClassificaÃ§Ã£o de Custo
          </label>
          <div className="flex gap-2">
            {COST_CLASSIFICATION_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() =>
                  setFormData({
                    ...formData,
                    tipo_custo: formData.tipo_custo === option.value ? null : option.value,
                  })
                }
                className={`flex-1 px-2 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
                  formData.tipo_custo === option.value
                    ? option.activeClass
                    : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
                }`}
                title={option.desc}
              >
                {option.label}
              </button>
            ))}
          </div>
          {formData.tipo_custo === "ambos" && (
            <p className="text-xs text-purple-600 mt-1">
              â†• As subcategorias desta categoria terÃ£o classificaÃ§Ã£o individual
            </p>
          )}
          {formData.tipo_custo === "fixo" && editando && (
            <p className="text-xs text-orange-600 mt-1">
              ðŸ”’ Ao salvar, todas as subcategorias serÃ£o classificadas como Fixo
            </p>
          )}
          {formData.tipo_custo === "variavel" && editando && (
            <p className="text-xs text-blue-600 mt-1">
              ðŸ“ˆ Ao salvar, todas as subcategorias serÃ£o classificadas como VariÃ¡vel
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Ãcone</label>
          <select
            value={formData.icone}
            onChange={(e) => setFormData({ ...formData, icone: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          >
            {icons.map((icon) => (
              <option key={icon} value={icon}>
                {icon}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cor</label>
          <div className="flex gap-2">
            <input
              type="color"
              value={formData.cor}
              onChange={(e) => setFormData({ ...formData, cor: e.target.value })}
              className="w-12 h-10 border border-gray-300 rounded-md"
            />
            <select
              value={formData.cor}
              onChange={(e) => setFormData({ ...formData, cor: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            >
              {colors.map((color) => (
                <option key={color} value={color}>
                  {color}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">DescriÃ§Ã£o</label>
        <textarea
          value={formData.descricao}
          onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          rows="3"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="ativo"
          checked={formData.ativo}
          onChange={(e) => setFormData({ ...formData, ativo: e.target.checked })}
          className="w-4 h-4 text-blue-600 rounded"
        />
        <label htmlFor="ativo" className="text-sm text-gray-700">
          Categoria ativa
        </label>
      </div>
    </>
  );
}
