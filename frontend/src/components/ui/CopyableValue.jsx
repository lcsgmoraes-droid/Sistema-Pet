import { useState } from "react";
import { Check, Copy } from "lucide-react";

export default function CopyableValue({
  buttonClassName = "",
  children,
  className = "",
  copied: copiedProp = false,
  copiedTitle = "Copiado",
  empty = null,
  label,
  onCopy,
  stopPropagation = true,
  title = "Copiar",
  value,
  valueClassName = "",
}) {
  const [copiedState, setCopiedState] = useState(false);
  const copied = copiedProp || copiedState;
  const displayValue = children ?? value;

  if (!displayValue) {
    return empty;
  }

  const handleCopy = async (event) => {
    if (stopPropagation) {
      event.stopPropagation();
    }

    const copyValue = value ?? displayValue;
    try {
      if (onCopy) {
        await Promise.resolve(onCopy(copyValue));
      } else {
        await navigator.clipboard?.writeText(String(copyValue));
      }
      setCopiedState(true);
      setTimeout(() => setCopiedState(false), 1400);
    } catch {
      setCopiedState(false);
    }
  };

  return (
    <span className={`inline-flex min-w-0 items-center gap-1 ${className}`}>
      {label ? <span className="shrink-0 text-xs font-medium text-slate-500">{label}:</span> : null}
      <span className={`min-w-0 truncate ${valueClassName}`}>{displayValue}</span>
      <button
        type="button"
        onClick={handleCopy}
        className={`shrink-0 text-slate-400 transition-colors hover:text-slate-700 ${buttonClassName}`}
        title={copied ? copiedTitle : title}
        aria-label={copied ? copiedTitle : title}
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-green-600" />
        ) : (
          <Copy className="h-3.5 w-3.5" />
        )}
      </button>
    </span>
  );
}
