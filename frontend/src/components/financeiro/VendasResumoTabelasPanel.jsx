import FormasRecebimentoTable from "./FormasRecebimentoTable";
import VendasPorDataTable from "./VendasPorDataTable";
import VendasPorFuncionarioTable from "./VendasPorFuncionarioTable";
import VendasResumoAgregadoTable from "./VendasResumoAgregadoTable";

export default function VendasResumoTabelasPanel({
  formasRecebimentoConsolidadas,
  formatarData,
  vendasPorDataCalendario,
  vendasPorFuncionarioFiltradas,
  vendasPorGrupo,
  vendasPorTipo,
}) {
  return (
    <>
      <div className="mb-6 rounded-lg bg-white shadow">
        <div className="rounded-t-lg bg-gray-600 px-4 py-2 font-semibold text-white">
          Vendas por data
        </div>
        <VendasPorDataTable
          formatarData={formatarData}
          linhas={vendasPorDataCalendario}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2 xl:gap-6">
        <div className="rounded-lg bg-white shadow">
          <div className="rounded-t-lg bg-gray-600 px-4 py-2 font-semibold text-white">
            Formas de recebimento
          </div>
          <FormasRecebimentoTable linhas={formasRecebimentoConsolidadas} />
        </div>

        <div className="rounded-lg bg-white shadow">
          <div className="rounded-t-lg bg-gray-600 px-4 py-2 font-semibold text-white">
            Funcionario
          </div>
          <VendasPorFuncionarioTable linhas={vendasPorFuncionarioFiltradas} />
        </div>

        <div className="rounded-lg bg-white shadow">
          <div className="rounded-t-lg bg-gray-600 px-4 py-2 font-semibold text-white">
            Tipo
          </div>
          <VendasResumoAgregadoTable
            emptyMessage="Nenhum tipo encontrado"
            includeQuantidade
            labelHeader="Tipo"
            labelKey="tipo"
            linhas={vendasPorTipo}
            rowKeyPrefix="tipo-row"
          />
        </div>

        <div className="rounded-lg bg-white shadow">
          <div className="rounded-t-lg bg-gray-600 px-4 py-2 font-semibold text-white">
            Grupo de produto
          </div>
          <VendasResumoAgregadoTable
            emptyMessage="Nenhum grupo encontrado"
            includePercentual
            labelHeader="Nome"
            labelKey="grupo"
            linhas={vendasPorGrupo}
            rowKeyPrefix="grupo-row"
          />
        </div>
      </div>
    </>
  );
}
