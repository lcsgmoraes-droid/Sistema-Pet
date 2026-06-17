import CopyableCode from "./CopyableCode";
import CopyableValue from "./CopyableValue";

function firstText(...values) {
  const value = values.find((item) => {
    if (typeof item === "string") return item.trim();
    return typeof item === "number" && Number.isFinite(item);
  });
  return value == null ? "" : String(value);
}

export function getFornecedorIdentityName(fornecedor) {
  return firstText(
    fornecedor?.fornecedor_nome,
    fornecedor?.nome_fornecedor,
    fornecedor?.supplier_name,
    fornecedor?.fornecedor?.nome,
    fornecedor?.fornecedor?.razao_social,
    fornecedor?.fornecedor?.nome_fantasia,
    fornecedor?.nome,
    fornecedor?.razao_social,
    fornecedor?.nome_fantasia,
    fornecedor?.fantasia,
    fornecedor?.name,
  );
}

export function getFornecedorIdentityDocument(fornecedor) {
  return firstText(
    fornecedor?.fornecedor_cpf_cnpj,
    fornecedor?.fornecedor_cnpj,
    fornecedor?.cpf_cnpj_fornecedor,
    fornecedor?.cnpj_fornecedor,
    fornecedor?.fornecedor?.cpf_cnpj,
    fornecedor?.fornecedor?.cnpj,
    fornecedor?.cpf_cnpj,
    fornecedor?.cnpj,
    fornecedor?.cpf,
  );
}

export function getFornecedorIdentityCode(fornecedor) {
  return firstText(
    fornecedor?.fornecedor_codigo,
    fornecedor?.codigo_fornecedor,
    fornecedor?.cod_fornecedor,
    fornecedor?.supplier_code,
    fornecedor?.fornecedor?.codigo,
    fornecedor?.fornecedor?.id,
    fornecedor?.codigo,
    fornecedor?.fornecedor_id,
    fornecedor?.id_fornecedor,
    fornecedor?.supplier_id,
  );
}

export default function FornecedorIdentity({
  className = "",
  code,
  codeClassName = "",
  codeLabel = "Cod. fornecedor",
  copyable = true,
  document,
  documentClassName = "",
  documentLabel = "Doc.",
  empty = "-",
  fallback = "Fornecedor nao informado",
  fornecedor,
  id,
  label = "Fornecedor",
  layout = "stacked",
  name,
  nameClassName = "font-medium text-slate-900",
  record,
  showCode = false,
  showDocument = true,
  showLabel = false,
}) {
  const fornecedorName = firstText(
    name,
    getFornecedorIdentityName(fornecedor),
    getFornecedorIdentityName(record),
    fallback,
  );
  const fornecedorDocument = firstText(
    document,
    getFornecedorIdentityDocument(fornecedor),
    getFornecedorIdentityDocument(record),
  );
  const fornecedorCode = firstText(
    code,
    getFornecedorIdentityCode(fornecedor),
    getFornecedorIdentityCode(record),
    id,
  );

  if (!fornecedorName && !fornecedorDocument && !fornecedorCode) {
    return empty;
  }

  const wrapperClass =
    layout === "inline"
      ? "inline-flex min-w-0 flex-wrap items-center gap-1.5"
      : "inline-flex min-w-0 flex-col items-start gap-1";

  const renderText = (value, textClassName, copyTitle, itemLabel) => {
    if (!value) return null;
    if (copyable) {
      return (
        <CopyableValue
          label={itemLabel}
          title={copyTitle}
          value={value}
          valueClassName={textClassName}
        />
      );
    }

    return (
      <span className="inline-flex min-w-0 items-center gap-1">
        {itemLabel ? (
          <span className="shrink-0 text-xs font-medium text-slate-500">{itemLabel}:</span>
        ) : null}
        <span className={`min-w-0 truncate ${textClassName}`}>{value}</span>
      </span>
    );
  };

  const renderCode = (value, itemLabel, title, itemClassName) => {
    if (!value) return null;
    if (copyable) {
      return (
        <CopyableCode className={itemClassName} label={itemLabel} title={title} value={value} />
      );
    }

    return (
      <span
        className={`inline-flex items-center gap-1 rounded-md bg-gray-50 px-1.5 py-0.5 text-xs font-medium text-gray-600 ${itemClassName}`}
      >
        {itemLabel}: {value}
      </span>
    );
  };

  return (
    <span className={`${wrapperClass} ${className}`}>
      {renderText(
        fornecedorName,
        nameClassName,
        "Copiar fornecedor",
        showLabel ? label : undefined,
      )}
      {showDocument
        ? renderCode(
            fornecedorDocument,
            documentLabel,
            "Copiar documento do fornecedor",
            documentClassName,
          )
        : null}
      {showCode
        ? renderCode(fornecedorCode, codeLabel, "Copiar codigo do fornecedor", codeClassName)
        : null}
    </span>
  );
}
