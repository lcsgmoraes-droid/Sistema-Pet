import { Download, FileText, Table } from "lucide-react";
import ActionButton from "./ActionButton";

const EXPORT_TYPES = {
  pdf: {
    icon: FileText,
    intent: "delete",
    label: "PDF",
  },
  excel: {
    icon: Download,
    intent: "create",
    label: "Excel",
  },
  csv: {
    icon: Table,
    intent: "create",
    label: "CSV",
  },
  report: {
    icon: FileText,
    intent: "edit",
    label: "Relatorios",
  },
};

export default function ExportActionButton({
  children,
  className = "",
  size = "xs",
  tone = "soft",
  type = "excel",
  ...props
}) {
  const config = EXPORT_TYPES[type] || EXPORT_TYPES.excel;

  return (
    <ActionButton
      className={["min-w-[76px]", className].filter(Boolean).join(" ")}
      icon={config.icon}
      intent={config.intent}
      size={size}
      tone={tone}
      {...props}
    >
      {children || config.label}
    </ActionButton>
  );
}
