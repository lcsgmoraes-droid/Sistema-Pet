import { formatarMoeda } from "../../api/produtos";
import { formatPercent } from "../../utils/formatters";
import { obterResumoPrecoPorKg } from "../../utils/racaoPrecoKg";
import MoneyCell from "../ui/MoneyCell";

function calcularMargem(preco, custo) {
  if (!preco || preco <= 0) return 0;
  return ((preco - custo) / preco) * 100;
}

function calcularPrecoParaMargem(custo, margem) {
  if (margem >= 100 || margem < 0) return custo;
  return custo / (1 - margem / 100);
}

export function createProdutosPricingColumns() {
  return [
    {
      key: "custo",
      label: "Custo",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
          Custo
        </th>
      ),
      renderCell: (produto) => (
        <td className="px-4 py-3 text-right">
          <MoneyCell className="text-sm text-gray-900" value={produto.preco_custo} />
        </td>
      ),
    },
    {
      key: "margem",
      label: "Margem",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
          Margem
        </th>
      ),
      renderCell: (produto, props) => {
        const custo = Number(produto.preco_custo || 0);
        const preco = Number(produto.preco_venda || 0);
        const margem = calcularMargem(preco, custo);
        const editandoMargem = props.editandoMargem;
        const setEditandoMargem = props.setEditandoMargem;
        const editandoPreco = props.editandoPreco;

        if (!custo || editandoPreco === produto.id) {
          return (
            <td className="px-4 py-3 text-right">
              <span className="text-sm text-gray-400">-</span>
            </td>
          );
        }

        const corMargem =
          margem >= 30 ? "text-emerald-600" : margem >= 15 ? "text-yellow-600" : "text-red-600";

        if (editandoMargem?.produtoId === produto.id) {
          const modo = editandoMargem.modo;
          return (
            <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
              <div className="flex flex-col gap-1 items-end">
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    step={modo === "margem" ? "0.1" : "0.01"}
                    value={editandoMargem.valor}
                    onChange={(e) =>
                      setEditandoMargem({ ...editandoMargem, valor: e.target.value })
                    }
                    className="w-20 px-2 py-1 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 text-right"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter") props.handleSalvarMargem(produto.id, custo);
                      if (e.key === "Escape") setEditandoMargem(null);
                    }}
                  />
                  <span className="text-xs text-gray-500">{modo === "margem" ? "%" : "R$"}</span>
                  <button
                    onClick={() => props.handleSalvarMargem(produto.id, custo)}
                    className="text-green-600 hover:text-green-800"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </button>
                  <button
                    onClick={() => setEditandoMargem(null)}
                    className="text-red-600 hover:text-red-800"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() =>
                      setEditandoMargem({
                        produtoId: produto.id,
                        modo: "margem",
                        valor: margem.toFixed(1),
                      })
                    }
                    className={`text-xs px-1 py-0.5 rounded ${modo === "margem" ? "bg-blue-100 text-blue-700" : "text-gray-400 hover:text-gray-600"}`}
                  >
                    % margem
                  </button>
                  <button
                    onClick={() =>
                      setEditandoMargem({
                        produtoId: produto.id,
                        modo: "preco",
                        valor: preco.toFixed(2),
                      })
                    }
                    className={`text-xs px-1 py-0.5 rounded ${modo === "preco" ? "bg-blue-100 text-blue-700" : "text-gray-400 hover:text-gray-600"}`}
                  >
                    R$ preco
                  </button>
                </div>
                <span className="text-xs text-gray-400">
                  {modo === "margem"
                    ? `PV: ${formatarMoeda(calcularPrecoParaMargem(custo, Number(editandoMargem.valor || 0)))}`
                    : `Margem: ${calcularMargem(Number(editandoMargem.valor || 0), custo).toFixed(1)}%`}
                </span>
              </div>
            </td>
          );
        }

        return (
          <td className="px-4 py-3 text-right">
            <div className="flex items-center gap-1 justify-end">
              <span className={`text-sm font-semibold ${corMargem}`}>{formatPercent(margem)}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setEditandoMargem({
                    produtoId: produto.id,
                    modo: "margem",
                    valor: margem.toFixed(1),
                  });
                }}
                className="text-blue-600 hover:text-blue-800"
                title="Ajustar margem ou preco"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
              </button>
            </div>
          </td>
        );
      },
    },
    {
      key: "preco_venda",
      label: "PV",
      visible: true,
      renderHeader: () => (
        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
          PV
        </th>
      ),
      renderCell: (produto, props) => (
        <td className="px-4 py-3 text-right">
          {props.editandoPreco === produto.id ? (
            <div
              className="flex items-center gap-1 justify-end"
              onClick={(e) => e.stopPropagation()}
            >
              <input
                type="number"
                step="0.01"
                value={props.novoPreco}
                onChange={(e) => props.setNovoPreco(e.target.value)}
                className="w-24 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
              <button
                onClick={() => props.handleSalvarPreco(produto.id)}
                className="text-green-600 hover:text-green-800"
                title="Salvar"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </button>
              <button
                onClick={props.handleCancelarEdicaoPreco}
                className="text-red-600 hover:text-red-800"
                title="Cancelar"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-end gap-0.5">
              <div className="flex items-center gap-2 justify-end">
                <MoneyCell
                  className="text-sm font-semibold text-green-600"
                  value={produto.preco_venda}
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    props.handleEditarPreco(produto.id, produto.preco_venda);
                  }}
                  className="text-blue-600 hover:text-blue-800"
                  title="Editar preco"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                </button>
              </div>
              {obterResumoPrecoPorKg(produto).disponivel && (
                <span
                  className="text-xs font-semibold text-teal-700"
                  title={`${obterResumoPrecoPorKg(produto).pesoFormatado} - ${obterResumoPrecoPorKg(produto).precoFormatado}`}
                >
                  {obterResumoPrecoPorKg(produto).precoPorKgFormatado}
                </span>
              )}
            </div>
          )}
        </td>
      ),
    },
  ];
}
