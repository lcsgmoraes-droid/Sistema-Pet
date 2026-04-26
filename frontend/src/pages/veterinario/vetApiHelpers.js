export function uploadArquivoExameApi(api, base, id, file) {
  const formData = new FormData();
  formData.append("arquivo", file);
  return api.post(`${base}/exames/${id}/arquivo`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export async function historicoInternacoesPetApi(api, base, petId) {
  const baseResponse = await api.get(`${base}/internacoes`, {
    params: {
      status: "",
      pet_id: petId,
    },
  });

  const lista = Array.isArray(baseResponse.data)
    ? baseResponse.data
    : (baseResponse.data?.items ?? []);

  const historicoDetalhado = await Promise.all(
    lista.map(async (internacao) => {
      try {
        const detalhe = await api.get(`${base}/internacoes/${internacao.id}`);
        return {
          internacao_id: internacao.id,
          status: detalhe.data?.status ?? internacao.status,
          motivo: detalhe.data?.motivo ?? internacao.motivo,
          box: detalhe.data?.box ?? internacao.box,
          data_entrada: detalhe.data?.data_entrada ?? internacao.data_entrada,
          data_saida: detalhe.data?.data_saida ?? internacao.data_saida,
          observacoes_alta: detalhe.data?.observacoes_alta ?? internacao.observacoes_alta,
          evolucoes: detalhe.data?.evolucoes ?? [],
          procedimentos: detalhe.data?.procedimentos ?? [],
        };
      } catch {
        return {
          internacao_id: internacao.id,
          status: internacao.status,
          motivo: internacao.motivo,
          box: internacao.box,
          data_entrada: internacao.data_entrada,
          data_saida: internacao.data_saida,
          observacoes_alta: internacao.observacoes_alta,
          evolucoes: [],
          procedimentos: [],
        };
      }
    })
  );

  return {
    ...baseResponse,
    data: {
      pet_id: petId,
      historico: historicoDetalhado,
    },
  };
}
