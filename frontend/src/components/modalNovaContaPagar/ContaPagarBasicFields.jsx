import { Calendar, DollarSign, Plus, Tag, User } from "lucide-react";
import { safeArray } from "../../utils/safeArray";
import FornecedorSelector from "../fornecedores/FornecedorSelector";

export default function ContaPagarBasicFields({ controller, onOpenCategoria }) {
  const {
    categorias,
    dados,
    fornecedorSelecionado,
    fornecedores,
    setDados,
    setFornecedores,
    subcategoriasDRE,
    tiposDespesa,
  } = controller;
  const categoriaSelecionada = dados.categoria_id
    ? categorias.find((categoria) => categoria.id === dados.categoria_id)
    : null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="md:col-span-2">
        <label className="block text-sm font-medium text-gray-700 mb-1">Descrição *</label>
        <input
          type="text"
          value={dados.descricao}
          onChange={(event) => setDados({ ...dados, descricao: event.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          placeholder="Ex: Aluguel, Conta de luz, Fornecedor XYZ..."
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          <User size={16} className="inline mr-1" />
          Fornecedor
        </label>
        <FornecedorSelector
          fornecedores={safeArray(fornecedores)}
          fornecedorId={dados.fornecedor_id}
          fornecedorSelecionado={fornecedorSelecionado}
          showLabel={false}
          placeholder="Digite o fornecedor..."
          inputClassName="rounded-md border-gray-300"
          onInputChange={(termo) => {
            if (!termo || dados.fornecedor_id) {
              setDados({ ...dados, fornecedor_id: null });
            }
          }}
          onSelect={(fornecedor) =>
            setDados({
              ...dados,
              fornecedor_id: fornecedor?.id ? parseInt(fornecedor.id, 10) : null,
            })
          }
          onClear={() => setDados({ ...dados, fornecedor_id: null })}
          onFornecedorCriado={(fornecedor) => {
            setFornecedores((prev) => [...safeArray(prev), fornecedor]);
            setDados({
              ...dados,
              fornecedor_id: fornecedor?.id ? parseInt(fornecedor.id, 10) : null,
            });
          }}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          <Tag size={16} className="inline mr-1" />
          Categoria
        </label>
        <div className="flex gap-2">
          <select
            value={dados.categoria_id || ""}
            onChange={(event) =>
              setDados({
                ...dados,
                categoria_id: event.target.value ? parseInt(event.target.value) : null,
              })
            }
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Selecione...</option>
            {safeArray(categorias).map((categoria) => (
              <option key={categoria.id} value={categoria.id}>
                {categoria.nome}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={onOpenCategoria}
            className="px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center gap-1 whitespace-nowrap"
            title="Adicionar nova categoria"
          >
            <Plus size={16} /> Adicionar
          </button>
        </div>
        {categoriaSelecionada?.tipo_custo && (
          <p
            className={`text-xs font-semibold mt-1 ${
              categoriaSelecionada.tipo_custo === "fixo"
                ? "text-orange-600"
                : categoriaSelecionada.tipo_custo === "variavel"
                  ? "text-blue-600"
                  : "text-purple-600"
            }`}
          >
            {categoriaSelecionada.tipo_custo === "fixo"
              ? "🔒 Despesa Fixa"
              : categoriaSelecionada.tipo_custo === "variavel"
                ? "📈 Despesa Variável"
                : "↕ Custo Misto (Fixo + Variável)"}
          </p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          🏷️ Subcategoria DRE (Demonstrativo de Resultado)
        </label>
        <select
          value={dados.dre_subcategoria_id || ""}
          onChange={(event) =>
            setDados({
              ...dados,
              dre_subcategoria_id: event.target.value ? parseInt(event.target.value) : null,
            })
          }
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Sem classificação DRE</option>
          {safeArray(subcategoriasDRE).map((subcategoria) => (
            <option key={subcategoria.id} value={subcategoria.id}>
              {subcategoria.nome}
            </option>
          ))}
        </select>
        <p className="text-xs text-gray-500 mt-1">Classifique para melhor análise gerencial</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de despesa</label>
        <select
          value={dados.tipo_despesa_id || ""}
          onChange={(event) =>
            setDados({
              ...dados,
              tipo_despesa_id: event.target.value ? parseInt(event.target.value) : null,
            })
          }
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Selecione...</option>
          {safeArray(tiposDespesa).map((tipo) => (
            <option key={tipo.id} value={tipo.id}>
              {tipo.nome}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Canal</label>
        <select
          value={dados.canal || "loja_fisica"}
          onChange={(event) => setDados({ ...dados, canal: event.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
        >
          <option value="loja_fisica">Loja Fisica</option>
          <option value="mercado_livre">Mercado Livre</option>
          <option value="shopee">Shopee</option>
          <option value="amazon">Amazon</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          <DollarSign size={16} className="inline mr-1" />
          Valor *
        </label>
        <input
          type="number"
          step="0.01"
          value={dados.valor_original}
          onChange={(event) => setDados({ ...dados, valor_original: event.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          placeholder="0.00"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          <Calendar size={16} className="inline mr-1" />
          Data Vencimento *
        </label>
        <input
          type="date"
          value={dados.data_vencimento}
          onChange={(event) => setDados({ ...dados, data_vencimento: event.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Documento/NF</label>
        <input
          type="text"
          value={dados.documento}
          onChange={(event) => setDados({ ...dados, documento: event.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          placeholder="Número do documento"
        />
      </div>
    </div>
  );
}
