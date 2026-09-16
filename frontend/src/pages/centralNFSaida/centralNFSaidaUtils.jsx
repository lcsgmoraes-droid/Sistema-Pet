import { AlertCircle, CheckCircle, FileText, X } from "lucide-react";

export const SITUACOES_NF_SAIDA = [
  { value: "", label: "Todas" },
  { value: "Autorizada", label: "Autorizada" },
  { value: "Emitida DANFE", label: "Emitida DANFE" },
  { value: "Cancelada", label: "Cancelada" },
  { value: "Pendente", label: "Pendente" },
];

export function formatarChave(valor) {
  return valor.replaceAll(/\D/g, "").slice(0, 44);
}

export function tratarColagemChave(event, setChave) {
  event.preventDefault();
  const texto = event.clipboardData?.getData("text") || "";
  setChave(formatarChave(texto));
}

export function formatarDataHora(valor) {
  if (!valor) return "-";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "-";
  return data.toLocaleString("pt-BR");
}

export function soDigitos(valor) {
  return String(valor || "").replaceAll(/\D/g, "");
}

export function getSituacaoCor(status) {
  switch (status?.toLowerCase()) {
    case "autorizada":
    case "emitida danfe":
      return "bg-green-100 text-green-800";
    case "cancelada":
      return "bg-red-100 text-red-800";
    case "pendente":
      return "bg-yellow-100 text-yellow-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

export function getSituacaoIcone(status) {
  switch (status?.toLowerCase()) {
    case "autorizada":
    case "emitida danfe":
      return <CheckCircle className="w-4 h-4" />;
    case "cancelada":
      return <X className="w-4 h-4" />;
    case "pendente":
      return <AlertCircle className="w-4 h-4" />;
    default:
      return <FileText className="w-4 h-4" />;
  }
}

export function formatarDataBR(valor) {
  if (!valor) return "-";
  if (typeof valor === "string" && /^\d{4}-\d{2}-\d{2}$/.test(valor)) {
    const [ano, mes, dia] = valor.split("-");
    return `${dia}/${mes}/${ano}`;
  }
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleDateString("pt-BR");
}

export function formatarValorDetalhe(valor) {
  if (valor === 0) return "0";
  if (valor === false) return "Não";
  if (valor === true) return "Sim";
  if (!valor) return "-";
  if (Array.isArray(valor)) {
    const partes = valor
      .map((item) => formatarValorDetalhe(item))
      .filter((item) => item && item !== "-");
    return partes.length ? partes.join(", ") : "-";
  }
  if (typeof valor === "object") {
    return (
      valor.nome ||
      valor.descricao ||
      valor.label ||
      valor.endereco ||
      valor.logradouro ||
      valor.identificacao ||
      "-"
    );
  }
  return String(valor);
}

export function valorBooleanoLabel(valor) {
  if (valor === true) return "Sim";
  if (valor === false) return "Não";
  return "-";
}

export function identificadorDocumentoFiscal(nota) {
  return nota.provedor === "intnfe" ? nota.venda_id : nota.id;
}

export function rotaDocumentoFiscal(nota, tipo) {
  return nota.provedor === "intnfe"
    ? `/nfe/vendas/${nota.venda_id}/${tipo}`
    : `/nfe/${nota.id}/${tipo}`;
}

export function mesclarStatusIntNFe(nota, status) {
  return {
    ...nota,
    status: status.situacao || nota.status,
    numero: status.numero || nota.numero,
    serie: status.serie ?? nota.serie,
    chave: status.chave_acesso || nota.chave,
    protocolo: status.protocolo || nota.protocolo,
    codigo_erro: status.codigo_erro || nota.codigo_erro,
    motivo_rejeicao: status.motivo_rejeicao || nota.motivo_rejeicao,
    ambiente_codigo: status.ambiente_codigo ?? nota.ambiente_codigo,
  };
}

export function montarDetalheFallback(nota) {
  return {
    id: nota.id,
    numero: nota.numero,
    serie: nota.serie,
    modelo: nota.modelo,
    tipo: nota.tipo,
    tipo_label: nota.tipo === "nfce" ? "NFC-e" : "NF-e",
    chave: nota.chave,
    status: nota.status,
    provedor: nota.provedor,
    correlation_id: nota.correlation_id,
    codigo_erro: nota.codigo_erro,
    motivo_rejeicao: nota.motivo_rejeicao,
    protocolo: nota.protocolo,
    ambiente_codigo: nota.ambiente_codigo,
    data_emissao: nota.data_emissao,
    cliente: {
      nome: nota.cliente?.nome,
      cpf_cnpj: nota.cliente?.cpf_cnpj,
    },
    totais: {
      valor_total: nota.valor,
    },
    canal: nota.canal,
    canal_label: nota.canal_label,
    loja: nota.loja,
    unidade_negocio: nota.unidade_negocio,
    informacoes_adicionais: {
      numero_pedido_loja: nota.numero_pedido_loja,
      numero_loja_virtual: nota.numero_loja_virtual,
      origem_loja_virtual: nota.origem_loja_virtual,
      origem_canal_venda: nota.origem_canal_venda,
    },
    itens: [],
    pagamento: { parcelas: [] },
    transporte: {},
    endereco_entrega: {},
    intermediador: {},
  };
}

export async function carregarDetalheIntNFe(api, nota) {
  const [statusResult, detalheResult] = await Promise.allSettled([
    api.get(`/nfe/vendas/${nota.venda_id}/status`),
    api.get(`/nfe/vendas/${nota.venda_id}/detalhes`),
  ]);
  const status = statusResult.status === "fulfilled" ? statusResult.value.data : {};
  const notaAtualizada = mesclarStatusIntNFe(nota, status);
  const detalheLocal =
    detalheResult.status === "fulfilled"
      ? detalheResult.value.data
      : montarDetalheFallback(notaAtualizada);

  let aviso = "";
  if (statusResult.status === "rejected" && detalheResult.status === "rejected") {
    aviso = "Não foi possível carregar os detalhes desta nota.";
  } else if (statusResult.status === "rejected") {
    aviso = "Os dados da venda foram carregados, mas o status da IntNFe não atualizou.";
  } else if (detalheResult.status === "rejected") {
    aviso = "O status foi atualizado, mas os dados completos da venda não carregaram.";
  }

  return {
    nota: notaAtualizada,
    detalhe: {
      ...detalheLocal,
      codigo_erro: status.codigo_erro || detalheLocal.codigo_erro,
      motivo_rejeicao: status.motivo_rejeicao || detalheLocal.motivo_rejeicao,
    },
    aviso,
  };
}
