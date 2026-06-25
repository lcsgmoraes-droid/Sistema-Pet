import { TabContent } from "../../../components/ResponsiveTabs";
import {
  formatarPorcentagemProduto as formatarPorcentagem,
  formatarValorMonetarioProduto as formatarValorMonetario,
  organizarCategoriasHierarquicas,
} from "../../produtosFormUtils";

export default function ProdutosFormDadosTab({
  categorias,
  departamentos,
  handleChange,
  handleGerarCodigo,
  handleSubmit,
  isEdit,
  marcas,
  onCancel,
  produto,
  salvando,
  setProduto,
}) {
  return (
    <TabContent>
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
        {/* Código e Nome */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Código / SKU</label>
            <div className="flex gap-2">
              <input
                type="text"
                name="codigo"
                value={produto.codigo}
                onChange={handleChange}
                className="flex-1 px-3 py-2 border-4 border-red-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="SKU-001"
                style={{ borderColor: "red", borderWidth: "3px" }}
              />
              <button
                type="button"
                onClick={handleGerarCodigo}
                className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition"
                title="Gerar código automaticamente"
              >
                🔄
              </button>
            </div>
          </div>

          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nome do Produto *
            </label>
            <input
              type="text"
              name="nome"
              value={produto.nome}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Ex: Ração Premium para Cães Adultos 15kg"
            />
          </div>
        </div>

        {/* Descrição */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Descrição</label>
          <textarea
            name="descricao"
            value={produto.descricao}
            onChange={handleChange}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Descrição detalhada do produto..."
          />
        </div>

        {/* Categoria, Marca, Departamento e Tipo */}
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Categoria</label>
            <select
              name="categoria_id"
              value={produto.categoria_id}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Selecione...</option>
              {organizarCategoriasHierarquicas(categorias).map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {"\u00a0\u00a0\u00a0\u00a0".repeat(cat.nivel)}
                  {cat.nivel > 0 ? "\u2192 " : ""}
                  {cat.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Marca</label>
            <select
              name="marca_id"
              value={produto.marca_id}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Selecione...</option>
              {marcas.map((marca) => (
                <option key={marca.id} value={marca.id}>
                  {marca.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Departamento</label>
            <select
              name="departamento_id"
              value={produto.departamento_id}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Selecione...</option>
              {departamentos.map((depto) => (
                <option key={depto.id} value={depto.id}>
                  {depto.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Tipo</label>
            <select
              name="tipo"
              value={produto.tipo}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="produto">Produto</option>
              <option value="servico">Serviço</option>
              <option value="produto_servico">Produto e Serviço</option>
            </select>
          </div>
        </div>

        {/* Preços e Margem */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Preço de Custo</label>
            <input
              type="text"
              name="preco_custo"
              value={formatarValorMonetario(produto.preco_custo)}
              onChange={(e) => {
                const value = e.target.value.replace(/[^\d.,]/g, "").replace(",", ".");
                setProduto({ ...produto, preco_custo: value || "" });
              }}
              onFocus={(e) => {
                if (produto.preco_custo) {
                  const numero = parseFloat(produto.preco_custo);
                  e.target.value = isNaN(numero) ? "" : numero.toFixed(2).replace(".", ",");
                  e.target.select();
                }
              }}
              onBlur={(e) => {
                const value = e.target.value.replace(",", ".");
                setProduto({ ...produto, preco_custo: value || "" });
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="R$ 0,00"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Preço de Venda *</label>
            <input
              type="text"
              name="preco_venda"
              value={formatarValorMonetario(produto.preco_venda)}
              onChange={(e) => {
                const value = e.target.value.replace(/[^\d.,]/g, "").replace(",", ".");
                setProduto({ ...produto, preco_venda: value || "" });
              }}
              onFocus={(e) => {
                if (produto.preco_venda) {
                  const numero = parseFloat(produto.preco_venda);
                  e.target.value = isNaN(numero) ? "" : numero.toFixed(2).replace(".", ",");
                  e.target.select();
                }
              }}
              onBlur={(e) => {
                const value = e.target.value.replace(",", ".");
                setProduto({ ...produto, preco_venda: value || "" });
              }}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="R$ 0,00"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Margem de Lucro</label>
            <input
              type="text"
              name="margem_lucro"
              value={formatarPorcentagem(produto.margem_lucro)}
              readOnly
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
              placeholder="0,00%"
            />
          </div>
        </div>

        {/* 💰 Preços por Canal */}
        <div className="border border-gray-100 rounded-lg p-4 bg-gray-50 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-700">
              💰 Preços por Canal (Ecommerce / App Móvel)
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Se vazio, o sistema usa o <strong>Preço de Venda padrão</strong>. Preencha apenas se
              quiser um preço diferente por canal.
            </p>
          </div>

          {/* Ecommerce */}
          <div>
            <div className="flex items-center justify-between gap-3 mb-2">
              <div className="text-xs font-bold text-purple-700 uppercase">🛒 Ecommerce</div>
              <label className="flex items-center gap-2 text-xs text-gray-700">
                <input
                  type="checkbox"
                  checked={produto.status !== "inativo" && produto.anunciar_ecommerce !== false}
                  onChange={(e) =>
                    setProduto((prev) => ({ ...prev, anunciar_ecommerce: e.target.checked }))
                  }
                  disabled={produto.status === "inativo"}
                />
                Exibir no canal
              </label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Preço normal</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="R$ 0,00"
                  value={produto.preco_ecommerce || ""}
                  onChange={(e) =>
                    setProduto((prev) => ({ ...prev, preco_ecommerce: e.target.value || null }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Preço promocional</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="R$ 0,00"
                  value={produto.preco_ecommerce_promo || ""}
                  onChange={(e) =>
                    setProduto((prev) => ({
                      ...prev,
                      preco_ecommerce_promo: e.target.value || null,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Promoção início</label>
                <input
                  type="datetime-local"
                  value={
                    produto.preco_ecommerce_promo_inicio
                      ? produto.preco_ecommerce_promo_inicio.toString().slice(0, 16)
                      : ""
                  }
                  onChange={(e) =>
                    setProduto((prev) => ({
                      ...prev,
                      preco_ecommerce_promo_inicio: e.target.value || null,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Promoção fim</label>
                <input
                  type="datetime-local"
                  value={
                    produto.preco_ecommerce_promo_fim
                      ? produto.preco_ecommerce_promo_fim.toString().slice(0, 16)
                      : ""
                  }
                  onChange={(e) =>
                    setProduto((prev) => ({
                      ...prev,
                      preco_ecommerce_promo_fim: e.target.value || null,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-sm"
                />
              </div>
            </div>
          </div>

          {/* App Móvel (Aplicativo) */}
          <div>
            <div className="flex items-center justify-between gap-3 mb-2">
              <div className="text-xs font-bold text-green-700 uppercase">
                📱 App Móvel (Aplicativo)
              </div>
              <label className="flex items-center gap-2 text-xs text-gray-700">
                <input
                  type="checkbox"
                  checked={produto.status !== "inativo" && produto.anunciar_app !== false}
                  onChange={(e) =>
                    setProduto((prev) => ({ ...prev, anunciar_app: e.target.checked }))
                  }
                  disabled={produto.status === "inativo"}
                />
                Exibir no canal
              </label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Preço normal</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="R$ 0,00"
                  value={produto.preco_app || ""}
                  onChange={(e) =>
                    setProduto((prev) => ({ ...prev, preco_app: e.target.value || null }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Preço promocional</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="R$ 0,00"
                  value={produto.preco_app_promo || ""}
                  onChange={(e) =>
                    setProduto((prev) => ({ ...prev, preco_app_promo: e.target.value || null }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Promoção início</label>
                <input
                  type="datetime-local"
                  value={
                    produto.preco_app_promo_inicio
                      ? produto.preco_app_promo_inicio.toString().slice(0, 16)
                      : ""
                  }
                  onChange={(e) =>
                    setProduto((prev) => ({
                      ...prev,
                      preco_app_promo_inicio: e.target.value || null,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Promoção fim</label>
                <input
                  type="datetime-local"
                  value={
                    produto.preco_app_promo_fim
                      ? produto.preco_app_promo_fim.toString().slice(0, 16)
                      : ""
                  }
                  onChange={(e) =>
                    setProduto((prev) => ({
                      ...prev,
                      preco_app_promo_fim: e.target.value || null,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 text-sm"
                />
              </div>
            </div>
          </div>

          {produto.status === "inativo" && (
            <p className="text-xs text-amber-700">
              Produto inativo na loja fisica: anuncio em Ecommerce e App Movel fica desativado
              automaticamente.
            </p>
          )}
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Estoque Mínimo</label>
            <input
              type="number"
              name="estoque_minimo"
              value={produto.estoque_minimo}
              onChange={handleChange}
              step="0.01"
              min="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="0"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Estoque Máximo</label>
            <input
              type="number"
              name="estoque_maximo"
              value={produto.estoque_maximo}
              onChange={handleChange}
              step="0.01"
              min="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="0"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Localização</label>
            <input
              type="text"
              name="localizacao"
              value={produto.localizacao}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Ex: Prateleira A1"
            />
          </div>
        </div>

        {/* Controle de Lote e Status */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg">
            <input
              type="checkbox"
              name="controle_lote"
              checked={produto.controle_lote}
              onChange={handleChange}
              className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
            />
            <div>
              <label className="text-sm font-medium text-gray-700 cursor-pointer">
                Controlar por Lotes
              </label>
              <p className="text-xs text-gray-500">Ativa o sistema FIFO de estoque por lotes</p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <select
              name="status"
              value={produto.status}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="ativo">Ativo</option>
              <option value="inativo">Inativo</option>
            </select>
          </div>
        </div>

        {/* Observações */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Observações</label>
          <textarea
            name="observacoes"
            value={produto.observacoes}
            onChange={handleChange}
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Observações internas..."
          />
        </div>

        {/* Botões */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <button
            type="button"
            onClick={onCancel}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
          >
            Cancelar
          </button>

          <button
            type="submit"
            disabled={salvando}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400"
          >
            {salvando ? "Salvando..." : isEdit ? "Atualizar" : "Cadastrar"}
          </button>
        </div>
      </form>
    </TabContent>
  );
}
