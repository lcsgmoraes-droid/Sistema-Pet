export function pixDoAlerta(alerta) {
  return {
    id: alerta.pagamento_id,
    assinatura: alerta.assinatura,
    identificacao_pix: alerta.identificacao_pix || {
      estado: "nao_identificado",
      registro_id: alerta.registro_id,
      justificativa: alerta.justificativa || alerta.observacoes || "",
      usuario_nome: alerta.operador,
      data: alerta.data_identificacao || alerta.dataidentificacao || alerta.data,
      historico: alerta.historico || [],
    },
  };
}
