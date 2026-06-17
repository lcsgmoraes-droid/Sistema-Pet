import PropTypes from "prop-types";
import { formatMoneyBRL } from "../../utils/formatters";

function formatarValorFiscal(valor, casas = 4) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function EntradaXmlRascunhoDevolucaoModal({ aberto, rascunhoDevolucao, onClose }) {
  if (!aberto || !rascunhoDevolucao) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Rascunho de NF de Devolucao</h2>
            <p className="text-sm text-gray-500">
              NF origem {rascunhoDevolucao.numero_nota_origem} - {rascunhoDevolucao.fornecedor_nome}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-2xl">
            X
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
              <div className="text-xs uppercase tracking-wide text-orange-700">Itens devolucao</div>
              <div className="text-2xl font-bold text-orange-900">
                {rascunhoDevolucao.quantidade_itens || 0}
              </div>
            </div>
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
              <div className="text-xs uppercase tracking-wide text-emerald-700">Valor estimado</div>
              <div className="text-2xl font-bold text-emerald-900">
                {formatMoneyBRL(rascunhoDevolucao.valor_total_estimado || 0)}
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs uppercase tracking-wide text-slate-600">Status</div>
              <div className="text-sm font-semibold text-slate-800">
                {rascunhoDevolucao.disponivel
                  ? "Rascunho pronto para gerar NF"
                  : "Sem itens avariados para devolucao"}
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="text-sm font-semibold text-gray-700 mb-1">Observacao sugerida</div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">
              {rascunhoDevolucao.observacao_sugerida}
            </p>
          </div>

          {rascunhoDevolucao.itens?.length > 0 ? (
            <div className="overflow-x-auto border border-gray-200 rounded-xl">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left">Item</th>
                    <th className="px-4 py-3 text-right">Qtd devolucao</th>
                    <th className="px-4 py-3 text-right">Valor unit.</th>
                    <th className="px-4 py-3 text-right">Valor total</th>
                  </tr>
                </thead>
                <tbody>
                  {rascunhoDevolucao.itens.map((item) => (
                    <tr key={item.item_id} className="border-t">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-900">{item.descricao}</div>
                        <div className="text-xs text-gray-500">
                          {item.codigo_produto || "Sem codigo"} - Item NF {item.numero_item_nf}
                        </div>
                        {item.observacao_conferencia && (
                          <div className="text-xs text-orange-700 mt-1">
                            {item.observacao_conferencia}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold">
                        {formatarValorFiscal(item.quantidade_devolucao, 2)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatMoneyBRL(item.valor_unitario || 0)}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-emerald-700">
                        {formatMoneyBRL(item.valor_total || 0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white p-6 text-center text-gray-500">
              Nenhum item avariado foi marcado nesta conferencia.
            </div>
          )}
        </div>

        <div className="border-t px-6 py-4 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg font-semibold hover:bg-gray-100"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

EntradaXmlRascunhoDevolucaoModal.propTypes = {
  aberto: PropTypes.bool.isRequired,
  rascunhoDevolucao: PropTypes.shape({
    numero_nota_origem: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    fornecedor_nome: PropTypes.string,
    quantidade_itens: PropTypes.number,
    valor_total_estimado: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    disponivel: PropTypes.bool,
    observacao_sugerida: PropTypes.string,
    itens: PropTypes.arrayOf(PropTypes.object),
  }),
  onClose: PropTypes.func.isRequired,
};

EntradaXmlRascunhoDevolucaoModal.defaultProps = {
  rascunhoDevolucao: null,
};

export default EntradaXmlRascunhoDevolucaoModal;
