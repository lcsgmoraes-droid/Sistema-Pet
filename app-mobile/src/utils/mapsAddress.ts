const ROTULO_NUMERO_RE = /\b(?:numero|n[uú]mero|n[º°])\s*[:\-]?\s*/gi;
const COMPLEMENTO_LABELS = String.raw`complemento|compl\.?|apto|apartamento|ap\.?|bloco|torre|sala|fundos|casa|referencia|refer[êé]ncia|ponto de referencia|ponto de refer[êé]ncia|obs\.?|observacao|observa[cç][aã]o|condominio|condom[ií]nio|cond\.?`;
const COMPLEMENTO_RE = new RegExp(`^(?:${COMPLEMENTO_LABELS})\\b`, "i");
const COMPLEMENTO_APOS_NUMERO_RE = new RegExp(
  `^(\\d+[A-Za-z]?)\\s+(?:${COMPLEMENTO_LABELS})\\b.*$`,
  "i",
);
const CEP_RE = /^(?:cep\s*[:\-]?\s*)?\d{5}-?\d{3}$/i;
const CIDADE_UF_RE = /^(.+?)\/([A-Z]{2})$/i;

// Exemplos removidos antes do Maps: Apto, complemento, CEP.
export function limparEnderecoParaMaps(endereco?: string | null): string {
  if (!endereco) {
    return "";
  }

  const partes = String(endereco)
    .replace(ROTULO_NUMERO_RE, "")
    .split(/[,;|\n]+|\s+-\s+/g);
  const partesLimpas: string[] = [];

  for (const parte of partes) {
    let parteLimpa = parte
      .replace(/\s+/g, " ")
      .trim()
      .replace(/^-+|-+$/g, "");

    if (!parteLimpa || CEP_RE.test(parteLimpa) || COMPLEMENTO_RE.test(parteLimpa)) {
      continue;
    }

    const complementoNumero = parteLimpa.match(COMPLEMENTO_APOS_NUMERO_RE);
    if (complementoNumero) {
      parteLimpa = complementoNumero[1];
    }

    const cidadeUf = parteLimpa.match(CIDADE_UF_RE);
    if (cidadeUf) {
      const cidade = cidadeUf[1]?.trim();
      const uf = cidadeUf[2]?.trim().toUpperCase();
      if (cidade) {
        partesLimpas.push(cidade);
      }
      if (uf) {
        partesLimpas.push(uf);
      }
      continue;
    }

    partesLimpas.push(parteLimpa);
  }

  return partesLimpas.join(", ");
}
