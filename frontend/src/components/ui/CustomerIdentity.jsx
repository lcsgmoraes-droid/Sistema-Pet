import CopyableCode from "./CopyableCode";
import CopyableValue from "./CopyableValue";
import { obterCodigoPessoaPublico } from "../../utils/codigosPublicos";

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
  return obterCodigoPessoaPublico(customer);
}

export default function CustomerIdentity({
  className = "",
  code,
  codeClassName = "",
  codeLabel = "Cod. cliente",
  customer,
  empty = "-",
  fallback = "Cliente nao informado",
  label = "Cliente",
  layout = "stacked",
  name,
  nameClassName = "font-medium text-slate-900",
  nameWrapperClassName = "",
  record,
  showCode = true,
  showLabel = false,
  venda,
}) {
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
          className={nameWrapperClassName}
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
