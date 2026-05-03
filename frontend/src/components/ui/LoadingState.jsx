import { Loader2 } from "lucide-react";

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

export default function LoadingState({
  className = "",
  compact = false,
  label = "Carregando...",
}) {
  return (
    <div
      className={cx(
        "flex items-center justify-center text-sm text-slate-500",
        compact ? "py-4" : "py-10",
        className,
      )}
    >
      <Loader2 className="mr-2 h-5 w-5 animate-spin text-blue-600" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
