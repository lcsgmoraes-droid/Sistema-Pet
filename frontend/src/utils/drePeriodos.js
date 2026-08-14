const doisDigitos = (valor) => String(valor).padStart(2, "0");

export const formatarMesLocal = (data = new Date()) =>
  `${data.getFullYear()}-${doisDigitos(data.getMonth() + 1)}`;

export const formatarDataLocal = (data = new Date()) =>
  `${formatarMesLocal(data)}-${doisDigitos(data.getDate())}`;

export const obterPeriodoPresetDRE = (preset, hoje = new Date()) => {
  switch (preset) {
    case "mes_atual":
      return {
        periodo: formatarMesLocal(hoje),
        mesInicial: null,
        dataFinal: null,
      };
    case "mes_anterior": {
      const mesPassado = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
      return {
        periodo: formatarMesLocal(mesPassado),
        mesInicial: null,
        dataFinal: null,
      };
    }
    case "ano_atual":
      return {
        periodo: formatarMesLocal(hoje),
        mesInicial: 1,
        dataFinal: formatarDataLocal(hoje),
      };
    default:
      return null;
  }
};
