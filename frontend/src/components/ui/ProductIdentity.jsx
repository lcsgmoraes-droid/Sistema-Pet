import CopyableCode from "./CopyableCode";
import CopyableValue from "./CopyableValue";

function firstText(...values) {
  const value = values.find((item) => {
    if (typeof item === "string") return item.trim();
    return typeof item === "number" && Number.isFinite(item);
  });
  return value == null ? "" : String(value);
}

export function getProductIdentityCode(product) {
  return firstText(
    product?.produto_codigo,
    product?.produto_sku,
    product?.produto?.codigo,
    product?.produto?.sku,
    product?.sku,
    product?.codigo,
    product?.produto_codigo_barras,
    product?.codigo_barras,
    product?.ean,
    product?.gtin,
  );
}

export function getProductIdentityName(product) {
  return firstText(
    product?.produto_nome,
    product?.produto,
    product?.nome,
    product?.descricao,
    product?.produto?.nome,
  );
}

export default function ProductIdentity({
  children,
  className = "",
  code,
  codeClassName = "",
  codeLabel = "SKU",
  empty = "-",
  name,
  nameClassName = "text-slate-700",
  product,
}) {
  const productName = name ?? getProductIdentityName(product);
  const productCode = code ?? getProductIdentityCode(product);

  if (!productName && !productCode && !children) {
    return empty;
  }

  return (
    <span className={`inline-flex min-w-0 flex-wrap items-center gap-1.5 ${className}`}>
      {productName ? (
        <CopyableValue
          title="Copiar produto"
          value={productName}
          valueClassName={nameClassName}
        />
      ) : null}
      <CopyableCode className={codeClassName} label={codeLabel} value={productCode} />
      {children}
    </span>
  );
}
