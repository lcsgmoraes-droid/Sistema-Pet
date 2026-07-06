import ActionButton from "../ui/ActionButton";
import FilterBar from "../ui/FilterBar";
import FornecedorSelector from "../fornecedores/FornecedorSelector";
import { PERIODOS_RAPIDOS_CONTAS_PAGAR, getFornecedorNome } from "./contasPagarHelpers";

export default function ContasPagarFilters({
  filtros,
  setFiltros,
  fornecedores,
  fornecedorFiltroSelecionado,
  tiposDespesaOrdenados,
  aplicarPeriodoRapido,
  filtrarDespesasCaixa,
  filtrarTaxasCartao,
  alternarOcultarTaxasCartao,
  limparFiltros,
  aplicarFiltros,
  handleFiltrosSubmit,
}) {
  return (
    <>
      {/* Filtros */}
      <FilterBar className="mb-6" onSubmit={handleFiltrosSubmit}>
        <h5 className="text-lg font-semibold mb-4">🔍 Filtros</h5>
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div className="md:col-span-3">
            <label className="block text-sm font-medium mb-1">Buscar</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded px-3 py-2"
              placeholder="Descrição, documento, NF, fornecedor..."
              value={filtros.busca}
              onChange={(e) => setFiltros({ ...filtros, busca: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && aplicarFiltros()}
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.status}
              onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}
            >
              <option value="todos">Todos</option>
              <option value="pendente">Pendente</option>
              <option value="parcial">Parcial</option>
              <option value="pago">Pago</option>
              <option value="vencido">Vencido</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Origem</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.origem}
              onChange={(e) => setFiltros({ ...filtros, origem: e.target.value })}
            >
              <option value="todos">Todas</option>
              <option value="caixa_pdv">Caixa/PDV</option>
              <option value="nota_entrada">Nota de entrada</option>
              <option value="manual">Manual/financeiro</option>
            </select>
          </div>

          <div className="md:col-span-3">
            <label className="block text-sm font-medium mb-1">Fornecedor</label>
            <FornecedorSelector
              fornecedores={fornecedores}
              fornecedorId={filtros.fornecedor_id}
              fornecedorSelecionado={fornecedorFiltroSelecionado}
              showLabel={false}
              value={filtros.fornecedor_busca || ""}
              placeholder="Digite nome, fantasia, CPF ou CNPJ..."
              onInputChange={(termo) =>
                setFiltros({
                  ...filtros,
                  fornecedor_busca: termo,
                  fornecedor_id: null,
                })
              }
              onSelect={(fornecedor) =>
                setFiltros({
                  ...filtros,
                  fornecedor_id: fornecedor?.id || null,
                  fornecedor_busca: getFornecedorNome(fornecedor),
                })
              }
              onClear={() =>
                setFiltros({
                  ...filtros,
                  fornecedor_id: null,
                  fornecedor_busca: "",
                })
              }
              onFornecedorCriado={(fornecedor) =>
                setFiltros({
                  ...filtros,
                  fornecedor_id: fornecedor?.id || null,
                  fornecedor_busca: getFornecedorNome(fornecedor),
                })
              }
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Tipo despesa</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.tipo_despesa_id || ""}
              onChange={(e) => setFiltros({ ...filtros, tipo_despesa_id: e.target.value })}
            >
              <option value="">Todos</option>
              {tiposDespesaOrdenados.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nome}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">NF/documento</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded px-3 py-2"
              placeholder="Ex: 12345"
              value={filtros.numero_nf}
              onChange={(e) => setFiltros({ ...filtros, numero_nf: e.target.value })}
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Tipo de custo</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.tipo_custo}
              onChange={(e) => setFiltros({ ...filtros, tipo_custo: e.target.value })}
            >
              <option value="todos">Todos</option>
              <option value="fixo">So fixos</option>
              <option value="variavel">Só variáveis</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Data usada</label>
            <select
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_campo}
              onChange={(e) => setFiltros({ ...filtros, data_campo: e.target.value })}
            >
              <option value="vencimento">Vencimento</option>
              <option value="pagamento">Pagamento</option>
              <option value="emissao">Emissão</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Data início</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_inicio}
              onChange={(e) =>
                setFiltros({ ...filtros, data_inicio: e.target.value, periodo_rapido: "" })
              }
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Data fim</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={filtros.data_fim}
              onChange={(e) =>
                setFiltros({ ...filtros, data_fim: e.target.value, periodo_rapido: "" })
              }
            />
          </div>

          <div className="md:col-span-4">
            <label className="block text-sm font-medium mb-1">Periodo rapido</label>
            <div className="flex flex-wrap gap-2">
              {PERIODOS_RAPIDOS_CONTAS_PAGAR.map((periodo) => {
                const ativo = filtros.periodo_rapido === periodo.value;

                return (
                  <button
                    key={periodo.value}
                    type="button"
                    onClick={() => aplicarPeriodoRapido(periodo.value)}
                    className={`rounded-md border px-3 py-2 text-sm font-semibold transition ${
                      ativo
                        ? "border-blue-600 bg-blue-600 text-white shadow-sm"
                        : "border-gray-300 bg-white text-gray-700 hover:border-blue-400 hover:text-blue-700"
                    }`}
                  >
                    {periodo.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="md:col-span-3 flex items-end gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.ocultar_taxas_cartao}
                onChange={(e) => alternarOcultarTaxasCartao(e.target.checked)}
              />
              <span className="text-sm">Ocultar taxas</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencidas}
                onChange={(e) =>
                  setFiltros({
                    ...filtros,
                    apenas_vencidas: e.target.checked,
                    apenas_vencer: false,
                  })
                }
              />
              <span className="text-sm">Só vencidas</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4"
                checked={filtros.apenas_vencer}
                onChange={(e) =>
                  setFiltros({
                    ...filtros,
                    apenas_vencer: e.target.checked,
                    apenas_vencidas: false,
                  })
                }
              />
              <span className="text-sm">A vencer</span>
            </label>
          </div>

          <div className="md:col-span-5 flex flex-wrap items-end justify-end gap-2">
            <ActionButton
              intent="warning"
              tone="soft"
              size="sm"
              onClick={filtrarTaxasCartao}
              type="button"
            >
              Taxas de cartao
            </ActionButton>
            <ActionButton
              intent="warning"
              tone="soft"
              size="sm"
              onClick={filtrarDespesasCaixa}
              type="button"
            >
              Despesas do caixa
            </ActionButton>
            <ActionButton
              intent="neutral"
              tone="soft"
              size="sm"
              onClick={limparFiltros}
              type="button"
            >
              Limpar
            </ActionButton>
            <ActionButton
              intent="neutral"
              tone="solid"
              size="sm"
              onClick={() => aplicarFiltros()}
              type="button"
            >
              Filtrar
            </ActionButton>
          </div>
        </div>
      </FilterBar>
    </>
  );
}
