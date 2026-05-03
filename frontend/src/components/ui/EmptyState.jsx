import { cloneElement, isValidElement } from "react";
import { Inbox } from "lucide-react";

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

function renderIcon(icon, className) {
  if (!icon) return null;

  if (isValidElement(icon)) {
    return cloneElement(icon, {
      className: cx(icon.props.className, className),
      "aria-hidden": true,
    });
  }

  const Icon = icon;
  return <Icon className={className} aria-hidden="true" />;
}

export default function EmptyState({
  action = null,
  className = "",
  compact = false,
  description,
  icon = Inbox,
  title = "Nenhum registro encontrado",
}) {
  return (
    <div
      className={cx(
        "rounded-xl border border-dashed border-slate-300 bg-white text-center shadow-sm",
        compact ? "px-4 py-6" : "px-6 py-10",
        className,
      )}
    >
      {renderIcon(icon, cx("mx-auto text-slate-300", compact ? "mb-2 h-8 w-8" : "mb-3 h-10 w-10"))}
      <div className="text-sm font-semibold text-slate-800">{title}</div>
      {description ? (
        <div className="mx-auto mt-1 max-w-2xl text-sm text-slate-500">{description}</div>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
