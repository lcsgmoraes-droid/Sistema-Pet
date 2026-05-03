import { actionButtonClasses } from "./actionStyles";

const PAGE_SIZE_OPTIONS = [10, 20, 30, 50, 100];

const VARIANT_CLASSES = {
  inline: "flex w-full flex-col gap-3 md:flex-row md:items-center md:justify-between",
  top:
    "mt-6 flex w-full flex-col gap-3 rounded-t-lg border border-gray-200 bg-gray-50 px-4 py-3 md:flex-row md:items-center md:justify-between",
  bottom:
    "flex w-full flex-col gap-3 border-t border-gray-200 bg-gray-50 px-4 py-3 md:flex-row md:items-center md:justify-between",
};

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

function getVisiblePages(currentPage, totalPages) {
  const firstPage =
    totalPages <= 5
      ? 1
      : currentPage <= 3
        ? 1
        : currentPage >= totalPages - 2
          ? totalPages - 4
          : currentPage - 2;

  return Array.from(
    { length: Math.min(totalPages, 5) },
    (_, index) => firstPage + index,
  );
}

export default function PaginationControls({
  className = "",
  currentPage = 1,
  disabled = false,
  itemName = "registros",
  itemsPerPage = 20,
  loading = false,
  onItemsPerPageChange,
  onPageChange,
  pageSizeOptions = PAGE_SIZE_OPTIONS,
  totalItems = 0,
  totalPages,
  variant = "inline",
}) {
  if (loading || totalItems <= 0) return null;

  const pageCount = Math.max(
    Number(totalPages) || Math.ceil(totalItems / Number(itemsPerPage || 1)),
    1,
  );
  const safeCurrentPage = Math.min(Math.max(Number(currentPage) || 1, 1), pageCount);
  const startItem = (safeCurrentPage - 1) * Number(itemsPerPage) + 1;
  const endItem = Math.min(safeCurrentPage * Number(itemsPerPage), totalItems);
  const visiblePages = getVisiblePages(safeCurrentPage, pageCount);
  const isFirstPage = safeCurrentPage === 1;
  const isLastPage = safeCurrentPage === pageCount;
  const containerClassName = VARIANT_CLASSES[variant] || VARIANT_CLASSES.inline;

  const goToPage = (page) => {
    if (disabled) return;
    const nextPage = Math.min(Math.max(Number(page) || 1, 1), pageCount);
    onPageChange?.(nextPage);
  };

  return (
    <div className={cx(containerClassName, className)}>
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:gap-4">
        <span className="text-sm text-gray-600">
          Mostrando {startItem} a {endItem} de {totalItems} {itemName}
        </span>
        <select
          value={itemsPerPage}
          onChange={(event) => onItemsPerPageChange?.(Number(event.target.value))}
          disabled={disabled}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1 text-sm outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
        >
          {pageSizeOptions.map((option) => (
            <option key={option} value={option}>
              {option} por pagina
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center justify-between gap-2 md:justify-end">
        <button
          type="button"
          onClick={() => goToPage(1)}
          disabled={disabled || isFirstPage}
          className={cx(actionButtonClasses({ intent: "neutral", tone: "soft", size: "xs" }), "hidden sm:inline-flex")}
        >
          Primeira
        </button>
        <button
          type="button"
          onClick={() => goToPage(safeCurrentPage - 1)}
          disabled={disabled || isFirstPage}
          className={actionButtonClasses({ intent: "neutral", tone: "soft", size: "xs" })}
        >
          Anterior
        </button>

        <span className="text-sm font-medium text-gray-600 sm:hidden">
          {safeCurrentPage}/{pageCount}
        </span>

        <div className="hidden items-center gap-1 sm:flex">
          {visiblePages.map((page) => (
            <button
              key={page}
              type="button"
              onClick={() => goToPage(page)}
              disabled={disabled}
              className={actionButtonClasses({
                intent: safeCurrentPage === page ? "edit" : "neutral",
                tone: safeCurrentPage === page ? "solid" : "soft",
                size: "xs",
              })}
            >
              {page}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => goToPage(safeCurrentPage + 1)}
          disabled={disabled || isLastPage}
          className={actionButtonClasses({ intent: "neutral", tone: "soft", size: "xs" })}
        >
          Proxima
        </button>
        <button
          type="button"
          onClick={() => goToPage(pageCount)}
          disabled={disabled || isLastPage}
          className={cx(actionButtonClasses({ intent: "neutral", tone: "soft", size: "xs" }), "hidden sm:inline-flex")}
        >
          Ultima
        </button>
      </div>
    </div>
  );
}
