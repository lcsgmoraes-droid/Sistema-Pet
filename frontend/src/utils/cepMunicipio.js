function onlyDigits(value) {
  return String(value || "").replace(/\D/g, "");
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

export async function resolveCepMunicipio(
  cep,
  { cidade = "", estado = "", fetchImpl = globalThis.fetch } = {},
) {
  const cepLimpo = onlyDigits(cep);
  if (cepLimpo.length !== 8) {
    throw new Error("Informe um CEP valido com 8 digitos.");
  }
  if (typeof fetchImpl !== "function") {
    throw new Error("A consulta automatica do CEP nao esta disponivel.");
  }

  const response = await fetchImpl(`https://viacep.com.br/ws/${cepLimpo}/json/`);
  if (!response.ok) {
    throw new Error("Nao foi possivel consultar o CEP agora. Tente novamente.");
  }

  const data = await response.json();
  const codigoMunicipio = onlyDigits(data.ibge);
  if (data.erro || codigoMunicipio.length !== 7) {
    throw new Error("CEP nao encontrado ou sem codigo IBGE do municipio.");
  }

  const cidadeInformada = normalizeText(cidade);
  const estadoInformado = normalizeText(estado);
  if (
    (cidadeInformada && cidadeInformada !== normalizeText(data.localidade)) ||
    (estadoInformado && estadoInformado !== normalizeText(data.uf))
  ) {
    throw new Error(
      `O CEP informado pertence a ${data.localidade}/${data.uf}. Confira cidade e estado.`,
    );
  }

  return {
    cep: cepLimpo,
    endereco: data.logradouro || "",
    bairro: data.bairro || "",
    cidade: data.localidade || "",
    estado: data.uf || "",
    codigo_municipio: codigoMunicipio,
  };
}
