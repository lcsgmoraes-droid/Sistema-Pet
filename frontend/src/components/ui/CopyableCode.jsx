import { Check, Copy } from "lucide-react";

export default function CopyableCode({
  className = "",
  copied = false,
  label = "SKU",
  onCopy,
  title = "Copiar codigo",
  value,
}) {
  if (!value) {
    return null;
  }

  const handleCopy = (event) => {
    event.stopPropagation();
    if (onCopy) {
      onCopy(value);
      return;
    }
    navigator.clipboard?.writeText(String(value));
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md bg-gray-50 px-1.5 py-0.5 text-xs font-medium text-gray-600 ${className}`}
    >
      <span>
        {label}: {value}
      </span>
      <button
        type="button"
        onClick={handleCopy}
        className="text-gray-400 transition-colors hover:text-gray-700"
        title={title}
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
