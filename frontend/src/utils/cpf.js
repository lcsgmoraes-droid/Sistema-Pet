export function normalizeCpf(value) {
  return String(value || "")
    .replace(/\D/g, "")
    .slice(0, 11);
}

export function documentoCpfCnpjCliente(cliente) {
  return (
    [cliente?.cpf, cliente?.cnpj, cliente?.cpf_cnpj]
      .map((value) => String(value ?? "").trim())
      .find(Boolean) || ""
  );
}

export function formatCpf(value) {
  const digits = normalizeCpf(value);
  return digits
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1-$2");
}

export function validarCpf(value) {
  const digits = normalizeCpf(value);
  if (digits.length !== 11 || /^(\d)\1{10}$/.test(digits)) return false;

  const calcularDigito = (base, factor) => {
    let total = 0;
    for (const char of base) {
      total += Number(char) * factor;
      factor -= 1;
    }
    const rest = (total * 10) % 11;
    return rest === 10 ? 0 : rest;
  };

  const firstDigit = calcularDigito(digits.slice(0, 9), 10);
  const secondDigit = calcularDigito(digits.slice(0, 10), 11);
  return firstDigit === Number(digits[9]) && secondDigit === Number(digits[10]);
}
