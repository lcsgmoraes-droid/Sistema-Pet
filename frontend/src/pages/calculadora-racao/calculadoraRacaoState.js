export function criarFormCalculadoraRacao() {
  return {
    pet_id: "",
    pet_nome: "",
    produto_id: "",
    produto_nome: "",
    categoria_racao: "",
    peso_pet_kg: "",
    idade_meses: "",
    nivel_atividade: "normal",
    classificacao: "",
    especies: "dog",
    produto_comparar_id: "",
    produto_comparar_nome: "",
  };
}

export function getPetLabel(pet) {
  return `${pet.nome} - ${pet.especie} ${pet.peso ? `(${pet.peso}kg)` : ""}`;
}

export function calcularIdadeMeses(dataNascimento) {
  if (!dataNascimento) return "";

  const nascimento = new Date(dataNascimento);
  const hoje = new Date();
  const diffTime = Math.abs(hoje - nascimento);
  const diffMonths = Math.floor(diffTime / (1000 * 60 * 60 * 24 * 30.44));
  return diffMonths.toString();
}

export function getEspecieRacaoPorPet(pet, fallback) {
  if (pet.especie === "Cachorro") return "dog";
  if (pet.especie === "Gato") return "cat";
  return fallback;
}

export function montarPayloadCalculo(form, produtoId) {
  return {
    produto_id: parseInt(produtoId),
    peso_pet_kg: parseFloat(form.peso_pet_kg),
    idade_meses: form.idade_meses ? parseInt(form.idade_meses) : null,
    nivel_atividade: form.nivel_atividade,
  };
}

export function montarParamsComparacao(form) {
  const params = {
    peso_pet_kg: parseFloat(form.peso_pet_kg),
    nivel_atividade: form.nivel_atividade,
  };

  if (form.idade_meses) params.idade_meses = parseInt(form.idade_meses);
  if (form.classificacao) params.classificacao = form.classificacao;
  if (form.especies) params.especies = form.especies;

  return params;
}

export function ordenarComparativoComPrincipal(racoes, produtoId, racaoPrincipal) {
  const semPrincipal = racoes.filter((racao) => racao.produto_id !== parseInt(produtoId));
  semPrincipal.sort((a, b) => a.custo_por_dia - b.custo_por_dia);
  return [racaoPrincipal, ...semPrincipal];
}
