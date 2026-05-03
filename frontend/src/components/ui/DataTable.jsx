import { Fragment } from "react";

const ALIGN_CLASSES = {
  center: "text-center",
  left: "text-left",
  right: "text-right",
};

function resolveClassName(value, ...args) {
  return typeof value === "function" ? value(...args) : value;
}

function renderCell(column, row, rowIndex) {
  if (typeof column.render === "function") {
    return column.render(row, rowIndex);
  }

  if (column.accessor) {
    return typeof column.accessor === "function"
      ? column.accessor(row, rowIndex)
      : row?.[column.accessor];
  }

  return row?.[column.key] ?? "-";
}

export default function DataTable({
  columns = [],
  data = [],
  emptyMessage = "Nenhum registro encontrado",
  getRowKey,
  isRowExpanded,
  loading = false,
  loadingMessage = "Carregando...",
  onRowClick,
  renderExpandedRow,
  tableClassName = "",
  tbodyClassName = "",
  theadClassName = "",
  rowClassName = "",
}) {
  const colSpan = Math.max(columns.length, 1);

  return (
    <div className="overflow-x-auto">
      <table
        className={[
          "w-full border-collapse text-sm",
          tableClassName,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <thead className={["bg-slate-100", theadClassName].filter(Boolean).join(" ")}>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={[
                  "px-2 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600",
                  ALIGN_CLASSES[column.align || "left"],
                  column.headerClassName,
                ]
                  .filter(Boolean)
                  .join(" ")}
                title={column.title}
                style={column.headerStyle}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className={tbodyClassName}>
          {loading ? (
            <tr>
              <td colSpan={colSpan} className="px-4 py-8 text-center text-slate-500">
                {loadingMessage}
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={colSpan} className="px-4 py-8 text-center text-slate-500">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => {
              const rowKey = getRowKey ? getRowKey(row, rowIndex) : row?.id ?? rowIndex;
              const expanded = isRowExpanded?.(row, rowIndex);
              const clickable = typeof onRowClick === "function";

              return (
                <Fragment key={rowKey}>
                  <tr
                    onClick={clickable ? () => onRowClick(row, rowIndex) : undefined}
                    className={[
                      "border-b border-slate-100 transition hover:bg-slate-50",
                      clickable ? "cursor-pointer" : "",
                      resolveClassName(rowClassName, row, rowIndex),
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    {columns.map((column) => (
                      <td
                        key={column.key}
                        className={[
                          "px-2 py-2 align-middle",
                          ALIGN_CLASSES[column.align || "left"],
                          resolveClassName(column.className, row, rowIndex),
                        ]
                          .filter(Boolean)
                          .join(" ")}
                        title={resolveClassName(column.cellTitle, row, rowIndex)}
                        style={resolveClassName(column.cellStyle, row, rowIndex)}
                      >
                        {renderCell(column, row, rowIndex)}
                      </td>
                    ))}
                  </tr>
                  {expanded && renderExpandedRow ? renderExpandedRow(row, rowIndex, colSpan) : null}
                </Fragment>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
