import PropTypes from "prop-types";
import { formatMoneyBRL } from "../../utils/formatters";

function formatarQuantidade(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

export default function ProdutosCompostosPrecoVendaModal({
  aberto,
  nomeProduto,
  onClose,
  onConfirmar,
  onToggleProduto,
  onToggleTodos,
  precoVendaAtual,
  precoVendaNovo,
  salvando,
  selecionados,
  sugestoes,
}) {
  if (!aberto) return null;

  const todosSelecionados =
    sugestoes.length > 0 && sugestoes.every((item) => selecionados.includes(item.produto_id));

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl">
        <div className="border-b border-gray-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                Atualizar preços dos produtos compostos?
              </h2>
              <p className="mt-1 text-sm text-gray-600">
                O preço de venda de <strong>{nomeProduto}</strong> mudou de{" "}
                <strong>{formatMoneyBRL(precoVendaAtual)}</strong> para{" "}
                <strong>{formatMoneyBRL(precoVendaNovo)}</strong>.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              disabled={salvando}
              className="text-2xl leading-none text-gray-400 hover:text-gray-600 disabled:opacity-50"
              aria-label="Fechar"
            >
              &times;
            </button>
          </div>

          <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
            O custo dos produtos compostos é recalculado automaticamente. A seleção abaixo autoriza
            somente a mudança do preço de venda.
          </div>
        </div>

        <div className="overflow-y-auto px-6 py-4">
          <label className="mb-3 flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 font-semibold text-gray-800">
            <input
              type="checkbox"
              checked={todosSelecionados}
              onChange={(event) => onToggleTodos(event.target.checked)}
              disabled={salvando}
              className="h-5 w-5 rounded text-blue-600 focus:ring-blue-500"
            />
            Selecionar todos ({selecionados.length}/{sugestoes.length})
          </label>

          <div className="space-y-3">
            {sugestoes.map((item) => {
              const selecionado = selecionados.includes(item.produto_id);
              return (
                <label
                  key={item.produto_id}
                  className={`block cursor-pointer rounded-lg border p-4 transition-colors ${
                    selecionado
                      ? "border-blue-300 bg-blue-50/50"
                      : "border-gray-200 bg-white hover:bg-gray-50"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selecionado}
                      onChange={(event) => onToggleProduto(item.produto_id, event.target.checked)}
                      disabled={salvando}
                      className="mt-1 h-5 w-5 shrink-0 rounded text-blue-600 focus:ring-blue-500"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-gray-900">{item.nome}</span>
                        <span className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-700">
                          {item.sku}
                        </span>
                        {!item.ativo && (
                          <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                            Inativo
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-gray-500">
                        Usa {formatarQuantidade(item.quantidade_componente)} unidade(s) de{" "}
                        {nomeProduto}.
                      </p>
                      <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                        <div className="rounded-md bg-gray-100 px-3 py-2 text-gray-700">
                          Venda atual: <strong>{formatMoneyBRL(item.preco_venda_atual)}</strong>
                        </div>
                        <div className="rounded-md bg-emerald-100 px-3 py-2 text-emerald-900">
                          Venda sugerida:{" "}
                          <strong>{formatMoneyBRL(item.preco_venda_sugerido)}</strong>
                        </div>
                      </div>
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col-reverse gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={salvando}
            className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50"
          >
            Voltar ao cadastro
          </button>
          <button
            type="button"
            onClick={onConfirmar}
            disabled={salvando}
            className="rounded-lg bg-blue-600 px-5 py-2.5 font-semibold text-white hover:bg-blue-700 disabled:bg-gray-400"
          >
            {salvando ? "Salvando..." : `Salvar e atualizar ${selecionados.length} preço(s)`}
          </button>
        </div>
      </div>
    </div>
  );
}

ProdutosCompostosPrecoVendaModal.propTypes = {
  aberto: PropTypes.bool,
  nomeProduto: PropTypes.string.isRequired,
  onClose: PropTypes.func.isRequired,
  onConfirmar: PropTypes.func.isRequired,
  onToggleProduto: PropTypes.func.isRequired,
  onToggleTodos: PropTypes.func.isRequired,
  precoVendaAtual: PropTypes.number,
  precoVendaNovo: PropTypes.number,
  salvando: PropTypes.bool,
  selecionados: PropTypes.arrayOf(PropTypes.number).isRequired,
  sugestoes: PropTypes.arrayOf(
    PropTypes.shape({
      ativo: PropTypes.bool,
      nome: PropTypes.string.isRequired,
      preco_venda_atual: PropTypes.number.isRequired,
      preco_venda_sugerido: PropTypes.number.isRequired,
      produto_id: PropTypes.number.isRequired,
      quantidade_componente: PropTypes.number.isRequired,
      sku: PropTypes.string.isRequired,
    }),
  ).isRequired,
};

ProdutosCompostosPrecoVendaModal.defaultProps = {
  aberto: false,
  precoVendaAtual: 0,
  precoVendaNovo: 0,
  salvando: false,
};
