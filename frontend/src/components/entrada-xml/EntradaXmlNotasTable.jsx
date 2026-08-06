import PropTypes from "prop-types";
import ActionButton from "../ui/ActionButton";
import DataTable from "../ui/DataTable";
import PaginationControls from "../ui/PaginationControls";
import Panel from "../ui/Panel";
import SegmentedControl from "../ui/SegmentedControl";
import StatusBadge from "../ui/StatusBadge";

const FILTROS_STATUS = [
  { value: "todos", label: "Todas" },
  { value: "pendente", label: "Pendentes" },
  { value: "processada", label: "Conciliadas" },
  { value: "erro", label: "Com erro" },
];

const STATUS_META = {
  cancelada: { label: "Cancelada", intent: "danger" },
  erro: { label: "Erro", intent: "danger" },
  pendente: { label: "Pendente", intent: "warning" },
  processada: { label: "Conciliada", intent: "success" },
};

const FILTROS_CONFERENCIA = [
  { value: "todos", label: "Todas" },
  { value: "nao_iniciada", label: "Nao conferidas" },
  { value: "sem_divergencia", label: "Sem divergencia" },
  { value: "com_divergencia", label: "Com divergencia" },
];

function NotaStatusBadge({ status }) {
  const meta = STATUS_META[status] || {
    label: String(status || "-").toUpperCase(),
    intent: "neutral",
  };

  return (
    <StatusBadge intent={meta.intent} size="md">
      {meta.label}
    </StatusBadge>
  );
}

NotaStatusBadge.propTypes = {
  status: PropTypes.string,
};

NotaStatusBadge.defaultProps = {
  status: "",
};

