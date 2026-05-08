import CopyableValue from "./CopyableValue";

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

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md bg-gray-50 px-1.5 py-0.5 text-xs font-medium text-gray-600 ${className}`}
    >
      <CopyableValue
        buttonClassName="text-gray-400 hover:text-gray-700"
        className="gap-1"
        copied={copied}
        label={label}
        onCopy={onCopy}
        title={title}
        value={value}
        valueClassName="font-medium text-gray-600"
      />
    </span>
  );
}
