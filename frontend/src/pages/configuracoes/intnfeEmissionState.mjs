export function resolveEmissionState(activation, environment) {
  const enabled = environment
    ? Boolean(environment.habilitada)
    : Boolean(activation?.emissao_disponivel);
  const code = environment
    ? environment.ambiente_codigo
    : activation?.ambiente === "producao"
      ? 1
      : 2;
  const production = code === 1;

  if (!enabled) {
    return {
      enabled: false,
      code,
      label: production ? "produção" : "homologação",
      badge: "Emissão direta desativada",
      description: "Conclua a integração e escolha um ambiente para liberar a emissão de notas.",
    };
  }

  return {
    enabled: true,
    code,
    label: production ? "produção" : "homologação",
    badge: production
      ? "Produção ativa · notas com valor fiscal"
      : "Homologação ativa · sem valor fiscal",
    description: production
      ? "As próximas notas enviadas pelo CorePet usarão o ambiente de produção."
      : "As notas de teste enviadas pelo CorePet usam o ambiente de homologação.",
  };
}
