export function formatarEnderecoPrincipalCliente(cliente) {
  const endereco = String(cliente?.endereco || "").trim();
  if (!endereco) return "";

  const numero = String(cliente?.numero || "").trim();
  const localidade = [cliente?.cidade, cliente?.estado]
    .map((parte) => String(parte || "").trim())
    .filter(Boolean)
    .join("/");

  return [
    [endereco, numero].filter(Boolean).join(", "),
    cliente?.complemento,
    cliente?.bairro,
    localidade,
  ]
    .map((parte) => String(parte || "").trim())
    .filter(Boolean)
    .join(" · ");
}
