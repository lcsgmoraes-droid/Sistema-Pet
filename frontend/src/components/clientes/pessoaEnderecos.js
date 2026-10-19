export const CAMPOS_ENDERECO_PRINCIPAL = [
  "cep",
  "endereco",
  "numero",
  "complemento",
  "bairro",
  "cidade",
  "estado",
  "codigo_municipio",
];

export function enderecoPrincipal(dados) {
  return Object.fromEntries(CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, dados[campo] || ""]));
}

export function prepararEnderecos(formData, adicionais, entrada, tipoAntigoPrincipal) {
  let principal = enderecoPrincipal(formData);
  let proximos = [...adicionais];
  const { index, ...endereco } = entrada;

  if (index === "principal") {
    principal = enderecoPrincipal(endereco);
  } else if (endereco.tipo === "principal") {
    if (typeof index === "number") proximos.splice(index, 1);
    if (principal.endereco || principal.cep || principal.cidade) {
      proximos.push({ ...principal, tipo: tipoAntigoPrincipal || "residencial", apelido: "" });
    }
    principal = enderecoPrincipal(endereco);
  } else if (typeof index === "number") {
    proximos[index] = endereco;
  } else {
    proximos.push(endereco);
  }

  return { ...principal, enderecos_adicionais: proximos };
}
