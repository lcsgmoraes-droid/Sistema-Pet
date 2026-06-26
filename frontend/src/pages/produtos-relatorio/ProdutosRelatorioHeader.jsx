export default function ProdutosRelatorioHeader({ onVoltar }) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Giro de Produto e Movimentacoes</h1>
        <p className="mt-2 max-w-4xl text-sm text-gray-600">
          Use esta tela para decidir compra com base no giro real do item. Ao escolher um produto, o
          painel mostra vendas em 7, 15, 30, 60 e 90 dias, historico recente e as movimentacoes de
          estoque com paginacao leve.
        </p>
      </div>

      <button
        type="button"
        onClick={onVoltar}
        className="inline-flex items-center justify-center rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
      >
        Voltar para produtos
      </button>
    </div>
  );
}