function renderConferenciaBadge({
  abrirDetalhes,
  conferenciaLabel,
  conferenciaMeta,
  nota,
  podeAbrirDivergencia,
}) {
  const classes = conferenciaMeta?.cls || "bg-gray-100 text-gray-700 border-gray-200";

  if (podeAbrirDivergencia) {
    return (
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          abrirDetalhes(nota.id, { abrirConferencia: true });
        }}
        className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] font-semibold transition-colors hover:brightness-95 focus:outline-none focus:ring-2 focus:ring-orange-300 ${classes}`}
        title="Abrir conferencia e tratar divergencias"
      >
        {conferenciaLabel}
      </button>
    );
  }

  return (
    <div
      className={`inline-flex items-center rounded-full border px-2 py-1 text-[11px] font-semibold ${classes}`}
    >
      {conferenciaLabel}
    </div>
  );
}

export default function EntradaXmlNotasTable({
  abrirDetalhes,
  abrirVisualizacao,
  carregarPreviewProcessamento,
  conferenciaStatusMeta,
  excluirNota,
  filtroStatus,
  filtrosNotas,
  formatMoneyBRL,
  loading,
  notasEntrada,
  onFiltrosChange,
  onItemsPerPageChange,
  onPageChange,
  paginacao,
  reverterNota,
  setFiltroStatus,
  totalNotasGlobal,
}) {
  const limparFiltrosNotas = () => {
    onFiltrosChange({
      fornecedor: "",
      nf: "",
      data_inicio: "",
      data_fim: "",
      conferencia: "todos",
    });
  };

  const emptyMessage =
    totalNotasGlobal === 0
      ? "Nenhuma nota fiscal importada. Importe um XML ou busque pela SEFAZ."
      : "Nenhuma nota encontrada com os filtros atuais.";

  const columns = [
    {
      key: "nota",
      header: "NF / Chave",
      render: (nota) => (
        <>
          <div className="font-semibold text-gray-900">NF {nota.numero_nota || "-"}</div>
          <div className="font-mono text-[11px] text-gray-500">
            {nota.chave_acesso.substring(0, 20)}...
          </div>
        </>
      ),
    },
    {
      key: "fornecedor",
      header: "Fornecedor",
      render: (nota) => (
        <>
          <div className="font-semibold">{nota.fornecedor_nome}</div>
          <div className="text-xs text-gray-500">{nota.fornecedor_cnpj}</div>
        </>
      ),
    },
    {
      key: "data_emissao",
      header: "Data Emissao",
      render: (nota) => new Date(nota.data_emissao).toLocaleDateString(),
    },
    {
      key: "valor",
      header: "Valor",
      align: "right",
      className: "font-semibold",
      render: (nota) => formatMoneyBRL(nota.valor_total || 0),
    },
    {
      key: "itens",
      header: "Itens",
      align: "center",
      render: (nota) => (
        <StatusBadge intent="info">
          {nota.produtos_vinculados + nota.produtos_nao_vinculados} itens
        </StatusBadge>
      ),
    },
    {
      key: "status",
      header: "Status",
      align: "center",
      render: (nota) => {
        const conferenciaMeta = conferenciaStatusMeta[nota.conferencia_status || "nao_iniciada"];
        const divergenciasCount = Number(nota.divergencias_count || 0);
        const podeAbrirDivergencia =
          divergenciasCount > 0 || nota.conferencia_status === "com_divergencia";
        const conferenciaLabel = (
          <>
            {conferenciaMeta?.label || "Nao conferida"}
            {divergenciasCount > 0 ? ` • ${divergenciasCount} divergencia(s)` : ""}
          </>
        );

        return (
          <div className="space-y-2">
            <div>
              <NotaStatusBadge status={nota.status} />
            </div>
            {renderConferenciaBadge({
              abrirDetalhes,
              conferenciaLabel,
              conferenciaMeta,
              nota,
              podeAbrirDivergencia,
            })}
          </div>
        );
      },
    },
    {
      key: "acoes",
      header: "Acoes",
      align: "center",
      render: (nota) => {
        const exibirBotaoConferir =
          nota.status === "pendente" &&
          (nota.conferencia_status || "nao_iniciada") === "nao_iniciada";
        const exibirBotaoMovimentos =
          nota.status === "processada" && Number(nota.produtos_vinculados || 0) > 0;

        return (
          <div className="flex justify-center gap-2">
            {nota.status === "pendente" && (
              <ActionButton
                type="button"
                intent="edit"
                size="xs"
                title="Vincular produtos"
                onClick={(event) => {
                  event.stopPropagation();
                  abrirDetalhes(nota.id);
                }}
              >
                Vincular
              </ActionButton>
            )}
            {exibirBotaoConferir && (
              <ActionButton
                type="button"
                intent="create"
                size="xs"
                title="Conferir entrada da nota"
                onClick={(event) => {
                  event.stopPropagation();
                  abrirDetalhes(nota.id, { abrirConferencia: true });
                }}
              >
                Conferir
              </ActionButton>
            )}
            {exibirBotaoMovimentos && (
              <ActionButton
                type="button"
                intent="create"
                size="xs"
                title="Lancar movimentos pendentes"
                onClick={(event) => {
                  event.stopPropagation();
                  carregarPreviewProcessamento(nota.id);
                }}
              >
                Lancar movimentos
              </ActionButton>
            )}
            {nota.entrada_estoque_realizada ? (
              <ActionButton
                type="button"
                intent="warning"
                tone="ghost"
                size="xs"
                title="Reverter entrada no estoque"
                onClick={(event) => {
                  event.stopPropagation();
                  reverterNota(nota.id, nota.numero_nota);
                }}
              >
                Reverter
              </ActionButton>
            ) : (
              <ActionButton
                type="button"
                intent="delete"
                tone="ghost"
                size="xs"
                title="Excluir nota"
                onClick={(event) => {
                  event.stopPropagation();
                  excluirNota(nota.id, nota.numero_nota);
                }}
              >
                Excluir
              </ActionButton>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <Panel
      padding="none"
      className="overflow-hidden"
      headerClassName="border-b bg-slate-50 px-6 py-4"
      title="Notas Fiscais de Entrada"
      actions={
        <SegmentedControl
          ariaLabel="Filtrar notas fiscais por status"
          value={filtroStatus}
          onChange={setFiltroStatus}
          options={FILTROS_STATUS}
        />
      }
    >
      <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-12">
          <div className="md:col-span-3">
            <label className="mb-1 block text-sm font-medium text-slate-700">Fornecedor</label>
            <input
              type="text"
              className="w-full rounded border border-slate-300 px-3 py-2"
              placeholder="Nome ou CNPJ"
              value={filtrosNotas.fornecedor}
              onChange={(event) =>
                onFiltrosChange((atuais) => ({
                  ...atuais,
                  fornecedor: event.target.value,
                }))
              }
            />
          </div>
          <div className="md:col-span-3">
            <label className="mb-1 block text-sm font-medium text-slate-700">NF ou chave</label>
            <input
              type="text"
              className="w-full rounded border border-slate-300 px-3 py-2"
              placeholder="Numero ou chave"
              value={filtrosNotas.nf}
              onChange={(event) =>
                onFiltrosChange((atuais) => ({ ...atuais, nf: event.target.value }))
              }
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-sm font-medium text-slate-700">Data inicial</label>
            <input
              type="date"
              className="w-full rounded border border-slate-300 px-3 py-2"
              value={filtrosNotas.data_inicio}
              onChange={(event) =>
                onFiltrosChange((atuais) => ({
                  ...atuais,
                  data_inicio: event.target.value,
                }))
              }
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-sm font-medium text-slate-700">Data final</label>
            <input
              type="date"
              className="w-full rounded border border-slate-300 px-3 py-2"
              value={filtrosNotas.data_fim}
              onChange={(event) =>
                onFiltrosChange((atuais) => ({
                  ...atuais,
                  data_fim: event.target.value,
                }))
              }
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-sm font-medium text-slate-700">Conferencia</label>
            <select
              className="w-full rounded border border-slate-300 px-3 py-2"
              value={filtrosNotas.conferencia}
              onChange={(event) =>
                onFiltrosChange((atuais) => ({
                  ...atuais,
                  conferencia: event.target.value,
                }))
              }
            >
              {FILTROS_CONFERENCIA.map((filtro) => (
                <option key={filtro.value} value={filtro.value}>
                  {filtro.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between gap-3">
          <span className="text-sm text-slate-500">{paginacao.total} nota(s) encontrada(s)</span>
          <ActionButton intent="neutral" tone="soft" size="sm" onClick={limparFiltrosNotas}>
            Limpar filtros
          </ActionButton>
        </div>
      </div>
      <DataTable
        columns={columns}
        data={notasEntrada}
        emptyMessage={emptyMessage}
        getRowKey={(nota) => nota.id}
        loading={loading}
        loadingMessage="Carregando notas fiscais..."
        onRowClick={(nota) => abrirVisualizacao(nota.id)}
        rowClassName="hover:bg-blue-50"
        tableClassName="min-w-[960px]"
      />
      <PaginationControls
        currentPage={paginacao.page}
        disabled={loading}
        itemName="notas"
        itemsPerPage={paginacao.page_size}
        onItemsPerPageChange={onItemsPerPageChange}
        onPageChange={onPageChange}
        pageSizeOptions={[10, 20, 50, 100]}
        totalItems={paginacao.total}
        totalPages={paginacao.pages}
        variant="bottom"
      />
    </Panel>
  );
}

EntradaXmlNotasTable.propTypes = {
  abrirDetalhes: PropTypes.func.isRequired,
  abrirVisualizacao: PropTypes.func.isRequired,
  carregarPreviewProcessamento: PropTypes.func.isRequired,
  conferenciaStatusMeta: PropTypes.objectOf(
    PropTypes.shape({
      cls: PropTypes.string,
      label: PropTypes.string,
    }),
  ).isRequired,
  excluirNota: PropTypes.func.isRequired,
  filtroStatus: PropTypes.string.isRequired,
  filtrosNotas: PropTypes.shape({
    fornecedor: PropTypes.string,
    nf: PropTypes.string,
    data_inicio: PropTypes.string,
    data_fim: PropTypes.string,
    conferencia: PropTypes.string,
  }).isRequired,
  formatMoneyBRL: PropTypes.func.isRequired,
  loading: PropTypes.bool.isRequired,
  notasEntrada: PropTypes.arrayOf(
    PropTypes.shape({
      chave_acesso: PropTypes.string,
      conferencia_status: PropTypes.string,
      data_emissao: PropTypes.string,
      divergencias_count: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
      entrada_estoque_realizada: PropTypes.bool,
      fornecedor_cnpj: PropTypes.string,
      fornecedor_nome: PropTypes.string,
      id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
      numero_nota: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
      produtos_nao_vinculados: PropTypes.number,
      produtos_vinculados: PropTypes.number,
      status: PropTypes.string,
      valor_total: PropTypes.number,
    }),
  ).isRequired,
  onFiltrosChange: PropTypes.func.isRequired,
  onItemsPerPageChange: PropTypes.func.isRequired,
  onPageChange: PropTypes.func.isRequired,
  paginacao: PropTypes.shape({
    page: PropTypes.number,
    page_size: PropTypes.number,
    pages: PropTypes.number,
    total: PropTypes.number,
  }).isRequired,
  reverterNota: PropTypes.func.isRequired,
  setFiltroStatus: PropTypes.func.isRequired,
  totalNotasGlobal: PropTypes.number.isRequired,
};
