import { cloneElement, Fragment, isValidElement, useEffect, useRef, useState } from "react";

const ALIGN_CLASSES = {
  center: "text-center",
  left: "text-left",
  right: "text-right",
};

function resolveClassName(value, ...args) {
  return typeof value === "function" ? value(...args) : value;
}

function isTableElement(element, type) {
  return isValidElement(element) && element.type === type;
}

function renderHeaderCell(column, headerContext) {
  if (typeof column.renderHeader === "function") {
    const rendered = column.renderHeader(headerContext);
    if (isTableElement(rendered, "th")) {
      return cloneElement(rendered, { key: column.key });
    }
    return renderDefaultHeaderCell(column, rendered);
  }

  return renderDefaultHeaderCell(column, column.header);
}

function renderDefaultHeaderCell(column, content) {
  return (
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
      {content}
    </th>
  );
}

function renderCell(column, row, rowIndex, cellContext) {
  if (typeof column.render === "function") {
    return column.render(row, rowIndex, cellContext);
  }

  if (typeof column.renderCell === "function") {
    return column.renderCell(row, cellContext, rowIndex);
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
  getCellContext,
  getRowRef,
  headerContext,
  tableClassName = "",
  tbodyClassName = "",
  theadClassName = "",
  rowClassName = "",
}) {
  const colSpan = Math.max(columns.length, 1);
  const topScrollRef = useRef(null);
  const bottomScrollRef = useRef(null);
  const tableRef = useRef(null);
  const syncingScrollRef = useRef(false);
  const [scrollMetrics, setScrollMetrics] = useState({ clientWidth: 0, scrollWidth: 0 });

  useEffect(() => {
    const medirTabela = () => {
      const table = tableRef.current;
      const scrollContainer = bottomScrollRef.current;
      if (!table || !scrollContainer) return;

      setScrollMetrics({
        clientWidth: scrollContainer.clientWidth,
        scrollWidth: table.scrollWidth,
      });
    };

    medirTabela();

    const ResizeObserverImpl = globalThis.ResizeObserver;
    const observers = [];
    if (ResizeObserverImpl && tableRef.current && bottomScrollRef.current) {
      const tableObserver = new ResizeObserverImpl(medirTabela);
      const containerObserver = new ResizeObserverImpl(medirTabela);
      tableObserver.observe(tableRef.current);
      containerObserver.observe(bottomScrollRef.current);
      observers.push(tableObserver, containerObserver);
    }

    globalThis.addEventListener?.("resize", medirTabela);
    return () => {
      observers.forEach((observer) => observer.disconnect());
      globalThis.removeEventListener?.("resize", medirTabela);
    };
  }, [columns, data, loading]);

  const sincronizarRolagem = (origem, destino) => {
    if (!origem || !destino || syncingScrollRef.current) return;
    syncingScrollRef.current = true;
    destino.scrollLeft = origem.scrollLeft;
    const liberarSincronizacao = () => {
      syncingScrollRef.current = false;
    };
    if (globalThis.requestAnimationFrame) {
      globalThis.requestAnimationFrame(liberarSincronizacao);
    } else {
      globalThis.setTimeout(liberarSincronizacao, 0);
    }
  };

  const mostrarBarraSuperior =
    scrollMetrics.scrollWidth > 0 &&
    scrollMetrics.clientWidth > 0 &&
    scrollMetrics.scrollWidth > scrollMetrics.clientWidth + 1;

  return (
    <div className="erp-data-table">
      {mostrarBarraSuperior && (
        <div
          ref={topScrollRef}
          onScroll={() => sincronizarRolagem(topScrollRef.current, bottomScrollRef.current)}
          className="sticky top-0 z-30 h-4 overflow-x-auto overflow-y-hidden border-b border-slate-100 bg-white"
          aria-hidden="true"
        >
          <div style={{ width: scrollMetrics.scrollWidth, height: 1 }} />
        </div>
      )}
      <div
        ref={bottomScrollRef}
        onScroll={() => sincronizarRolagem(bottomScrollRef.current, topScrollRef.current)}
        className="erp-data-table-wrap overflow-x-auto"
      >
      <table
        ref={tableRef}
        className={[
          "w-full border-collapse text-sm",
          tableClassName,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <thead className={["bg-slate-100", theadClassName].filter(Boolean).join(" ")}>
          <tr>
            {columns.map((column) => renderHeaderCell(column, headerContext))}
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
              const cellContext = getCellContext?.(row, rowIndex);

              return (
                <Fragment key={rowKey}>
                  <tr
                    ref={getRowRef ? (element) => getRowRef(row, rowIndex, element) : undefined}
                    onClick={clickable ? (event) => onRowClick(row, rowIndex, event) : undefined}
                    className={[
                      "border-b border-slate-100 transition hover:bg-slate-50",
                      clickable ? "cursor-pointer" : "",
                      resolveClassName(rowClassName, row, rowIndex),
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    {columns.map((column) => {
                      const rendered = renderCell(column, row, rowIndex, cellContext);

                      if (isTableElement(rendered, "td")) {
                        return cloneElement(rendered, { key: column.key });
                      }

                      return (
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
                          {rendered}
                        </td>
                      );
                    })}
                  </tr>
                  {expanded && renderExpandedRow ? renderExpandedRow(row, rowIndex, colSpan) : null}
                </Fragment>
              );
            })
          )}
        </tbody>
      </table>
      </div>
    </div>
  );
}
