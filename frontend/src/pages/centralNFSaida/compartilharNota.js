export function telefoneWhatsApp(valor) {
  const digitos = String(valor || "").replaceAll(/\D/g, "");
  if ([10, 11].includes(digitos.length)) return `55${digitos}`;
  return /^55\d{10,11}$/.test(digitos) ? digitos : "";
}

export function mensagemNota(dados) {
  return `Olá! Segue sua nota fiscal nº ${dados.numero}:\n${dados.link}`;
}

export function linkWhatsAppNota(dados, telefone) {
  const numero = telefoneWhatsApp(telefone);
  return numero ? `https://wa.me/${numero}?text=${encodeURIComponent(mensagemNota(dados))}` : "";
}
