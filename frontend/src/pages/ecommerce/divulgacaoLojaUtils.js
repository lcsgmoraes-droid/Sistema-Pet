export const DIVULGACAO_DESTINOS = {
  smart: {
    label: "Acesso principal",
    descricao: "Encontra a loja e oferece app ou compra online.",
  },
  ecommerce: {
    label: "Loja virtual",
    descricao: "Abre diretamente o catálogo público da loja.",
  },
  app: {
    label: "App CorePet",
    descricao: "Abre a loja no app quando ele já está instalado.",
  },
  whatsapp: {
    label: "WhatsApp",
    descricao: "Inicia uma conversa com a mensagem configurada.",
  },
};

export function normalizarOrigemPublica(origin) {
  return String(origin || "https://corepet.com.br")
    .trim()
    .replace(/\/$/, "");
}

export function normalizarSlugLoja(slug) {
  return String(slug || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "");
}

export function normalizarTelefoneWhatsApp(telefone) {
  let digitos = String(telefone || "").replace(/\D/g, "");
  digitos = digitos.replace(/^0+/, "");

  if (!digitos) return "";
  if ((digitos.length === 10 || digitos.length === 11) && !digitos.startsWith("55")) {
    digitos = `55${digitos}`;
  }
  return digitos;
}

export function telefoneWhatsAppValido(telefone) {
  const telefoneNormalizado = normalizarTelefoneWhatsApp(telefone);
  return telefoneNormalizado.length >= 12 && telefoneNormalizado.length <= 15;
}

export function montarLinksDivulgacao({ origin, slug, telefone, mensagem }) {
  const origem = normalizarOrigemPublica(origin);
  const slugLimpo = normalizarSlugLoja(slug);
  const telefoneLimpo = normalizarTelefoneWhatsApp(telefone);
  const mensagemLimpa = String(mensagem || "").trim();

  if (!slugLimpo) {
    return { smart: "", ecommerce: "", app: "", whatsapp: "" };
  }

  return {
    smart: `${origem}/app?loja=${encodeURIComponent(slugLimpo)}`,
    ecommerce: `${origem}/${encodeURIComponent(slugLimpo)}`,
    app: `corepet://app?loja=${encodeURIComponent(slugLimpo)}`,
    whatsapp: telefoneLimpo
      ? `https://wa.me/${telefoneLimpo}${
          mensagemLimpa ? `?text=${encodeURIComponent(mensagemLimpa)}` : ""
        }`
      : "",
  };
}

export function nomeArquivoDivulgacao(nomeLoja, formato, extensao) {
  const nome =
    String(nomeLoja || "loja")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "loja";
  return `divulgacao-${nome}-${formato}.${extensao}`;
}
