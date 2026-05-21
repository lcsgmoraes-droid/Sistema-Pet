export const numeroCampoParaFloat = (valor) => {
  if (valor === null || valor === undefined || valor === "") return 0;
  const numero = Number(String(valor).replace(",", "."));
  return Number.isFinite(numero) ? numero : 0;
};

const formatarNumero = (valor) => {
  if (!Number.isFinite(valor)) return "0.00";
  return valor.toFixed(2);
};

export const calcularValorPorPercentual = (salarioBase, percentual) => {
  const base = numeroCampoParaFloat(salarioBase);
  const pct = numeroCampoParaFloat(percentual);
  return formatarNumero((base * pct) / 100);
};

export const calcularPercentualPorValor = (salarioBase, valor) => {
  const base = numeroCampoParaFloat(salarioBase);
  if (base <= 0) return "0.00";
  return formatarNumero((numeroCampoParaFloat(valor) / base) * 100);
};

const CAMPOS_SINCRONIZADOS = {
  inss_patronal_percentual: {
    percentual: "inss_patronal_percentual",
    valor: "inss_patronal_valor",
  },
  inss_patronal_valor: {
    percentual: "inss_patronal_percentual",
    valor: "inss_patronal_valor",
  },
  fgts_percentual: {
    percentual: "fgts_percentual",
    valor: "fgts_valor",
  },
  fgts_valor: {
    percentual: "fgts_percentual",
    valor: "fgts_valor",
  },
  inss_funcionario_percentual: {
    percentual: "inss_funcionario_percentual",
    valor: "inss_funcionario_valor",
  },
  inss_funcionario_valor: {
    percentual: "inss_funcionario_percentual",
    valor: "inss_funcionario_valor",
  },
};

export const normalizarCamposRemuneracao = (form) => ({
  ...form,
  inss_patronal_valor: calcularValorPorPercentual(
    form.salario_base,
    form.inss_patronal_percentual,
  ),
  fgts_valor: calcularValorPorPercentual(form.salario_base, form.fgts_percentual),
  inss_funcionario_valor:
    numeroCampoParaFloat(form.inss_funcionario_valor) > 0
      ? String(form.inss_funcionario_valor)
      : calcularValorPorPercentual(form.salario_base, form.inss_funcionario_percentual),
});

export const sincronizarCampoRemuneracao = (form, campo, valor) => {
  const proximo = {
    ...form,
    [campo]: valor,
  };

  if (campo === "salario_base") {
    return normalizarCamposRemuneracao(proximo);
  }

  const sincronizado = CAMPOS_SINCRONIZADOS[campo];
  if (!sincronizado) return proximo;

  if (campo === sincronizado.percentual) {
    return {
      ...proximo,
      [sincronizado.valor]: calcularValorPorPercentual(proximo.salario_base, valor),
    };
  }

  return {
    ...proximo,
    [sincronizado.percentual]: calcularPercentualPorValor(proximo.salario_base, valor),
  };
};
