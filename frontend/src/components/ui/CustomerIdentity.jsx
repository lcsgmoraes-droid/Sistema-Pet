import CopyableCode from "./CopyableCode";
import CopyableValue from "./CopyableValue";

function firstText(...values) {
  const value = values.find((item) => {
    if (typeof item === "string") return item.trim();
    return typeof item === "number" && Number.isFinite(item);
  });
  return value == null ? "" : String(value);
}

export function getCustomerIdentityName(customer) {
  return firstText(
    customer?.cliente_nome,
    customer?.nome_cliente,
    customer?.tutor_nome,
    customer?.nome_tutor,
    customer?.pessoa_nome,
    customer?.nome_pessoa,
    customer?.customer_name,
    customer?.cliente?.nome,
    customer?.cliente?.nome_fantasia,
    customer?.cliente?.razao_social,
    customer?.tutor?.nome,
    customer?.pessoa?.nome,
    customer?.customer?.nome,
    customer?.customer?.name,
    customer?.nome,
    customer?.nome_fantasia,
    customer?.razao_social,
    customer?.name,
  );
}

export function getCustomerIdentityCode(customer) {
  return firstText(
    customer?.cliente_codigo,
    customer?.codigo_cliente,
    customer?.cod_cliente,
    customer?.tutor_codigo,
    customer?.codigo_tutor,
    customer?.pessoa_codigo,
    customer?.codigo_pessoa,
    customer?.customer_code,
    customer?.cliente?.codigo,
    customer?.cliente?.cod_cliente,
    customer?.cliente?.id,
    customer?.tutor?.codigo,
    customer?.tutor?.id,
    customer?.pessoa?.codigo,
    customer?.pessoa?.id,
    customer?.customer?.codigo,
    customer?.customer?.id,
    customer?.id_cliente,
    customer?.cliente_id,
    customer?.id_tutor,
    customer?.tutor_id,
    customer?.id_pessoa,
    customer?.pessoa_id,
    customer?.customer_id,
  );
}

export default function CustomerIdentity({
  className = "",
  code,
  codeClassName = "",
  codeLabel = "Cod. cliente",
  customer,
  empty = "-",
  fallback = "Cliente nao informado",
  id,
  label = "Cliente",
  layout = "stacked",
  name,
  nameClassName = "font-medium text-slate-900",
  record,
  showCode = true,
  showLabel = false,
  venda,
}) {
  const explicitCustomerCode = customer || venda || record ? "" : firstText(id);
  const customerName = firstText(
    name,
    getCustomerIdentityName(customer),
    getCustomerIdentityName(venda),
    getCustomerIdentityName(record),
    fallback,
  );
  const customerCode = firstText(
    code,
    getCustomerIdentityCode(customer),
    getCustomerIdentityCode(venda),
    getCustomerIdentityCode(record),
    id,
    explicitCustomerCode,
  );

  if (!customerName && !customerCode) {
    return empty;
  }

  const wrapperClass =
    layout === "inline"
      ? "inline-flex min-w-0 flex-wrap items-center gap-1.5"
      : "inline-flex min-w-0 flex-col items-start gap-1";

  return (
    <span className={`${wrapperClass} ${className}`}>
      {customerName ? (
        <CopyableValue
          label={showLabel ? label : undefined}
          title="Copiar cliente"
          value={customerName}
          valueClassName={nameClassName}
        />
      ) : null}
      {showCode && customerCode ? (
        <CopyableCode
          className={codeClassName}
          label={codeLabel}
          title="Copiar codigo do cliente"
          value={customerCode}
        />
      ) : null}
    </span>
  );
}
