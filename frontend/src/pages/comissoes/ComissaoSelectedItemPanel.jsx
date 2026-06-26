import { COMMISSION_ITEM_ICONS } from "./comissoesConstants";

export default function ComissaoSelectedItemPanel({
  adicionarConfiguracao,
  itemSelecionado,
  salvarItem,
  setItemSelecionado,
}) {
  if (!itemSelecionado) {
    return (
      <div className="border rounded-lg p-8 text-center text-gray-500">
        <p>
          Selecione a regra geral, uma categoria, subcategoria ou produto ao lado para configurar
        </p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-4 space-y-4">
      <div>
        <h4 className="font-medium text-gray-700">
          {itemSelecionado.tipo === "geral"
            ? `${COMMISSION_ITEM_ICONS.geral} `
            : `${COMMISSION_ITEM_ICONS[itemSelecionado.tipo]} `}
          {itemSelecionado.nome}
        </h4>
        <p className="text-xs text-gray-500 mt-1">Tipo: {itemSelecionado.tipo}</p>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Tipo de Comissão</label>
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              value="percentual"
              checked={itemSelecionado.tipo_calculo === "percentual"}
              onChange={(event) =>
                setItemSelecionado({ ...itemSelecionado, tipo_calculo: event.target.value })
              }
            />
            <span className="text-sm">Percentual fixo sobre venda</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              value="lucro"
              checked={itemSelecionado.tipo_calculo === "lucro"}
              onChange={(event) =>
                setItemSelecionado({ ...itemSelecionado, tipo_calculo: event.target.value })
              }
            />
            <span className="text-sm">Divisão de lucro</span>
          </label>
        </div>
      </div>

      {itemSelecionado.tipo_calculo === "percentual" ? (
        <div>
          <label className="block text-sm font-medium mb-2">Percentual</label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={itemSelecionado.percentual}
              onChange={(event) =>
                setItemSelecionado({ ...itemSelecionado, percentual: event.target.value })
              }
              className="border rounded px-3 py-2 w-24"
            />
            <span>%</span>
          </div>
        </div>
      ) : (
        <div>
          <label className="block text-sm font-medium mb-2">Divisão do Lucro</label>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-600">Parceiro</label>
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={itemSelecionado.percentual}
                  onChange={(event) => {
                    const val = parseFloat(event.target.value);
                    setItemSelecionado({
                      ...itemSelecionado,
                      percentual: val,
                      percentual_loja: 100 - val,
                    });
                  }}
                  className="border rounded px-2 py-1 w-20"
                />
                <span className="text-sm">%</span>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-600">Loja</label>
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="number"
                  value={itemSelecionado.percentual_loja}
                  readOnly
                  className="border rounded px-2 py-1 w-20 bg-gray-100"
                />
                <span className="text-sm">%</span>
              </div>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Cálculo: Preço Venda - Desconto - Taxas - Impostos - Custo = Lucro
          </p>
        </div>
      )}

      <div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={itemSelecionado.permite_edicao_venda}
            onChange={(event) =>
              setItemSelecionado({
                ...itemSelecionado,
                permite_edicao_venda: event.target.checked,
              })
            }
            className="rounded"
          />
          <span className="text-sm">Permite editar percentual na venda</span>
        </label>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Observações</label>
        <textarea
          value={itemSelecionado.observacoes}
          onChange={(event) =>
            setItemSelecionado({ ...itemSelecionado, observacoes: event.target.value })
          }
          className="border rounded px-3 py-2 w-full"
          rows="3"
        />
      </div>

      <button
        onClick={adicionarConfiguracao}
        className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded mb-2"
      >
        ➕ Adicionar à Lista
      </button>

      <button
        onClick={salvarItem}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded"
      >
        💾 Salvar Agora
      </button>
    </div>
  );
}
