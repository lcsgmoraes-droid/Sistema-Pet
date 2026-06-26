import { COMMISSION_HIERARCHY_LABEL } from "./comissoesConstants";

export default function ComissaoRulesPanel({ regras, setRegra }) {
  return (
    <div className="mb-6 p-4 bg-gray-50 rounded-lg">
      <h3 className="font-semibold mb-3">Regras de Cálculo</h3>

      <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded text-sm">
        <div className="font-semibold text-blue-800 mb-1">📋 Hierarquia de Configurações</div>
        <div className="text-blue-700 text-xs">
          <strong aria-label={COMMISSION_HIERARCHY_LABEL}>
            Produto {">"} Subcategoria {">"} Categoria {">"} Regra geral
          </strong>
          <br />
          <span className="text-blue-600">
            Ao vender um produto, o sistema busca a configuração mais específica. A regra geral
            cobre tudo quando nao houver uma regra especifica.
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={regras.desconta_taxa_cartao}
            onChange={(event) => setRegra("desconta_taxa_cartao", event.target.checked)}
            className="rounded"
          />
          <span className="text-sm">Desconta taxa de cartão</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={regras.desconta_impostos}
            onChange={(event) => setRegra("desconta_impostos", event.target.checked)}
            className="rounded"
          />
          <span className="text-sm">Desconta impostos</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={regras.desconta_taxa_entrega}
            onChange={(event) => setRegra("desconta_taxa_entrega", event.target.checked)}
            className="rounded"
          />
          <span className="text-sm">Desconta taxa de entrega</span>
        </label>
        <div className="border-t pt-2 mt-3">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={regras.comissao_venda_parcial}
              onChange={(event) => setRegra("comissao_venda_parcial", event.target.checked)}
              className="rounded"
            />
            <div className="flex flex-col">
              <span className="text-sm font-medium">Gerar comissão em vendas parciais</span>
              <span className="text-xs text-gray-500">
                {regras.comissao_venda_parcial
                  ? "Comissão gerada proporcionalmente a cada pagamento recebido"
                  : "Comissão gerada somente quando a venda estiver 100% paga"}
              </span>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
}
