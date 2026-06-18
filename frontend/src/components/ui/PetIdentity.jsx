import CopyableCode from "./CopyableCode";
import CopyableValue from "./CopyableValue";

function firstText(...values) {
  const value = values.find((item) => {
    if (typeof item === "string") return item.trim();
    return typeof item === "number" && Number.isFinite(item);
  });
  return value == null ? "" : String(value);
}

export function getPetIdentityName(pet) {
  return firstText(
    pet?.pet_nome,
    pet?.nome_pet,
    pet?.animal_nome,
    pet?.nome_animal,
    pet?.pet?.nome,
    pet?.animal?.nome,
    pet?.nome,
    pet?.name,
  );
}

export function getPetIdentityCode(pet) {
  return firstText(
    pet?.pet_codigo,
    pet?.codigo_pet,
    pet?.cod_pet,
    pet?.animal_codigo,
    pet?.codigo_animal,
    pet?.pet?.codigo,
    pet?.pet?.id,
    pet?.animal?.codigo,
    pet?.animal?.id,
    pet?.pet_id,
    pet?.id_pet,
    pet?.animal_id,
    pet?.id_animal,
  );
}

export default function PetIdentity({
  className = "",
  code,
  codeClassName = "",
  codeLabel = "Cod. pet",
  copyable = true,
  empty = "-",
  fallback = "Pet nao informado",
  id,
  label = "Pet",
  layout = "stacked",
  name,
  nameClassName = "font-medium text-slate-900",
  pet,
  record,
  showCode = true,
  showLabel = false,
}) {
  const petName = firstText(name, getPetIdentityName(pet), getPetIdentityName(record), fallback);
  const petCode = firstText(code, getPetIdentityCode(pet), getPetIdentityCode(record), id);

  if (!petName && !petCode) {
    return empty;
  }

  const wrapperClass =
    layout === "inline"
      ? "inline-flex min-w-0 flex-wrap items-center gap-1.5"
      : "inline-flex min-w-0 flex-col items-start gap-1";

  return (
    <span className={`${wrapperClass} ${className}`}>
      {petName ? (
        copyable ? (
          <CopyableValue
            label={showLabel ? label : undefined}
            title="Copiar pet"
            value={petName}
            valueClassName={nameClassName}
          />
        ) : (
          <span className="inline-flex min-w-0 items-center gap-1">
            {showLabel ? (
              <span className="shrink-0 text-xs font-medium text-slate-500">{label}:</span>
            ) : null}
            <span className={`min-w-0 truncate ${nameClassName}`}>{petName}</span>
          </span>
        )
      ) : null}
      {showCode && petCode ? (
        copyable ? (
          <CopyableCode
            className={codeClassName}
            label={codeLabel}
            title="Copiar codigo do pet"
            value={petCode}
          />
        ) : (
          <span
            className={`inline-flex items-center gap-1 rounded-md bg-gray-50 px-1.5 py-0.5 text-xs font-medium text-gray-600 ${codeClassName}`}
          >
            {codeLabel}: {petCode}
          </span>
        )
      ) : null}
    </span>
  );
}
