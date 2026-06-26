export function createNovoExame() {
  return {
    nome: "",
    tipo: "laboratorial",
    data_solicitacao: "",
    laboratorio: "",
    observacoes: "",
    arquivo: null,
  };
}

export function listaClinica(lista = [], fallback = "") {
  if (Array.isArray(lista) && lista.length > 0) {
    return lista;
  }

  return (fallback || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function calcularIdade(dataNascimento) {
  if (!dataNascimento) return null;

  const hoje = new Date();
  const nascimento = new Date(dataNascimento);
  const anos = hoje.getFullYear() - nascimento.getFullYear();
  const meses = hoje.getMonth() - nascimento.getMonth();

  if (anos === 0) {
    return `${meses} ${meses === 1 ? "mÃªs" : "meses"}`;
  }
  if (meses < 0) {
    return `${anos - 1} anos e ${12 + meses} meses`;
  }
  if (meses === 0) {
    return `${anos} ${anos === 1 ? "ano" : "anos"}`;
  }
  return `${anos} anos e ${meses} ${meses === 1 ? "mÃªs" : "meses"}`;
}

export function formatarData(data) {
  if (!data) return "-";
  return new Date(data).toLocaleDateString("pt-BR");
}

export function formatarDataHora(data) {
  if (!data) return "-";
  return new Date(data).toLocaleString("pt-BR");
}

export function normalizeItemsPayload(data) {
  return Array.isArray(data) ? data : (data?.items ?? []);
}

export function ordenarVacinasPorData(lista) {
  return [...lista].sort((a, b) => {
    const da = new Date(a.data_aplicacao || 0).getTime();
    const db = new Date(b.data_aplicacao || 0).getTime();
    return db - da;
  });
}

export function ordenarConsultasPorData(lista) {
  return [...lista].sort((a, b) => {
    const da = new Date(a.inicio_atendimento || a.created_at || 0).getTime();
    const db = new Date(b.inicio_atendimento || b.created_at || 0).getTime();
    return db - da;
  });
}

export function selecionarUltimaAlta(historico) {
  const altas = historico.filter((item) => item?.data_saida);
  return [...altas].sort((a, b) => {
    const da = new Date(a.data_saida || 0).getTime();
    const db = new Date(b.data_saida || 0).getTime();
    return db - da;
  })[0];
}

export function filtrarVacinas(historicoVacinas, filtroVacinas) {
  const termo = filtroVacinas.trim().toLowerCase();
  if (!termo) return historicoVacinas;

  return historicoVacinas.filter((vacina) => {
    const texto = [
      vacina?.nome_vacina,
      vacina?.fabricante,
      vacina?.lote,
      vacina?.veterinario_responsavel,
      vacina?.veterinario_nome,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return texto.includes(termo);
  });
}

export function filtrarConsultas(historicoConsultas, filtroConsultas) {
  const termo = filtroConsultas.trim().toLowerCase();
  if (!termo) return historicoConsultas;

  return historicoConsultas.filter((consulta) => {
    const texto = [
      consulta?.queixa_principal,
      consulta?.motivo_consulta,
      consulta?.diagnostico,
      consulta?.veterinario_nome,
      consulta?.status,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return texto.includes(termo);
  });
}
