function normalizarEspecie(valor) {
  const especie = String(valor || "")
    .trim()
    .toLowerCase();
  if (["dog", "cao", "cão", "canino", "cachorro"].includes(especie)) return "dog";
  if (["cat", "gato", "felino"].includes(especie)) return "cat";
  return especie || null;
}

function obterIdadeMeses(pet) {
  const informada = Number(pet?.idade_meses ?? pet?.idade_aproximada);
  if (Number.isFinite(informada)) return informada;
  if (!pet?.data_nascimento) return null;
  const nascimento = new Date(pet.data_nascimento);
  if (Number.isNaN(nascimento.getTime())) return null;
  return Math.max(Math.floor((Date.now() - nascimento.getTime()) / (30.4375 * 86400000)), 0);
}

export function protocoloCompativelComPet(protocolo, pet) {
  const especie = protocolo?.especie_compativel || "both";
  if (especie !== "both" && normalizarEspecie(pet?.especie) !== especie) return false;

  const fase = protocolo?.fase_vida || "all";
  if (fase === "all") return true;
  const idadeMeses = obterIdadeMeses(pet);
  if (idadeMeses === null) return false;
  return fase === (idadeMeses < 12 ? "puppy" : "adult");
}

export function sugerirProtocoloRecorrencia(protocolos = [], pet = null) {
  const ativos = protocolos.filter((protocolo) => protocolo.ativo !== false);
  const compativeis = ativos.filter((protocolo) => protocoloCompativelComPet(protocolo, pet));
  return compativeis.length === 1 ? compativeis[0].id || null : null;
}

export function rotuloProtocoloRecorrencia(protocolo) {
  const fase = { all: "todas as fases", puppy: "filhote", adult: "adulto" }[
    protocolo?.fase_vida || "all"
  ];
  const especie = { both: "cães e gatos", dog: "cães", cat: "gatos" }[
    protocolo?.especie_compativel || "both"
  ];
  return `${protocolo?.nome || "Protocolo"} · ${especie} · ${fase}`;
}
