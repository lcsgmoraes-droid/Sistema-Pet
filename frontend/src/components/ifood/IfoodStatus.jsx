import { IFOOD_STATUS } from "./ifoodPresentation";

export default function IfoodStatus({ status }) {
  const info = IFOOD_STATUS[status] || {
    label: "A conferir",
    className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  };
  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-full px-2 py-1 text-xs font-medium ${info.className}`}
    >
      {info.label}
    </span>
  );
}
