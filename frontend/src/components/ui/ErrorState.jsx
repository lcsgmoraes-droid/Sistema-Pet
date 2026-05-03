import { AlertTriangle } from "lucide-react";

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

export default function ErrorState({
  action = null,
  className = "",
  description,
  title = "Nao foi possivel carregar os dados",
}) {
  return (
    <div
      className={cx(
        "rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center text-red-900",
        className,
      )}
    >
      <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-red-500" aria-hidden="true" />
      <div className="text-sm font-semibold">{title}</div>
      {description ? (
        <div className="mx-auto mt-1 max-w-2xl text-sm text-red-700">{description}</div>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
